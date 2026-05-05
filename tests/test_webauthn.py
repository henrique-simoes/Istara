"""Tests for WebAuthn API routes — register start/finish, authenticate start/finish, credentials."""

import pytest
from app.config import settings
from app.core.auth import create_token, hash_password
from app.core.field_encryption import hash_field
from app.main import app
from app.models.database import async_session, init_db
from app.models.user import User
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_rp_id = settings.webauthn_rp_id
    original_origins = settings.webauthn_origins
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.webauthn_rp_id = original_rp_id
    settings.webauthn_origins = original_origins


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_webauthn_register_start_requires_user():
    """POST /api/webauthn/register/start requires username."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/webauthn/register/start", json={})
        assert response.status_code in (401, 404, 422)


@pytest.mark.asyncio
async def test_webauthn_requires_auth():
    """WebAuthn endpoints require authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/webauthn/credentials")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_webauthn_authenticate_start_is_public_but_validated():
    """Passkey sign-in must be reachable before a token exists."""
    await init_db()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    import uuid

    suffix = uuid.uuid4().hex[:8]
    username = f"passkeyuser_{suffix}"
    email = f"passkey_{suffix}@example.com"

    async with async_session() as db:
        user = User(
            id=f"passkey-user-{suffix}",
            username=username,
            email=email,
            email_hash=hash_field(email),
            password_hash=hash_password("xK9#mP2$vL7nQ4@wR1!"),
            role="researcher",
        )
        db.add(user)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/webauthn/authenticate/start",
            json={"username": username},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "No passkeys registered for this user"


@pytest.mark.asyncio
async def test_webauthn_authenticate_start_rejects_untrusted_browser_origin():
    """Passkey sign-in ceremonies should share the auth trusted-origin gate."""
    await init_db()
    settings.team_mode = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/webauthn/authenticate/start",
            json={"username": "anyone"},
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    assert "Untrusted browser origin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webauthn_register_start_returns_browser_options():
    """Registration start should work with the installed webauthn package API."""
    await init_db()
    settings.team_mode = True
    settings.webauthn_rp_id = "localhost"
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    import uuid

    suffix = uuid.uuid4().hex[:8]
    user_id = f"passkey-register-{suffix}"
    username = f"passkeyregister_{suffix}"
    email = f"passkeyregister_{suffix}@example.com"

    async with async_session() as db:
        user = User(
            id=user_id,
            username=username,
            email=email,
            email_hash=hash_field(email),
            password_hash=hash_password("xK9#mP2$vL7nQ4@wR1!"),
            role="researcher",
        )
        db.add(user)
        await db.commit()

    token = create_token(user_id, username, "researcher")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/webauthn/register/start",
            json={"username": username, "display_name": username},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    public_key = response.json()["publicKey"]
    assert public_key["rp"]["id"] == "localhost"
    assert public_key["user"]["name"] == username
    assert public_key["authenticatorSelection"]["userVerification"] == "required"
    assert public_key["challenge"]


@pytest.mark.asyncio
async def test_webauthn_challenges_are_scoped_by_ceremony():
    """Registration and authentication challenges cannot overwrite each other."""
    from app.api.routes.webauthn import _get_and_clear_challenge, _store_challenge

    await init_db()
    suffix = "challenge-scope"
    async with async_session() as db:
        user = User(
            id=suffix,
            username=suffix,
            email=f"{suffix}@example.com",
            email_hash=hash_field(f"{suffix}@example.com"),
            password_hash=hash_password("xK9#mP2$vL7nQ4@wR1!"),
            role="researcher",
        )
        await db.merge(user)
        await db.commit()
        await _store_challenge(db, "registration", suffix, b"registration")
        await _store_challenge(db, "authentication", suffix, b"authentication")

        assert await _get_and_clear_challenge(db, "registration", suffix) == b"registration"
        assert await _get_and_clear_challenge(db, "authentication", suffix) == b"authentication"
        assert await _get_and_clear_challenge(db, "registration", suffix) is None


def test_webauthn_expected_origins_are_configurable():
    """Production passkey verification should not be locked to localhost."""
    from app.api.routes.webauthn import _expected_origins, _rp_id

    settings.webauthn_rp_id = "istara.example.com"
    settings.webauthn_origins = "https://istara.example.com, https://app.istara.example.com/"

    assert _rp_id() == "istara.example.com"
    assert _expected_origins() == [
        "https://istara.example.com",
        "https://app.istara.example.com",
    ]


def test_webauthn_expected_origins_require_secure_rp_compatible_origins():
    """Passkey verification should ignore origins that browsers cannot bind to the RP."""
    from app.api.routes.webauthn import _expected_origins

    settings.webauthn_rp_id = "istara.example.com"
    settings.webauthn_origins = (
        "https://istara.example.com, http://istara.example.com, "
        "https://evil.example.com, https://research.istara.example.com"
    )

    assert _expected_origins() == [
        "https://istara.example.com",
        "https://research.istara.example.com",
    ]
