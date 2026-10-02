"""
Key-point feature extraction for static hand gestures.

Every frame of 21 landmarks is converted into seven feature groups:

    group           dims  invariant to          captures
    --------------  ----  --------------------  -------------------------------
    canonical_xy     40   position/scale/rot.   pose shape in the palm plane
    canonical_z      20   position/scale/rot.   finger depth (noisy, low weight)
    joint_angles     15   everything            flexion of every finger joint
    tip_distances    10   position/scale/rot.   which fingertips touch/spread
    abduction         4   everything            spread between adjacent fingers
    orientation       6   position/scale        palm normal + up vector
                                                (thumbs-up vs thumbs-down)
    hand_geometry    20   pose                  bone-length ratios — a weak
                                                *biometric* (whose hand it is)

The first five groups (89 dims) are pose-only and form the neural network
input.  All seven groups are used by the template matcher.
"""

import numpy as np

from airauth.common import hand_landmarks as hl
from airauth.static_gesture.preprocessing import palm_size

FEATURE_GROUPS = [
    ("canonical_xy", 40),
    ("canonical_z", 20),
    ("joint_angles", 15),
    ("tip_distances", 10),
    ("abduction", 4),
    ("orientation", 6),
    ("hand_geometry", 20),
]

POSE_GROUPS = ["canonical_xy", "canonical_z", "joint_angles", "tip_distances", "abduction"]


def _build_slices():
    slices = {}
    start = 0
    for name, size in FEATURE_GROUPS:
        slices[name] = slice(start, start + size)
        start += size
    return slices, start


GROUP_SLICES, FEATURE_DIM = _build_slices()

POSE_FEATURE_DIM = sum(size for name, size in FEATURE_GROUPS if name in POSE_GROUPS)


# ---------------------------------------------------------------------------
# GEOMETRY HELPERS
# ---------------------------------------------------------------------------

def _unit(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 1e-9 else vector


def palm_frame(points):
    """
    Orthonormal hand coordinate frame.

        y: wrist -> middle-finger knuckle   (hand "up")
        x: index knuckle -> pinky knuckle   (across the palm)
        z: x × y                            (palm normal)

    Returns a (3, 3) rotation matrix whose rows are the axes.
    """

    y_axis = _unit(points[hl.MIDDLE_MCP] - points[hl.WRIST])

    across = points[hl.PINKY_MCP] - points[hl.INDEX_MCP]
    x_axis = _unit(across - np.dot(across, y_axis) * y_axis)

    z_axis = np.cross(x_axis, y_axis)

    return np.stack([x_axis, y_axis, z_axis])


def canonicalize(points):
    """Translate to wrist, scale by palm size, rotate into the palm frame."""

    unit = palm_size(points)
    rotation = palm_frame(points)

    centred = (points - points[hl.WRIST]) / unit

    return centred @ rotation.T, rotation, unit


def _angle_between(a, b):
    cosine = np.dot(_unit(a), _unit(b))
    return float(np.arccos(np.clip(cosine, -1.0, 1.0)))


# ---------------------------------------------------------------------------
# FEATURE GROUPS
# ---------------------------------------------------------------------------

def joint_flexion_angles(canonical):
    """0 rad = straight joint, π/2 = bent at right angle."""

    return np.array(
        [
            np.pi - _angle_between(canonical[a] - canonical[b], canonical[c] - canonical[b])
            for a, b, c in hl.JOINT_TRIPLETS
        ]
    )


def fingertip_distances(canonical):
    tips = canonical[hl.FINGERTIPS]
    return np.array(
        [
            np.linalg.norm(tips[i] - tips[j])
            for i in range(len(tips))
            for j in range(i + 1, len(tips))
        ]
    )


def abduction_angles(canonical):
    """Angle between adjacent finger directions, projected on the palm plane."""

    def direction(finger):
        chain = hl.FINGER_CHAINS[finger]
        # Thumb uses MCP->IP, other fingers MCP->PIP.
        vector = canonical[chain[3]] - canonical[chain[2]] if finger == "thumb" \
            else canonical[chain[2]] - canonical[chain[1]]
        return vector[:2]

    return np.array(
        [_angle_between(direction(a), direction(b)) for a, b in hl.ABDUCTION_PAIRS]
    )


def hand_geometry(points, unit):
    return np.array(
        [np.linalg.norm(points[child] - points[parent]) / unit for parent, child in hl.BONES]
    )


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def extract_frame_features(points):
    """(21, 3) landmarks -> FEATURE_DIM vector."""

    canonical, rotation, unit = canonicalize(points)

    vector = np.concatenate(
        [
            canonical[1:, :2].ravel(),
            canonical[1:, 2],
            joint_flexion_angles(canonical),
            fingertip_distances(canonical),
            abduction_angles(canonical),
            np.concatenate([rotation[2], rotation[1]]),
            hand_geometry(points, unit),
        ]
    )

    return vector


def extract_sample_features(frames):
    """
    (F, 21, 3) -> one robust FEATURE_DIM vector (median over frames) plus
    the per-feature spread across frames (used as a quality signal).
    """

    per_frame = np.stack([extract_frame_features(frame) for frame in frames])

    return np.median(per_frame, axis=0), np.std(per_frame, axis=0)


def pose_vector(feature_vector):
    """Select the pose-only groups that feed the neural network."""

    feature_vector = np.asarray(feature_vector)
    parts = [feature_vector[..., GROUP_SLICES[name]] for name in POSE_GROUPS]
    return np.concatenate(parts, axis=-1)


def flip_pose_chirality(pose_vectors):
    """
    Mirror a batch of pose vectors (canonical z changes sign; angles and
    distances are unchanged).  Used as augmentation during training.
    """

    flipped = np.array(pose_vectors, copy=True)
    z_slice = GROUP_SLICES["canonical_z"]
    flipped[..., z_slice] *= -1.0
    return flipped


def group_distance(vector_a, vector_b, scales, weights):
    """
    Weighted distance between two feature vectors.  Each group contributes
    the RMS of its differences divided by that group's expected natural
    variation (scales), so 1.0 ≈ "typical genuine repetition".
    """

    vector_a = np.asarray(vector_a, dtype=float)
    vector_b = np.asarray(vector_b, dtype=float)

    total = 0.0
    weight_sum = 0.0

    for name, _ in FEATURE_GROUPS:
        weight = weights.get(name, 0.0)
        if weight <= 0:
            continue
        diff = (vector_a[GROUP_SLICES[name]] - vector_b[GROUP_SLICES[name]]) / scales[name]
        total += weight * float(np.sqrt(np.mean(diff ** 2)))
        weight_sum += weight

    return total / weight_sum


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# features.py is the key-point feature extractor for Step 1 (static gesture).
# It builds a palm-aligned coordinate frame (wrist origin, palm-size unit,
# rotation into palm axes) and computes 115 features per frame across seven
# groups: canonical xy/z coordinates, 15 joint flexion angles, 10 fingertip
# distances, 4 abduction angles, 6 orientation values and 20 bone-length
# ratios.  extract_sample_features() takes the per-frame median for
# robustness, pose_vector() picks the 89 pose-only dims for the neural model,
# flip_pose_chirality() is the mirror augmentation, and group_distance() is
# the scale-normalised template-matching distance.
# =============================================================================
