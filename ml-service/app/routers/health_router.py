from fastapi import APIRouter

from airauth import config
from airauth.common.model_registry import dynamic_signature_model, static_gesture_model

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    """Liveness + which models / calibrations are active (no secrets)."""

    static_calibration = config.load_static_calibration()
    dynamic_calibration = config.load_dynamic_calibration()

    return {
        "status": "ok",
        "models": {
            "static_gesture": static_gesture_model.status(),
            "dynamic_signature": dynamic_signature_model.status(),
        },
        "calibration": {
            "static_gesture": {
                "threshold": static_calibration["threshold"],
                "source": static_calibration.get("source"),
            },
            "dynamic_signature": {
                "threshold": dynamic_calibration["threshold"],
                "source": dynamic_calibration.get("source"),
            },
        },
        "feature_versions": {
            "static_gesture": config.STATIC_FEATURE_VERSION,
            "dynamic_signature": config.DYNAMIC_FEATURE_VERSION,
        },
        "enrollment": {
            "static_min_samples": config.STATIC_MIN_ENROLL_SAMPLES,
            "dynamic_min_samples": config.DYNAMIC_MIN_ENROLL_SAMPLES,
            "dynamic_recommended_samples": config.DYNAMIC_RECOMMENDED_ENROLL_SAMPLES,
        },
    }


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# health_router.py serves GET /health (no auth): service status, whether each
# neural model is loaded (and its version), the active thresholds and their
# calibration source, feature versions and enrollment sample requirements.
# The Node backend proxies this for the UI's system-status panel.
# =============================================================================
