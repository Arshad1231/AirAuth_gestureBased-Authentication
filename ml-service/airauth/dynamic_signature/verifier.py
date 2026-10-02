"""
Enrollment and verification for Step 2 — the dynamic air signature.

Template (stored by the Node backend in MongoDB, opaque to it):
    {
      "modality": "dynamic_signature",
      "feature_version": "dynamic-v1",
      "trajectories": [[[x, y] * 128] * N],   normalised xy sequences
      "durations":    [seconds * N],
      "global_features": [[12 floats] * N]
    }

Verification components (all normalised by the user's own leave-one-out
variation, then fused):

    dtw        elastic shape+timing distance to the closest enrollment
               signatures (Sakoe-Chiba DTW on xy)
    embedding  cosine distance in the neural embedding space
               (Conv1D + BiGRU + attention network)
    global     z-score distance of behavioural statistics
               (duration, speed profile, pauses, reversals ...)
"""

import numpy as np

from airauth import config
from airauth.common import score_fusion
from airauth.common.errors import BiometricInputError
from airauth.common.model_registry import dynamic_signature_model
from airauth.dynamic_signature import features
from airauth.dynamic_signature.dtw import dtw_one_to_many, pairwise_dtw
from airauth.dynamic_signature.preprocessing import preprocess_signature

# A sample is rejected at enrollment when its mean DTW distance to the other
# samples exceeds this multiple of the median.  On the research dataset the
# worst *genuine* sample in an 8-sample enrollment reached 3.54x, so the
# check is only a safety net for botched captures (tracking failure, a
# half-drawn signature) — not an impostor detector.
ENROLL_CONSISTENCY_LIMIT = 4.0

# Distance to the single closest enrollment signature.  Compared on the
# research dataset against mean-of-3-nearest and mean-of-all, "min" had the
# lowest EER in every protocol (see docs / evaluation report).
DTW_NEAREST_K = 1


def _nearest_mean(distances, k=DTW_NEAREST_K):
    distances = np.sort(np.asarray(distances, dtype=float))
    return float(distances[: max(1, min(k, len(distances)))].mean())


def _quality(processed):
    return {
        "points": processed.raw_point_count,
        "duration": round(processed.duration, 3),
        "corrected_spikes": processed.corrected_spikes,
    }


# ---------------------------------------------------------------------------
# ENROLLMENT
# ---------------------------------------------------------------------------

def enroll(samples):

    if len(samples) < config.DYNAMIC_MIN_ENROLL_SAMPLES:
        raise BiometricInputError(
            f"At least {config.DYNAMIC_MIN_ENROLL_SAMPLES} signature samples are required.",
            code="not_enough_samples",
        )

    processed = []
    for index, sample in enumerate(samples):
        try:
            processed.append(preprocess_signature(sample))
        except BiometricInputError as error:
            error.details["sample_index"] = index
            raise

    trajectories = [p.xy for p in processed]
    matrix = pairwise_dtw(trajectories)
    n = len(processed)

    mean_to_others = matrix.sum(axis=1) / (n - 1)
    typical = float(np.median(mean_to_others))
    worst = int(np.argmax(mean_to_others))

    if typical > 0 and mean_to_others[worst] > ENROLL_CONSISTENCY_LIMIT * typical:
        raise BiometricInputError(
            f"Signature sample {worst + 1} looks different from the others. "
            "Please redraw it the way you normally sign.",
            code="inconsistent_enrollment",
            details={
                "sample_index": worst,
                "consistency": (mean_to_others / typical).round(3).tolist(),
            },
        )

    template = {
        "modality": "dynamic_signature",
        "feature_version": config.DYNAMIC_FEATURE_VERSION,
        "enrolled_count": n,
        "trajectories": [p.xy.round(5).tolist() for p in processed],
        "durations": [round(p.duration, 4) for p in processed],
        "global_features": [features.global_features(p).round(6).tolist() for p in processed],
    }

    report = {
        "samples": n,
        "mean_duration": round(float(np.mean([p.duration for p in processed])), 3),
        "consistency": (mean_to_others / max(typical, 1e-9)).round(3).tolist(),
        "quality": [_quality(p) for p in processed],
    }

    return template, report


# ---------------------------------------------------------------------------
# VERIFICATION
# ---------------------------------------------------------------------------

def _embed(trajectories):
    batch = np.stack([features.sequence_features(xy) for xy in trajectories])
    return dynamic_signature_model.embed(batch)


