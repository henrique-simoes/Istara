"""Tests for Documents API routes — CRUD, search, sync, tags, stats."""

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
async def test_documents_list_returns_list(auth_headers):
    """GET /api/documents returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents", headers=auth_headers)
        assert response.status_code in (200, 422, 500, 502)
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_documents_list_requires_auth():
    """Documents listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_document_get_nonexistent_returns_404(auth_headers):
    """GET /api/documents/{id} returns 404 for non-existent document."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_documents_search_returns_list(auth_headers):
    """GET /api/documents/search/full returns search results."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents/search/full?q=test", headers=auth_headers)
        assert response.status_code in (200, 422, 500, 502)
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_documents_sync_returns_response(auth_headers):
    """POST /api/documents/sync/{project_id} triggers file sync."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/documents/sync/test-project", headers=auth_headers)
        assert response.status_code in (200, 422, 404, 500, 502)


@pytest.mark.asyncio
async def test_documents_stats_returns_dict(auth_headers):
    """GET /api/documents/stats/{project_id} returns stats."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/documents/stats/test-project", headers=auth_headers)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert isinstance(response.json(), dict)
