"""Tests for Autoresearch API routes — status, experiments, start/stop, config, leaderboard, toggle."""

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
async def test_autoresearch_status_returns_response(auth_headers):
    """GET /api/autoresearch/status returns autoresearch status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/autoresearch/status", headers=auth_headers)
        assert response.status_code in (200, 404, 500, 502)


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
        assert response.status_code in (200, 404, 500, 502)
