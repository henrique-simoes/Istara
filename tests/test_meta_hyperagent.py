"""Tests for Meta-Agent API routes — status, proposals, variants, observations, toggle."""

import asyncio

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
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


@pytest.mark.asyncio
async def test_meta_agent_status_returns_response(auth_headers):
    """GET /api/meta-hyperagent/status returns meta-agent status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/meta-hyperagent/status", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "enabled" in body
        assert "running" in body
        assert "pending_proposals" in body


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
async def test_meta_agent_proposals_returns_list(auth_headers):
    """GET /api/meta-hyperagent/proposals returns proposals."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/meta-hyperagent/proposals", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["proposals"], list)
        assert body["pending_count"] >= 0


@pytest.mark.asyncio
async def test_meta_hyperagent_start_retains_task_and_stop_cancels(monkeypatch):
    from app.core.meta_hyperagent import MetaHyperagent

    mh = MetaHyperagent()
    original_interval = settings.meta_hyperagent_observation_interval_hours

    async def observe_once():
        return {"timestamp": "test"}

    async def analyze_none():
        return []

    try:
        settings.meta_hyperagent_observation_interval_hours = 1
        monkeypatch.setattr(mh, "observe_cycle", observe_once)
        monkeypatch.setattr(mh, "analyze_and_propose", analyze_none)

        task = mh.start()
        await asyncio.sleep(0)

        assert mh.is_running is True
        assert mh._task is task

        mh.stop()
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
        async def summary(self):
            return {"total": 2, "recent_failures_24h": 1}

    monkeypatch.setattr("app.core.reasoning_bank.reasoning_bank", FakeReasoningBank())

    mh = MetaHyperagent()
    observation = await mh.observe_cycle()

    assert observation["reasoning_bank"]["total"] == 2
    assert observation["reasoning_bank"]["recent_failures_24h"] == 1
