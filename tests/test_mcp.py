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
    original_mcp_enabled = settings.mcp_server_enabled
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.mcp_server_enabled = original_mcp_enabled


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
        assert response.status_code == 200
        body = response.json()
        assert body["configured_enabled"] is settings.mcp_server_enabled
        assert body["serving"] is False
        assert body["lifecycle_state"] in ("disabled", "restart_required")


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
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["servers"], list)
        assert body["count"] == len(body["servers"])


@pytest.mark.asyncio
async def test_mcp_toggle_reports_restart_required_when_config_enabled(auth_headers, monkeypatch):
    await init_db()
    monkeypatch.setattr("app.mcp.server.MCP_AVAILABLE", True)
    persisted: dict[str, str] = {}
    monkeypatch.setattr(
        "app.api.routes.mcp.persist_env_value",
        lambda key, value: persisted.update({key: value}),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/mcp/server/toggle",
            headers=auth_headers,
            json={"enabled": True},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["configured_enabled"] is True
    assert body["serving"] is False
    assert body["restart_required"] is True
    assert body["persisted"] is True
    assert persisted["MCP_SERVER_ENABLED"] == "true"


@pytest.mark.asyncio
async def test_mcp_client_registration_rejects_unsupported_transport(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/mcp/clients",
            headers=auth_headers,
            json={
                "name": "stdio server",
                "url": "http://localhost:3001/mcp",
                "transport": "stdio",
            },
        )

    assert response.status_code == 422
    assert "Only HTTP MCP client transport" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_client_registration_rejects_invalid_http_url(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/mcp/clients",
            headers=auth_headers,
            json={
                "name": "bad url",
                "url": "localhost:3001/mcp",
                "transport": "http",
            },
        )

    assert response.status_code == 422
    assert "absolute http(s) URL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_audit_endpoint_returns_entries_envelope(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/mcp/server/audit", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["entries"] == []
    assert body["count"] == 0
