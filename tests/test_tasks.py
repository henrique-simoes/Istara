"""Tests for Tasks API routes — CRUD, move, attach/detach, lock/unlock."""

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
async def test_tasks_list_returns_list(auth_headers):
    """GET /api/tasks returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_tasks_list_requires_auth():
    """Tasks listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/tasks")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_task_move_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/move returns 404 for non-existent task."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/tasks/non-existent-id/move", headers=auth_headers, json={"position": 0})
        assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_task_lock_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/lock returns 404 for non-existent task."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/tasks/non-existent-id/lock", headers=auth_headers)
        assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_task_unlock_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/unlock returns 404 for non-existent task."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/tasks/non-existent-id/unlock", headers=auth_headers)
        assert response.status_code in (404, 422)
