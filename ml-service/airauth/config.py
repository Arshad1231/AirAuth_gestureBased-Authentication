"""
Central configuration for the AirAuth ML service.

Every tunable constant used by preprocessing, feature extraction, model
training and verification lives here so that the pipelines and the API
always agree with each other.
"""

import json
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

SERVICE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SERVICE_ROOT.parent

MODELS_DIR = Path(os.getenv("AIRAUTH_MODELS_DIR", SERVICE_ROOT / "models"))
DATA_DIR = Path(os.getenv("AIRAUTH_DATA_DIR", SERVICE_ROOT / "data"))
REPORTS_DIR = Path(os.getenv("AIRAUTH_REPORTS_DIR", SERVICE_ROOT / "reports"))

# Samples exported from MongoDB by server/scripts/exportBiometricSamples.js
COLLECTED_DATA_DIR = DATA_DIR / "collected"

# Research dataset (3 users x 3 sessions x 10 air signatures) recorded with the
# original desktop collector; used to evaluate and calibrate Step 2.
RESEARCH_SIGNATURE_DATASET_DIR = Path(
    os.getenv(
        "AIRAUTH_RESEARCH_DATASET_DIR",
        DATA_DIR / "research_signatures",
    )
)

STATIC_MODEL_PATH = MODELS_DIR / "static_gesture_embedding.keras"
STATIC_MODEL_META_PATH = MODELS_DIR / "static_gesture_embedding.json"
STATIC_CALIBRATION_PATH = MODELS_DIR / "static_gesture_calibration.json"

DYNAMIC_MODEL_PATH = MODELS_DIR / "dynamic_signature_embedding.keras"
DYNAMIC_MODEL_META_PATH = MODELS_DIR / "dynamic_signature_embedding.json"
DYNAMIC_CALIBRATION_PATH = MODELS_DIR / "dynamic_signature_calibration.json"

# ---------------------------------------------------------------------------
# SERVICE
# ---------------------------------------------------------------------------

# Shared secret between the Express backend and this service.
SERVICE_API_KEY = os.getenv("ML_SERVICE_API_KEY", "dev-ml-service-key")

# Set to "0" to run without TensorFlow (template matchers only).
ENABLE_NEURAL_MODELS = os.getenv("AIRAUTH_ENABLE_NEURAL_MODELS", "1") == "1"

# ---------------------------------------------------------------------------
# STATIC GESTURE (STEP 1)
# ---------------------------------------------------------------------------

STATIC_FEATURE_VERSION = "static-v1"

STATIC_MIN_FRAMES = 5
STATIC_MIN_ENROLL_SAMPLES = 3
STATIC_MAX_HOLD_MOTION = 0.35          # palm-units of wrist drift allowed while holding
STATIC_REQUIRE_SAME_HANDEDNESS = True

# Expected natural variation of each feature group for a genuine repeat
# of the same gesture.  Used to turn raw differences into z-like scores.
STATIC_GROUP_SCALES = {
    "canonical_xy": 0.12,
    "canonical_z": 0.30,
    "joint_angles": 0.22,
    "tip_distances": 0.15,
    "abduction": 0.15,
    "orientation": 0.30,
    "hand_geometry": 0.10,
}

STATIC_GROUP_WEIGHTS = {
    "canonical_xy": 1.0,
    "canonical_z": 0.3,
    "joint_angles": 1.0,
    "tip_distances": 1.0,
    "abduction": 0.5,
    "orientation": 0.6,
    "hand_geometry": 0.4,
}

# Component weights for the fused static decision.
STATIC_FUSION_WEIGHTS = {"template": 0.6, "embedding": 0.4}

# Floors for the per-user reference distances (prevents an unusually
# consistent enrollment from producing an impossibly strict profile).
STATIC_REFERENCE_FLOORS = {"template": 0.35, "embedding": 0.01}

# Population priors the user reference is shrunk towards (see
# airauth/common/score_fusion.py).  Overwritten by calibration files.
STATIC_REFERENCE_PRIORS = {"template": 0.41, "embedding": 0.044}
STATIC_REFERENCE_BLEND = 0.5

