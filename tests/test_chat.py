"""Tests for Chat API routes — POST /api/chat and GET /api/chat/history."""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.routes.chat import ChatRequest
from app.config import settings
from app.models.agent import Agent
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.session import ChatSession
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


@pytest.mark.asyncio
async def test_chat_rejects_blank_message_before_project_lookup():
    """POST /api/chat rejects blank messages at the request contract."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "   ", "project_id": "some-project"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_rejects_session_with_cross_project_agent_before_llm():
    """Chat must not compose prompts from a session's stale foreign agent id."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")
    project_id = str(uuid.uuid4())
    hidden_project_id = str(uuid.uuid4())
    hidden_agent_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Chat Agent Project A"),
                Project(id=hidden_project_id, name="Chat Agent Project B"),
                Agent(
                    id=hidden_agent_id,
                    name="Hidden Agent",
                    system_prompt="Hidden prompt should never be loaded",
                    scope="project",
                    project_id=hidden_project_id,
                ),
                ChatSession(
                    id=session_id,
                    project_id=project_id,
                    title="Stale hidden agent session",
                    agent_id=hidden_agent_id,
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={
                "message": "hello",
                "project_id": project_id,
                "session_id": session_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"


def test_chat_request_accepts_only_supported_thinking_modes():
    request = ChatRequest.model_validate(
        {"message": "hello", "project_id": "project-1", "thinking_mode": "auto"}
    )

    assert request.thinking_mode == "auto"

    with pytest.raises(Exception):
        ChatRequest.model_validate(
            {"message": "hello", "project_id": "project-1", "thinking_mode": "show_raw"}
        )
