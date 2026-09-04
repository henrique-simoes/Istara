"""Tests for Meta-Agent API routes — status, proposals, variants, observations, toggle."""

import asyncio
import contextlib
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.models.project import Project
from app.core.auth import create_token


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


async def create_project(project_id: str, name: str = "Meta Project") -> None:
    async with async_session() as db:
        db.add(Project(id=project_id, name=name))
        await db.commit()


async def create_paused_project(project_id: str, name: str = "Paused Meta Project") -> None:
    async with async_session() as db:
        db.add(Project(id=project_id, name=name, is_paused=True))
        await db.commit()


@pytest.mark.asyncio
async def test_meta_agent_status_returns_response(auth_headers):
    """GET /api/meta-hyperagent/status returns meta-agent status."""
    await init_db()
    project_id = f"meta-status-{uuid.uuid4().hex[:8]}"
    await create_project(project_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/meta-hyperagent/status?project_id={project_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "enabled" in body
        assert "running" in body
        assert "pending_proposals" in body
        assert body["project_id"] == project_id


@pytest.mark.asyncio
async def test_meta_agent_status_requires_auth():
    """Meta-agent status requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/meta-hyperagent/status")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_meta_agent_status_requires_project_scope(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing = await ac.get("/api/meta-hyperagent/status", headers=auth_headers)
        assert missing.status_code == 400
        assert missing.json()["detail"] == "project_id is required"

        unknown = await ac.get(
            "/api/meta-hyperagent/status?project_id=missing-meta-project",
            headers=auth_headers,
        )
        assert unknown.status_code == 404


@pytest.mark.asyncio
async def test_meta_hyperagent_toggle_rejects_paused_project(auth_headers):
    await init_db()
    project_id = f"meta-paused-{uuid.uuid4().hex[:8]}"
    await create_paused_project(project_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/meta-hyperagent/toggle?project_id={project_id}",
            headers=auth_headers,
            json={"enabled": True},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Project is paused"


@pytest.mark.asyncio
async def test_meta_hyperagent_toggle_reports_runtime_when_env_is_read_only(
    auth_headers, monkeypatch
):
    """A read-only Docker image must not turn a valid toggle into a 500."""
    from app.api.routes import meta_hyperagent as meta_routes

    await init_db()
    project_id = f"meta-read-only-{uuid.uuid4().hex[:8]}"
    await create_project(project_id)

    def raise_read_only(*_args, **_kwargs):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(meta_routes, "persist_env_value", raise_read_only)
    monkeypatch.setattr(meta_routes.meta_hyperagent, "start", lambda **_kwargs: None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/meta-hyperagent/toggle?project_id={project_id}",
            headers=auth_headers,
            json={"enabled": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["persisted"] is False
    assert "runtime" in payload["message"].lower()


@pytest.mark.asyncio
async def test_meta_agent_proposals_returns_list(auth_headers):
    """GET /api/meta-hyperagent/proposals returns proposals."""
    await init_db()
    project_id = f"meta-proposals-{uuid.uuid4().hex[:8]}"
    await create_project(project_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/meta-hyperagent/proposals?project_id={project_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project_id
        assert isinstance(body["proposals"], list)
        assert body["pending_count"] >= 0


@pytest.mark.asyncio
async def test_meta_hyperagent_start_retains_task_and_stop_cancels(monkeypatch):
    from app.core.meta_hyperagent import MetaHyperagent

    mh = MetaHyperagent()
    original_interval = settings.meta_hyperagent_observation_interval_hours

    async def observe_once(project_id: str | None = None):
        assert project_id == "project-meta-loop"
        return {"timestamp": "test"}

    async def analyze_none(project_id: str | None = None):
        assert project_id == "project-meta-loop"
        return []

    try:
        settings.meta_hyperagent_observation_interval_hours = 1
        monkeypatch.setattr(mh, "observe_cycle", observe_once)
        monkeypatch.setattr(mh, "analyze_and_propose", analyze_none)
        monkeypatch.setattr(
            "app.core.meta_hyperagent.is_project_active",
            lambda _project_id: asyncio.sleep(0, result=True),
        )

        task = mh.start(project_id="project-meta-loop")
        await asyncio.sleep(0)

        assert mh.is_running is True
        assert mh._task is task
        assert mh.active_project_id == "project-meta-loop"

        mh.stop(project_id="project-meta-loop")
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1)

        assert mh.is_running is False
        assert mh._task is None
        assert task.cancelled() or task.done()
    finally:
        settings.meta_hyperagent_observation_interval_hours = original_interval


@pytest.mark.asyncio
async def test_meta_hyperagent_stops_before_proposing_when_project_is_paused(monkeypatch):
    from app.core.meta_hyperagent import MetaHyperagent

    await init_db()
    project_id = f"meta-pause-loop-{uuid.uuid4().hex[:8]}"
    await create_project(project_id)
    mh = MetaHyperagent()
    original_interval = settings.meta_hyperagent_observation_interval_hours
    analyzed = False

    async def observe_and_pause(project_id: str | None = None):
        async with async_session() as db:
            project = await db.get(Project, project_id)
            project.is_paused = True
            await db.commit()
        return {"timestamp": "test", "project_id": project_id}

    async def analyze_none(project_id: str | None = None):
        nonlocal analyzed
        analyzed = True
        return []

    try:
        settings.meta_hyperagent_observation_interval_hours = 1
        monkeypatch.setattr(mh, "observe_cycle", observe_and_pause)
        monkeypatch.setattr(mh, "analyze_and_propose", analyze_none)

        task = mh.start(project_id=project_id)
        await asyncio.wait_for(task, timeout=1)

        assert analyzed is False
        assert mh.is_running is False
        assert mh.active_project_id is None
    finally:
        mh.stop(project_id=project_id)
        settings.meta_hyperagent_observation_interval_hours = original_interval


@pytest.mark.asyncio
async def test_meta_hyperagent_observes_reasoning_bank(monkeypatch):
    from app.core.meta_hyperagent import MetaHyperagent

    class FakeReasoningBank:
        def __init__(self):
            self.project_id = None

        async def summary(self, *, project_id=None):
            self.project_id = project_id
            return {"total": 2, "recent_failures_24h": 1}

    fake_bank = FakeReasoningBank()
    monkeypatch.setattr("app.core.reasoning_bank.reasoning_bank", fake_bank)

    mh = MetaHyperagent()
    mh._save_observations = lambda: None
    mh._log_audit = lambda *_args, **_kwargs: None
    observation = await mh.observe_cycle(project_id="project-meta-reasoning")

    assert observation["project_id"] == "project-meta-reasoning"
    assert fake_bank.project_id == "project-meta-reasoning"
    assert observation["reasoning_bank"]["total"] == 2
    assert observation["reasoning_bank"]["recent_failures_24h"] == 1


@pytest.mark.asyncio
async def test_meta_hyperagent_requires_project_evidence_for_self_evolution_proposal():
    from app.core.meta_hyperagent import MetaHyperagent

    mh = MetaHyperagent()
    mh._save = lambda: None
    mh._log_audit = lambda *_args, **_kwargs: None
    mh._proposals = []
    mh._variants = []
    mh._recent_observations = [
        {
            "timestamp": "2026-05-19T00:00:00+00:00",
            "project_id": "empty-project",
            "task_routing": {},
            "self_evolution": {
                "thresholds": {"min_occurrences": 3},
                "project_learning_count": 0,
                "project_promoted_count": 0,
            },
            "skill_selection": {"total_executions": 0, "semantic_fallback_count": 0},
            "quality_eval": {"verification_passes": 0, "verification_fails": 0},
            "agent_capabilities": {},
            "reasoning_bank": {},
        }
    ]

    proposals = await mh.analyze_and_propose(project_id="empty-project")

    assert proposals == []
    assert mh._proposals == []


@pytest.mark.asyncio
async def test_meta_hyperagent_records_content_free_validity_telemetry(monkeypatch):
    from unittest.mock import AsyncMock

    from app.core.meta_hyperagent import MetaHyperagent

    mh = MetaHyperagent()
    mh._save = lambda: None
    mh._log_audit = lambda *_args, **_kwargs: None
    mh._proposals = []
    mh._variants = []
    mh._recent_observations = [
        {
            "timestamp": "2026-05-19T00:00:00+00:00",
            "project_id": "telemetry-project",
            "task_routing": {},
            "self_evolution": {
                "thresholds": {"min_occurrences": 3},
                "project_learning_count": 0,
                "project_promoted_count": 0,
            },
            "skill_selection": {"total_executions": 20, "semantic_fallback_count": 10},
            "quality_eval": {"verification_passes": 0, "verification_fails": 0},
            "agent_capabilities": {},
            "reasoning_bank": {},
        }
    ]
    record = AsyncMock()
    monkeypatch.setattr(
        "app.core.telemetry.telemetry_recorder.record_research_validity_event",
        record,
    )

    proposals = await mh.analyze_and_propose(project_id="telemetry-project")

    assert proposals
    record.assert_awaited_once()
    _, kwargs = record.await_args
    assert kwargs["operation"] == "meta_hyperagent.proposal"
    assert kwargs["project_id"] == "telemetry-project"
    assert kwargs["agent_id"] == "meta-hyperagent"
    assert kwargs["skill_name"] == "skill_selection"
    assert "reason" not in kwargs


@pytest.mark.asyncio
async def test_meta_hyperagent_filters_proposals_by_project():
    from app.core.meta_hyperagent import MetaHyperagent

    mh = MetaHyperagent()
    mh._save = lambda: None
    mh._log_audit = lambda *_args, **_kwargs: None
    mh._proposals = [
        {
            "id": "proposal-a",
            "project_id": "project-a",
            "status": "pending",
            "parameter_path": "agent.skill_similarity_threshold",
        },
        {
            "id": "proposal-b",
            "project_id": "project-b",
            "status": "pending",
            "parameter_path": "agent.skill_similarity_threshold",
        },
        {
            "id": "legacy-global",
            "status": "pending",
            "parameter_path": "agent.skill_similarity_threshold",
        },
    ]
    mh._variants = []
    mh._recent_observations = []

    assert [p["id"] for p in mh.get_pending_proposals(project_id="project-a")] == ["proposal-a"]
    assert [p["id"] for p in mh.get_pending_proposals(project_id="project-b")] == ["proposal-b"]
    assert mh.reject_proposal("proposal-b", project_id="project-a") is None
    assert mh.reject_proposal("proposal-a", project_id="project-a")["status"] == "rejected"


@pytest.mark.asyncio
async def test_meta_hyperagent_refuses_protected_research_spine_parameters():
    from app.core.meta_hyperagent import MetaHyperagent

    mh = MetaHyperagent()
    mh._save = lambda: None
    mh._log_audit = lambda *_args, **_kwargs: None
    mh._proposals = [
        {
            "id": "proposal-protected",
            "project_id": "project-protected",
            "status": "pending",
            "target_system": "research_validity",
            "parameter_path": "research_validity.kappa_threshold",
            "current_value": 0.6,
            "proposed_value": 0.2,
        }
    ]
    mh._variants = []

    result = await mh.apply_proposal(
        "proposal-protected",
        project_id="project-protected",
    )

    assert "Protected Research Spine" in result["error"]
    assert mh._variants == []


@pytest.mark.asyncio
async def test_meta_hyperagent_project_variant_does_not_mutate_global_thresholds():
    import app.core.self_evolution as self_evolution
    from app.core.meta_hyperagent import MetaHyperagent

    original = dict(self_evolution.PROMOTION_THRESHOLDS)
    mh = MetaHyperagent()
    mh._save = lambda: None
    mh._log_audit = lambda *_args, **_kwargs: None
    mh._proposals = [
        {
            "id": "proposal-project-a",
            "project_id": "project-a",
            "status": "pending",
            "target_system": "self_evolution",
            "parameter_path": "self_evolution.PROMOTION_THRESHOLDS.min_confidence",
            "current_value": original["min_confidence"],
            "proposed_value": original["min_confidence"] + 5,
        }
    ]
    mh._variants = []

    variant = await mh.apply_proposal("proposal-project-a", project_id="project-a")

    assert variant["status"] == "active"
    assert self_evolution.PROMOTION_THRESHOLDS == original
    assert mh.get_self_evolution_threshold_overrides("project-a") == {
        "min_confidence": original["min_confidence"] + 5
    }
    assert mh.get_self_evolution_threshold_overrides("project-b") == {}