# Defaults mirror the last calibration run; models/static_gesture_calibration.json
# overrides them whenever it exists.
STATIC_DEFAULT_THRESHOLD = 3.4

# ---------------------------------------------------------------------------
# DYNAMIC SIGNATURE (STEP 2)
# ---------------------------------------------------------------------------

DYNAMIC_FEATURE_VERSION = "dynamic-v1"

SEQUENCE_LENGTH = 128
DYNAMIC_MIN_POINTS = 20
DYNAMIC_MIN_DURATION = 0.5             # seconds
DYNAMIC_MAX_DURATION = 15.0            # seconds
DYNAMIC_MIN_ENROLL_SAMPLES = 3
DYNAMIC_SPIKE_MAD_MULTIPLIER = 6.0
DYNAMIC_SPIKE_REVERSAL_RATIO = 0.5
DTW_BAND_RATIO = 0.15                  # Sakoe-Chiba band as fraction of length

DYNAMIC_FUSION_WEIGHTS = {"dtw": 0.45, "embedding": 0.35, "global": 0.20}
DYNAMIC_REFERENCE_FLOORS = {"dtw": 0.02, "embedding": 0.01, "global": 0.5}
DYNAMIC_REFERENCE_PRIORS = {"dtw": 0.035, "embedding": 0.44, "global": 0.89}
DYNAMIC_REFERENCE_BLEND = 0.5

# Defaults mirror the last calibration run; models/dynamic_signature_calibration.json
# overrides them whenever it exists.
DYNAMIC_DEFAULT_THRESHOLD = 1.25

# Template adaptation: a login accepted with a comfortable margin is added
# to the user's template (oldest *adapted* sample dropped beyond the cap).
# Research data: 5 enrollment samples -> EER ~18 %, 10 -> ~8 %,
# 20 from two sessions -> ~3-6 %, so the template should grow over time.
DYNAMIC_RECOMMENDED_ENROLL_SAMPLES = 8
DYNAMIC_MAX_TEMPLATE_SAMPLES = 20
DYNAMIC_ADAPTATION_MARGIN = 0.75       # adapt only if score <= margin * threshold

# A probe that is closer than this fraction of the user's own natural
# variation to a stored enrollment sample is treated as a replayed recording.
REPLAY_SIMILARITY_RATIO = 0.03


# ---------------------------------------------------------------------------
# CALIBRATION OVERRIDES
# ---------------------------------------------------------------------------

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def load_static_calibration():
    """Threshold/weights written by pipelines/evaluate_static_gesture_model.py."""

    calibration = {
        "threshold": STATIC_DEFAULT_THRESHOLD,
        "fusion_weights": dict(STATIC_FUSION_WEIGHTS),
        "reference_priors": dict(STATIC_REFERENCE_PRIORS),
        "source": "defaults",
    }
    calibration.update(_load_json(STATIC_CALIBRATION_PATH))
    return calibration


def load_dynamic_calibration():
    """Threshold/weights written by pipelines/evaluate_dynamic_signature_model.py."""

    calibration = {
        "threshold": DYNAMIC_DEFAULT_THRESHOLD,
        "fusion_weights": dict(DYNAMIC_FUSION_WEIGHTS),
        "reference_priors": dict(DYNAMIC_REFERENCE_PRIORS),
        "source": "defaults",
    }
    calibration.update(_load_json(DYNAMIC_CALIBRATION_PATH))
    return calibration


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# config.py is the single source of truth for the ML service:
#   * filesystem locations (models/, data/, reports/, research dataset)
#   * the shared service key used by the Express backend
#   * static-gesture constants (frame counts, feature-group scales/weights,
#     fusion weights, default decision threshold)
#   * dynamic-signature constants (sequence length, duration limits, DTW band,
#     fusion weights, reference priors/blend, replay-detection ratio,
#     template-adaptation limits, default threshold)
# load_static_calibration()/load_dynamic_calibration() merge the defaults with
# the JSON calibration files produced by the evaluation pipelines, so a
# retrained/re-evaluated model automatically changes the live thresholds.
# =============================================================================
