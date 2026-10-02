"""
Enrollment and verification for Step 1 — the static hand gesture.

Template (stored by the Node backend in MongoDB, opaque to it):
    {
      "modality": "static_gesture",
      "feature_version": "static-v1",
      "handedness": "Right",
      "feature_vectors": [[...115 floats...] * N]
    }

Verification components:
    template   group-scaled distance between the probe and the mean
               enrollment feature vector (all 7 feature groups)
    embedding  cosine distance between the probe embedding and the
               centroid of enrollment embeddings (neural model)

Both are normalised by the user's own leave-one-out variation and fused
(see airauth/common/score_fusion.py).
"""

import numpy as np

from airauth import config
from airauth.common import score_fusion
from airauth.common.errors import BiometricInputError
from airauth.common.model_registry import static_gesture_model
from airauth.static_gesture import features
from airauth.static_gesture.preprocessing import preprocess_static_sample

# A single enrollment sample this many "typical variations" away from the
# others is considered a different gesture and must be re-captured.
ENROLL_CONSISTENCY_LIMIT = 2.5


def _template_distance(vector_a, vector_b):
    return features.group_distance(
        vector_a, vector_b, config.STATIC_GROUP_SCALES, config.STATIC_GROUP_WEIGHTS
    )


def extract(sample):
    """Raw capture -> (feature vector, handedness, quality info)."""

    frames, handedness, drift = preprocess_static_sample(sample)
    vector, spread = features.extract_sample_features(frames)

    quality = {
        "frames": int(len(frames)),
        "hand_drift": round(drift, 4),
        "angle_jitter_deg": round(
            float(np.rad2deg(spread[features.GROUP_SLICES["joint_angles"]].mean())), 2
        ),
    }

    return vector, handedness, quality


# ---------------------------------------------------------------------------
# ENROLLMENT
# ---------------------------------------------------------------------------

def enroll(samples):

    if len(samples) < config.STATIC_MIN_ENROLL_SAMPLES:
        raise BiometricInputError(
            f"At least {config.STATIC_MIN_ENROLL_SAMPLES} gesture samples are required.",
            code="not_enough_samples",
        )

    vectors, hands, qualities = [], [], []

    for index, sample in enumerate(samples):
        try:
            vector, handedness, quality = extract(sample)
        except BiometricInputError as error:
            error.details["sample_index"] = index
            raise

        vectors.append(vector)
        hands.append(handedness)
        qualities.append(quality)

    if len(set(hands)) > 1:
        raise BiometricInputError(
            "Please use the same hand for every gesture sample.",
            code="mixed_handedness",
            details={"handedness": hands},
        )

    vectors = np.stack(vectors)
    n = len(vectors)

    # Each sample vs. the mean of the others: catches a sample where the
    # user showed a different gesture by mistake.
    consistency = []
    for i in range(n):
        others = np.delete(vectors, i, axis=0).mean(axis=0)
        consistency.append(_template_distance(vectors[i], others))

    worst = int(np.argmax(consistency))
    if consistency[worst] > ENROLL_CONSISTENCY_LIMIT:
        raise BiometricInputError(
            f"Gesture sample {worst + 1} does not match the others. "
            "Show exactly the same gesture every time.",
            code="inconsistent_enrollment",
            details={"sample_index": worst, "consistency": [round(c, 3) for c in consistency]},
        )

    template = {
        "modality": "static_gesture",
        "feature_version": config.STATIC_FEATURE_VERSION,
        "handedness": hands[0],
        "feature_vectors": vectors.round(6).tolist(),
    }

    report = {
        "samples": n,
        "handedness": hands[0],
        "consistency": [round(c, 3) for c in consistency],
        "quality": qualities,
    }

    return template, report


# ---------------------------------------------------------------------------
# VERIFICATION
# ---------------------------------------------------------------------------

def fuse_components(raw, references, calibration):
    return score_fusion.fuse(
        raw,
        references,
        config.STATIC_REFERENCE_FLOORS,
        calibration["fusion_weights"],
        priors=calibration.get("reference_priors", config.STATIC_REFERENCE_PRIORS),
        blend=config.STATIC_REFERENCE_BLEND,
    )


def component_scores(enrolled, probe):
    """Raw distances and leave-one-out references for every component."""

    n = len(enrolled)
    raw, references = {}, {}

    # --- template matcher --------------------------------------------------
    mean_vector = enrolled.mean(axis=0)
    raw["template"] = _template_distance(probe, mean_vector)
    references["template"] = float(
        np.mean(
            [
                _template_distance(enrolled[i], np.delete(enrolled, i, axis=0).mean(axis=0))
                for i in range(n)
            ]
        )
    )

    # --- neural embedding --------------------------------------------------
    embeddings = static_gesture_model.embed(
        features.pose_vector(np.vstack([enrolled, probe[None, :]]))
    )

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

    return raw, references


def verify(template, sample):

    if template.get("feature_version") != config.STATIC_FEATURE_VERSION:
        raise BiometricInputError(
            "The stored gesture profile was created with an older version. "
            "Please re-register.",
            code="template_version_mismatch",
        )

    calibration = config.load_static_calibration()
    threshold = float(calibration["threshold"])

    probe, handedness, quality = extract(sample)
    enrolled = np.asarray(template["feature_vectors"], dtype=float)

    base_result = {
        "step": "static_gesture",
        "threshold": threshold,
        "handedness": handedness,
        "expected_handedness": template["handedness"],
        "model_version": static_gesture_model.version
        if static_gesture_model.available else None,
        "quality": quality,
    }

    if config.STATIC_REQUIRE_SAME_HANDEDNESS and handedness != template["handedness"]:
        return {
            **base_result,
            "accepted": False,
            "score": None,
            "match_percent": 0.0,
            "components": {},
            "reason": "wrong_hand",
        }

    # An exact copy of a stored sample cannot come from a live hand.
    if np.min(np.max(np.abs(enrolled - probe), axis=1)) < 1e-6:
        return {
            **base_result,
            "accepted": False,
            "score": None,
            "match_percent": 0.0,
            "components": {},
            "reason": "replay_suspected",
        }

    raw, references = component_scores(enrolled, probe)

    fused, normalised = fuse_components(raw, references, calibration)

    accepted = fused <= threshold

    return {
        **base_result,
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
        "reason": "match" if accepted else "gesture_mismatch",
    }


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# verifier.py implements Step 1 of the login: static hand-gesture
# verification.
#   enroll(samples)  -> extracts the 115-dim key-point vector for each capture,
#                       enforces one hand and a consistent gesture across all
#                       samples, and returns the JSON template + a report.
#   verify(template, sample)
#                    -> rejects a wrong hand or an exact replay of a stored
#                       sample, then computes the template-matching distance
#                       and (if the model is trained) the neural embedding
#                       distance, normalises both by the user's own variation,
#                       fuses them and compares to the calibrated threshold.
# The returned dictionary (accepted, score, match_percent, components,
# reason) is passed straight through the API to the Node backend / UI.
# =============================================================================
