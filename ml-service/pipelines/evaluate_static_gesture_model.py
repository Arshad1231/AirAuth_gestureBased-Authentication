"""
PIPELINE 3 — Evaluate and calibrate the static-gesture verifier (Step 1).

Simulated users (synthetic, held-out pose classes never seen in training):
    each user = own hand geometry + own secret gesture + habitual wrist angle
    enrollment: 5 captures, genuine probes: 4 captures (10 frames each)

Attackers:
    random_impostor    another person showing *their own* gesture
    shoulder_surfer    another person who saw and copies the exact gesture

If real gesture captures from >= 2 users exist in data/collected/static
(exported from MongoDB), they are evaluated too and used for calibration.

Outputs:
    models/static_gesture_calibration.json
    reports/static_gesture_evaluation.json / .md

Usage (from ml-service/):
    python -m pipelines.evaluate_static_gesture_model
    python -m pipelines.evaluate_static_gesture_model --users 200 --target-far 0.01
"""

import argparse

import numpy as np

from airauth import config
from airauth.common import metrics
from airauth.common.errors import BiometricInputError
from airauth.common.model_registry import static_gesture_model
from airauth.data.dataset_loader import group_by_user, load_collected_samples
from airauth.static_gesture.synthetic_hand import SyntheticHandGenerator
from airauth.static_gesture.verifier import component_scores, extract, fuse_components
from pipelines import pipeline_utils as utils
from pipelines.train_static_gesture_model import split_pose_classes

ENROLL_CAPTURES = 5
GENUINE_CAPTURES = 4
SURFER_CAPTURES = 2
FRAMES_PER_CAPTURE = 10


def to_sample(frames):
    return {
        "frames": [{"landmarks": frame.tolist(), "handedness": "Right"} for frame in frames],
        "width": 1,
        "height": 1,
    }


def capture(generator, pose, person, base_orientation, spread=(8.0, 8.0, 8.0)):
    frames = generator.render(
        pose, person, generator.make_orientation(base_orientation, spread),
        n_frames=FRAMES_PER_CAPTURE,
    )
    vector, _, _ = extract(to_sample(frames))
    return vector


def simulate_users(count, seed, log):

    _, held_out = split_pose_classes(seed)
    generator = SyntheticHandGenerator(seed + 1000)
    rng = np.random.default_rng(seed)

    users = []
    for index in range(count):
        combination = held_out[rng.integers(len(held_out))]
        pose = generator.make_pose_class(combination)
        person = generator.make_person()
        base = generator.make_orientation(spread_deg=(25.0, 20.0, 25.0))

        users.append(
            {
                "pose": pose,
                "base": base,
                "enroll": np.stack([capture(generator, pose, person, base) for _ in range(ENROLL_CAPTURES)]),
                "genuine": [capture(generator, pose, person, base) for _ in range(GENUINE_CAPTURES)],
                "surfer": [
                    capture(generator, pose, generator.make_person(), base, spread=(12.0, 12.0, 12.0))
                    for _ in range(SURFER_CAPTURES)
                ],
            }
        )

    log.info("Simulated %d users", len(users))
    return users


def synthetic_trials(users, impostors_per_user, seed):

    rng = np.random.default_rng(seed)
    trials = []

    for index, user in enumerate(users):

        def add(probe, kind):
            raw, references = component_scores(user["enroll"], probe)
            trials.append({"kind": kind, "raw": raw, "references": references})

        for probe in user["genuine"]:
            add(probe, "genuine")

        for probe in user["surfer"]:
            add(probe, "shoulder_surfer")

        others = rng.choice([i for i in range(len(users)) if i != index],
                            size=min(impostors_per_user, len(users) - 1), replace=False)
        for other in others:
            add(users[other]["genuine"][0], "random_impostor")

    return trials


