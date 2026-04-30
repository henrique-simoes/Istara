"""Tests for LLM Servers API routes — CRUD, health-check, discover."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token
from app.api.routes.llm_servers import _is_local_host


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


@pytest.fixture
def researcher_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user2", "researcher", "researcher")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_llm_servers_list_returns_list(auth_headers):
    """GET /api/llm-servers returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/llm-servers", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_llm_servers_list_requires_auth():
    """LLM servers listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/llm-servers")
        assert response.status_code == 401


def test_local_server_detection_rejects_remote_hosts_marked_local():
    assert _is_local_host("http://localhost:11434")
    assert _is_local_host("127.0.0.1:1234")
    assert not _is_local_host("http://192.168.1.25:11434")
    assert not _is_local_host("https://istara.example.com")


@pytest.mark.asyncio
async def test_llm_server_discovery_requires_admin(researcher_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/llm-servers/discover", headers=researcher_headers)
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_add_remote_server_marked_local(researcher_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/llm-servers",
            headers=researcher_headers,
            json={
                "name": "Remote LAN",
                "provider_type": "ollama",
                "host": "http://192.168.1.25:11434",
                "is_local": True,
            },
        )
        assert response.status_code == 403
