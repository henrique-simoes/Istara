import pytest
from app.config import settings
from app.core.auth import create_token
from app.core.auth_cookies import AUTH_COOKIE_NAME, LEGACY_AUTH_COOKIE_NAME
from app.main import app
from app.models.database import init_db
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings after each test."""
    from app.api.routes.auth import _login_limiter, _mfa_limiter

    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_cors_origin_regex = settings.cors_origin_regex
    _login_limiter.clear()
    _mfa_limiter.clear()
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.cors_origin_regex = original_cors_origin_regex
    _login_limiter.clear()
    _mfa_limiter.clear()


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
        assert "security_warnings" in response.json()


@pytest.mark.asyncio
async def test_team_status_reports_origin_hardening_warnings():
    """Team status should expose actionable production auth configuration warnings."""
    await init_db()
    original_regex = settings.cors_origin_regex
    settings.team_mode = True
    settings.cors_origin_regex = r"https?://[^/]+:3000"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/auth/team-status")

    settings.cors_origin_regex = original_regex
    assert response.status_code == 200
    warnings = response.json()["security_warnings"]
    assert any(
        "CORS_ORIGIN_REGEX allows arbitrary hosts" in warning for warning in warnings
    )


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
        response = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
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
    assert user.recovery_codes_hashed is None


@pytest.mark.asyncio
async def test_public_registration_bootstraps_first_admin_and_closes():
    """Public registration is a one-time first-admin bootstrap flow."""
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        before = await ac.get("/api/auth/team-status")
        reg = await ac.post(
            "/api/auth/register",
            json={
                "username": "bootstrap_admin",
                "email": "bootstrap_admin@example.com",
                "password": "xK9#mP2$vL7nQ4@wR1!",
            },
        )
        after = await ac.get("/api/auth/team-status")

    assert before.status_code == 200
    assert before.json()["has_users"] is False
    assert before.json()["registration_enabled"] is True
    assert reg.status_code == 200
    assert reg.json()["user"]["role"] == "admin"
    assert len(reg.json()["recovery_codes"]) >= 8
    assert after.json()["has_users"] is True
    assert after.json()["registration_enabled"] is False


@pytest.mark.asyncio
async def test_user_can_update_profile_with_current_password(monkeypatch):
    """Users can change username/email/display name only after password verification."""
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    async def not_breached(_password: str) -> bool:
        return False

    monkeypatch.setattr("app.api.routes.auth.is_password_breached", not_breached)
    await _create_team_user(
        username="security_user",
        email="security_user@example.com",
        password="xK9#mP2$vL7nQ4@wR1!",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/auth/login",
            json={"username": "security_user", "password": "xK9#mP2$vL7nQ4@wR1!"},
        )
        token = login.json()["token"]
        denied = await ac.patch(
            "/api/auth/profile",
            json={"current_password": "wrong", "username": "security_user_2"},
            headers={"Authorization": f"Bearer {token}"},
        )
        updated = await ac.patch(
            "/api/auth/profile",
            json={
                "current_password": "xK9#mP2$vL7nQ4@wR1!",
                "username": "security_user_2",
                "email": "security_user_2@example.com",
                "display_name": "Security User Two",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert denied.status_code == 401
    assert updated.status_code == 200
    assert updated.json()["user"]["username"] == "security_user_2"
    assert updated.json()["user"]["email"] == "security_user_2@example.com"


@pytest.mark.asyncio
async def test_user_can_change_password_and_old_password_stops_working(monkeypatch):
    """Password changes require the current password and immediately affect login."""
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    async def not_breached(_password: str) -> bool:
        return False

    monkeypatch.setattr("app.api.routes.auth.is_password_breached", not_breached)
    await _create_team_user(
        username="password_user",
        email="password_user@example.com",
        password="xK9#mP2$vL7nQ4@wR1!",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/auth/login",
            json={"username": "password_user", "password": "xK9#mP2$vL7nQ4@wR1!"},
        )
        token = login.json()["token"]
        changed = await ac.post(
            "/api/auth/password/change",
            json={
                "current_password": "xK9#mP2$vL7nQ4@wR1!",
                "new_password": "zR8$vQ3#nL6!pT2@fresh",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        old_login = await ac.post(
            "/api/auth/login",
            json={"username": "password_user", "password": "xK9#mP2$vL7nQ4@wR1!"},
        )
        new_login = await ac.post(
            "/api/auth/login",
            json={"username": "password_user", "password": "zR8$vQ3#nL6!pT2@fresh"},
        )

    assert changed.status_code == 200
    assert old_login.status_code == 401
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_public_registration_rejects_post_bootstrap_accounts():
    """Additional accounts must be created by admin workflow or invite strings."""
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    await _create_team_user(
        username="existing_admin",
        email="existing_admin@example.com",
        password="xK9#mP2$vL7nQ4@wR1!",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/register",
            json={
                "username": "driveby_user",
                "email": "driveby@example.com",
                "password": "xK9#mP2$vL7nQ4@wR1!",
            },
        )

    assert response.status_code == 403
    assert "first admin account" in response.json()["detail"]


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


async def _clear_auth_accounts() -> None:
    """Remove account records so public registration tests exercise first-user bootstrap."""
    from sqlalchemy import delete

    from app.models.auth_session import AuthSession
    from app.models.database import async_session
    from app.models.recovery_code import RecoveryCode
    from app.models.user import User
    from app.models.webauthn_challenge import WebAuthnChallenge
    from app.models.webauthn_credential import WebAuthnCredential

    async with async_session() as db:
        for model in (
            AuthSession,
            RecoveryCode,
            WebAuthnChallenge,
            WebAuthnCredential,
            User,
        ):
            await db.execute(delete(model))
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
    payload = _b64encode(
        json.dumps({"sub": "hacker", "role": "admin", "exp": 9999999999}).encode()
    )
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
    sig = _b64encode(
        hmac.new(settings.jwt_secret.encode(), sig_input, hashlib.sha256).digest()
    )
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
        response = await ac.post(
            "/api/auth/login", json={"username": "testuser", "password": ""}
        )
        assert response.status_code == 200
        assert AUTH_COOKIE_NAME in response.cookies, (
            "Login should set hardened session cookie"
        )
        set_cookie = response.headers.get("set-cookie", "")
        assert f"{AUTH_COOKIE_NAME}=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=strict" in set_cookie
        assert "Path=/" in set_cookie
        assert f"{LEGACY_AUTH_COOKIE_NAME}=" in set_cookie


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
        response = await ac.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
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
        ac.cookies.set(AUTH_COOKIE_NAME, token)
        response = await ac.put(
            "/api/auth/preferences",
            json={"preferences": {"theme": "dark"}},
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    assert "Untrusted browser origin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_legacy_session_cookie_still_accepted_during_transition():
    """Existing browser sessions using the old cookie name should still read."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("admin-1", "admin", "admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set(LEGACY_AUTH_COOKIE_NAME, token)
        response = await ac.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "admin"


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

        active = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert active.status_code == 200

        logout = await ac.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert logout.status_code == 200

        async with async_session() as db:
            session = await db.get(AuthSession, payload["sid"])
            assert session is not None
            assert session.revoked_at is not None

        revoked = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
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
        assert [session["id"] for session in sessions if session["current"]] == [
            first_payload["sid"]
        ]
        assert all("token" not in session for session in sessions)
        assert all("token_jti" not in session for session in sessions)

        revoke = await ac.delete(
            f"/api/auth/sessions/{second_payload['sid']}",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert revoke.status_code == 200
        assert revoke.json()["revoked"] is True
        assert revoke.json()["revoked_current"] is False

        revoked = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {second_token}"}
        )
        active = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {first_token}"}
        )
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

        current = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {first_token}"}
        )
        other = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {second_token}"}
        )
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

        revoked = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
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


