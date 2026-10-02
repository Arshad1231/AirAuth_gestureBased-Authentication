"""
Feature extraction for in-air signatures.

1. SEQUENCE FEATURES  (128 x 9, input of the neural embedding network)

    x, y            normalised position              (shape)
    vx, vy          velocity  d(pos)/d(t/duration)   (stroke direction + rhythm)
    speed           |v|                              (rhythm)
    sin θ, cos θ    pen direction                    (shape, rotation-aware)
    curvature       dθ/ds, clipped                   (loops, corners)
    accel           |dv/dt|                          (motor dynamics)

2. GLOBAL BEHAVIOURAL FEATURES  (12 values, user-specific statistics)

    log_duration, log_path_length, log_aspect_ratio, speed_cv,
    peak_speed_ratio, pause_ratio, x_reversals, y_reversals,
    start_x, start_y, end_x, end_y

3. DTW SEQUENCE  (128 x 2) — the normalised xy trajectory itself.
"""

import numpy as np

SEQUENCE_CHANNELS = ["x", "y", "vx", "vy", "speed", "sin_dir", "cos_dir", "curvature", "accel"]

GLOBAL_FEATURE_NAMES = [
    "log_duration",
    "log_path_length",
    "log_aspect_ratio",
    "speed_cv",
    "peak_speed_ratio",
    "pause_ratio",
    "x_reversals",
    "y_reversals",
    "start_x",
    "start_y",
    "end_x",
    "end_y",
]

# Minimum standard deviation assumed for each global feature, so a user
# whose 3–5 enrollment samples happen to agree perfectly on a feature is
# not rejected for a tiny natural deviation.
GLOBAL_FEATURE_FLOORS = np.array(
    [0.12, 0.10, 0.12, 0.08, 0.25, 0.05, 1.5, 1.5, 0.12, 0.12, 0.12, 0.12]
)

CURVATURE_CLIP = 50.0


def _smooth(values, passes=2):
    """[1, 2, 1] / 4 smoothing used only before differentiation."""

    out = np.asarray(values, dtype=float)
    for _ in range(passes):
        padded = np.concatenate([out[:1], out, out[-1:]])
        out = 0.25 * padded[:-2] + 0.5 * padded[1:-1] + 0.25 * padded[2:]
    return out


def sequence_features(xy):
    """(T, 2) normalised trajectory -> (T, 9) per-timestep features."""

    xy = np.asarray(xy, dtype=float)
    length = len(xy)
    dt = 1.0 / (length - 1)            # time normalised to [0, 1]

    smooth_xy = np.stack([_smooth(xy[:, 0]), _smooth(xy[:, 1])], axis=1)

    velocity = np.gradient(smooth_xy, dt, axis=0)
    speed = np.linalg.norm(velocity, axis=1)

    direction = np.arctan2(velocity[:, 1], velocity[:, 0])

    unwrapped = np.unwrap(direction)
    arc = np.maximum(speed * dt, 1e-6)
    curvature = np.clip(np.gradient(unwrapped) / arc, -CURVATURE_CLIP, CURVATURE_CLIP)

    acceleration = np.linalg.norm(np.gradient(velocity, dt, axis=0), axis=1)

    return np.column_stack(
        [
            xy[:, 0],
            xy[:, 1],
            velocity[:, 0],
            velocity[:, 1],
            speed,
            np.sin(direction),
            np.cos(direction),
            curvature,
            acceleration,
        ]
    ).astype(np.float32)


def _reversals(values):
    signs = np.sign(values[np.abs(values) > 1e-3 * (np.abs(values).max() + 1e-12)])
    return float(np.sum(signs[1:] != signs[:-1])) if len(signs) > 1 else 0.0


def global_features(processed):
    """ProcessedSignature -> 12 behavioural statistics."""

    xy = processed.xy
    seq = sequence_features(xy)
    speed = seq[:, 4]

    path_length = float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1)))
    mean_speed = float(speed.mean()) + 1e-9

    return np.array(
        [
            np.log(processed.duration),
            np.log(path_length + 1e-9),
            np.log(processed.aspect_ratio + 1e-9),
            float(speed.std() / mean_speed),
            float(speed.max() / mean_speed),
            float(np.mean(speed < 0.15 * mean_speed)),
            _reversals(seq[:, 2]),
            _reversals(seq[:, 3]),
            xy[0, 0],
            xy[0, 1],
            xy[-1, 0],
            xy[-1, 1],
        ]
    )


def global_distance(probe, enrolled_vectors):
    """
    RMS z-score of the probe's global features against the enrollment
    distribution (std floored by GLOBAL_FEATURE_FLOORS).
    """

    enrolled_vectors = np.asarray(enrolled_vectors, dtype=float)

    mean = enrolled_vectors.mean(axis=0)
    std = enrolled_vectors.std(axis=0) if len(enrolled_vectors) > 1 else np.zeros_like(mean)
    effective = np.sqrt(std ** 2 + GLOBAL_FEATURE_FLOORS ** 2)

    z = (np.asarray(probe, dtype=float) - mean) / effective

    return float(np.sqrt(np.mean(z ** 2)))


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# features.py extracts everything the Step-2 verifier and neural model need
# from a ProcessedSignature:
#   sequence_features()  9 channels per timestep (position, velocity, speed,
#                        direction sin/cos, curvature, acceleration) computed
#                        on a lightly smoothed copy so derivatives are stable
#   global_features()    12 behavioural statistics (duration, path length,
#                        aspect ratio, speed variability, pauses, direction
#                        reversals, start/end points)
#   global_distance()    floored z-score distance of a probe's global
#                        features against the user's enrollment samples
# =============================================================================
