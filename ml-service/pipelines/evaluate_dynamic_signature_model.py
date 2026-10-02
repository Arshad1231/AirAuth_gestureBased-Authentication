"""
PIPELINE 4 — Evaluate and calibrate the dynamic-signature verifier (Step 2).

Uses the *real* signatures (research dataset + web-app exports) and the
exact production scoring code (verifier.component_scores + fuse).

Protocols
---------
  web_registration   enroll the first K signatures of a user's first
                     session (K = 8, what the web app collects); probe
                     with all later sessions.  Impostors = other users'
                     later-session signatures claiming this user.
  multi_session      enroll two full sessions, probe the third
                     (rotated over all folds) — equals a user whose
                     template has grown through adaptation.

Outputs
-------
  models/dynamic_signature_calibration.json   threshold + priors (+ weights)
  reports/dynamic_signature_evaluation.json   all metrics
  reports/dynamic_signature_evaluation.md     human-readable tables

Usage (from ml-service/):
    python -m pipelines.evaluate_dynamic_signature_model
    python -m pipelines.evaluate_dynamic_signature_model --target-far 0.05 --enroll 8
"""

import argparse
import itertools

import numpy as np

from airauth import config
from airauth.common import metrics
from airauth.common.errors import BiometricInputError
from airauth.common.model_registry import dynamic_signature_model
from airauth.data.dataset_loader import load_collected_samples, load_research_signatures
from airauth.dynamic_signature import features
from airauth.dynamic_signature.preprocessing import preprocess_signature
from airauth.dynamic_signature.verifier import component_scores
from airauth.common import score_fusion
from pipelines import pipeline_utils as utils

COMPONENTS = ["dtw", "embedding", "global"]


def load_processed(log):

    records = load_research_signatures() + load_collected_samples("dynamic")
    processed = []

    for record in records:
        try:
            item = preprocess_signature(record["sample"])
        except BiometricInputError as error:
            log.warning("Skipping %s/%s/%s: %s", record["user_id"], record.get("session_id"),
                        record.get("sample_id"), error.message)
            continue
        processed.append(
            {
                "user_id": record["user_id"],
                "session_id": record.get("session_id", "S01"),
                "sample_id": record.get("sample_id", ""),
                "xy": item.xy,
                "global": features.global_features(item),
            }
        )

    return processed


def protocol_folds(processed, protocol, enroll_count):
    """Yield (claimed_user, enrollment_items, probe_items)."""

    users = sorted({p["user_id"] for p in processed})

    for user in users:
        own = sorted((p for p in processed if p["user_id"] == user),
                     key=lambda p: (p["session_id"], p["sample_id"]))
        sessions = sorted({p["session_id"] for p in own})

        if protocol == "web_registration":
            first = [p for p in own if p["session_id"] == sessions[0]][:enroll_count]
            later_sessions = set(sessions[1:])
            probe_sessions = later_sessions or {sessions[0]}
            enrollment_ids = {id(p) for p in first}
            probes = [p for p in processed
                      if p["session_id"] in probe_sessions and id(p) not in enrollment_ids]
            yield user, first, probes

        elif protocol == "multi_session" and len(sessions) >= 3:
            for test_session in sessions:
                enroll = [p for p in own if p["session_id"] != test_session]
                probes = [p for p in processed if p["session_id"] == test_session]
                yield user, enroll, probes


def collect_trials(processed, protocol, enroll_count):

    trials = []

    for user, enroll, probes in protocol_folds(processed, protocol, enroll_count):

        enrolled_xy = [p["xy"] for p in enroll]
        enrolled_global = np.array([p["global"] for p in enroll])

        for probe in probes:
            raw, references, _ = component_scores(enrolled_xy, enrolled_global, probe["xy"], probe["global"])
            trials.append(
                {
                    "claimed_user": user,
                    "true_user": probe["user_id"],
                    "genuine": probe["user_id"] == user,
                    "raw": raw,
                    "references": references,
                }
            )

    return trials


