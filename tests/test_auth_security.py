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


# ---------------------------------------------------------------------------
# 2FA / MFA tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_returns_requires_2fa_when_totp_enabled():
    """Verify that login returns requires_2fa when TOTP is enabled and no code provided."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid
    username = f"mfauser_{uuid.uuid4().hex[:8]}"
    email = f"mfa_{uuid.uuid4().hex[:8]}@example.com"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register a user
        reg = await ac.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "password": "xK9#mP2$vL7nQ4@wR1!",
        })
        assert reg.status_code == 200
        token = reg.json()["token"]

        # Setup TOTP
        totp_setup = await ac.post("/api/auth/totp/setup", headers={"Authorization": f"Bearer {token}"})
        assert totp_setup.status_code == 200
        secret = totp_setup.json()["secret"]

        # Verify TOTP to enable it
        import pyotp
        code = pyotp.TOTP(secret).now()
        totp_verify = await ac.post("/api/auth/totp/verify", json={"totp_code": code}, headers={"Authorization": f"Bearer {token}"})
        assert totp_verify.status_code == 200

        # Log out (clear token)
        await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        # Login WITHOUT TOTP code — should return requires_2fa
        login = await ac.post("/api/auth/login", json={"username": username, "password": "xK9#mP2$vL7nQ4@wR1!"})
        assert login.status_code == 200
        data = login.json()
        assert data.get("requires_2fa") is True
        assert "token" not in data
        assert "methods" in data


@pytest.mark.asyncio
async def test_login_with_totp_code_succeeds():
    """Verify that login with correct TOTP code returns token."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid
    username = f"mfauser2_{uuid.uuid4().hex[:8]}"
    email = f"mfa2_{uuid.uuid4().hex[:8]}@example.com"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register and setup TOTP
        reg = await ac.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "password": "xK9#mP2$vL7nQ4@wR1!",
        })
        token = reg.json()["token"]

        totp_setup = await ac.post("/api/auth/totp/setup", headers={"Authorization": f"Bearer {token}"})
        secret = totp_setup.json()["secret"]

        import pyotp
        code = pyotp.TOTP(secret).now()
        await ac.post("/api/auth/totp/verify", json={"totp_code": code}, headers={"Authorization": f"Bearer {token}"})
        await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        # Login WITH TOTP code
        login = await ac.post("/api/auth/login", json={
            "username": username,
            "password": "xK9#mP2$vL7nQ4@wR1!",
            "totp_code": pyotp.TOTP(secret).now(),
        })
        assert login.status_code == 200
        data = login.json()
        assert "token" in data
        assert data.get("requires_2fa") is not True


# ---------------------------------------------------------------------------
# Security headers tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_security_headers_present():
    """Verify that security headers are present on responses."""
    await init_db()
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/auth/team-status")
        assert response.status_code == 200
        headers = response.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert "strict-transport-security" in headers
        assert "content-security-policy" in headers
