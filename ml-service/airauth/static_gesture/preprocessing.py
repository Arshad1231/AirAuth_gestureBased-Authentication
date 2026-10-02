"""
Validation and clean-up of a captured static hand gesture.

A static sample is a short burst of frames (≈0.5–1 s) in which the user
holds one hand pose in front of the camera:

    {
      "frames": [
        {"landmarks": [[x, y, z] * 21], "handedness": "Right", "score": 0.97},
        ...
      ],
      "width": 640, "height": 480
    }

x / y are MediaPipe normalised image coordinates (0..1), z is MediaPipe's
relative depth (same scale as x, wrist ≈ 0).
"""

from collections import Counter

import numpy as np

from airauth import config
from airauth.common import hand_landmarks as hl
from airauth.common.errors import BiometricInputError


def parse_frames(sample):
    """Convert the JSON sample into a (F, 21, 3) array plus handedness."""

    frames = sample.get("frames") or []

    landmark_frames = []
    labels = []

    for frame in frames:

        landmarks = np.asarray(frame.get("landmarks", []), dtype=float)

        if landmarks.shape != (hl.NUM_LANDMARKS, 3):
            continue

        if not np.all(np.isfinite(landmarks)):
            continue

        landmark_frames.append(landmarks)
        labels.append(str(frame.get("handedness", "Unknown")).capitalize())

    if len(landmark_frames) < config.STATIC_MIN_FRAMES:
        raise BiometricInputError(
            "Not enough hand frames were captured. Keep your hand fully "
            "visible and hold the gesture steady.",
            code="too_few_frames",
            details={"valid_frames": len(landmark_frames)},
        )

    handedness = Counter(labels).most_common(1)[0][0]

    return np.stack(landmark_frames), handedness


def correct_aspect_ratio(frames, width, height):
    """
    MediaPipe normalises x by image width and y by image height.  Scale x
    (and z, which shares x's scale) so that distances are isotropic.
    """

    frames = frames.copy()

    if width and height:
        aspect = float(width) / float(height)
        frames[..., 0] *= aspect
        frames[..., 2] *= aspect

    return frames


def mirror_left_hand(frames, handedness):
    """Mirror left hands so that both hands share one canonical chirality."""

    if handedness == "Left":
        frames = frames.copy()
        frames[..., 0] *= -1.0

    return frames


def palm_size(points):
    """Mean wrist-to-knuckle distance; the unit for all normalised lengths."""

    knuckles = points[hl.PALM_BASE_POINTS]
    return float(np.mean(np.linalg.norm(knuckles - points[hl.WRIST], axis=1)))


def check_pose_stability(frames):
    """
    Reject captures where the hand moved a lot — the user was not holding a
    static pose (or tracking was unstable).
    """

    sizes = np.array([palm_size(frame) for frame in frames])
    unit = float(np.median(sizes))

    if unit < 1e-6:
        raise BiometricInputError(
            "Hand is too small or tracking failed.", code="tracking_failed"
        )

    anchors = frames[:, [hl.WRIST, hl.MIDDLE_MCP, hl.INDEX_TIP, hl.THUMB_TIP], :2]
    median_anchor = np.median(anchors, axis=0)
    drift = np.linalg.norm(anchors - median_anchor, axis=2).max() / unit

    if drift > config.STATIC_MAX_HOLD_MOTION:
        raise BiometricInputError(
            "Your hand moved while capturing. Hold the gesture still until "
            "the capture finishes.",
            code="unstable_pose",
            details={"drift": round(float(drift), 3)},
        )

    return float(drift)


def preprocess_static_sample(sample):
    """
    Full preprocessing for one static gesture capture.

    Returns:
        frames      (F, 21, 3) aspect-corrected, left hands mirrored
        handedness  "Left" / "Right"
        drift       hand motion during capture (palm units)
    """

    frames, handedness = parse_frames(sample)
    frames = correct_aspect_ratio(frames, sample.get("width"), sample.get("height"))
    drift = check_pose_stability(frames)
    frames = mirror_left_hand(frames, handedness)

    return frames, handedness, drift


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# preprocessing.py prepares a raw static-gesture capture for feature
# extraction:
#   1. parse_frames()          JSON -> (F,21,3) array, drops malformed frames,
#                              majority-votes the handedness label
#   2. correct_aspect_ratio()  makes x/y/z distances isotropic
#   3. check_pose_stability()  rejects captures where the hand drifted
#                              (user was not holding a static pose)
#   4. mirror_left_hand()      maps left hands onto right-hand chirality
# Problems are raised as BiometricInputError so the UI can ask for a retry.
# =============================================================================
