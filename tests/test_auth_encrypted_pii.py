from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.config import settings
from app.core.auth import create_token, hash_password
from app.core.field_encryption import (
    encryption_health_snapshot,
    hash_field,
    reset_encryption_health_for_tests,
    safe_decrypt_field,
)
from app.api.routes.auth import _user_to_dict
from app.main import app
from app.models.database import async_session, init_db
from app.models.user import User, UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text


@pytest.mark.asyncio
async def test_auth_users_fail_closed_on_unreadable_encrypted_email():
    """Unreadable encrypted user PII must not leak raw ciphertext to Settings."""
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    try:
        reset_encryption_health_for_tests()
        now = datetime.now(UTC)
        async with async_session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO users (
                        id, username, email, email_hash, password_hash, role,
                        display_name, preferences, totp_enabled, passkey_enabled,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :username, :email, :email_hash, :password_hash, :role,
                        :display_name, :preferences, :totp_enabled, :passkey_enabled,
                        :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": "cipher-admin",
                    "username": "cipher_admin",
                    "email": "ENC:invalid-base64-data!!!",
                    "email_hash": hash_field("cipher_admin@example.com"),
                    "password_hash": hash_password("xK9#mP2$vL7nQ4@wR1!"),
                    "role": "ADMIN",
                    "display_name": "Cipher Admin",
                    "preferences": "{}",
                    "totp_enabled": False,
                    "passkey_enabled": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await db.commit()

        token = create_token("admin-1", "admin", "admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                "/api/auth/users",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert "ENC:" not in response.text
        user = next(item for item in response.json() if item["username"] == "cipher_admin")
        assert user["email"] == ""
        assert encryption_health_snapshot()["decryption_failures"] >= 1
    finally:
        await _clear_auth_accounts()
        settings.team_mode = original_team_mode
        settings.jwt_secret = original_jwt_secret


def test_user_serializer_redacts_stale_ciphertext_after_key_mismatch():
    """Every user-facing serializer must fail closed even for a stale ORM value."""
    user = User(
        id="stale-cipher-user",
        username="stale_cipher",
        email="ENC:stale-ciphertext",
        email_hash=hash_field("stale@example.com"),
        password_hash="not-used",
        role=UserRole.RESEARCHER,
        display_name="Stale Cipher",
        preferences="{}",
    )

    assert safe_decrypt_field(user.email) == ""
    assert _user_to_dict(user)["email"] == ""


@pytest.mark.asyncio
async def test_admin_users_fail_closed_on_unreadable_encrypted_email():
    """The admin user list must not leak raw ciphertext for unreadable emails."""
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    await init_db()
    await _clear_auth_accounts()
    settings.team_mode = True
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"

    try:
        reset_encryption_health_for_tests()
        now = datetime.now(UTC)
        async with async_session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO users (
                        id, username, email, email_hash, password_hash, role,
                        display_name, preferences, totp_enabled, passkey_enabled,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :username, :email, :email_hash, :password_hash, :role,
                        :display_name, :preferences, :totp_enabled, :passkey_enabled,
                        :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": "cipher-admin-list",
                    "username": "cipher_admin_list",
                    "email": "ENC:invalid-base64-data!!!",
                    "email_hash": hash_field("cipher_admin_list@example.com"),
                    "password_hash": hash_password("xK9#mP2$vL7nQ4@wR1!"),
                    "role": "ADMIN",
                    "display_name": "Cipher Admin List",
                    "preferences": "{}",
                    "totp_enabled": False,
                    "passkey_enabled": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await db.commit()

        token = create_token("admin-1", "admin", "admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                "/api/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert "ENC:" not in response.text
        user = next(item for item in response.json()["users"] if item["username"] == "cipher_admin_list")
        assert user["email"] == ""
        assert encryption_health_snapshot()["decryption_failures"] >= 1
    finally:
        await _clear_auth_accounts()
        settings.team_mode = original_team_mode
        settings.jwt_secret = original_jwt_secret


async def _clear_auth_accounts() -> None:
    from app.models.auth_session import AuthSession
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
