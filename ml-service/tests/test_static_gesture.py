import numpy as np
import pytest

from airauth.common.errors import BiometricInputError
from airauth.static_gesture import features, verifier
from airauth.static_gesture.synthetic_hand import SyntheticHandGenerator
from tests.conftest import hand_capture


def test_feature_vector_has_expected_size(gesture_user):
    vector, handedness, quality = verifier.extract(gesture_user["capture"]())
    assert vector.shape == (features.FEATURE_DIM,)
    assert features.pose_vector(vector).shape == (features.POSE_FEATURE_DIM,)
    assert handedness == "Right"
    assert quality["frames"] == 10


def test_features_are_translation_and_scale_invariant(hand_generator, gesture_user):
    frames = hand_generator.render(gesture_user["pose"], gesture_user["person"], np.zeros(3), n_frames=1)[0]
    moved = frames * 1.7 + np.array([0.2, -0.1, 0.0])
    assert np.allclose(
        features.pose_vector(features.extract_frame_features(frames)),
        features.pose_vector(features.extract_frame_features(moved)),
        atol=1e-6,
    )


def test_genuine_gesture_is_accepted(gesture_user):
    template, report = verifier.enroll([gesture_user["capture"]() for _ in range(5)])
    assert report["samples"] == 5

    accepted = [verifier.verify(template, gesture_user["capture"]())["accepted"] for _ in range(5)]
    assert sum(accepted) >= 4


def test_different_gesture_is_rejected(hand_generator, gesture_user):
    template, _ = verifier.enroll([gesture_user["capture"]() for _ in range(5)])

    other_pose = hand_generator.make_pose_class((("curled", "curled", "curled", "curled"), "together", "out"))
    probe = hand_capture(hand_generator, other_pose, hand_generator.make_person(), np.zeros(3))

    result = verifier.verify(template, probe)
    assert result["accepted"] is False
    assert result["reason"] == "gesture_mismatch"


def test_wrong_hand_is_rejected(gesture_user):
    template, _ = verifier.enroll([gesture_user["capture"]() for _ in range(5)])
    result = verifier.verify(template, gesture_user["capture"](handedness="Left"))
    assert result["accepted"] is False
    assert result["reason"] == "wrong_hand"


def test_exact_replay_is_rejected(gesture_user):
    samples = [gesture_user["capture"]() for _ in range(5)]
    template, _ = verifier.enroll(samples)
    result = verifier.verify(template, samples[0])
    assert result["accepted"] is False
    assert result["reason"] == "replay_suspected"


def test_enrollment_rejects_mixed_gestures(hand_generator, gesture_user):
    samples = [gesture_user["capture"]() for _ in range(4)]
    other_pose = hand_generator.make_pose_class((("curled", "curled", "curled", "curled"), "together", "out"))
    samples.append(hand_capture(hand_generator, other_pose, gesture_user["person"], np.zeros(3)))

    with pytest.raises(BiometricInputError) as error:
        verifier.enroll(samples)
    assert error.value.code == "inconsistent_enrollment"
    assert error.value.details["sample_index"] == 4


def test_moving_hand_is_rejected():
    generator = SyntheticHandGenerator(5)
    pose = generator.make_pose_class((("extended",) * 4, "spread", "out"))
    person = generator.make_person()
    frames = [generator.render(pose, person, np.zeros(3), n_frames=1)[0] for _ in range(8)]
    sample = {"frames": [{"landmarks": f.tolist(), "handedness": "Right"} for f in frames]}

    with pytest.raises(BiometricInputError) as error:
        verifier.extract(sample)
    assert error.value.code == "unstable_pose"


def test_too_few_frames():
    with pytest.raises(BiometricInputError) as error:
        verifier.extract({"frames": []})
    assert error.value.code == "too_few_frames"


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# test_static_gesture.py checks Step 1 end to end on synthetic hands:
# feature dimensions and invariance, acceptance of the genuine gesture,
# rejection of a different gesture, the wrong hand and an exact replay,
# enrollment consistency checking (identifies the bad sample) and capture
# validation (moving hand, too few frames).
# =============================================================================
