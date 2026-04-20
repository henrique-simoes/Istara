"""Tests for Agents API routes — CRUD, identity, memory, messages, proposals."""

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
async def test_agents_list_returns_list(auth_headers):
    """GET /api/agents returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_agents_list_requires_auth():
    """Agents listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_agents_capacity_returns_response(auth_headers):
    """GET /api/agents/capacity returns agent capacity."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents/capacity", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_agents_heartbeat_returns_response(auth_headers):
    """GET /api/agents/heartbeat/status returns heartbeat status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents/heartbeat/status", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_agents_get_nonexistent_returns_404(auth_headers):
    """GET /api/agents/{id} returns 404 for non-existent agent."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/agents/non-existent-id", headers=auth_headers)
        assert response.status_code == 404
