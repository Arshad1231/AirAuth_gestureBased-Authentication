"""
AirAuth ML service — FastAPI application.

Run (from ml-service/):
    uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from airauth.common.errors import BiometricInputError
from airauth.common.model_registry import dynamic_signature_model, static_gesture_model
from app.routers import dynamic_signature_router, health_router, static_gesture_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("airauth.api")


@asynccontextmanager
async def lifespan(_app):
    # Load models and trace their inference graphs once at start-up so the
    # first login is not slow.
    for handle in (static_gesture_model, dynamic_signature_model):
        handle.warm_up()
        logger.info("%s model: %s", handle.name, handle.status())
    yield


app = FastAPI(
    title="AirAuth ML Service",
    description="Static hand-gesture + dynamic air-signature verification",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(BiometricInputError)
async def biometric_input_error_handler(_request: Request, error: BiometricInputError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": error.code, "message": error.message, "details": error.details}},
    )


app.include_router(health_router.router)
app.include_router(static_gesture_router.router)
app.include_router(dynamic_signature_router.router)


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# main.py assembles the FastAPI application: it loads both embedding models
# and traces their inference graphs at start-up (lifespan), converts BiometricInputError into a
# structured HTTP 422 {"error": {code, message, details}} that the UI shows
# as a "please retry" message, and mounts the health, static-gesture
# (/static/*) and dynamic-signature (/dynamic/*) routers.
# =============================================================================