def real_trials(log):
    """Trials from real captures exported by the web app (if any)."""

    by_user = group_by_user(load_collected_samples("static"))
    vectors = {}

    for user_id, records in by_user.items():
        extracted = []
        for record in records:
            try:
                extracted.append(extract(record["sample"])[0])
            except BiometricInputError:
                continue
        if len(extracted) > ENROLL_CAPTURES:
            vectors[user_id] = np.stack(extracted)

    if len(vectors) < 2:
        log.info("Real static data: not enough users (%d) — synthetic only", len(vectors))
        return []

    trials = []
    for user_id, own in vectors.items():
        enroll, genuine = own[:ENROLL_CAPTURES], own[ENROLL_CAPTURES:]
        for probe in genuine:
            raw, references = component_scores(enroll, probe)
            trials.append({"kind": "genuine", "raw": raw, "references": references})
        for other_id, other in vectors.items():
            if other_id != user_id:
                for probe in other[ENROLL_CAPTURES:]:
                    raw, references = component_scores(enroll, probe)
                    trials.append({"kind": "random_impostor", "raw": raw, "references": references})

    log.info("Real static data: %d trials from %d users", len(trials), len(vectors))
    return trials


def scores_for(trials, calibration):
    return np.array([fuse_components(t["raw"], t["references"], calibration)[0] for t in trials])


def by_kind(trials, scores, kind):
    return np.array([s for t, s in zip(trials, scores) if t["kind"] == kind])


def estimate_priors(trials):
    priors = dict(config.STATIC_REFERENCE_PRIORS)
    for name in priors:
        values = [t["references"][name] for t in trials if name in t["references"]]
        if values:
            priors[name] = float(np.median(values))
    return priors


def evaluate(trials, calibration, threshold=None):

    scores = scores_for(trials, calibration)
    genuine = by_kind(trials, scores, "genuine")
    report = {}

    for kind in ("random_impostor", "shoulder_surfer"):
        impostor = by_kind(trials, scores, kind)
        if len(impostor):
            report[kind] = metrics.summarize(genuine, impostor, threshold)

    for name in ("template", "embedding"):
        usable = [t for t in trials if name in t["raw"]]
        if usable:
            raw = np.array([t["raw"][name] for t in usable])
            g, i = by_kind(usable, raw, "genuine"), by_kind(usable, raw, "random_impostor")
            report[f"component_{name}"] = metrics.summarize(g, i)

    return report, genuine, by_kind(trials, scores, "random_impostor")


