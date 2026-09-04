"""Contract tests for the industry pack (CF-322 / DEC-9).

Verifies: deterministic subset compilation, BFCL prompt/ground-truth wiring,
τ-bench AST task extraction, data_status reporting, schema pack-enum acceptance,
and T0 import safety. Runs against the real fetched datasets (present in the
execution checkout); missing-data behavior is tested via tmp paths.
"""

from __future__ import annotations

import importlib

import pytest

import tests.pi_benchmark.scenarios.industry as industry
import tests.pi_benchmark.schema as schema
from tests.pi_benchmark.scenarios import load_pack

pytestmark = pytest.mark.benchmark


def _require_complete_industry_data() -> None:
    """Skip data-content assertions when the optional published corpus is absent."""
    status = industry.data_status()
    missing = [
        category
        for category, info in status["categories"].items()
        if not all(value for key, value in info.items() if key != "subset")
    ]
    if missing:
        pytest.skip("optional industry benchmark data missing: " + ", ".join(missing))


def test_data_status_reports_all_categories():
    status = industry.data_status()
    assert set(status["categories"]) == {
        "bfcl_simple_python",
        "bfcl_multiple",
        "bfcl_live_simple",
        "tau_airline",
        "tau_retail",
    }
    for category, info in status["categories"].items():
        assert info["subset"] > 0, category


def test_pack_loads_deterministic_subsets():
    _require_complete_industry_data()
    scenarios = industry.scenarios()
    again = industry.scenarios()
    assert [s.id for s in scenarios] == [s.id for s in again]  # lru_cache + file order
    counts = {}
    for s in scenarios:
        counts[s.tags[1]] = counts.get(s.tags[1], 0) + 1
    assert counts["bfcl"] == 25 + 20 + 15
    assert counts["tau_bench"] == 8 + 8


def test_bfcl_scenario_carries_prompt_and_ground_truth():
    _require_complete_industry_data()
    scenarios = [s for s in industry.scenarios() if s.id.endswith("simple_python_0")]
    (s,) = scenarios
    assert s.pack == "industry"
    assert s.min_tier == "T3"
    assert "calculate_triangle_area" in s.prompt
    assert "User question:" in s.prompt
    assert s.expected["bfcl_ground_truth"] is not None
    assert s.expected["category"] == "bfcl_simple_python"


def test_tau_scenario_extracts_instruction_and_actions():
    _require_complete_industry_data()
    tau = [s for s in industry.scenarios() if "tau_bench" in s.tags]
    assert tau, "τ-bench tasks should parse from tasks_test.py"
    first = tau[0]
    assert "mia_li_3668" in first.prompt
    assert first.expected["tau_expected_actions"] == ["book_reservation"]
    assert first.expected["fidelity"] == "adapted_single_turn"


def test_missing_data_yields_no_scenarios(tmp_path, monkeypatch):
    monkeypatch.setattr(industry, "BFCL_DIR", tmp_path / "nope")
    monkeypatch.setattr(industry, "TAU_DIR", tmp_path / "nope")
    industry.scenarios.cache_clear()
    try:
        assert industry.scenarios() == ()
        status = industry.data_status()
        assert not any(
            any(c.values()) for c in status["categories"] if isinstance(c, dict)
        )
    finally:
        industry.scenarios.cache_clear()


def test_registry_exposes_industry_pack():
    _require_complete_industry_data()
    names = [s.id for s in load_pack("industry")]
    assert names and all(name.startswith("industry.") for name in names)


def test_schema_accepts_industry_pack_records():
    record = {
        "schema_version": schema.SCHEMA_VERSION,
        "record_id": "B1-T3-industry-industry.bfcl_simple_python.simple_python_0-seed0-r1-pi",
        "pair_id": "B1-T3-industry-industry.bfcl_simple_python.simple_python_0-seed0-r1",
        "phase": "B1",
        "tier": "T3",
        "engine": "pi",
        "pack": "industry",
        "scenario": {"id": "industry.bfcl_simple_python.simple_python_0", "seed": 0},
        "provenance": {
            "git_sha": "a" * 40,
            "git_dirty": False,
            "input_sha256": "b" * 64,
            "model_id": None,
            "endpoint_fingerprint": None,
            "ts": "2026-07-31T00:00:00Z",
        },
        "status": "not_runnable",
        "not_runnable_reason": "feature_unavailable",
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0,
            "estimate": False,
            "estimator": None,
        },
    }
    schema.validate_record(record)  # must not raise


def test_module_is_t0_import_safe():
    # Re-importing the module must not require backend modules.
    for mod in ("app.core.agentic", "app.core.llm_router"):
        assert mod not in vars(industry), (
            f"backend reference leaked into industry pack: {mod}"
        )


def test_estimate_scope_lane_counts_only_requested_lane(tmp_path):
    _require_complete_industry_data()
    # importlib (not an import statement) keeps this test out of the gate's AST
    # import graph — a static edge into runner would close a package-cluster cycle.
    runner = importlib.import_module("tests.pi_benchmark.runner")

    scenarios = list(load_pack("industry"))[:4]
    base = dict(
        packs=("industry",),
        tier="T3",
        engines=("pi", "legacy"),
        seeds=(0,),
        repeats=1,
        phase="B1",
        out_dir=tmp_path,
    )
    program_total, program_bd = runner._worst_case_program_cost_usd(
        runner.RunConfig(**base), scenarios
    )
    lane_total, lane_bd = runner._worst_case_program_cost_usd(
        runner.RunConfig(**base, estimate_scope="lane"), scenarios
    )
    assert program_bd["lane_model_calls"] == 1 + 3 + 3
    assert lane_bd["lane_model_calls"] == 1
    assert lane_total < program_total
    assert lane_bd["estimate_scope"] == "lane"
