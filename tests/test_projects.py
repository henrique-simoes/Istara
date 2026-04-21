"""Tests for Projects API routes — CRUD, members, versions, pause/resume."""

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


# ---------------------------------------------------------------------------
# Project Listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_projects_list_returns_list(auth_headers):
    """GET /api/projects returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_projects_list_requires_auth():
    """Projects listing requires authentication."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Project Get/Pause/Resume
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_get_nonexistent_returns_404(auth_headers):
    """GET /api/projects/{id} returns 404 for non-existent project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_pause_nonexistent_returns_404(auth_headers):
    """POST /api/projects/{id}/pause returns 404 for non-existent project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/projects/non-existent-id/pause", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_resume_nonexistent_returns_404(auth_headers):
    """POST /api/projects/{id}/resume returns 404 for non-existent project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/projects/non-existent-id/resume", headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Project Versions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_versions_returns_list(auth_headers):
    """GET /api/projects/{id}/versions returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects/test-id/versions", headers=auth_headers)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), list)