def fused_scores(trials, weights, priors):
    calibration = {"fusion_weights": weights, "reference_priors": priors}
    from airauth.dynamic_signature.verifier import fuse_components
    return np.array([fuse_components(t["raw"], t["references"], calibration)[0] for t in trials])


def split(trials, scores):
    genuine = np.array([s for t, s in zip(trials, scores) if t["genuine"]])
    impostor = np.array([s for t, s in zip(trials, scores) if not t["genuine"]])
    return genuine, impostor


def estimate_priors(trials):
    """Population prior = median of per-user references (one per claim)."""

    priors = dict(config.DYNAMIC_REFERENCE_PRIORS)
    for name in COMPONENTS:
        values = [t["references"][name] for t in trials if name in t["references"]]
        if values:
            priors[name] = float(np.median(values))
    return priors


def component_report(trials):
    report = {}
    for name in COMPONENTS:
        usable = [t for t in trials if name in t["raw"]]
        if not usable:
            continue
        scores = np.array([t["raw"][name] for t in usable])
        genuine, impostor = split(usable, scores)
        if len(genuine) and len(impostor):
            report[name] = metrics.summarize(genuine, impostor)
    return report


def weight_grid(available):
    steps = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    for combo in itertools.product(steps, repeat=len(available)):
        if abs(sum(combo) - 1.0) < 1e-9:
            yield dict(zip(available, combo))


