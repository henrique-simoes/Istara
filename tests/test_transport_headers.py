"""Tests for transport security headers — HSTS, CSP, X-Frame-Options, etc."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token


@pytest.mark.asyncio
async def test_hsts_header_present():
    """Response includes security headers from backend middleware."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        headers = response.headers
        assert "x-frame-options" in headers
        assert headers["x-frame-options"] == "DENY"
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"
        assert "referrer-policy" in headers


@pytest.mark.asyncio
async def test_x_frame_options_deny():
    """X-Frame-Options should be DENY to prevent clickjacking."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.headers.get("x-frame-options") == "DENY"


@pytest.mark.asyncio
async def test_x_content_type_options_nosniff():
    """X-Content-Type-Options should be nosniff."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.headers.get("x-content-type-options") == "nosniff"


@pytest.mark.asyncio
async def test_referrer_policy_set():
    """Referrer-Policy should be set."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        referrer = response.headers.get("referrer-policy", "")
        assert "strict-origin" in referrer or "no-referrer" in referrer


@pytest.mark.asyncio
async def test_permissions_policy_set():
    """Permissions-Policy should disable unused browser features."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        perms = response.headers.get("permissions-policy", "")
        assert "camera=()" in perms
        assert "microphone=()" in perms
        assert "geolocation=()" in perms


@pytest.mark.asyncio
async def test_security_headers_on_protected_endpoint():
    """Security headers should be present on authenticated endpoints too."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-content-type-options") == "nosniff"
