import pytest
from app.config import settings
from app.core.auth import create_token
from app.main import app
from app.models.database import init_db
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings after each test."""
    from app.api.routes.auth import _login_limiter

    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    _login_limiter.clear()
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    _login_limiter.clear()


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
async def test_auth_users_requires_admin_role():
    """Team user listing must not expose emails and roles to non-admin users."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    researcher_token = create_token("researcher-1", "researcher", "researcher")
    admin_token = create_token("admin-1", "admin", "admin")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        denied = await ac.get(
            "/api/auth/users",
            headers={"Authorization": f"Bearer {researcher_token}"},
        )
        allowed = await ac.get(
            "/api/auth/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert isinstance(allowed.json(), list)


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


@pytest.mark.asyncio
async def test_local_mode_protected_api_bootstraps_without_token():
    """Local desktop mode should not strand first-run users behind JWT middleware."""
    await init_db()
    settings.team_mode = False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        me_response = await ac.get("/api/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "admin"

        projects_response = await ac.get("/api/projects")
        assert projects_response.status_code == 200
        assert isinstance(projects_response.json(), list)


def test_bootstrap_admin_user_has_required_email_hash():
    """Fresh installs must be able to create the first admin with encrypted email enabled."""
    from app.core.field_encryption import hash_field
    from app.main import _build_bootstrap_admin_user

    user = _build_bootstrap_admin_user(
        user_id="admin-id",
        username="admin",
        password_hash="hashed-password",
        recovery_codes_hashed="hashed-codes",
    )

    assert user.email == "admin@istara.local"
    assert user.email_hash == hash_field("admin@istara.local")


async def _create_team_user(
    *,
    username: str,
    email: str,
    password: str,
    role: str = "admin",
) -> None:
    from app.core.auth import hash_password
    from app.core.field_encryption import hash_field
    from app.models.database import async_session
    from app.models.user import User

    async with async_session() as db:
        user = User(
            id=f"user-{username}",
            username=username,
            email=email,
            email_hash=hash_field(email),
            password_hash=hash_password(password),
            role=role,
            display_name=username,
        )
        db.add(user)
        await db.commit()


# ---------------------------------------------------------------------------
# JWT security tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jwt_alg_none_rejected():
    """Verify that JWT with alg:none is rejected."""
    import json

    from app.core.auth import _b64encode, verify_token

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

    import json
    import time

    from app.core.auth import _b64encode, verify_token

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
    from app.core.auth import hashlib, hmac

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


@pytest.mark.asyncio
async def test_cookie_auth_rejects_untrusted_origin_on_state_change():
    """Cookie-authenticated unsafe requests should reject untrusted browser origins."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("admin-1", "admin", "admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set("istara_session", token)
        response = await ac.put(
            "/api/auth/preferences",
            json={"preferences": {"theme": "dark"}},
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    assert "Untrusted browser origin" in response.json()["detail"]


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
    assert "istara_session" not in origin_response.cookies
    assert "Untrusted browser origin" in origin_response.json()["detail"]
    assert fetch_metadata_response.status_code == 403
    assert "istara_session" not in fetch_metadata_response.cookies
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
    assert "istara_session" not in response.cookies
    assert "Untrusted browser origin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_creates_revocable_server_auth_session():
    """Team-mode login should create a server-backed session that logout revokes."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid

    username = f"sessionuser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"
    await _create_team_user(username=username, email=email, password=password)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200
        token = login.json()["token"]

        from app.core.auth import verify_token
        from app.models.auth_session import AuthSession
        from app.models.database import async_session

        payload = verify_token(token)
        assert payload is not None
        assert payload["session_bound"] is True
        assert payload["sid"]

        async with async_session() as db:
            session = await db.get(AuthSession, payload["sid"])
            assert session is not None
            assert session.user_id == payload["sub"]
            assert session.token_jti == payload["jti"]
            assert session.revoked_at is None

        active = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert active.status_code == 200

        logout = await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout.status_code == 200

        async with async_session() as db:
            session = await db.get(AuthSession, payload["sid"])
            assert session is not None
            assert session.revoked_at is not None

        revoked = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert revoked.status_code == 401


@pytest.mark.asyncio
async def test_auth_sessions_list_and_revoke_specific_other_session():
    """Users can inspect active sessions without token leakage and revoke another device."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid

    username = f"sessionlist_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"
    await _create_team_user(username=username, email=email, password=password)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first_login = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"User-Agent": "IstaraTest/first"},
        )
        second_login = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"User-Agent": "IstaraTest/second"},
        )
        assert first_login.status_code == 200
        assert second_login.status_code == 200
        first_token = first_login.json()["token"]
        second_token = second_login.json()["token"]

        from app.core.auth import verify_token

        first_payload = verify_token(first_token)
        second_payload = verify_token(second_token)
        assert first_payload is not None
        assert second_payload is not None

        sessions_response = await ac.get(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert sessions_response.status_code == 200
        sessions = sessions_response.json()
        session_ids = {session["id"] for session in sessions}
        assert first_payload["sid"] in session_ids
        assert second_payload["sid"] in session_ids
        assert [session["id"] for session in sessions if session["current"]] == [first_payload["sid"]]
        assert all("token" not in session for session in sessions)
        assert all("token_jti" not in session for session in sessions)

        revoke = await ac.delete(
            f"/api/auth/sessions/{second_payload['sid']}",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert revoke.status_code == 200
        assert revoke.json()["revoked"] is True
        assert revoke.json()["revoked_current"] is False

        revoked = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {second_token}"})
        active = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {first_token}"})
        assert revoked.status_code == 401
        assert active.status_code == 200


@pytest.mark.asyncio
async def test_auth_sessions_revoke_others_keeps_current_session():
    """The revoke-others endpoint should preserve the caller's session."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid

    username = f"sessionothers_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"
    await _create_team_user(username=username, email=email, password=password)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first_login = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        second_login = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        first_token = first_login.json()["token"]
        second_token = second_login.json()["token"]

        revoke = await ac.post(
            "/api/auth/sessions/revoke-others",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert revoke.status_code == 200
        assert revoke.json()["revoked_count"] >= 1

        current = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {first_token}"})
        other = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {second_token}"})
        assert current.status_code == 200
        assert other.status_code == 401


@pytest.mark.asyncio
async def test_auth_session_revoke_current_invalidates_token():
    """Revoking the current auth session should invalidate the active token."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid

    username = f"sessioncurrent_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"
    await _create_team_user(username=username, email=email, password=password)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200
        token = login.json()["token"]

        from app.core.auth import verify_token

        payload = verify_token(token)
        assert payload is not None

        revoke = await ac.delete(
            f"/api/auth/sessions/{payload['sid']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revoke.status_code == 200
        assert revoke.json()["revoked"] is True
        assert revoke.json()["revoked_current"] is True

        revoked = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert revoked.status_code == 401


@pytest.mark.asyncio
async def test_bound_session_uses_current_user_role():
    """Role changes should take effect immediately for server-bound sessions."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid

    username = f"rolebound_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"
    await _create_team_user(username=username, email=email, password=password)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        allowed = await ac.get("/api/auth/users", headers=headers)
        assert allowed.status_code == 200

        from app.models.database import async_session
        from app.models.user import User
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one()
            user.role = "viewer"
            await db.commit()

        denied = await ac.get("/api/auth/users", headers=headers)
        assert denied.status_code == 403


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
        reg = await ac.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "xK9#mP2$vL7nQ4@wR1!",
            },
        )
        assert reg.status_code == 200
        token = reg.json()["token"]

        # Setup TOTP
        totp_setup = await ac.post(
            "/api/auth/totp/setup",
            json={"current_password": "xK9#mP2$vL7nQ4@wR1!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert totp_setup.status_code == 200
        secret = totp_setup.json()["secret"]

        # Verify TOTP to enable it
        import pyotp

        code = pyotp.TOTP(secret).now()
        totp_verify = await ac.post(
            "/api/auth/totp/verify",
            json={"totp_code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert totp_verify.status_code == 200

        # Log out (clear token)
        await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        # Login WITHOUT TOTP code — should return requires_2fa
        login = await ac.post(
            "/api/auth/login", json={"username": username, "password": "xK9#mP2$vL7nQ4@wR1!"}
        )
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
        reg = await ac.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "xK9#mP2$vL7nQ4@wR1!",
            },
        )
        token = reg.json()["token"]

        totp_setup = await ac.post(
            "/api/auth/totp/setup",
            json={"current_password": "xK9#mP2$vL7nQ4@wR1!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        secret = totp_setup.json()["secret"]

        import pyotp

        code = pyotp.TOTP(secret).now()
        await ac.post(
            "/api/auth/totp/verify",
            json={"totp_code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        # Login WITH TOTP code
        login = await ac.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": "xK9#mP2$vL7nQ4@wR1!",
                "totp_code": pyotp.TOTP(secret).now(),
            },
        )
        assert login.status_code == 200
        data = login.json()
        assert "token" in data
        assert data.get("requires_2fa") is not True


@pytest.mark.asyncio
async def test_totp_setup_requires_current_password():
    """Changing MFA state requires a password confirmation."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid

    username = f"mfareauth_{uuid.uuid4().hex[:8]}"
    email = f"mfareauth_{uuid.uuid4().hex[:8]}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        token = reg.json()["token"]

        missing = await ac.post(
            "/api/auth/totp/setup",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        wrong = await ac.post(
            "/api/auth/totp/setup",
            json={"current_password": "wrong-password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ok = await ac.post(
            "/api/auth/totp/setup",
            json={"current_password": password},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert missing.status_code == 422
    assert wrong.status_code == 401
    assert ok.status_code == 200


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
