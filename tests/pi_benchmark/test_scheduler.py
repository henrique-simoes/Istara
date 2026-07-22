"""Contract tests for the B0 offline scheduler and immutable manifest. Pure tier-T0."""

from __future__ import annotations

import json
import shutil
from collections import namedtuple
from pathlib import Path

import pytest

from tests.pi_benchmark.scheduler import (
    ManifestConflict,
    build_run_units,
    completed_unit_ids,
    load_manifest,
    shard_units,
    write_manifest,
)

pytestmark = pytest.mark.benchmark

FIXTURE_RECORD = (
    Path(__file__).resolve().parent / "fixtures" / "example_run_record.json"
)

FakeScenario = namedtuple("FakeScenario", ["id", "pack"])

SCENARIOS = [
    FakeScenario("01-chat", "canonical"),
    FakeScenario("02-tools", "canonical"),
    FakeScenario("07-delegation", "a2a"),
    FakeScenario("11-evidence", "spine"),
    FakeScenario("99-misc", "experiments"),  # unknown pack -> B2
]


def _units(moa_modes: tuple[str, ...] = ()):
    return build_run_units(
        scenarios=SCENARIOS,
        tier="T2",
        engines=("pi", "legacy"),
        seeds=(0, 1),
        repeats=2,
        moa_modes=moa_modes,
    )


def _manifest_kwargs(shards):
    return dict(
        max_processes=len(shards),
        provider="deepseek",
        model="deepseek-v4-pro",
        budget_cap_usd=1.00,
        moa_n=0,
        repeats=2,
        tier="T2",
        shards=shards,
    )


def test_unit_id_format_and_phase_mapping():
    units = build_run_units(
        scenarios=[FakeScenario("01-chat", "canonical")],
        tier="T2",
        engines=("pi",),
        seeds=(3,),
        repeats=1,
    )
    assert [u.unit_id for u in units] == ["B1-T2-canonical-01-chat-seed3-r0-pi"]
    assert units[0].phase == "B1"
    assert units[0].moa_mode is None

    by_pack = build_run_units(
        scenarios=SCENARIOS[2:], tier="T2", engines=("pi",), seeds=(0,), repeats=1
    )
    assert [(u.pack, u.phase) for u in by_pack] == [
        ("a2a", "B2"),
        ("spine", "B3"),
        ("experiments", "B2"),  # anything else -> B2
    ]

    moa = build_run_units(
        scenarios=[FakeScenario("01-chat", "canonical")],
        tier="T2",
        engines=("pi",),
        seeds=(0,),
        repeats=1,
        moa_modes=("self_moa", "full_ensemble"),
    )
    assert [u.unit_id for u in moa] == [
        "B1-T2-canonical-01-chat-seed0-r0-pi-self_moa",
        "B1-T2-canonical-01-chat-seed0-r0-pi-full_ensemble",
    ]


def test_build_order_is_scenario_seed_repeat_engine_moa():
    units = build_run_units(
        scenarios=[FakeScenario("a", "canonical"), FakeScenario("b", "canonical")],
        tier="T0",
        engines=("pi", "legacy"),
        seeds=(0, 1),
        repeats=2,
    )
    assert [u.unit_id for u in units[:6]] == [
        "B1-T0-canonical-a-seed0-r0-pi",
        "B1-T0-canonical-a-seed0-r0-legacy",
        "B1-T0-canonical-a-seed0-r1-pi",
        "B1-T0-canonical-a-seed0-r1-legacy",
        "B1-T0-canonical-a-seed1-r0-pi",
        "B1-T0-canonical-a-seed1-r0-legacy",
    ]
    # 2 scenarios x 2 seeds x 2 repeats x 2 engines.
    assert len(units) == 16


def test_shard_map_deterministic_disjoint_complete():
    first = shard_units(_units(), 3)
    second = shard_units(_units(), 3)
    assert [[u.unit_id for u in shard] for shard in first] == [
        [u.unit_id for u in shard] for shard in second
    ]
    flat = [u.unit_id for shard in first for u in shard]
    assert len(flat) == len(_units())
    assert len(set(flat)) == len(flat)  # disjoint
    assert set(flat) == {u.unit_id for u in _units()}  # complete
    # Round-robin: shard k holds units k, k+n, k+2n, ...
    assert [u.unit_id for u in first[0]] == [u.unit_id for u in _units()[::3]]


