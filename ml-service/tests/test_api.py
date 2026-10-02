import numpy as np
from fastapi.testclient import TestClient

from airauth import config
from app.main import app

client = TestClient(app)
HEADERS = {"X-Service-Key": config.SERVICE_API_KEY}


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["models"]) == {"static_gesture", "dynamic_signature"}


def test_biometric_endpoints_require_service_key(gesture_user):
    response = client.post("/static/enroll", json={"samples": [gesture_user["capture"]()]})
    assert response.status_code == 401


def test_static_round_trip(gesture_user):
    enroll = client.post(
        "/static/enroll", headers=HEADERS,
        json={"samples": [gesture_user["capture"]() for _ in range(5)]},
    )
    assert enroll.status_code == 200, enroll.text
    template = enroll.json()["template"]

    verify = client.post(
        "/static/verify", headers=HEADERS,
        json={"template": template, "sample": gesture_user["capture"]()},
    )
    assert verify.status_code == 200
    body = verify.json()
    assert {"accepted", "score", "threshold", "match_percent", "components", "reason"} <= set(body)


def test_dynamic_round_trip(signature_generator):
    writer = signature_generator.make_writer()
    enroll = client.post(
        "/dynamic/enroll", headers=HEADERS,
        json={"samples": [signature_generator.render(writer) for _ in range(5)]},
    )
    assert enroll.status_code == 200, enroll.text

    verify = client.post(
        "/dynamic/verify", headers=HEADERS,
        json={"template": enroll.json()["template"], "sample": signature_generator.render(writer)},
    )
    assert verify.status_code == 200
    assert verify.json()["step"] == "dynamic_signature"


def test_unusable_capture_returns_structured_422():
    sample = {"points": [[i * 0.03, 0.5, 0.5, 0.0] for i in range(5)]}
    response = client.post("/dynamic/enroll", headers=HEADERS, json={"samples": [sample] * 3})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "too_short"
    assert error["details"]["sample_index"] == 0


def test_schema_validation_rejects_bad_landmarks():
    bad = {"frames": [{"landmarks": np.zeros((5, 3)).tolist()}]}
    response = client.post("/static/enroll", headers=HEADERS, json={"samples": [bad]})
    assert response.status_code == 422


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# test_api.py exercises the FastAPI layer with TestClient: public health
# endpoint, service-key protection, full enroll -> verify round trips for
# both steps, the structured 422 error for unusable captures (including the
# offending sample index) and Pydantic schema validation.
# =============================================================================
