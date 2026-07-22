"""Contract tests for the paired runner (task B0-4). Pure tier-T0."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.pi_benchmark import schema
from tests.pi_benchmark import runner
from tests.pi_benchmark.runner import (
    OwnerGateRequired,
    RunConfig,
    build_config_from_args,
    run_benchmark,
    write_run,
)

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


def test_t2_with_gate_artifact_is_not_yet_implemented(tmp_path):
    gate = tmp_path / "gate.json"
    gate.write_text("{}", encoding="utf-8")
    # A gate artifact clears the fail-closed refusal, but live execution (which would load
    # a model) is deliberately owner-gated future work — never a silent empty result.
    with pytest.raises(NotImplementedError):
        run_benchmark(_canonical_t0(tier="T2", phase="B2", owner_gate=gate))


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
