"""Tests for Chat API routes — POST /api/chat and GET /api/chat/history."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings after each test."""
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.mark.asyncio
async def test_chat_history_returns_messages():
    """GET /api/chat/history/{project_id} returns messages for a project."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/chat/history/test-project-123",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should return 200 even if no messages exist
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_chat_history_requires_auth():
    """GET /api/chat/history requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/chat/history/some-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_rejects_without_auth():
    """POST /api/chat requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "hello", "project_id": "test-project"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_rejects_missing_project():
    """POST /api/chat returns 404 for non-existent project."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "hello", "project_id": "non-existent-project-xyz"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_requires_message_field():
    """POST /api/chat validates required message field."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Missing message field — Pydantic validation error
        response = await ac.post(
            "/api/chat",
            json={"project_id": "some-project"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_requires_project_id_field():
    """POST /api/chat validates required project_id field."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
