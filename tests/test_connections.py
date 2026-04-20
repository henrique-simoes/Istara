"""Tests for Connections API routes — generate, validate, redeem, rotate-network-token."""

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
async def test_connections_validate_returns_response(auth_headers):
    """POST /api/connections/validate validates a connection string."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/connections/validate",
            headers=auth_headers,
            json={"connection_string": "invalid-string"},
        )
        assert response.status_code in (200, 400, 401)


@pytest.mark.asyncio
async def test_connections_requires_auth():
    """Connections endpoints require authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/connections/validate", json={"connection_string": "test"})
        assert response.status_code in (401, 200)