def write_markdown(path, payload):

    lines = [
        "# Static gesture verifier — evaluation",
        "",
        f"Generated: {payload['generated_at']}  ",
        f"Embedding model: {payload['embedding_model']}  ",
        f"Calibration source: {payload['calibration']['data_source']}",
        "",
    ]

    for dataset, report in payload["results"].items():
        lines += [f"## {dataset}", "", "| comparison | EER | ROC-AUC | FAR @thr | FRR @thr |", "|---|---|---|---|---|"]
        for name, summary in report.items():
            far = f"{summary['operating_far']:.3f}" if "operating_far" in summary else "-"
            frr = f"{summary['operating_frr']:.3f}" if "operating_frr" in summary else "-"
            lines.append(f"| {name} | {summary['eer']:.3f} | {summary['roc_auc']:.3f} | {far} | {frr} |")
        lines.append("")

    calibration = payload["calibration"]
    lines += [
        "## Calibration written to models/",
        "",
        f"* threshold: **{calibration['threshold']:.4f}** ({calibration['threshold_policy']})",
        f"* fusion weights: {calibration['fusion_weights']}",
        f"* reference priors: { {k: round(v, 5) for k, v in calibration['reference_priors'].items()} }",
        "",
        "Note: a shoulder-surfer who copies the exact gesture is only partly",
        "stopped by Step 1 (hand-geometry features).  This is by design — the",
        "static gesture is the *knowledge* factor; Step 2 (the air signature) is",
        "the behavioural biometric that stops copy attacks.",
        "",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--users", type=int, default=150)
    parser.add_argument("--impostors-per-user", type=int, default=12)
    parser.add_argument("--target-far", type=float, default=0.01)
    parser.add_argument("--target-frr", type=float, default=0.01)
    parser.add_argument("--genuine-margin", type=float, default=1.25)
    parser.add_argument("--seed", type=int, default=7, help="must match the training seed (held-out split)")
    args = parser.parse_args(argv)

    log = utils.setup_logging()

    status = static_gesture_model.status()
    log.info("Embedding model: %s", status)

    weights = dict(config.STATIC_FUSION_WEIGHTS)
    if not status["available"]:
        weights.pop("embedding", None)

    with utils.Timer() as timer:
        users = simulate_users(args.users, args.seed, log)
        synthetic = synthetic_trials(users, args.impostors_per_user, args.seed)
    log.info("Synthetic trials: %d (%.1fs)", len(synthetic), timer.seconds)

    real = real_trials(log)
    calibration_trials = real if real else synthetic
    source = "real web-app captures" if real else "synthetic held-out gestures"

    calibration = {"fusion_weights": weights, "reference_priors": estimate_priors(calibration_trials)}

    _, genuine, impostor = evaluate(calibration_trials, calibration)

    # Anchor the threshold on genuine variation (accept 99 % of genuine
    # attempts, plus a safety margin because real users vary more than
    # simulated ones) and never let it become looser than the target-FAR
    # bound.  Using the FAR bound alone would be far too permissive when
    # impostors are well separated, as they are in synthetic data.
    far_bound = metrics.threshold_for_far(genuine, impostor, args.target_far)["threshold"]
    genuine_bound = args.genuine_margin * metrics.threshold_for_frr(genuine, args.target_frr)
    threshold = min(far_bound, genuine_bound)
    policy = (
        f"min(FAR <= {args.target_far:.1%} bound, {args.genuine_margin} x genuine "
        f"{1 - args.target_frr:.0%} quantile)"
    )

    results = {"synthetic": evaluate(synthetic, calibration, threshold)[0]}
    if real:
        results["real"] = evaluate(real, calibration, threshold)[0]

    for dataset, report in results.items():
        for name, summary in report.items():
            extra = ""
            if "operating_far" in summary:
                extra = f" | FAR {summary['operating_far']:.3f} FRR {summary['operating_frr']:.3f}"
            log.info("%-9s %-22s EER %.3f AUC %.3f%s", dataset, name, summary["eer"], summary["roc_auc"], extra)

    calibration.update(
        {
            "threshold": float(threshold),
            "threshold_policy": policy,
            "far_bound": float(far_bound),
            "genuine_bound": float(genuine_bound),
            "data_source": source,
            "embedding_model": status["version"],
            "calibrated_at": utils.timestamp(),
            "source": "pipelines/evaluate_static_gesture_model.py",
        }
    )
    utils.write_json(config.STATIC_CALIBRATION_PATH, calibration)

    payload = {
        "generated_at": utils.timestamp(),
        "embedding_model": status["version"],
        "results": results,
        "calibration": calibration,
    }
    utils.write_json(config.REPORTS_DIR / "static_gesture_evaluation.json", payload)
    write_markdown(config.REPORTS_DIR / "static_gesture_evaluation.md", payload)

    log.info("Calibration saved: threshold %.4f (%s)", threshold, source)


if __name__ == "__main__":
    main()


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# evaluate_static_gesture_model.py measures Step 1 with the production
# scoring code.  It simulates users who each pick a gesture from the pose
# classes held out of training, enrolls 5 captures, and scores genuine
# repeats, random impostors (other people, other gestures) and shoulder-
# surfers (other people copying the exact gesture).  It reports EER/ROC-AUC
# per attacker type and per component, estimates reference priors, picks the
# threshold as the stricter of (a) the target-FAR bound against random
# impostors and (b) 1.25 x the 99th percentile of genuine scores (preferring
# real exported captures when at least two users exist) and writes
# models/static_gesture_calibration.json plus JSON/Markdown reports.
# =============================================================================
