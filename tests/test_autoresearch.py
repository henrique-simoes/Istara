"""Tests for Autoresearch API routes — status, experiments, start/stop, config, leaderboard, toggle."""

import pytest
from httpx import AsyncClient, ASGITransport
from types import SimpleNamespace
import uuid

from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.project import Project
from app.models.research_deployment import ResearchDeployment
from app.models.task import Task, TaskStatus


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


@pytest.fixture
def researcher_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("researcher1", "researcher", "researcher")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_autoresearch_status_returns_response(auth_headers):
    """GET /api/autoresearch/status returns autoresearch status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/autoresearch/status?project_id=project-1",
            headers=auth_headers,
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_autoresearch_status_requires_auth():
    """Autoresearch status requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/autoresearch/status?project_id=project-1")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_researcher_cannot_configure_autoresearch(researcher_headers):
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            "/api/autoresearch/config",
            headers=researcher_headers,
            json={"enabled": True, "max_experiments_per_run": 2},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_configure_autoresearch(auth_headers):
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            "/api/autoresearch/config",
            headers=auth_headers,
            json={"enabled": True, "max_experiments_per_run": 2},
        )
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["max_experiments_per_run"] == 2


@pytest.mark.asyncio
async def test_autoresearch_leaderboard_returns_response(auth_headers):
    """GET /api/autoresearch/leaderboard returns leaderboard."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/autoresearch/leaderboard?project_id=project-1",
            headers=auth_headers,
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_autoresearch_status_metrics_are_project_scoped(auth_headers):
    await init_db()
    suffix = uuid.uuid4().hex[:8]
    project_a = f"autoresearch-scope-a-{suffix}"
    project_b = f"autoresearch-scope-b-{suffix}"

    async with async_session() as db:
        db.add_all([
            Project(id=project_a, name="Autoresearch Scope A"),
            Project(id=project_b, name="Autoresearch Scope B"),
            Task(
                id=f"ar-task-a-{suffix}",
                project_id=project_a,
                title="A done task",
                status=TaskStatus.DONE,
                review_state="approved",
            ),
            Task(
                id=f"ar-task-b-{suffix}",
                project_id=project_b,
                title="B in review task",
                status=TaskStatus.IN_REVIEW,
                review_state="needs_revision",
            ),
            ResearchDeployment(
                id=f"ar-deploy-a-{suffix}",
                project_id=project_a,
                name="A deployment",
                deployment_type="survey",
                state="active",
                target_responses=10,
                current_responses=4,
            ),
            ResearchDeployment(
                id=f"ar-deploy-b-{suffix}",
                project_id=project_b,
                name="B deployment",
                deployment_type="survey",
                state="active",
                target_responses=50,
                current_responses=30,
            ),
        ])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/autoresearch/status?project_id={project_a}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    metrics = response.json()["operational_metrics"]
    assert metrics["tasks"]["total"] == 1
    assert metrics["tasks"]["done"] == 1
    assert metrics["tasks"]["in_review"] == 0
    assert metrics["research_collection"]["deployments"] == 1
    assert metrics["research_collection"]["deployment_responses"] == 4
    assert metrics["research_collection"]["deployment_targets"] == 10


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
    project_id = f"project-start-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Autoresearch Start Project"))
        await db.commit()

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
                "project_id": project_id,
            },
        )

    assert response.status_code == 200
    assert response.json()["max_iterations"] == 3
    assert fake_engine.calls == [
        {
            "runner": fake_runner,
            "target": "analysis",
            "max_iterations": 3,
            "project_id": project_id,
        }
    ]


@pytest.mark.asyncio
async def test_start_autoresearch_rejects_paused_project(monkeypatch):
    await init_db()
    settings.team_mode = False
    settings.autoresearch_enabled = True
    project_id = f"paused-autoresearch-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused Autoresearch", is_paused=True))
        await db.commit()

    class FakeEngine:
        is_running = False

        async def run_loop(self, **_kwargs):
            raise AssertionError("paused projects must not start autoresearch")

    monkeypatch.setattr("app.api.routes.autoresearch._get_engine", lambda: FakeEngine())
    monkeypatch.setattr(
        "app.api.routes.autoresearch._get_runner",
        lambda _loop_type: SimpleNamespace(loop_type="model_temp"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/autoresearch/start",
            json={
                "loop_type": "model_temp",
                "target": "analysis",
                "max_iterations": 1,
                "project_id": project_id,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Project is paused"


@pytest.mark.asyncio
async def test_stop_autoresearch_requests_stop(monkeypatch):
    await init_db()
    settings.team_mode = False

    class FakeEngine:
        is_running = True

        def __init__(self):
            self.stopped = False

        def get_current_experiment(self):
            return {"project_id": "project-1"}

        def request_stop(self):
            self.stopped = True

    fake_engine = FakeEngine()
    monkeypatch.setattr("app.api.routes.autoresearch._get_engine", lambda: fake_engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/autoresearch/stop?project_id=project-1")

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
    project_id = f"project-autoresearch-memory-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Autoresearch Memory"))
        await db.commit()

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
        project_id=project_id,
    )

    assert persisted
    assert results[0]["kept"] is True
    assert results[0]["reasoning_memory_ids"] == ["memory-1"]
    assert results[0]["improvement_proposal_ids"] == ["proposal-1"]


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
