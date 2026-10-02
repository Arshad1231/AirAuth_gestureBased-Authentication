"""
Procedural (kinematic) hand generator that produces MediaPipe-style
21-landmark hands.

Why it exists
-------------
Each user invents their *own* secret gesture, so there is no fixed list
of classes to train on and no public dataset of "personal" gestures.
What the neural model must learn is a general notion of *pose
similarity*: two captures of the same pose — by different people, at
different wrist angles, with tracking noise — must embed close together,
while different poses embed far apart.

The generator provides unlimited labelled data for exactly that:

    pose class  = discrete state of every finger + thumb
                  (2,048 combinations) plus a class-specific offset
    person      = bone lengths / palm width            (geometry)
    orientation = roll / pitch / yaw of the hand        (viewpoint)
    noise       = landmark jitter like MediaPipe's

Real captures exported from the web app can be mixed in later
(pipelines/train_static_gesture_model.py --collected).
"""

import itertools

import numpy as np

# ---------------------------------------------------------------------------
# HAND MODEL (palm length = 1.0)
# ---------------------------------------------------------------------------

FINGER_BASES = {
    "index": np.array([-0.30, 0.95, 0.0]),
    "middle": np.array([-0.08, 1.00, 0.0]),
    "ring": np.array([0.13, 0.93, 0.0]),
    "pinky": np.array([0.32, 0.82, 0.0]),
}

FINGER_BONES = {
    "index": np.array([0.48, 0.28, 0.22]),
    "middle": np.array([0.53, 0.32, 0.23]),
    "ring": np.array([0.50, 0.30, 0.22]),
    "pinky": np.array([0.40, 0.22, 0.20]),
}

THUMB_BASE = np.array([-0.20, 0.18, 0.06])
THUMB_BONES = np.array([0.42, 0.32, 0.26])
THUMB_FLEX_TOWARD = np.array([0.6, 0.0, 0.8]) / np.linalg.norm([0.6, 0.0, 0.8])

# (MCP, PIP, DIP) flexion in degrees
FINGER_STATES = {
    "extended": (5.0, 5.0, 3.0),
    "half": (40.0, 45.0, 25.0),
    "curled": (80.0, 100.0, 60.0),
    "hooked": (5.0, 90.0, 60.0),
}

# Abduction in degrees for (index, middle, ring, pinky)
ABDUCTION_STATES = {
    "together": (4.0, 0.0, -3.0, -6.0),
    "spread": (15.0, 2.0, -10.0, -20.0),
}

# Metacarpal direction and (MCP, IP) flexion in degrees
THUMB_STATES = {
    "out": ((-0.85, 0.50, 0.15), (5.0, 5.0)),
    "side": ((-0.35, 0.92, 0.15), (5.0, 5.0)),
    "across": ((0.25, 0.75, 0.60), (35.0, 30.0)),
    "tucked": ((0.10, 0.55, 0.85), (55.0, 65.0)),
}

FINGER_ORDER = ["index", "middle", "ring", "pinky"]


