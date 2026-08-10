"""Contract and unit tests for the benchmark report generator (task B4-1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import pi_benchmark_report as report_mod
from tests.pi_benchmark import schema
from tests.pi_benchmark.runner import (
    RunConfig,
    run_benchmark,
    write_run,
)

pytestmark = pytest.mark.benchmark


def test_scorecard_generation_and_schema_traceability(tmp_path):
    # Run B1 T0
    cfg = RunConfig(
        packs=("canonical",), tier="T0", engines=("pi", "legacy"), seeds=(0,),
        repeats=1, phase="B1", out_dir=tmp_path / "b1-t0",
    )
    summary = run_benchmark(cfg)
    write_run(summary)

    records = report_mod.load_records_from_runs(tmp_path / "b1-t0")
    assert len(records) == 30

    scorecard = report_mod.generate_scorecard(records)
    assert scorecard["schema_version"] == "1.1.0"
    assert scorecard["total_records_processed"] == 30
    assert "axes" in scorecard
    assert "tool_calling" in scorecard["axes"]
    assert "feature_matrix" in scorecard["axes"]


def test_report_generation_reproducibility_and_html_self_contained(tmp_path):
    cfg = RunConfig(
        packs=("canonical",), tier="T0", engines=("pi", "legacy"), seeds=(0,),
        repeats=1, phase="B1", out_dir=tmp_path / "b1-t0",
    )
    summary = run_benchmark(cfg)
    write_run(summary)

    records = report_mod.load_records_from_runs(tmp_path / "b1-t0")
    scorecard1 = report_mod.generate_scorecard(records)

    out_dir1 = tmp_path / "report1"
    out_dir2 = tmp_path / "report2"
    out_dir1.mkdir()
    out_dir2.mkdir()

    report_mod.generate_markdown_report(scorecard1, out_dir1 / "report.md")
    report_mod.generate_html_report(scorecard1, out_dir1 / "report.html")

    scorecard2 = report_mod.generate_scorecard(records)
    report_mod.generate_markdown_report(scorecard2, out_dir2 / "report.md")
    report_mod.generate_html_report(scorecard2, out_dir2 / "report.html")

    # A14: Report reproducibility (byte-identical scorecard.json modulo timestamp)
    scorecard1_copy = dict(scorecard1)
    scorecard2_copy = dict(scorecard2)
    del scorecard1_copy["generated_ts"]
    del scorecard2_copy["generated_ts"]
    assert json.dumps(scorecard1_copy, sort_keys=True) == json.dumps(scorecard2_copy, sort_keys=True)

    # A13: HTML is self-contained (no external http/https urls or CDN scripts)
    html_content = (out_dir1 / "report.html").read_text()
    assert "http://" not in html_content
    assert "https://" not in html_content
