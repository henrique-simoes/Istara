"""Contract tests for the paired runner (task B0-4). Pure tier-T0."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from dataclasses import replace
from pathlib import Path

import pytest

from tests.pi_benchmark import schema
from tests.pi_benchmark import runner
from tests.pi_benchmark import scheduler
from tests.pi_benchmark.live_driver import LiveCapture
from tests.pi_benchmark.runner import (
    LiveConsentRequired,
    OwnerGateRequired,
    RunConfig,
    build_config_from_args,
    run_benchmark,
    write_run,
)
from tests.pi_benchmark.scenarios import load_pack

pytestmark = pytest.mark.benchmark


def _canonical_t0(**overrides) -> RunConfig:
    base = dict(
        packs=("canonical",), tier="T0", engines=("pi", "legacy"), seeds=(0,),
        repeats=1, phase="B1", out_dir=Path("/tmp/pi-benchmark-unused"),
    )
    base.update(overrides)
    return RunConfig(**base)


def test_canonical_both_engines_emits_paired_schema_valid_records():
    summary = run_benchmark(_canonical_t0())
    # 15 scenarios × 1 seed × 1 repeat × 2 engines.
    assert len(summary.records) == 30
    assert summary.counts == {"ok": 30}
    for record in summary.records:
        # Every record is on-contract (acceptance A1 / A5).
        assert schema.is_valid(record)
        assert record["tier"] == "T0"
        assert record["engine"] in ("pi", "legacy")


def test_pairing_and_order_control():
    summary = run_benchmark(_canonical_t0())
    by_pair: dict[str, list[dict]] = {}
    for record in summary.records:
        by_pair.setdefault(record["pair_id"], []).append(record)
    # Each pair has exactly the two engine arms sharing one input hash.
    for arms in by_pair.values():
        assert {a["engine"] for a in arms} == {"pi", "legacy"}
        assert arms[0]["provenance"]["input_sha256"] == arms[1]["provenance"]["input_sha256"]
        assert arms[0]["scenario"]["order"] == arms[1]["scenario"]["order"]
    # Order alternates across pairs (both order classes appear).
    orders = {arms[0]["scenario"]["order"] for arms in by_pair.values()}
    assert orders == {"legacy_first", "pi_first"}


def test_deterministic_outcome_classes_match_across_repeats():
    # Acceptance A5: repeats of the same seed produce matching outcome classes.
    summary = run_benchmark(_canonical_t0(repeats=3))
    classes: dict[tuple[str, str], set[str]] = {}
    for record in summary.records:
        key = (record["scenario"]["id"], record["engine"])
        classes.setdefault(key, set()).add(record["extensions"]["outcome_class"])
    for key, seen in classes.items():
        assert len(seen) == 1, f"non-deterministic outcome class for {key}: {seen}"


def test_spine_pack_at_t0_is_not_runnable_with_a_reason():
    summary = run_benchmark(_canonical_t0(packs=("spine",), engines=("pi",)))
    assert summary.counts.get("not_runnable") == len(summary.records)
    for record in summary.records:
        # Never dropped: counted with a typed, schema-valid reason.
        assert record["not_runnable_reason"] == "feature_unavailable"
        assert schema.is_valid(record)


def test_t2_without_owner_gate_is_refused():
    with pytest.raises(OwnerGateRequired):
        run_benchmark(_canonical_t0(tier="T2", phase="B2"))


def test_t2_with_gate_but_without_live_consent_is_refused(tmp_path):
    # The synthetic T2/T3 path is gone: live tiers need BOTH the owner gate and the
    # explicit --live consent flag before any dispatch or spend can happen.
    gate = tmp_path / "gate.json"
    gate.write_text("{}", encoding="utf-8")
    with pytest.raises(LiveConsentRequired):
        run_benchmark(_canonical_t0(tier="T2", phase="B2", owner_gate=gate))


def test_cli_t2_without_gate_exits_3(tmp_path):
    code = runner.main([
        "--pack", "canonical", "--tier", "T2", "--engine", "pi",
        "--out", str(tmp_path / "out"),
    ])
    assert code == 3


def test_cli_t2_with_gate_but_no_live_prints_plan_and_exits_0(tmp_path, capsys):
    gate = tmp_path / "gate.json"
    gate.write_text("{}", encoding="utf-8")
    code = runner.main([
        "--pack", "canonical", "--tier", "T2", "--engine", "pi",
        "--out", str(tmp_path / "out"), "--owner-gate", str(gate),
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "[plan]" in out and "no --live" in out
    assert not (tmp_path / "out" / "records").exists()  # no dispatch, no spend


def test_cli_rejects_non_deepseek_provider(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        build_config_from_args([
            "--pack", "canonical", "--tier", "T3", "--engine", "pi",
            "--out", str(tmp_path), "--provider", "claude",
        ])
    assert excinfo.value.code == 2


def test_cli_rejects_non_deepseek_model(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        build_config_from_args([
            "--pack", "canonical", "--tier", "T3", "--engine", "pi",
            "--out", str(tmp_path), "--model", "gpt-5.6-luna",
        ])
    assert excinfo.value.code == 2


# ── wave mode (fake Lane A modules injected via sys.modules) ────────────────


def _fake_lane_a_modules():
    """Fake Lane A scheduler/budget_ledger/deepseek_provider (exact quoted surfaces)."""
    scheduler = types.ModuleType("tests.pi_benchmark.scheduler")
    scheduler.load_manifest = lambda path: _FAKE_MANIFEST
    scheduler.completed_unit_ids = lambda records_dir: {
        p.stem for p in Path(records_dir).glob("*.json") if not p.name.endswith(".tmp")
    }

    ledger_mod = types.ModuleType("tests.pi_benchmark.budget_ledger")

    class BudgetExceeded(RuntimeError):
        pass

    class BudgetLedger:
        def __init__(self, path, cap_usd=1.00):
            self.path, self.cap_usd, self._spent = path, cap_usd, 0.0

        def reserve(self, call_id, max_cost_usd, *, kind, meta=None):
            pass

        def commit(self, call_id, actual_cost_usd, *, usage, meta=None):
            self._spent += actual_cost_usd

        def release(self, call_id, *, reason):
            pass

        def spent_usd(self):
            return self._spent

        def outstanding(self):
            return {}

        def close(self):
            return {"spent_usd": self._spent}

        @property
        def closed(self):
            return False

    ledger_mod.BudgetExceeded = BudgetExceeded
    ledger_mod.BudgetLedger = BudgetLedger

    provider_mod = types.ModuleType("tests.pi_benchmark.deepseek_provider")

    class DeepSeekProvider:
        def __init__(self, *, provider, model, **kwargs):
            self.provider, self.model = provider, model

        def estimate_cost(self, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0):
            return (input_tokens * 0.55 + output_tokens * 2.19) / 1e6

        def endpoint_fingerprint(self):
            return "deepseek:fedcba098765"

    provider_mod.DeepSeekProvider = DeepSeekProvider
    return scheduler, ledger_mod, provider_mod


_FAKE_MANIFEST: dict = {}


def _wave_config(tmp_path, wave=1):
    gate = tmp_path / "gate.json"
    gate.write_text("{}", encoding="utf-8")
    return RunConfig(
        packs=("canonical",), tier="T3", engines=("pi",), seeds=(0,), repeats=1,
        phase="B2", out_dir=tmp_path / "out", owner_gate=gate, live=True,
        wave=wave, max_processes=1, manifest=tmp_path / "manifest.json",
        budget_ledger=tmp_path / "ledger.json",
    )


def test_wave_mode_executes_shard_then_resume_skips_completed(monkeypatch, tmp_path):
    global _FAKE_MANIFEST
    scenario_id = load_pack("canonical")[0].id
    unit = {
        "unit_id": f"B2-T3-canonical-{scenario_id}-seed0-r1-pi", "pack": "canonical",
        "scenario_id": scenario_id, "seed": 0, "repeat": 1, "engine": "pi",
        "phase": "B2", "moa_mode": None,
    }
    _FAKE_MANIFEST = {"shards": [[unit]], "budget_cap_usd": 1.0, "moa_n": 3, "repeats": 1}
    scheduler, ledger_mod, provider_mod = _fake_lane_a_modules()
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.scheduler", scheduler)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.budget_ledger", ledger_mod)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.deepseek_provider", provider_mod)

    capture = LiveCapture(
        text="wave output", usage={
            "input_tokens": 40, "output_tokens": 12, "cache_read_tokens": 0,
            "cache_write_tokens": 0, "total_tokens": 52,
        },
        estimate=False, endpoint_ids=("pi-deepseek-default",),
        route_evidence=({"endpoint_id": "pi-deepseek-default"},), raw_method=None,
    )

    async def dispatch(**kwargs):
        return capture

    code, records = runner.run_wave(_wave_config(tmp_path), dispatch=dispatch)
    assert code == 0 and len(records) == 1
    record = records[0]
    assert record["status"] == "ok"
    assert schema.is_valid(record)
    assert record["extensions"]["wave"] == {"index": 1}
    record_path = tmp_path / "out" / "records" / f"{unit['unit_id']}.json"
    assert record_path.is_file()

    # Resume: a repeated wave command produces no duplicate work.
    async def exploding_dispatch(**kwargs):  # pragma: no cover - must never run
        raise AssertionError("completed unit must not re-dispatch")

    code, records = runner.run_wave(_wave_config(tmp_path), dispatch=exploding_dispatch)
    assert code == 0 and records == []


def test_wave_mode_dispatches_all_pending_units_on_one_event_loop(monkeypatch, tmp_path):
    """A wave must not bind the singleton Pi supervisor to one loop per unit."""
    global _FAKE_MANIFEST
    scenario_id = load_pack("canonical")[0].id
    units = [
        {
            "unit_id": f"B1-T3-canonical-{scenario_id}-seed0-r{repeat}-pi",
            "pack": "canonical", "scenario_id": scenario_id, "seed": 0,
            "repeat": repeat, "engine": "pi", "phase": "B1", "moa_mode": None,
        }
        for repeat in (1, 2)
    ]
    _FAKE_MANIFEST = {"shards": [units], "budget_cap_usd": 1.0, "moa_n": 3}
    scheduler, ledger_mod, provider_mod = _fake_lane_a_modules()
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.scheduler", scheduler)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.budget_ledger", ledger_mod)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.deepseek_provider", provider_mod)

    capture = LiveCapture(
        text="wave output", usage={
            "input_tokens": 40, "output_tokens": 12, "cache_read_tokens": 0,
            "cache_write_tokens": 0, "total_tokens": 52,
        }, estimate=False, endpoint_ids=("pi-deepseek-default",),
        route_evidence=({"endpoint_id": "pi-deepseek-default"},), raw_method=None,
    )
    loops = []

    async def dispatch(**kwargs):
        loops.append(asyncio.get_running_loop())
        return capture

    code, records = runner.run_wave(_wave_config(tmp_path), dispatch=dispatch)

    assert code == 0 and len(records) == len(units)
    assert len(loops) == len(units)
    assert loops[0] is loops[1]


def test_wave_mode_executes_manifest_written_by_scheduler(monkeypatch, tmp_path):
    """The real B0 manifest can be consumed directly by a B1 wave."""
    scenario_id = load_pack("canonical")[0].id
    unit = scheduler.RunUnit(
        unit_id=f"B1-T3-canonical-{scenario_id}-seed0-r0-pi",
        pack="canonical", scenario_id=scenario_id, seed=0, repeat=0,
        engine="pi", phase="B1", moa_mode=None,
    )
    manifest_path = tmp_path / "manifest.json"
    scheduler.write_manifest(
        manifest_path, max_processes=1, provider="deepseek", model="deepseek-v4-pro",
        budget_cap_usd=1.0, moa_n=3, repeats=1, tier="T3", shards=[[unit]],
    )

    _, ledger_mod, provider_mod = _fake_lane_a_modules()
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.scheduler", scheduler)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.budget_ledger", ledger_mod)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.deepseek_provider", provider_mod)

    capture = LiveCapture(
        text="manifest output", usage={
            "input_tokens": 40, "output_tokens": 12, "cache_read_tokens": 0,
            "cache_write_tokens": 0, "total_tokens": 52,
        },
        estimate=False, endpoint_ids=("pi-deepseek-default",),
        route_evidence=({"endpoint_id": "pi-deepseek-default"},), raw_method=None,
    )

    async def dispatch(**kwargs):
        return capture

    config = replace(_wave_config(tmp_path, wave=1), phase="B1", manifest=manifest_path)
    code, records = runner.run_wave(config, dispatch=dispatch)
    assert code == 0 and len(records) == 1
    assert records[0]["extensions"]["unit_id"] == unit.unit_id
    assert (tmp_path / "out" / "records" / f"{unit.unit_id}.json").is_file()


def test_wave_out_of_range_exits_2(monkeypatch, tmp_path):
    global _FAKE_MANIFEST
    _FAKE_MANIFEST = {"shards": [[]], "budget_cap_usd": 1.0, "moa_n": 3}
    scheduler, ledger_mod, provider_mod = _fake_lane_a_modules()
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.scheduler", scheduler)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.budget_ledger", ledger_mod)
    monkeypatch.setitem(sys.modules, "tests.pi_benchmark.deepseek_provider", provider_mod)
    code, records = runner.run_wave(_wave_config(tmp_path, wave=2))
    assert code == 2 and records == []


def test_write_run_round_trips_and_revalidates(tmp_path):
    summary = run_benchmark(_canonical_t0(out_dir=tmp_path / "b1-t0"))
    out = write_run(summary)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["record_count"] == 30
    assert manifest["scenario_count"] == 15
    record_files = list((out / "records").glob("*.json"))
    assert len(record_files) == 30
    for path in record_files:
        schema.validate_record(json.loads(path.read_text()))


def test_cli_arg_parsing():
    config = build_config_from_args(
        ["--pack", "all", "--tier", "T1", "--engine", "both", "--seeds", "0,1",
         "--repeats", "2", "--out", "/tmp/x"]
    )
    assert config.packs == runner.STATIC_PACKS
    assert config.tier == "T1"
    assert config.engines == ("pi", "legacy")
    assert config.seeds == (0, 1)
    assert config.repeats == 2


def test_cli_rejects_unknown_pack():
    with pytest.raises(SystemExit):
        build_config_from_args(["--pack", "bogus", "--tier", "T0", "--engine", "pi", "--out", "/tmp/x"])


# ── B0 plan-only scheduling (offline manifest gate) ─────────────────────────


def _plan_only_args(tmp_path, *extra):
    return [
        "--pack", "canonical", "--tier", "T3", "--engine", "pi",
        "--out", str(tmp_path / "b0"), "--max-processes", "2",
        "--plan-only", *extra,
    ]


def test_plan_only_requires_max_processes(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        build_config_from_args([
            "--pack", "canonical", "--tier", "T3", "--engine", "pi",
            "--out", str(tmp_path), "--plan-only",
        ])
    assert excinfo.value.code == 2


def test_plan_only_writes_immutable_manifest_and_is_idempotent(tmp_path, capsys):
    code = runner.main(_plan_only_args(tmp_path))
    assert code == 0
    out = capsys.readouterr().out
    assert "[plan] B0 schedule:" in out and "no dispatch, no spend" in out
    manifest_path = tmp_path / "b0" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["max_processes"] == 2
    assert manifest["provider"] == "deepseek"
    assert manifest["model"] == "deepseek-v4-pro"
    assert manifest["budget_cap_usd"] == 1.0
    assert manifest["shard_count"] == 2 and len(manifest["shards"]) == 2
    # Disjoint + complete shard map.
    flat = [u for shard in manifest["shards"] for u in shard]
    assert len(flat) == len(set(flat)) == len(manifest["units"])
    first_bytes = manifest_path.read_bytes()

    # Identical re-run resumes the same manifest without rewriting it.
    code = runner.main(_plan_only_args(tmp_path))
    assert code == 0
    assert manifest_path.read_bytes() == first_bytes


def test_plan_only_refuses_a_conflicting_manifest(tmp_path):
    assert runner.main(_plan_only_args(tmp_path)) == 0
    # Same path, different schedule arguments -> the immutable manifest refuses.
    code = runner.main(_plan_only_args(tmp_path, "--budget-usd", "0.50"))
    assert code == 2


def test_plan_only_moa_mode_is_baked_into_units(tmp_path):
    code = runner.main(_plan_only_args(tmp_path, "--moa-mode", "self_moa"))
    assert code == 0
    manifest = json.loads((tmp_path / "b0" / "manifest.json").read_text(encoding="utf-8"))
    modes = {unit["moa_mode"] for unit in manifest["units"].values()}
    assert modes == {"self_moa"}
    assert manifest["moa_n"] == 3
    # moa_n (samples), repeats, and max_processes stay separate manifest fields.
    assert manifest["repeats"] == 1 and manifest["max_processes"] == 2


# ── RT-2: dry-run worst-case estimate gate ──────────────────────────────────


def _full_retake_plan_args(tmp_path, *extra):
    return [
        "--pack", "canonical,spine,a2a", "--tier", "T3", "--engine", "both",
        "--seeds", "0", "--repeats", "1", "--out", str(tmp_path / "b0"),
        "--max-processes", "4", "--plan-only", *extra,
    ]


def test_plan_only_prints_estimate_and_writes_manifest_within_cap(tmp_path, capsys):
    # The default retake schedule (22 scenarios × both engines × 3 shared-ledger MoA lanes)
    # is comfortably under the $1.00 cap (~$0.73), so the estimate prints and the manifest
    # is written (acceptance AC-3).
    code = runner.main(_full_retake_plan_args(tmp_path))
    assert code == 0
    out = capsys.readouterr().out
    assert "worst-case program estimate:" in out
    manifest = json.loads((tmp_path / "b0" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["max_processes"] == 4


def test_plan_only_over_budget_estimate_exits_2_without_manifest(tmp_path, capsys):
    # repeats=2 roughly doubles the schedule to ~$1.47 > $1.00; the gate must refuse before
    # any manifest write or live call, leaving nothing behind (acceptance AC-3).
    code = runner.main(_full_retake_plan_args(tmp_path, "--repeats", "2"))
    assert code == 2
    err = capsys.readouterr().err
    assert "exceeds budget" in err
    assert not (tmp_path / "b0" / "manifest.json").exists()


def test_worst_case_estimate_arithmetic_is_deterministic():
    from tests.pi_benchmark import live_driver
    from tests.pi_benchmark.deepseek_provider import DeepSeekProvider

    config = _canonical_t0(tier="T3", phase="B1", engines=("pi", "legacy"), moa_n=3)
    scenarios = load_pack("canonical")
    total, breakdown = runner._worst_case_program_cost_usd(config, scenarios)
    # none(1) + self_moa(moa_n=3) + full_ensemble(max(3, moa_n)=3) = 7 model-calls/unit.
    assert breakdown["lane_model_calls"] == 7
    assert breakdown["units_per_lane"] == len(scenarios) * 2  # 1 seed × 1 repeat × 2 engines
    # Smoke prompts are tiny, so the reservation floors at MIN_RESERVE_INPUT_TOKENS.
    assert breakdown["reserve_input_tokens"] == live_driver.MIN_RESERVE_INPUT_TOKENS
    provider = DeepSeekProvider(provider="deepseek", model="deepseek-v4-pro")
    per_call = provider.estimate_cost(live_driver.MIN_RESERVE_INPUT_TOKENS, live_driver.DEFAULT_MAX_TOKENS)
    preflight = provider.estimate_cost(live_driver.MIN_RESERVE_INPUT_TOKENS, 1)
    expected = round(breakdown["units_per_lane"] * 7 * per_call + preflight, 7)
    assert total == pytest.approx(expected)
    assert total < 1.00  # the default program fits the cumulative $1.00 envelope