def rotation_matrix(axis, angle):
    """Rodrigues rotation matrix."""

    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s = np.cos(angle), np.sin(angle)
    C = 1 - c

    return np.array(
        [
            [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
        ]
    )


def euler_rotation(roll, pitch, yaw):
    return (
        rotation_matrix([0, 0, 1], roll)
        @ rotation_matrix([1, 0, 0], pitch)
        @ rotation_matrix([0, 1, 0], yaw)
    )


def all_pose_combinations():
    """Every discrete pose class: 4^4 finger states x 2 abduction x 4 thumb."""

    return list(
        itertools.product(
            itertools.product(FINGER_STATES.keys(), repeat=4),
            ABDUCTION_STATES.keys(),
            THUMB_STATES.keys(),
        )
    )


class SyntheticHandGenerator:

    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # RANDOM FACTORS
    # ------------------------------------------------------------------

    def make_pose_class(self, combination, class_offset_deg=6.0):
        """A concrete pose class: discrete states + fixed per-class offsets."""

        finger_states, abduction_state, thumb_state = combination
        rng = self.rng

        flexion = np.array([FINGER_STATES[state] for state in finger_states])
        flexion = flexion + rng.normal(0, class_offset_deg, flexion.shape)

        abduction = np.array(ABDUCTION_STATES[abduction_state])
        abduction = abduction + rng.normal(0, class_offset_deg / 2, abduction.shape)

        thumb_direction, thumb_flex = THUMB_STATES[thumb_state]
        thumb_direction = np.array(thumb_direction, dtype=float)
        thumb_direction /= np.linalg.norm(thumb_direction)
        wobble = rotation_matrix(rng.normal(size=3), np.deg2rad(rng.normal(0, class_offset_deg)))
        thumb_direction = wobble @ thumb_direction

        thumb_flex = np.array(thumb_flex) + rng.normal(0, class_offset_deg, 2)

        return {
            "combination": combination,
            "flexion": np.clip(flexion, 0.0, 120.0),
            "abduction": abduction,
            "thumb_direction": thumb_direction,
            "thumb_flex": np.clip(thumb_flex, 0.0, 90.0),
        }

    def make_person(self):
        """Hand geometry of one person."""

        rng = self.rng

        return {
            "palm_width": rng.normal(1.0, 0.06),
            "finger_scale": {name: rng.normal(1.0, 0.06) for name in FINGER_ORDER},
            "bone_noise": {name: rng.normal(1.0, 0.04, 3) for name in FINGER_ORDER},
            "thumb_scale": rng.normal(1.0, 0.06) * rng.normal(1.0, 0.04, 3),
        }

    def make_orientation(self, base=None, spread_deg=(35.0, 30.0, 35.0)):
        """(roll, pitch, yaw) in radians, optionally jittered around a base."""

        spread = np.deg2rad(np.asarray(spread_deg))

        if base is None:
            return self.rng.uniform(-spread, spread)

        return np.asarray(base) + self.rng.normal(0, spread)

    # ------------------------------------------------------------------
    # RENDERING
    # ------------------------------------------------------------------

    def _finger_points(self, base, bones, abduction_deg, flexion_deg):

        palm_normal = np.array([0.0, 0.0, 1.0])

        direction = rotation_matrix(palm_normal, np.deg2rad(abduction_deg)) @ np.array([0.0, 1.0, 0.0])
        bend_axis = np.cross(direction, palm_normal)

        points = [base]
        cumulative = 0.0

        for length, flex in zip(bones, flexion_deg):
            cumulative += np.deg2rad(flex)
            bone_direction = rotation_matrix(bend_axis, cumulative) @ direction
            points.append(points[-1] + length * bone_direction)

        return points[1:]

    def _thumb_points(self, base, bones, direction, flex_deg):

        bend_axis = np.cross(direction, THUMB_FLEX_TOWARD)
        if np.linalg.norm(bend_axis) < 1e-6:
            bend_axis = np.array([0.0, 1.0, 0.0])

        points = [base, base + bones[0] * direction]
        cumulative = 0.0

        for length, flex in zip(bones[1:], flex_deg):
            cumulative += np.deg2rad(flex)
            bone_direction = rotation_matrix(bend_axis, cumulative) @ direction
            points.append(points[-1] + length * bone_direction)

        return points

    def render_local(self, pose, person, angle_jitter_deg=5.0):
        """21 landmarks in the hand's local frame."""

        rng = self.rng
        points = np.zeros((21, 3))

        thumb_direction = rotation_matrix(
            rng.normal(size=3), np.deg2rad(rng.normal(0, angle_jitter_deg))
        ) @ pose["thumb_direction"]

        thumb = self._thumb_points(
            THUMB_BASE * np.array([person["palm_width"], 1.0, 1.0]),
            THUMB_BONES * person["thumb_scale"],
            thumb_direction,
            pose["thumb_flex"] + rng.normal(0, angle_jitter_deg, 2),
        )
        points[1:5] = thumb

        for index, name in enumerate(FINGER_ORDER):

            base = FINGER_BASES[name] * np.array([person["palm_width"], 1.0, 1.0])
            bones = FINGER_BONES[name] * person["finger_scale"][name] * person["bone_noise"][name]

            chain = self._finger_points(
                base,
                bones,
                pose["abduction"][index] + rng.normal(0, angle_jitter_deg / 2),
                pose["flexion"][index] + rng.normal(0, angle_jitter_deg, 3),
            )

            start = 5 + 4 * index
            points[start] = base
            points[start + 1:start + 4] = chain

        return points

    def random_placement(self):
        """Hand size and position in the image for one capture."""

        return self.rng.uniform(0.15, 0.30), self.rng.uniform(0.35, 0.65, 2)

    def to_image_space(self, local_points, orientation, placement=None,
                       xy_noise=0.0015, z_noise=0.004):
        """Rotate, scale and place the hand like a MediaPipe detection."""

        rng = self.rng

        rotated = local_points @ euler_rotation(*orientation).T

        scale, centre = placement if placement is not None else self.random_placement()

        image = np.empty_like(rotated)
        image[:, 0] = centre[0] + scale * rotated[:, 0]
        image[:, 1] = centre[1] - scale * rotated[:, 1]
        image[:, 2] = scale * (rotated[:, 2] - rotated[0, 2])

        image[:, :2] += rng.normal(0, xy_noise, (21, 2))
        image[:, 2] += rng.normal(0, z_noise, 21)

        return image

    def render(self, pose, person, orientation, angle_jitter_deg=5.0, n_frames=1):
        """
        One capture: (n_frames, 21, 3) landmarks in normalised image space.
        Frames share the pose but have independent tracking noise.
        """

        local = self.render_local(pose, person, angle_jitter_deg)
        placement = self.random_placement()
        return np.stack(
            [self.to_image_space(local, orientation, placement) for _ in range(n_frames)]
        )


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# synthetic_hand.py is a small forward-kinematics hand model used to train
# and evaluate the static-gesture embedding network without a real dataset.
# A pose class fixes the state of each finger (extended/half/curled/hooked),
# finger spread (together/spread) and thumb (out/side/across/tucked) plus a
# class-specific random offset — 2,048 discrete combinations in total.
# SyntheticHandGenerator samples persons (bone lengths, palm width),
# orientations (roll/pitch/yaw) and per-capture angle jitter, then projects
# the 21 joints into MediaPipe-like normalised image coordinates with
# tracking noise.  all_pose_combinations() lets the pipelines split pose
# classes into disjoint train / validation sets so the model is evaluated on
# gestures it has never seen.
# =============================================================================
