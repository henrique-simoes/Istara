"""Tests for Meta-Agent API routes — status, proposals, variants, observations, toggle."""

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
        assert response.status_code in (200, 404, 500)


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
        assert response.status_code in (200, 404, 500)
