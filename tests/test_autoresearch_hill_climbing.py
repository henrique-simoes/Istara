"""Autoresearch engine behaviour after the hill-climbing audit (CF-SPEC-1, Phase 6).

A deterministic fake runner with known noise drives the real engine: candidates with no true effect
are almost never kept, the incumbent is re-measured every iteration, unmeasurable samples make an
iteration ``not_runnable`` (never a fabricated score), the persisted record carries the real
mutation, meta-hyperagent conflicts are recorded, and the leaderboard ranks by a lower bound.
"""

import json
import random
import uuid
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.autoresearch_engine import AutoresearchEngine
from app.core.autoresearch_runners import BaseLoopRunner
from app.models.autoresearch_experiment import AutoresearchExperiment
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.telemetry_span import TelemetrySpan


class NoisyRunner(BaseLoopRunner):
    """Scores are N(mean, sd); a candidate adds ``effect``. ``fail_on`` returns None that time."""

    loop_type = "skill_prompt"

    def __init__(self, *, effect=0.0, sd=0.05, seed=0, fail_on=None):
        self.effect, self.sd, self.rng = effect, sd, random.Random(seed)
        self.mutated = False
        self.incumbent_calls = 0
        self.reverts = 0
        self.fail_on = fail_on
        self.calls = 0

    def _draw(self, effect):
        self.calls += 1
        if self.fail_on is not None and self.calls == self.fail_on:
            return None
        return self.rng.gauss(0.6 + effect, self.sd)

    async def measure_baseline(self, target):
        return self._draw(0.0)

    async def measure_incumbent(self, target):
        assert not self.mutated
        self.incumbent_calls += 1
        return self._draw(0.0)

    async def measure(self, target):
        assert self.mutated
        return self._draw(self.effect)

    async def hypothesize(self, target, current_score, history):
        return "tweak", {"description": "tweak", "params": {"x": len(history)}}

    async def apply_mutation(self, target, mutation):
        self.mutated = True

        async def revert():
            self.mutated = False
            self.reverts += 1

        return revert


@pytest.fixture
async def project(monkeypatch):
    await init_db()
    project_id = f"project-hill-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Hill climbing"))
        await db.commit()
    original = (
        settings.autoresearch_min_improvement_delta,
        settings.autoresearch_measurement_repeats,
    )
    settings.autoresearch_min_improvement_delta = 0.01
    settings.autoresearch_measurement_repeats = 3

    async def allow(db, target):
        return True, ""

    async def none(*args, **kwargs):
        return []

    monkeypatch.setattr("app.core.autoresearch_engine.check_experiment_limit", allow)
    monkeypatch.setattr(AutoresearchEngine, "_record_reasoning_memory", none)
    monkeypatch.setattr(AutoresearchEngine, "_register_improvement_proposals", none)
    monkeypatch.setattr(
        "app.core.telemetry.telemetry_recorder.record_research_validity_event", AsyncMock()
    )
    yield project_id
    (
        settings.autoresearch_min_improvement_delta,
        settings.autoresearch_measurement_repeats,
    ) = original


async def test_zero_effect_candidates_are_rarely_kept_and_incumbent_is_remeasured(project):
    runner = NoisyRunner(effect=0.0, sd=0.08, seed=11)
    results = await AutoresearchEngine().run_loop(
        runner, target="t", max_iterations=25, project_id=project
    )
    assert len(results) == 25
    assert sum(r["kept"] for r in results) <= 1
    assert runner.incumbent_calls == 2 + 25 * 3  # baseline extras + 3 per iteration
    assert runner.reverts == 25 and runner.mutated is False
    assert all(len(r["incumbent_samples"]) == 3 for r in results)


async def test_a_real_gain_is_kept_after_confirmation(project):
    runner = NoisyRunner(effect=0.2, sd=0.02, seed=3)
    [result] = await AutoresearchEngine().run_loop(
        runner, target="t", max_iterations=1, project_id=project
    )
    assert result["kept"] and result["status"] == "proposal_ready"
    assert len(result["confirmation_samples"]) == 3
    assert result["delta_ci_95"][0] > 0.01


async def test_unmeasurable_sample_is_not_runnable_never_a_score(project):
    # Calls: 3 baseline, 3 incumbent, then the first candidate measurement fails.
    runner = NoisyRunner(effect=0.3, sd=0.01, seed=5, fail_on=7)
    [result] = await AutoresearchEngine().run_loop(
        runner, target="t", max_iterations=1, project_id=project
    )
    assert result["status"] == "not_runnable" and result["kept"] is False
    assert "experiment_score" not in result and runner.mutated is False


async def test_persisted_record_carries_the_real_mutation(project):
    runner = NoisyRunner(effect=0.0, seed=8)
    [result] = await AutoresearchEngine().run_loop(
        runner, target="t", max_iterations=1, project_id=project
    )
    async with async_session() as db:
        row = await db.get(AutoresearchExperiment, result["id"])
    assert json.loads(row.mutation_diff) == {"description": "tweak", "params": {"x": 0}}
    assert row.baseline_score == pytest.approx(sum(result["incumbent_samples"]) / 3)


async def test_meta_conflict_is_recorded_not_silently_skipped(project, monkeypatch):
    monkeypatch.setattr(AutoresearchEngine, "_conflicts_with_meta", lambda self, r, p: True)
    runner = NoisyRunner(seed=9)
    results = await AutoresearchEngine().run_loop(
        runner, target="t", max_iterations=2, project_id=project
    )
    assert [r["status"] for r in results] == ["skipped_meta_conflict"] * 2
    assert runner.mutated is False and runner.reverts == 0


async def test_leaderboard_ranks_by_lower_bound_not_one_lucky_run(project):
    async with async_session() as db:
        for model, scores in (("lucky", [0.95, 0.15, 0.2]), ("steady", [0.7, 0.72, 0.71])):
            for score in scores:
                db.add(
                    TelemetrySpan(
                        trace_id=uuid.uuid4().hex,
                        operation="skill.execute",
                        project_id=project,
                        skill_name="interview-synthesis",
                        model_name=model,
                        temperature=0.3,
                        quality_score=score,
                    )
                )
        await db.commit()
    [entry] = await AutoresearchEngine().get_leaderboard(project)
    assert entry["model_name"] == "steady"
    assert entry["quality_lower_bound_95"] < entry["avg_quality"]