def write_markdown(path, payload):

    lines = [
        "# Dynamic signature verifier — evaluation",
        "",
        f"Generated: {payload['generated_at']}  ",
        f"Embedding model: {payload['embedding_model']}  ",
        f"Users: {payload['users']}, signatures: {payload['signatures']}",
        "",
        "Impostor trials are *random forgeries* (other users' own signatures).",
        "",
    ]

    for protocol, result in payload["protocols"].items():
        lines += [
            f"## Protocol: {protocol}",
            "",
            f"Genuine trials: {result['fused']['genuine_trials']}, "
            f"impostor trials: {result['fused']['impostor_trials']}",
            "",
            "| Score | EER | ROC-AUC | genuine mean | impostor mean |",
            "|---|---|---|---|---|",
        ]
        for name, summary in list(result["components"].items()) + [("**fused**", result["fused"])]:
            lines.append(
                f"| {name} | {summary['eer']:.3f} | {summary['roc_auc']:.3f} | "
                f"{summary['genuine_mean']:.4f} | {summary['impostor_mean']:.4f} |"
            )
        if "operating_far" in result["fused"]:
            lines += [
                "",
                f"At the calibrated threshold {result['fused']['operating_threshold']:.3f}: "
                f"FAR = {result['fused']['operating_far']:.3f}, "
                f"FRR = {result['fused']['operating_frr']:.3f}",
            ]
        lines.append("")

    calibration = payload["calibration"]
    lines += [
        "## Calibration written to models/",
        "",
        f"* threshold: **{calibration['threshold']:.4f}** ({calibration['threshold_policy']})",
        f"* fusion weights: {calibration['fusion_weights']}",
        f"* reference priors: { {k: round(v, 5) for k, v in calibration['reference_priors'].items()} }",
        "",
    ]

    if payload.get("weight_search"):
        lines += ["## Fusion-weight search (web_registration, informational)", "",
                  "| weights | EER | ROC-AUC |", "|---|---|---|"]
        for row in payload["weight_search"][:8]:
            lines.append(f"| {row['weights']} | {row['eer']:.3f} | {row['roc_auc']:.3f} |")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--enroll", type=int, default=config.DYNAMIC_RECOMMENDED_ENROLL_SAMPLES)
    parser.add_argument("--target-far", type=float, default=0.05,
                        help="threshold = loosest value whose FAR <= target (web_registration)")
    parser.add_argument("--apply-best-weights", action="store_true",
                        help="store the best grid-searched fusion weights in the calibration")
    args = parser.parse_args(argv)

    log = utils.setup_logging()

    processed = load_processed(log)
    users = sorted({p["user_id"] for p in processed})
    log.info("Loaded %d signatures from %d users", len(processed), len(users))

    if len(users) < 2:
        raise SystemExit("At least two users are needed to evaluate verification.")

    embedding_status = dynamic_signature_model.status()
    log.info("Embedding model: %s", embedding_status)

    weights = dict(config.DYNAMIC_FUSION_WEIGHTS)
    if not embedding_status["available"]:
        weights.pop("embedding", None)

    protocol_trials = {}
    for protocol in ("web_registration", "multi_session"):
        with utils.Timer() as timer:
            trials = collect_trials(processed, protocol, args.enroll)
        if trials:
            protocol_trials[protocol] = trials
            log.info("%s: %d trials (%.1fs)", protocol, len(trials), timer.seconds)

    calibration_trials = protocol_trials["web_registration"]
    priors = estimate_priors(calibration_trials)

    # Optional informational search for better fusion weights.
    available = [name for name in COMPONENTS if name in weights]
    search = []
    for candidate in weight_grid(available):
        genuine, impostor = split(calibration_trials, fused_scores(calibration_trials, candidate, priors))
        search.append({"weights": candidate, "eer": metrics.compute_eer(genuine, impostor)["eer"],
                       "roc_auc": metrics.roc_auc(genuine, impostor)})
    search.sort(key=lambda row: (row["eer"], -row["roc_auc"]))

    if args.apply_best_weights and search:
        weights = search[0]["weights"]
        log.info("Applying grid-searched weights %s", weights)

    genuine, impostor = split(calibration_trials, fused_scores(calibration_trials, weights, priors))
    operating = metrics.threshold_for_far(genuine, impostor, args.target_far)
    eer_point = metrics.compute_eer(genuine, impostor)

    # Never stricter than the EER point: with tiny impostor sets the
    # target-FAR threshold can collapse and reject most genuine users.
    threshold = max(operating["threshold"], eer_point["threshold"]) \
        if operating["frr"] > 0.5 else operating["threshold"]
    policy = f"FAR <= {args.target_far:.0%} on web_registration"
    if threshold != operating["threshold"]:
        policy = "EER point (target-FAR threshold rejected >50% of genuine users)"

    results = {}
    for protocol, trials in protocol_trials.items():
        genuine_p, impostor_p = split(trials, fused_scores(trials, weights, priors))
        results[protocol] = {
            "components": component_report(trials),
            "fused": metrics.summarize(genuine_p, impostor_p, threshold),
        }
        fused = results[protocol]["fused"]
        log.info("%-17s fused EER %.3f AUC %.3f | at threshold: FAR %.3f FRR %.3f",
                 protocol, fused["eer"], fused["roc_auc"], fused["operating_far"], fused["operating_frr"])

    calibration = {
        "threshold": float(threshold),
        "threshold_policy": policy,
        "fusion_weights": weights,
        "reference_priors": priors,
        "enroll_samples": args.enroll,
        "embedding_model": embedding_status["version"],
        "calibrated_at": utils.timestamp(),
        "source": "pipelines/evaluate_dynamic_signature_model.py",
    }
    utils.write_json(config.DYNAMIC_CALIBRATION_PATH, calibration)

    payload = {
        "generated_at": utils.timestamp(),
        "embedding_model": embedding_status["version"],
        "users": len(users),
        "signatures": len(processed),
        "protocols": results,
        "calibration": calibration,
        "weight_search": search[:20],
    }
    utils.write_json(config.REPORTS_DIR / "dynamic_signature_evaluation.json", payload)
    write_markdown(config.REPORTS_DIR / "dynamic_signature_evaluation.md", payload)

    log.info("Calibration saved: threshold %.4f (%s)", threshold, policy)


if __name__ == "__main__":
    main()


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# evaluate_dynamic_signature_model.py measures how well Step 2 separates
# genuine users from impostors on real recorded signatures, using exactly
# the production scoring code.  It runs two protocols (single-session web
# registration with K samples, and multi-session enrollment), reports EER /
# ROC-AUC per component (DTW, embedding, global) and fused, estimates the
# population reference priors, optionally grid-searches fusion weights, and
# writes the live calibration (threshold at a target FAR, priors, weights)
# to models/dynamic_signature_calibration.json plus JSON/Markdown reports.
# =============================================================================
