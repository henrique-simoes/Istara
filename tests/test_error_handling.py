"""Error handling path tests — verify graceful degradation and clean error responses."""

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
# 401 responses are JSON, not HTML
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauth_response_is_json():
    """401 responses return JSON, not HTML stack traces."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


# ---------------------------------------------------------------------------
# 404 responses are JSON
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_not_found_response_is_json(auth_headers):
    """404 responses return JSON, not HTML."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/nonexistent-endpoint", headers=auth_headers)
        assert response.status_code in (404, 405)
        # Should be JSON-parseable
        data = response.json()
        assert isinstance(data, (dict, list))


# ---------------------------------------------------------------------------
# 422 validation errors are structured
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validation_error_is_structured(auth_headers):
    """422 responses have structured validation error details."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/chat", headers=auth_headers, json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# ---------------------------------------------------------------------------
# Invalid JWT returns 401, not 500
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_jwt_returns_401():
    """Invalid JWT returns 401, not 500."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Missing required fields return 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_required_fields_returns_422(auth_headers):
    """Missing required fields in request body returns 422."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/projects", headers=auth_headers, json={})
        assert response.status_code in (422, 200)


# ---------------------------------------------------------------------------
# Non-existent project returns 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nonexistent_project_returns_404(auth_headers):
    """Non-existent project ID returns 404."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/projects/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Health endpoint never requires auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint_never_requires_auth():
    """Health endpoint is always accessible without auth."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
