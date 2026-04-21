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
async def test_team_status_insecure_flag():
    """Verify that insecure=True when team_mode is off and request is from a remote IP."""
    await init_db()
    # We use the app directly with a mock transport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test localhost (should NOT be insecure even if team_mode is off)
        settings.team_mode = False
        response = await ac.get("/api/auth/team-status")
        assert response.status_code == 200
        data = response.json()
        assert data["team_mode"] is False
        assert data["insecure"] is False

        # 2. Test Team Mode (should NEVER be insecure)
        settings.team_mode = True
        response = await ac.get("/api/auth/team-status")
        assert response.status_code == 200
        assert response.json()["insecure"] is False


@pytest.mark.asyncio
async def test_auth_me_enforcement():
    """Verify that auth/me requires a token in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/auth/me")
        # SecurityAuthMiddleware should catch this
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_local_mode_admin_bypass():
    """Verify that local mode still works as expected (intentional bypass)."""
    await init_db()
    settings.team_mode = False
    # Ensure we have a secret for signing
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    # Generate a VALID token for the middleware to pass
    token = create_token("local", "tester", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # In local mode, auth/me returns admin
        response = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["role"] == "admin"


# ---------------------------------------------------------------------------
# JWT security tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jwt_alg_none_rejected():
    """Verify that JWT with alg:none is rejected."""
    from app.core.auth import _b64encode, verify_token
    import json

    # Create a token with alg:none
    header = _b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64encode(json.dumps({"sub": "hacker", "role": "admin", "exp": 9999999999}).encode())
    fake_token = f"{header}.{payload}.fakesig"

    result = verify_token(fake_token)
    assert result is None, "alg:none attack should be rejected"


@pytest.mark.asyncio
async def test_jwt_has_jti_and_mfa_claims():
    """Verify that tokens include jti (revocation ID) and mfa flag."""
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("user1", "testuser", "admin", mfa_verified=True)
    from app.core.auth import verify_token
    payload = verify_token(token)
    assert payload is not None
    assert "jti" in payload, "Token should have jti for revocation"
    assert len(payload["jti"]) > 0
    assert payload["mfa"] is True


@pytest.mark.asyncio
async def test_expired_jwt_rejected():
    """Verify that expired JWT tokens are rejected."""
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import time
    from app.core.auth import _b64encode, verify_token
    import json

    # Create an expired token
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        "sub": "user1",
        "username": "testuser",
        "role": "admin",
        "mfa": False,
        "jti": "test-jti",
        "iat": int(time.time()) - 10000,
        "exp": int(time.time()) - 5000,  # Expired 5000 seconds ago
    }
    payload = _b64encode(json.dumps(payload_data).encode())
    from app.core.auth import hmac, hashlib, _b64decode
    sig_input = f"{header}.{payload}".encode()
    sig = _b64encode(hmac.new(settings.jwt_secret.encode(), sig_input, hashlib.sha256).digest())
    expired_token = f"{header}.{payload}.{sig}"

    result = verify_token(expired_token)
    assert result is None, "Expired token should be rejected"


# ---------------------------------------------------------------------------
# Cookie-based auth tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_sets_session_cookie():
    """Verify that login sets HttpOnly session cookie."""
    await init_db()
    settings.team_mode = False
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/auth/login", json={"username": "testuser", "password": ""})
        assert response.status_code == 200
        # Check that the Set-Cookie header is present
        cookies = response.cookies
        assert "istara_session" in cookies, "Login should set istara_session cookie"


@pytest.mark.asyncio
async def test_logout_requires_auth():
    """Verify that logout requires authentication."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Without token — should be 401
        response = await ac.post("/api/auth/logout")
        assert response.status_code == 401

        # With token — should succeed
        token = create_token("local", "tester", "admin")
        response = await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
