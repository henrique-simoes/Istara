"""Tests for Meta-Agent API routes — status, proposals, variants, observations, toggle."""

import asyncio
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

        task = mh.start(project_id="project-meta-loop")
        await asyncio.sleep(0)

        assert mh.is_running is True
        assert mh._task is task
        assert mh.active_project_id == "project-meta-loop"

        mh.stop(project_id="project-meta-loop")
        await asyncio.sleep(0)

        assert mh.is_running is False
        assert mh._task is None
        assert task.cancelled() or task.done()
    finally:
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
