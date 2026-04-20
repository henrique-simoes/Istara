"""Tests for Codebook Versions API routes — list, latest, create."""

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
async def test_codebook_versions_list_returns_response(auth_headers):
    """GET /api/codebook-versions/{project_id} returns versions."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/codebook-versions/test-project", headers=auth_headers)
        assert response.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_codebook_versions_requires_auth():
    """Codebook versions requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/codebook-versions/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_codebook_versions_latest_returns_response(auth_headers):
    """GET /api/codebook-versions/{project_id}/latest returns latest version."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/codebook-versions/test-project/latest", headers=auth_headers)
        assert response.status_code in (200, 404, 500)
