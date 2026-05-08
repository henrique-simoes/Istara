from __future__ import annotations

from scripts.security_release_readiness import evaluate_readiness


def test_release_security_readiness_passes() -> None:
    result = evaluate_readiness()

    assert result["status"] == "pass"
    assert result["issues"] == []
    assert float(result["minimum_score_percent"]) >= 98
