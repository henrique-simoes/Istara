"""QA capabilities declaration contract tests (consulted, not authoritative)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_qa_capabilities import (
    DETERMINISTIC_OBLIGATIONS,
    LIVE_OBLIGATIONS,
    SPINE_OBLIGATION,
    validate,
)

ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES = ROOT / "qa" / "runtime_capabilities.json"


def test_capabilities_validate_clean():
    assert validate(CAPABILITIES) == []


def test_capabilities_every_surface_has_deterministic():
    data = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    for surface in data["surfaces"]:
        assert surface["deterministic"], f"{surface['id']} has no deterministic obligations"
        assert set(surface["deterministic"]) <= DETERMINISTIC_OBLIGATIONS
        assert set(surface.get("live_optional", [])) <= LIVE_OBLIGATIONS


def test_capabilities_spine_touch_requires_synthetic_provisional():
    data = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    for surface in data["surfaces"]:
        if surface.get("spine_touch"):
            assert SPINE_OBLIGATION in surface["deterministic"]


def test_validate_rejects_unknown_obligation(tmp_path):
    bad = tmp_path / "caps.json"
    bad.write_text(
        json.dumps(
            {
                "version": 1,
                "surfaces": [
                    {
                        "id": "x",
                        "paths": ["a"],
                        "deterministic": ["not_a_real_obligation"],
                        "live_optional": [],
                        "spine_touch": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    issues = validate(bad)
    assert any("unknown deterministic obligations" in i for i in issues)


def test_validate_rejects_surface_without_deterministic(tmp_path):
    bad = tmp_path / "caps.json"
    bad.write_text(
        json.dumps(
            {
                "version": 1,
                "surfaces": [
                    {
                        "id": "y",
                        "paths": ["a"],
                        "deterministic": [],
                        "live_optional": ["authorized_live"],
                        "spine_touch": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    issues = validate(bad)
    assert any("at least one deterministic obligation" in i for i in issues)


def test_validate_rejects_non_bool_spine_touch(tmp_path):
    bad = tmp_path / "caps.json"
    bad.write_text(
        json.dumps(
            {
                "version": 1,
                "surfaces": [
                    {
                        "id": "z",
                        "paths": ["a"],
                        "deterministic": ["governance"],
                        "live_optional": [],
                        "spine_touch": "yes",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    issues = validate(bad)
    assert any("spine_touch must be a boolean" in i for i in issues)


def test_validate_rejects_invalid_json(tmp_path):
    bad = tmp_path / "caps.json"
    bad.write_text("{not json", encoding="utf-8")
    assert validate(bad)  # non-empty issues