@pytest.mark.asyncio
async def test_http_query_token_is_rejected_for_auth_me():
    """HTTP auth should not accept JWTs in query strings."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    token = create_token("query-user", "query-user", "admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/auth/me?token={token}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_last_admin_protection_rejects_zero_admin_outcome(monkeypatch):
    """Admin management should not strand a team with zero admin accounts."""
    from fastapi import HTTPException

    from app.api.routes import auth as auth_routes
    from app.models.user import User

    async def one_admin(_db):
        return 1

    monkeypatch.setattr(auth_routes, "_admin_count", one_admin)
    user = User(
        id="last-admin",
        username="last-admin",
        email="last-admin@example.com",
        email_hash="hash",
        password_hash="hash",
        role="admin",
    )

    with pytest.raises(HTTPException) as exc:
        await auth_routes._ensure_not_last_admin_demoted_or_deleted(
            None,
            user,
            new_role="viewer",
        )

    assert exc.value.status_code == 400
    assert "admin" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# 2FA / MFA tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_requires_2fa_when_totp_enabled():
    """Verify that login returns requires_2fa when TOTP is enabled and no code provided."""
    await init_db()
    await _clear_auth_accounts()
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
            "/api/auth/login",
            json={"username": username, "password": "xK9#mP2$vL7nQ4@wR1!"},
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
    await _clear_auth_accounts()
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
        import time

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
                "totp_code": pyotp.TOTP(secret).at(int(time.time()) + 30),
            },
        )
        assert login.status_code == 200
        data = login.json()
        assert "token" in data
        assert data.get("requires_2fa") is not True


@pytest.mark.asyncio
async def test_totp_code_replay_is_rejected():
    """Accepted TOTP counters should not be reusable inside the tolerance window."""
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import pyotp
    import time
    import uuid

    username = f"mfareplay_{uuid.uuid4().hex[:8]}"
    email = f"mfareplay_{uuid.uuid4().hex[:8]}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        token = reg.json()["token"]
        setup = await ac.post(
            "/api/auth/totp/setup",
            json={"current_password": password},
            headers={"Authorization": f"Bearer {token}"},
        )
        secret = setup.json()["secret"]
        totp = pyotp.TOTP(secret)
        await ac.post(
            "/api/auth/totp/verify",
            json={"totp_code": totp.now()},
            headers={"Authorization": f"Bearer {token}"},
        )
        await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        login_code = totp.at(int(time.time()) + 30)
        first = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password, "totp_code": login_code},
        )
        replay = await ac.post(
            "/api/auth/login",
            json={"username": username, "password": password, "totp_code": login_code},
        )

    assert first.status_code == 200
    assert replay.status_code == 401
    assert "already been used" in replay.json()["detail"]


@pytest.mark.asyncio
async def test_recovery_code_is_table_backed_and_single_use():
    """Recovery codes should stay as auditable one-time records, not deleted strings."""
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import pyotp
    import uuid

    username = f"recovery_{uuid.uuid4().hex[:8]}"
    email = f"recovery_{uuid.uuid4().hex[:8]}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        assert reg.status_code == 200
        recovery_code = reg.json()["recovery_codes"][0]
        token = reg.json()["token"]

        from app.models.database import async_session
        from app.models.recovery_code import RecoveryCode
        from app.models.user import User
        from sqlalchemy import select

        async with async_session() as db:
            user = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one()
            records = (
                (
                    await db.execute(
                        select(RecoveryCode).where(RecoveryCode.user_id == user.id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(records) == 8
            assert user.recovery_codes_hashed is None

        setup = await ac.post(
            "/api/auth/totp/setup",
            json={"current_password": password},
            headers={"Authorization": f"Bearer {token}"},
        )
        secret = setup.json()["secret"]
        await ac.post(
            "/api/auth/totp/verify",
            json={"totp_code": pyotp.TOTP(secret).now()},
            headers={"Authorization": f"Bearer {token}"},
        )
        await ac.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        first = await ac.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password,
                "recovery_code": recovery_code,
            },
        )
        second = await ac.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password,
                "recovery_code": recovery_code,
            },
        )
        assert first.status_code == 200
        assert second.status_code == 401

        status = await ac.get(
            "/api/auth/recovery-codes/status",
            headers={"Authorization": f"Bearer {first.json()['token']}"},
        )
        assert status.status_code == 200
        assert status.json() == {"remaining": 7, "total": 8}

        async with async_session() as db:
            user = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one()
            used = (
                (
                    await db.execute(
                        select(RecoveryCode).where(
                            RecoveryCode.user_id == user.id,
                            RecoveryCode.used_at.is_not(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(used) == 1
            assert used[0].used_ip_hash


@pytest.mark.asyncio
async def test_auth_events_are_written_to_audit_log():
    """Auth-critical events should be first-class audit entries."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    import uuid

    username = f"auditlogin_{uuid.uuid4().hex[:8]}"
    email = f"auditlogin_{uuid.uuid4().hex[:8]}@example.com"
    password = "xK9#mP2$vL7nQ4@wR1!"
    await _create_team_user(username=username, email=email, password=password)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert login.status_code == 200

    from app.core.audit_middleware import AuditLog
    from app.models.database import async_session
    from sqlalchemy import select

    async with async_session() as db:
        event = (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.event_type == "auth.login.success",
                    AuditLog.user_id == f"user-{username}",
                )
            )
        ).scalar_one_or_none()

    assert event is not None
    assert event.method == "AUTH"
    assert username in event.details


@pytest.mark.asyncio
async def test_totp_setup_requires_current_password():
    """Changing MFA state requires a password confirmation."""
    await init_db()
    await _clear_auth_accounts()
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
