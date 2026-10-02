import numpy as np
import pytest

from airauth import config
from airauth.common.errors import BiometricInputError
from airauth.data.dataset_loader import load_research_signatures
from airauth.dynamic_signature import features, verifier
from airauth.dynamic_signature.dtw import dtw_distance
from airauth.dynamic_signature.preprocessing import preprocess_signature


def test_preprocessing_output_shape(signature_generator):
    processed = preprocess_signature(signature_generator.render(signature_generator.make_writer()))
    assert processed.xy.shape == (config.SEQUENCE_LENGTH, 2)
    assert np.allclose(processed.xy.mean(axis=0), 0.0, atol=1e-9)
    assert np.isclose(np.ptp(processed.xy, axis=0).max(), 1.0)
    assert features.sequence_features(processed.xy).shape == (config.SEQUENCE_LENGTH, 9)
    assert features.global_features(processed).shape == (len(features.GLOBAL_FEATURE_NAMES),)


def test_spike_is_corrected():
    t = np.linspace(0, 2, 60)
    x = 0.4 + 0.2 * np.cos(2 * np.pi * t / 2)
    y = 0.5 + 0.2 * np.sin(2 * np.pi * t / 2)
    x[30] += 0.3
    sample = {"points": np.column_stack([t, x, y, np.zeros_like(t)]).tolist()}
    assert preprocess_signature(sample).corrected_spikes == 1


def test_dtw_is_zero_for_identical_and_symmetric(signature_generator):
    a = preprocess_signature(signature_generator.render(signature_generator.make_writer())).xy
    b = preprocess_signature(signature_generator.render(signature_generator.make_writer())).xy
    assert dtw_distance(a, a) == pytest.approx(0.0)
    assert dtw_distance(a, b) == pytest.approx(dtw_distance(b, a))


def test_genuine_accepted_and_other_writer_rejected(signature_generator):
    writer = signature_generator.make_writer()
    template, report = verifier.enroll([signature_generator.render(writer) for _ in range(8)])
    assert report["samples"] == 8

    genuine = [verifier.verify(template, signature_generator.render(writer))["accepted"] for _ in range(5)]
    assert sum(genuine) >= 4

    impostor = [
        verifier.verify(template, signature_generator.render(signature_generator.make_writer()))["accepted"]
        for _ in range(5)
    ]
    assert sum(impostor) == 0


def test_replay_is_rejected(signature_generator):
    writer = signature_generator.make_writer()
    samples = [signature_generator.render(writer) for _ in range(5)]
    template, _ = verifier.enroll(samples)
    result = verifier.verify(template, samples[2])
    assert result["accepted"] is False
    assert result["reason"] == "replay_suspected"


def test_too_short_signature():
    sample = {"points": [[i * 0.03, 0.5, 0.5, 0.0] for i in range(5)]}
    with pytest.raises(BiometricInputError) as error:
        preprocess_signature(sample)
    assert error.value.code == "too_short"


def test_template_adaptation_keeps_enrollment_and_caps_size(signature_generator):
    writer = signature_generator.make_writer()
    template, _ = verifier.enroll([signature_generator.render(writer) for _ in range(5)])
    original = template["trajectories"][:5]

    for _ in range(config.DYNAMIC_MAX_TEMPLATE_SAMPLES + 3):
        template = verifier.adapt_template(template, preprocess_signature(signature_generator.render(writer)))

    assert len(template["trajectories"]) == config.DYNAMIC_MAX_TEMPLATE_SAMPLES
    assert template["trajectories"][:5] == original
    assert template["enrolled_count"] == 5


@pytest.mark.skipif(not load_research_signatures(), reason="research dataset not available")
def test_research_dataset_loads_and_preprocesses():
    records = load_research_signatures()
    processed = [preprocess_signature(record["sample"]) for record in records[:10]]
    assert all(p.xy.shape == (config.SEQUENCE_LENGTH, 2) for p in processed)


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# test_dynamic_signature.py checks Step 2: preprocessing output shape and
# normalisation, spike correction, DTW identity/symmetry, acceptance of the
# genuine writer and rejection of other writers, replay detection, input
# validation and template adaptation (original enrollment preserved, size
# capped), plus loading the real research dataset when present.
# =============================================================================
