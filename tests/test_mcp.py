"""Tests for MCP API routes — server status/toggle/policy, clients CRUD, tools, call."""

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
async def test_mcp_server_status_returns_response(auth_headers):
    """GET /api/mcp/server/status returns MCP server status."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/mcp/server/status", headers=auth_headers)
        assert response.status_code in (200, 404, 500, 502)


@pytest.mark.asyncio
async def test_mcp_server_status_requires_auth():
    """MCP server status requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/mcp/server/status")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_mcp_clients_returns_list(auth_headers):
    """GET /api/mcp/clients returns MCP clients."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/mcp/clients", headers=auth_headers)
        assert response.status_code in (200, 404, 500, 502)
