from fastapi import APIRouter, Depends

from airauth.dynamic_signature import verifier
from app.schemas import DynamicEnrollRequest, DynamicVerifyRequest
from app.security import require_service_key

router = APIRouter(prefix="/dynamic", tags=["Step 2 - air signature"],
                   dependencies=[Depends(require_service_key)])


@router.post("/enroll")
def enroll_air_signature(request: DynamicEnrollRequest):
    """Build a signature template from several air-signature recordings."""

    samples = [sample.model_dump() for sample in request.samples]
    template, report = verifier.enroll(samples)

    return {"template": template, "report": report}


@router.post("/verify")
def verify_air_signature(request: DynamicVerifyRequest):
    """
    Compare one air signature with a stored template.  When the match is
    confident, the response includes `template_update` for adaptation.
    """

    return verifier.verify(request.template, request.sample.model_dump())


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# dynamic_signature_router.py exposes Step 2 over HTTP:
#   POST /dynamic/enroll  {samples:[...]}     -> {template, report}
#   POST /dynamic/verify  {template, sample}  -> verification result
#                                               (+ template_update)
# Both require the X-Service-Key header.
# =============================================================================
