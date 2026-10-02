"""
Request schemas for the ML service API (validated by Pydantic).

Size limits protect the service from oversized payloads; the shapes of
landmarks/points are checked again, in more detail, by the preprocessing
modules.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StaticFrame(BaseModel):
    landmarks: List[List[float]] = Field(..., min_length=21, max_length=21,
                                         description="21 MediaPipe landmarks as [x, y, z]")
    handedness: str = Field("Unknown", max_length=16)
    score: Optional[float] = None


class StaticSample(BaseModel):
    frames: List[StaticFrame] = Field(..., min_length=1, max_length=120)
    width: Optional[int] = Field(None, gt=0, le=10000)
    height: Optional[int] = Field(None, gt=0, le=10000)


class DynamicSample(BaseModel):
    points: List[List[float]] = Field(..., min_length=2, max_length=3000,
                                      description="[t_seconds, x, y, z] of the index fingertip")
    width: Optional[int] = Field(None, gt=0, le=10000)
    height: Optional[int] = Field(None, gt=0, le=10000)


class StaticEnrollRequest(BaseModel):
    samples: List[StaticSample] = Field(..., min_length=1, max_length=15)


class StaticVerifyRequest(BaseModel):
    template: Dict[str, Any]
    sample: StaticSample


class DynamicEnrollRequest(BaseModel):
    samples: List[DynamicSample] = Field(..., min_length=1, max_length=25)


class DynamicVerifyRequest(BaseModel):
    template: Dict[str, Any]
    sample: DynamicSample


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# schemas.py declares the Pydantic models for every ML-service endpoint:
# a static sample is up to 120 frames of 21 [x,y,z] landmarks with a
# handedness label; a dynamic sample is up to 3,000 [t,x,y,z] fingertip
# points; enroll requests carry a list of samples and verify requests carry
# the stored template plus one probe sample.  Frame size (width/height) is
# optional and used for aspect-ratio correction.
# =============================================================================
