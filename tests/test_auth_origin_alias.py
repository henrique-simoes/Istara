import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.auth_cookies import AUTH_COOKIE_NAME
from app.main import app
from app.models.database import init_db


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.mark.asyncio
async def test_login_allows_trusted_loopback_alias_fetch_metadata():
    """A trusted localhost UI may use a 127.0.0.1 API tunnel without CSRF denial."""
    await init_db()
    settings.team_mode = False
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as ac:
        response = await ac.post(
            "/api/auth/login",
            json={"username": "local", "password": ""},
            headers={
                "Origin": "http://localhost:3000",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "cors",
            },
        )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "local"
    assert AUTH_COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_login_rejects_cross_site_browser_attempts_before_cookie_creation():
    """Auth-exempt login should still reject browser CSRF signals."""
    await init_db()
    settings.team_mode = False
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        origin_response = await ac.post(
            "/api/auth/login",
            json={"username": "testuser", "password": ""},
            headers={"Origin": "https://evil.example"},
        )
        fetch_metadata_response = await ac.post(
            "/api/auth/login",
            json={"username": "testuser", "password": ""},
            headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"},
        )

    assert origin_response.status_code == 403
    assert AUTH_COOKIE_NAME not in origin_response.cookies
    assert "Untrusted browser origin" in origin_response.json()["detail"]
    assert fetch_metadata_response.status_code == 403
    assert AUTH_COOKIE_NAME not in fetch_metadata_response.cookies
    assert "Untrusted browser origin" in fetch_metadata_response.json()["detail"]


@pytest.mark.asyncio
async def test_register_rejects_untrusted_browser_origin_before_user_creation():
    """Team registration should not mint a first session for an untrusted origin."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/register",
            json={
                "username": "origin_attack",
                "email": "origin_attack@example.com",
                "password": "xK9#mP2$vL7nQ4@wR1!",
            },
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    assert AUTH_COOKIE_NAME not in response.cookies
    assert "Untrusted browser origin" in response.json()["detail"]
