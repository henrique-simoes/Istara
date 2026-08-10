"""Contract tests for the feature-criteria compiler (task B0-6). Pure tier-T0."""

from __future__ import annotations

import pytest

from tests.pi_benchmark import schema
from tests.pi_benchmark.feature_criteria import (
    CRITERIA,
    compile_features,
    coverage_summary,
)

pytestmark = pytest.mark.benchmark


def _record_with(block: dict) -> dict:
    return {
        "schema_version": "1.0.0",
        "record_id": "r", "pair_id": "p", "phase": "B2", "tier": "T2",
        "engine": "pi", "pack": "features",
        "scenario": {"id": "s", "seed": 0},
        "provenance": {
            "git_sha": "abcdef1", "git_dirty": False,
            "input_sha256": "0" * 64, "ts": "2026-07-22T00:00:00Z",
        },
        "status": "ok",
        "usage": {"estimate": False},
        "metrics": {"feature_integration": block},
    }


def test_every_inventory_feature_is_compiled_once():
    compiled = compile_features()
    summary = coverage_summary(compiled)
    assert summary["total"] == len(compiled)
    assert summary["auto"] + summary["manual"] == summary["total"]
    # No feature dropped: ids are unique and cover the whole matrix denominator.
    ids = [c.feature_id for c in compiled]
    assert len(ids) == len(set(ids))
    assert summary["total"] >= 80  # inventory ships 86 features; guard against silent shrink


def test_auto_and_manual_are_both_present():
    # A meaningful compiler produces a mix, not a degenerate all-manual/all-auto matrix.
    summary = coverage_summary()
    assert summary["auto"] > 0
    assert summary["manual"] > 0


def test_derivability_rules():
    from tests.pi_benchmark.feature_criteria import _derivability
    both = _derivability({"api_refs": ["/x"], "test_refs": ["t"]})
    assert all(both.values())  # api + test → fully auto
    no_test = _derivability({"api_refs": ["/x"], "test_refs": []})
    assert no_test["evidence_emitted"] is False
    no_api = _derivability({"api_refs": [], "test_refs": ["t"]})
    assert no_api["reachable"] is False and no_api["expected_action"] is False


def test_compiled_blocks_are_schema_valid():
    for compiled in compile_features():
        block = compiled.to_metrics_block()
        assert set(block) == {"feature_id", "criteria", "criteria_scores"}
        assert block["criteria"] in ("auto", "manual")
        assert set(block["criteria_scores"]) == set(CRITERIA)
        assert schema.is_valid(_record_with(block))


def test_criteria_scores_start_null_for_the_live_runner_to_fill():
    block = compile_features()[0].to_metrics_block()
    assert all(v is None for v in block["criteria_scores"].values())
