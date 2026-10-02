import hmac

from fastapi import Header, HTTPException, status

from airauth import config


def require_service_key(x_service_key: str = Header(default="")):
    """
    Only the Express backend may call the ML service.  It sends the shared
    secret ML_SERVICE_API_KEY in the X-Service-Key header.
    """

    if not hmac.compare_digest(x_service_key.encode(), config.SERVICE_API_KEY.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service key")


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# security.py provides require_service_key(), a FastAPI dependency that
# compares the X-Service-Key header with ML_SERVICE_API_KEY in constant time.
# Every biometric endpoint depends on it, so browsers can never reach the ML
# service directly — all traffic must go through the Node backend.
# =============================================================================
