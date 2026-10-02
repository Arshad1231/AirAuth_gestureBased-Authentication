import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from airauth.dynamic_signature.synthetic_signature import SyntheticSignatureGenerator  # noqa: E402
from airauth.static_gesture.synthetic_hand import SyntheticHandGenerator  # noqa: E402


def hand_capture(generator, pose, person, orientation, handedness="Right", frames=10):
    landmarks = generator.render(pose, person, generator.make_orientation(orientation, (6, 6, 6)),
                                 n_frames=frames)
    return {
        "frames": [{"landmarks": frame.tolist(), "handedness": handedness} for frame in landmarks],
        "width": 1,
        "height": 1,
    }


@pytest.fixture
def hand_generator():
    return SyntheticHandGenerator(seed=123)


@pytest.fixture
def signature_generator():
    return SyntheticSignatureGenerator(seed=321)


@pytest.fixture
def gesture_user(hand_generator):
    """A simulated user with a fixed gesture, hand and habitual wrist angle."""

    pose = hand_generator.make_pose_class((("extended", "extended", "curled", "curled"), "spread", "tucked"))
    person = hand_generator.make_person()
    orientation = np.zeros(3)

    def capture(**kwargs):
        return hand_capture(hand_generator, pose, person, orientation, **kwargs)

    return {"pose": pose, "person": person, "orientation": orientation, "capture": capture}


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# conftest.py holds shared pytest fixtures: seeded synthetic hand / signature
# generators and a simulated "gesture user" whose capture() returns API-shaped
# static samples (same pose, same hand, small natural variation), so tests
# exercise the full production preprocessing path without a webcam.
# =============================================================================
