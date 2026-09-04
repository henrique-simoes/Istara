"""B1 contract execution (task B1-1, acceptance A5/A6). Pure tier-T0/T1, no live model.

B1 runs the canonical pack across both engines at T0 and T1 and asserts the acceptance:
every one of the 15 canonical scenarios × both engines produces a schema-valid record, no
record is ``not_runnable`` without a filed reason, and deterministic outcome classes match
across repeats of the same seed. This is the smoke gate that the B0 assets are correct
before any owner-gated (T2/T3) spend is requested.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.pi_benchmark import schema
from tests.pi_benchmark.runner import RunConfig, run_benchmark, write_run

pytestmark = pytest.mark.benchmark

CANONICAL_COUNT = 15


def _b1_config(tier: str, out_dir: Path, repeats: int = 3) -> RunConfig:
    return RunConfig(
        packs=("canonical",),
        tier=tier,
        engines=("pi", "legacy"),
        seeds=(0,),
        repeats=repeats,
        phase="B1",
        out_dir=out_dir,
    )


@pytest.mark.parametrize("tier", ["T0", "T1"])
def test_b1_canonical_both_engines_produce_schema_valid_records(tier, tmp_path):
    summary = run_benchmark(
        _b1_config(tier, tmp_path / f"b1-{tier.lower()}", repeats=1)
    )
    assert len(summary.records) == CANONICAL_COUNT * 2  # both engines
    engines_seen = {r["engine"] for r in summary.records}
    assert engines_seen == {"pi", "legacy"}
    for record in summary.records:
        assert schema.is_valid(record)
        assert record["tier"] == tier
        # Acceptance A5: 0 not_runnable without a filed reason.
        if record["status"] == "not_runnable":
            assert record.get("not_runnable_reason")


def test_b1_no_canonical_scenario_is_not_runnable():
    # The canonical pack is fully T0-runnable — none should be not_runnable at B1.
    summary = run_benchmark(_b1_config("T0", Path("/tmp/unused"), repeats=1))
    assert summary.counts == {"ok": CANONICAL_COUNT * 2}


def test_b1_outcome_classes_are_stable_across_repeats():
    summary = run_benchmark(_b1_config("T0", Path("/tmp/unused"), repeats=5))
    classes: dict[tuple[str, str], set[str]] = {}
    for record in summary.records:
        key = (record["scenario"]["id"], record["engine"])
        classes.setdefault(key, set()).add(record["extensions"]["outcome_class"])
    assert all(len(v) == 1 for v in classes.values())


def test_b1_baseline_manifest_is_written(tmp_path):
    # Acceptance A6: B1 results are published as a regression baseline manifest.
    summary = run_benchmark(_b1_config("T0", tmp_path / "b1-t0", repeats=1))
    out = write_run(summary)
    manifest = out / "manifest.json"
    assert manifest.is_file()
    assert (out / "records").is_dir()