@pytest.mark.parametrize("bad_n", [0, -1])
def test_shard_rejects_invalid_n(bad_n):
    with pytest.raises(ValueError):
        shard_units(_units(), bad_n)


def test_write_manifest_records_separate_fields(tmp_path):
    shards = shard_units(_units(moa_modes=("self_moa",)), 4)
    manifest = write_manifest(tmp_path / "manifest.json", **_manifest_kwargs(shards))
    assert manifest["max_processes"] == 4
    assert manifest["moa_n"] == 0
    assert manifest["repeats"] == 2
    assert manifest["provider"] == "deepseek"
    assert manifest["model"] == "deepseek-v4-pro"
    assert manifest["budget_cap_usd"] == 1.00
    assert manifest["tier"] == "T2"
    assert manifest["shard_count"] == 4
    assert len(manifest["shards"]) == 4
    assert set(manifest["units"]) == {u.unit_id for u in _units(moa_modes=("self_moa",))}
    assert all(entry["status"] == "pending" for entry in manifest["units"].values())
    assert manifest["content_sha256"]


def test_write_manifest_idempotent_resume(tmp_path):
    path = tmp_path / "manifest.json"
    shards = shard_units(_units(), 3)
    first = write_manifest(path, **_manifest_kwargs(shards))
    bytes_after_first = path.read_bytes()
    second = write_manifest(path, **_manifest_kwargs(shards))
    # Identical arguments resume: file untouched, equal manifest returned.
    assert path.read_bytes() == bytes_after_first
    assert second == first


def test_write_manifest_conflict_on_different_args(tmp_path):
    path = tmp_path / "manifest.json"
    write_manifest(path, **_manifest_kwargs(shard_units(_units(), 3)))
    conflicting = _manifest_kwargs(shard_units(_units(), 3))
    conflicting["budget_cap_usd"] = 0.50
    with pytest.raises(ManifestConflict):
        write_manifest(path, **conflicting)
    different_tier = _manifest_kwargs(shard_units(_units(), 3))
    different_tier["tier"] = "T3"
    with pytest.raises(ManifestConflict):
        write_manifest(path, **different_tier)


def test_write_manifest_validates_process_count(tmp_path):
    with pytest.raises(ValueError):
        write_manifest(tmp_path / "m.json", **_manifest_kwargs(shard_units(_units(), 0)))
    kwargs = _manifest_kwargs(shard_units(_units(), 3))
    kwargs["max_processes"] = 4  # != len(shards)
    with pytest.raises(ValueError):
        write_manifest(tmp_path / "m.json", **kwargs)


def test_load_manifest_detects_tampering(tmp_path):
    path = tmp_path / "manifest.json"
    manifest = write_manifest(path, **_manifest_kwargs(shard_units(_units(), 2)))
    assert load_manifest(path) == manifest

    tampered = json.loads(path.read_text())
    tampered["budget_cap_usd"] = 999.0
    path.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ManifestConflict):
        load_manifest(path)


def test_completed_unit_ids_only_schema_valid_records(tmp_path):
    records = tmp_path / "records"
    records.mkdir()
    # Valid: the golden fixture copied under a unit-id file name.
    shutil.copy(FIXTURE_RECORD, records / "B1-T2-canonical-01-chat-seed0-r0-pi.json")
    # Corrupt JSON: not complete.
    (records / "B1-T2-canonical-02-tools-seed0-r0-pi.json").write_text("{ not json")
    # Parseable but schema-invalid: not complete.
    (records / "B1-T2-canonical-02-tools-seed0-r0-legacy.json").write_text(
        json.dumps({"schema_version": "1.0.0"})
    )

    assert completed_unit_ids(records) == {"B1-T2-canonical-01-chat-seed0-r0-pi"}
    assert completed_unit_ids(tmp_path / "missing-dir") == set()
