"""The S1-S5 study-capture harness measures the product path and reports exact counts."""

from __future__ import annotations

import app.core.agentic  # noqa: F401  (import-order guard, see tests/test_deployments.py)

import pytest

from app.evals.study_capture_eval import measure_channels, measure_survey_resync


@pytest.mark.asyncio
async def test_small_study_captures_exactly_the_answers_given():
    report = await measure_channels(n_per_channel=2, seed=3)
    assert report["S1_attribution"]["misattributed"] == 0
    assert report["S1_attribution"]["share"] in (1.0, None)
    assert report["S2_completeness"]["not_stored_exactly_once"] == []
    assert report["S3_non_research_data_stored"] == 0
    assert report["S4_quota_overshoot"] == 0


@pytest.mark.asyncio
async def test_survey_resync_harness_sees_no_duplicates():
    report = await measure_survey_resync(syncs=2)
    assert report["S5_duplicate_units"] == 0
    assert report["response_count_after"] == report["responses"]
