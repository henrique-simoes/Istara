"""Adaptive validation scoring guardrails."""

from app.core.adaptive_validation import _sample_confidence_weight


def test_sample_confidence_weight_penalizes_tiny_samples():
    assert _sample_confidence_weight(0) == 0
    assert 0 < _sample_confidence_weight(1) < _sample_confidence_weight(4)
    assert _sample_confidence_weight(5) == 1
    assert _sample_confidence_weight(100) == 1
