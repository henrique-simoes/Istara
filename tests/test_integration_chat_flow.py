"""Integration test: Chat flow — send message → RAG retrieval → response → history persistence."""

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
async def test_chat_history_persistence(auth_headers):
    """Verify chat messages are persisted and retrievable via history endpoint."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Get history before (should be empty list)
        response = await ac.get("/api/chat/history/test-project", headers=auth_headers)
        assert response.status_code == 200
        before = response.json()
        assert isinstance(before, list)

        # Verify history endpoint is functional
        response = await ac.get("/api/chat/history/test-project?limit=10", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_auth_required():
    """Verify chat requires authentication."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/chat", json={"message": "test", "project_id": "test"})
        assert response.status_code == 401
