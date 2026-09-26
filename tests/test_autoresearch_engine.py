"""Autoresearch engine: keep rule, reasoning-memory records, paused projects, sandboxes."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.models.database import async_session, init_db
from app.models.project import Project


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_enabled = settings.autoresearch_enabled
    original_max_per_run = settings.autoresearch_max_experiments_per_run
    original_daily = settings.autoresearch_max_daily_experiments
    original_min_delta = settings.autoresearch_min_improvement_delta
    original_repeats = settings.autoresearch_measurement_repeats
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.autoresearch_enabled = original_enabled
    settings.autoresearch_max_experiments_per_run = original_max_per_run
    settings.autoresearch_max_daily_experiments = original_daily
    settings.autoresearch_min_improvement_delta = original_min_delta
    settings.autoresearch_measurement_repeats = original_repeats


def test_autoresearch_keep_rule_rejects_noise_below_minimum_delta():
    from app.core.autoresearch_engine import AutoresearchEngine

    engine = AutoresearchEngine()
    keep, reason = engine._should_keep_candidate(
        0.005,
        min_delta=0.01,
        confidence_interval_95=None,
    )
    assert keep is False
    assert "below minimum" in reason


def test_autoresearch_keep_rule_rejects_delta_inside_confidence_interval():
    from app.core.autoresearch_engine import AutoresearchEngine

    engine = AutoresearchEngine()
    keep, reason = engine._should_keep_candidate(
        0.03,
        min_delta=0.01,
        confidence_interval_95=0.04,
    )
    assert keep is False
    assert "95% CI" in reason


@pytest.mark.asyncio
async def test_autoresearch_records_reasoning_memory_ids(monkeypatch):
    """Kept/reverted experiments should be distilled into ReasoningBank memories."""
    await init_db()
    from app.core.autoresearch_engine import AutoresearchEngine
    from app.core.autoresearch_isolation import is_autoresearch_active

    settings.autoresearch_min_improvement_delta = 0.01
    settings.autoresearch_measurement_repeats = 1
    project_id = f"project-autoresearch-memory-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Autoresearch Memory"))
        await db.commit()

    class FakeRunner:
        loop_type = "model_temp"
        needs_persona_lock = False

        def __init__(self):
            self.project_id = ""
            self.mutated = False
            self.reverted = False

        def bind_project(self, project_id):
            self.project_id = project_id

        async def measure_baseline(self, target):
            assert is_autoresearch_active() is True
            assert self.project_id == project_id
            return 0.5

        async def hypothesize(self, target, best_score, results):
            return "Improve model temperature for synthesis", {"description": "temperature +0.1"}

        async def apply_mutation(self, target, mutation):
            self.mutated = True

            async def revert():
                self.mutated = False
                self.reverted = True
                return None

            return revert

        async def measure(self, target):
            assert is_autoresearch_active() is True
            assert self.project_id == project_id
            assert self.mutated is True
            return 0.6

    async def allow_experiment(db, target):
        return True, ""

    persisted = []

    async def fake_persist(self, experiment, project_id):
        persisted.append((experiment.copy(), project_id))

    async def fake_record(self, experiment, project_id):
        return ["memory-1"]

    async def fake_register(self, experiment, project_id):
        return ["proposal-1"]

    record = AsyncMock()
    monkeypatch.setattr("app.core.autoresearch_engine.check_experiment_limit", allow_experiment)
    monkeypatch.setattr(AutoresearchEngine, "_persist_experiment", fake_persist)
    monkeypatch.setattr(AutoresearchEngine, "_record_reasoning_memory", fake_record)
    monkeypatch.setattr(AutoresearchEngine, "_register_improvement_proposals", fake_register)
    monkeypatch.setattr(
        "app.core.telemetry.telemetry_recorder.record_research_validity_event",
        record,
    )

    engine = AutoresearchEngine()
    runner = FakeRunner()
    results = await engine.run_loop(
        runner,
        target="kappa-thematic-analysis",
        max_iterations=1,
        project_id=project_id,
    )

    assert persisted
    assert results[0]["kept"] is True
    assert results[0]["status"] == "proposal_ready"
    assert results[0]["sandboxed"] is True
    assert results[0]["governance_required"] is True
    assert results[0]["mutation_live_after_measurement"] is False
    assert runner.reverted is True
    assert runner.mutated is False
    assert results[0]["research_spine_policy"]["report_evidence"] is False
    assert results[0]["research_spine_policy"]["can_bypass_research_spine"] is False
    assert results[0]["reasoning_memory_ids"] == ["memory-1"]
    assert results[0]["improvement_proposal_ids"] == ["proposal-1"]
    assert runner.project_id == ""
    record.assert_awaited_once()
    _, kwargs = record.await_args
    assert kwargs["operation"] == "autoresearch.validity_update"
    assert kwargs["project_id"] == project_id
    assert kwargs["agent_id"] == "autoresearch"
    assert kwargs["skill_name"] == "model_temp"
    assert "hypothesis" not in kwargs


@pytest.mark.asyncio
async def test_autoresearch_engine_rejects_paused_project_before_runner_work():
    await init_db()
    from app.core.autoresearch_engine import AutoresearchEngine

    project_id = f"paused-engine-project-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused Engine", is_paused=True))
        await db.commit()

    class FakeRunner:
        loop_type = "model_temp"
        needs_persona_lock = False

        async def measure_baseline(self, target):
            raise AssertionError("baseline should not run for paused projects")

    engine = AutoresearchEngine()
    with pytest.raises(RuntimeError, match="Project is paused or not found"):
        await engine.run_loop(
            FakeRunner(),
            target="analysis",
            max_iterations=1,
            project_id=project_id,
        )


class _SandboxRunner:
    """A runner that measures on a sandbox and must be closed when the loop ends (F3)."""

    loop_type = "rag_params"
    needs_persona_lock = False

    def __init__(self, fail_baseline: bool = False):
        self.fail_baseline = fail_baseline
        self.closed = 0

    async def measure_baseline(self, target):
        if self.fail_baseline:
            raise RuntimeError("retrieval benchmark unavailable")
        return 0.5

    def close(self):
        self.closed += 1


@pytest.mark.parametrize("fail_baseline", [False, True])
async def test_the_engine_closes_a_runner_sandbox_when_the_loop_ends(monkeypatch, fail_baseline):
    """The RAG tuning loop measures on sandbox indices rebuilt per chunking; the engine removes
    them when the loop ends, including when the baseline fails closed without a benchmark."""
    from app.core.autoresearch_engine import AutoresearchEngine

    engine = AutoresearchEngine()

    async def _active(project_id):
        return project_id

    async def _is_active(project_id):
        return True

    monkeypatch.setattr(engine, "_require_active_project_id", _active)
    monkeypatch.setattr(engine, "_is_project_active", _is_active)
    runner = _SandboxRunner(fail_baseline=fail_baseline)
    if fail_baseline:
        with pytest.raises(RuntimeError):
            await engine.run_loop(runner, "rag", max_iterations=0, project_id="p1")
    else:
        await engine.run_loop(runner, "rag", max_iterations=0, project_id="p1")
    assert runner.closed == 1
