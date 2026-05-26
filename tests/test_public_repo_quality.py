from __future__ import annotations

from scripts.public_repo_quality_audit import audit


def test_public_repo_quality_audit_passes() -> None:
    assert audit() == []
