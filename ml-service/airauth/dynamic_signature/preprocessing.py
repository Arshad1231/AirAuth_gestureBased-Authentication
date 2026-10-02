"""
Preprocessing for in-air signatures (Step 2).

Input sample (index-fingertip trajectory, MediaPipe landmark 8):

    {"points": [[t_seconds, x, y, z], ...], "width": 1280, "height": 720}

Pipeline (NumPy port of the original research preprocessing):

    RAW POINTS
      │ 1. clean          drop NaN/inf, sort by time, drop duplicate stamps
      │ 2. validate       minimum points, duration limits
      │ 3. aspect fix     x *= width / height
      │ 4. trim idle      remove the motionless start / end dwell
      │ 5. de-spike       MAD jump threshold + local reversal test,
      │                   confirmed spikes are re-interpolated
      │ 6. size check     reject tiny / degenerate drawings
      │ 7. resample       128 points uniformly in TIME (keeps rhythm)
      │ 8. normalise      centroid -> origin, largest xy range -> 1
      ▼
    ProcessedSignature(xy[128,2], duration, ...)

z (MediaPipe relative depth) is discarded: the original research DTW
feature ablation showed XY-only DTW performs best
(EER 14 % vs 31 % with z).
"""

from dataclasses import dataclass

import numpy as np

from airauth import config
from airauth.common.errors import BiometricInputError

TRIM_PATH_FRACTION = 0.02
MIN_DRAWING_SIZE = 0.04       # fraction of image height


@dataclass
class ProcessedSignature:
    xy: np.ndarray            # (SEQUENCE_LENGTH, 2) normalised trajectory
    duration: float           # seconds (after trimming)
    raw_point_count: int
    corrected_spikes: int
    drawing_size: float       # largest xy range before normalisation
    aspect_ratio: float       # bbox width / height


# ---------------------------------------------------------------------------
# STEPS
# ---------------------------------------------------------------------------

def parse_points(sample):

    points = np.asarray(sample.get("points") or [], dtype=float)

    if points.ndim != 2 or points.shape[1] < 3:
        raise BiometricInputError("Signature data is malformed.", code="malformed")

    points = points[:, :3]                                   # t, x, y
    points = points[np.all(np.isfinite(points), axis=1)]

    order = np.argsort(points[:, 0], kind="stable")
    points = points[order]

    _, unique_index = np.unique(points[:, 0], return_index=True)
    points = points[np.sort(unique_index)]

    return points


def validate(points):

    if len(points) < config.DYNAMIC_MIN_POINTS:
        raise BiometricInputError(
            "The signature was too short. Draw your full signature in the air.",
            code="too_short",
            details={"points": int(len(points))},
        )

    duration = points[-1, 0] - points[0, 0]

    if duration < config.DYNAMIC_MIN_DURATION:
        raise BiometricInputError(
            "The signature was drawn too quickly to be captured reliably.",
            code="too_fast",
            details={"duration": round(float(duration), 3)},
        )

    if duration > config.DYNAMIC_MAX_DURATION:
        raise BiometricInputError(
            "The signature took too long. Draw it in one smooth motion.",
            code="too_slow",
            details={"duration": round(float(duration), 3)},
        )


def correct_aspect_ratio(points, width, height):

    points = points.copy()

    if width and height:
        points[:, 1] *= float(width) / float(height)

    return points


def trim_idle(points):
    """
    Remove the dwell before the user starts moving and after they stop
    (the web capture auto-stops after ~1 s of stillness).
    """

    steps = np.linalg.norm(np.diff(points[:, 1:3], axis=0), axis=1)
    cumulative = np.concatenate([[0.0], np.cumsum(steps)])
    total = cumulative[-1]

    if total <= 0:
        raise BiometricInputError(
            "No finger movement was detected.", code="no_movement"
        )

    start = int(np.searchsorted(cumulative, TRIM_PATH_FRACTION * total, side="left"))
    end = int(np.searchsorted(cumulative, (1 - TRIM_PATH_FRACTION) * total, side="right"))

    start = max(start - 1, 0)
    end = min(end + 1, len(points))

    return points[start:end]


def correct_spikes(points):
    """
    Detect isolated tracking spikes: a jump larger than
    median + k * MAD that immediately reverses.  Replace them by linear
    interpolation; genuine fast strokes (which keep going) are untouched.
    """

    xy = points[:, 1:3]
    steps = np.concatenate([[0.0], np.linalg.norm(np.diff(xy, axis=0), axis=1)])

    valid = steps[1:]
    median = np.median(valid)
    mad = max(np.median(np.abs(valid - median)), 1e-8)
    threshold = median + config.DYNAMIC_SPIKE_MAD_MULTIPLIER * mad

    outliers = np.zeros(len(points), dtype=bool)

    for i in range(1, len(points) - 1):

        incoming = np.linalg.norm(xy[i] - xy[i - 1])
        outgoing = np.linalg.norm(xy[i + 1] - xy[i])

        if incoming <= threshold and outgoing <= threshold:
            continue

        skip = np.linalg.norm(xy[i + 1] - xy[i - 1])
        local = incoming + outgoing

        if local > 1e-8 and skip / local < config.DYNAMIC_SPIKE_REVERSAL_RATIO:
            outliers[i] = True

    if outliers.any():
        good = np.where(~outliers)[0]
        corrected = points.copy()
        for axis in (1, 2):
            corrected[:, axis] = np.interp(np.arange(len(points)), good, points[good, axis])
        points = corrected

    return points, int(outliers.sum())


def resample_by_time(points, length):

    t = points[:, 0]
    new_t = np.linspace(t[0], t[-1], length)

    return np.stack(
        [np.interp(new_t, t, points[:, 1]), np.interp(new_t, t, points[:, 2])], axis=1
    )


def normalise(xy):

    xy = xy - xy.mean(axis=0)
    ranges = xy.max(axis=0) - xy.min(axis=0)
    scale = float(ranges.max())

    return xy / scale, scale, float(ranges[0] / max(ranges[1], 1e-9))


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def preprocess_signature(sample):

    points = parse_points(sample)
    validate(points)

    raw_count = len(points)

    points = correct_aspect_ratio(points, sample.get("width"), sample.get("height"))
    points = trim_idle(points)
    validate(points)

    points, spikes = correct_spikes(points)

    xy = resample_by_time(points, config.SEQUENCE_LENGTH)

    size = float((xy.max(axis=0) - xy.min(axis=0)).max())
    if size < MIN_DRAWING_SIZE:
        raise BiometricInputError(
            "The signature was too small. Draw larger, using your whole arm.",
            code="too_small",
            details={"size": round(size, 4)},
        )

    xy, scale, aspect = normalise(xy)

    return ProcessedSignature(
        xy=xy,
        duration=float(points[-1, 0] - points[0, 0]),
        raw_point_count=raw_count,
        corrected_spikes=spikes,
        drawing_size=scale,
        aspect_ratio=aspect,
    )


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# preprocessing.py converts a raw fingertip trajectory into a fixed-length,
# position- and size-invariant signature.  It cleans and validates the
# points, corrects the camera aspect ratio, trims the idle dwell at both
# ends, removes isolated MediaPipe tracking spikes with a MAD + reversal
# test (same algorithm as the original research TrajectorySmoother),
# resamples to 128 points uniformly in time and normalises by centroid and
# largest range.  The returned ProcessedSignature also keeps duration, size
# and aspect ratio, which feed the behavioural (global) features.
# =============================================================================