def component_scores(enrolled_xy, enrolled_global, probe_xy, probe_global):
    """Raw distances and per-user references.  Shared with the evaluator."""

    n = len(enrolled_xy)
    raw, references = {}, {}

    # --- DTW --------------------------------------------------------------
    probe_to_enrolled = dtw_one_to_many(probe_xy, enrolled_xy).tolist()
    raw["dtw"] = _nearest_mean(probe_to_enrolled)

    matrix = pairwise_dtw(enrolled_xy)
    references["dtw"] = float(
        np.mean([_nearest_mean(np.delete(matrix[i], i)) for i in range(n)])
    )

    # --- global behavioural statistics -----------------------------------
    raw["global"] = features.global_distance(probe_global, enrolled_global)
    references["global"] = float(
        np.mean(
            [
                features.global_distance(enrolled_global[i], np.delete(enrolled_global, i, axis=0))
                for i in range(n)
            ]
        )
    )

    # --- neural embedding -------------------------------------------------
    embeddings = _embed(list(enrolled_xy) + [probe_xy])

    if embeddings is not None:
        enrolled_emb, probe_emb = embeddings[:-1], embeddings[-1]

        def cosine_distance(vector, group):
            centroid = group.mean(axis=0)
            centroid /= np.linalg.norm(centroid) + 1e-12
            return float(1.0 - np.dot(vector, centroid))

        raw["embedding"] = cosine_distance(probe_emb, enrolled_emb)
        references["embedding"] = float(
            np.mean(
                [
                    cosine_distance(enrolled_emb[i], np.delete(enrolled_emb, i, axis=0))
                    for i in range(n)
                ]
            )
        )

    return raw, references, probe_to_enrolled


def verify(template, sample):

    if template.get("feature_version") != config.DYNAMIC_FEATURE_VERSION:
        raise BiometricInputError(
            "The stored signature profile was created with an older version. "
            "Please re-register.",
            code="template_version_mismatch",
        )

    calibration = config.load_dynamic_calibration()
    threshold = float(calibration["threshold"])

    processed = preprocess_signature(sample)

    enrolled_xy = [np.asarray(xy, dtype=float) for xy in template["trajectories"]]
    enrolled_global = np.asarray(template["global_features"], dtype=float)

    raw, references, probe_to_enrolled = component_scores(
        enrolled_xy, enrolled_global, processed.xy, features.global_features(processed)
    )

    result = {
        "step": "dynamic_signature",
        "threshold": threshold,
        "model_version": dynamic_signature_model.version
        if dynamic_signature_model.available else None,
        "quality": _quality(processed),
    }

    # Humans never reproduce a trajectory exactly; a near-perfect copy of a
    # stored enrollment sample indicates replayed data.
    replay_limit = config.REPLAY_SIMILARITY_RATIO * max(
        references["dtw"], config.DYNAMIC_REFERENCE_FLOORS["dtw"]
    )
    if min(probe_to_enrolled) < replay_limit:
        return {
            **result,
            "accepted": False,
            "score": None,
            "match_percent": 0.0,
            "components": {},
            "reason": "replay_suspected",
        }

    fused, normalised = fuse_components(raw, references, calibration)

    accepted = fused <= threshold

    template_update = None
    if accepted and fused <= config.DYNAMIC_ADAPTATION_MARGIN * threshold:
        template_update = adapt_template(template, processed)

    return {
        **result,
        "accepted": bool(accepted),
        "score": round(fused, 4),
        "match_percent": round(score_fusion.match_percentage(fused, threshold), 1),
        "components": {
            name: {
                "raw": round(raw[name], 5),
                "reference": round(references[name], 5),
                "normalised": round(normalised[name], 4),
            }
            for name in normalised
        },
        "reason": "match" if accepted else "signature_mismatch",
        "template_update": template_update,
    }


def fuse_components(raw, references, calibration):
    return score_fusion.fuse(
        raw,
        references,
        config.DYNAMIC_REFERENCE_FLOORS,
        calibration["fusion_weights"],
        priors=calibration.get("reference_priors", config.DYNAMIC_REFERENCE_PRIORS),
        blend=config.DYNAMIC_REFERENCE_BLEND,
    )


def adapt_template(template, processed):
    """
    Return a copy of the template with the accepted probe appended.

    The original enrollment samples are always kept; once the template is
    full, the oldest *adapted* sample is dropped.  This lets the profile
    absorb the user's natural session-to-session drift.
    """

    enrolled_count = int(template.get("enrolled_count", len(template["trajectories"])))

    updated = dict(template)
    trajectories = list(template["trajectories"]) + [processed.xy.round(5).tolist()]
    durations = list(template["durations"]) + [round(processed.duration, 4)]
    global_features = list(template["global_features"]) + [
        features.global_features(processed).round(6).tolist()
    ]

    while len(trajectories) > config.DYNAMIC_MAX_TEMPLATE_SAMPLES and len(trajectories) > enrolled_count:
        for series in (trajectories, durations, global_features):
            del series[enrolled_count]

    updated.update(
        {
            "enrolled_count": enrolled_count,
            "trajectories": trajectories,
            "durations": durations,
            "global_features": global_features,
        }
    )

    return updated


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# verifier.py implements Step 2 of the login: dynamic air-signature
# verification.
#   enroll(samples)   preprocesses every signature, rejects a sample whose
#                     DTW distance to the others is far above the user's
#                     typical variation, and returns a template holding the
#                     normalised trajectories, durations and global features.
#   component_scores  computes the three raw distances (DTW, global
#                     behaviour, neural embedding) and the matching
#                     leave-one-out references — also reused by the
#                     evaluation pipeline so offline metrics match live use.
#   verify(template, sample)
#                     blocks near-exact replays, fuses the normalised
#                     components and accepts when the fused score is at or
#                     below the calibrated threshold.  A confidently accepted
#                     login returns template_update (adapt_template) so the
#                     backend can grow the profile up to 20 signatures,
#                     always keeping the original enrollment samples.
# =============================================================================
