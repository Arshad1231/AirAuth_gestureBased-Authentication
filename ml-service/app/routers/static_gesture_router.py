from fastapi import APIRouter, Depends

from airauth.static_gesture import verifier
from app.schemas import StaticEnrollRequest, StaticVerifyRequest
from app.security import require_service_key

router = APIRouter(prefix="/static", tags=["Step 1 - static gesture"],
                   dependencies=[Depends(require_service_key)])


@router.post("/enroll")
def enroll_static_gesture(request: StaticEnrollRequest):
    """Build a gesture template from several captures of the same pose."""

    samples = [sample.model_dump() for sample in request.samples]
    template, report = verifier.enroll(samples)

    return {"template": template, "report": report}


@router.post("/verify")
def verify_static_gesture(request: StaticVerifyRequest):
    """Compare one capture with a stored gesture template."""

    return verifier.verify(request.template, request.sample.model_dump())


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# static_gesture_router.py exposes Step 1 over HTTP:
#   POST /static/enroll  {samples:[...]}           -> {template, report}
#   POST /static/verify  {template, sample}        -> verification result
# Both require the X-Service-Key header.  Endpoints are synchronous so
# FastAPI runs the CPU-bound work in its thread pool.
# =============================================================================
