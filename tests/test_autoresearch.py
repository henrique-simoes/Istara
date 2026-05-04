"""Tests for Autoresearch API routes — status, experiments, start/stop, config, leaderboard, toggle."""

import pytest
from httpx import AsyncClient, ASGITransport
from types import SimpleNamespace

from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token


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


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_autoresearch_status_returns_response(auth_headers):
    """GET /api/autoresearch/status returns autoresearch status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/autoresearch/status", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_autoresearch_status_requires_auth():
    """Autoresearch status requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/autoresearch/status")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_autoresearch_leaderboard_returns_response(auth_headers):
    """GET /api/autoresearch/leaderboard returns leaderboard."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/autoresearch/leaderboard", headers=auth_headers)
        assert response.status_code == 200


def test_get_runner_returns_runner_instance():
    """Route helper returns instantiated runner classes, not modules."""
    from app.api.routes.autoresearch import _get_runner
    from app.core.autoresearch_runners import BaseLoopRunner

    runner = _get_runner("model_temp")
    assert isinstance(runner, BaseLoopRunner)
    assert runner.loop_type == "model_temp"


@pytest.mark.asyncio
async def test_start_autoresearch_calls_engine_with_runner_and_clamped_iterations(monkeypatch):
    await init_db()
    settings.team_mode = False
    settings.autoresearch_enabled = True
    settings.autoresearch_max_experiments_per_run = 3

    class FakeEngine:
        is_running = False

        def __init__(self):
            self.calls = []

        async def run_loop(self, *, runner, target, max_iterations, project_id):
            self.calls.append(
                {
                    "runner": runner,
                    "target": target,
                    "max_iterations": max_iterations,
                    "project_id": project_id,
                }
            )

    fake_engine = FakeEngine()
    fake_runner = SimpleNamespace(loop_type="model_temp")
    monkeypatch.setattr("app.api.routes.autoresearch._get_engine", lambda: fake_engine)
    monkeypatch.setattr("app.api.routes.autoresearch._get_runner", lambda loop_type: fake_runner)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/autoresearch/start",
            json={
                "loop_type": "model_temp",
                "target": "analysis",
                "max_iterations": 10,
                "project_id": "project-1",
            },
        )

    assert response.status_code == 200
    assert response.json()["max_iterations"] == 3
    assert fake_engine.calls == [
        {
            "runner": fake_runner,
            "target": "analysis",
            "max_iterations": 3,
            "project_id": "project-1",
        }
    ]


@pytest.mark.asyncio
async def test_stop_autoresearch_requests_stop(monkeypatch):
    await init_db()
    settings.team_mode = False

    class FakeEngine:
        is_running = True

        def __init__(self):
            self.stopped = False

        def request_stop(self):
            self.stopped = True

    fake_engine = FakeEngine()
    monkeypatch.setattr("app.api.routes.autoresearch._get_engine", lambda: fake_engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/autoresearch/stop")

    assert response.status_code == 200
    assert fake_engine.stopped is True


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

    settings.autoresearch_min_improvement_delta = 0.01
    settings.autoresearch_measurement_repeats = 1

    class FakeRunner:
        loop_type = "model_temp"
        needs_persona_lock = False

        async def measure_baseline(self, target):
            return 0.5

        async def hypothesize(self, target, best_score, results):
            return "Improve model temperature for synthesis", {"description": "temperature +0.1"}

        async def apply_mutation(self, target, mutation):
            async def revert():
                return None

            return revert

        async def measure(self, target):
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

    monkeypatch.setattr("app.core.autoresearch_engine.check_experiment_limit", allow_experiment)
    monkeypatch.setattr(AutoresearchEngine, "_persist_experiment", fake_persist)
    monkeypatch.setattr(AutoresearchEngine, "_record_reasoning_memory", fake_record)
    monkeypatch.setattr(AutoresearchEngine, "_register_improvement_proposals", fake_register)

    engine = AutoresearchEngine()
    results = await engine.run_loop(
        FakeRunner(),
        target="kappa-thematic-analysis",
        max_iterations=1,
        project_id="project-autoresearch-memory",
    )

    assert persisted
    assert results[0]["kept"] is True
    assert results[0]["reasoning_memory_ids"] == ["memory-1"]
    assert results[0]["improvement_proposal_ids"] == ["proposal-1"]
