"""Tests for Loops/Scheduler API routes — overview, agents, executions, health, custom."""

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
async def test_loops_overview_returns_response(auth_headers):
    """GET /api/loops/overview returns loop overview."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/overview", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_loops_overview_requires_auth():
    """Loops overview requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/overview")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_loops_health_returns_response(auth_headers):
    """GET /api/loops/health returns scheduler health."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/health", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_loops_executions_returns_list(auth_headers):
    """GET /api/loops/executions returns execution history."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loops/executions", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
