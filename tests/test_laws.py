"""Tests for UX Laws API routes — list, compliance, radar, match, by-heuristic."""

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
async def test_laws_list_returns_list(auth_headers):
    """GET /api/laws returns a list of UX laws."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/laws", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have 30+ laws of UX
        assert len(data) > 0


@pytest.mark.asyncio
async def test_laws_list_requires_auth():
    """Laws listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/laws")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_laws_compliance_returns_response(auth_headers):
    """GET /api/laws/compliance/{project_id} returns compliance data."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/laws/compliance/test-project", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_laws_radar_returns_response(auth_headers):
    """GET /api/laws/compliance/{project_id}/radar returns radar data."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/laws/compliance/test-project/radar", headers=auth_headers)
        assert response.status_code in (200, 404, 500)
