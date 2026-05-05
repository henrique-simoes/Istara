"""Tests for Connections API routes — generate, validate, redeem, rotate-network-token."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.models.database import async_session
from app.core.auth import create_token
from app.core.connection_string import (
    create_connection_string,
    decode_connection_string,
    hash_connection_string,
)
from app.api.routes import connections as connection_routes
from app.models.connection_string import ConnectionString


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    connection_routes._validation_limiter.clear()
    connection_routes._redeem_limiter.clear()
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    connection_routes._validation_limiter.clear()
    connection_routes._redeem_limiter.clear()


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
        assert response.status_code == 200
        assert response.json()["valid"] is False


@pytest.mark.asyncio
async def test_connections_list_requires_auth():
    """Listing generated connection strings requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/connections")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_connection_string_rejects_unsafe_urls(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        bad_server = await ac.post(
            "/api/connections/generate",
            headers=auth_headers,
            json={"server_url": "file:///tmp/istara", "label": "Bad"},
        )
        bad_ws = await ac.post(
            "/api/connections/compute-donation/generate",
            headers=auth_headers,
            json={
                "server_url": "https://istara.example.com",
                "ws_url": "https://istara.example.com/ws/relay",
            },
        )
        bad_expiry = await ac.post(
            "/api/connections/generate",
            headers=auth_headers,
            json={"server_url": "https://istara.example.com", "expires_hours": 0},
        )

    assert bad_server.status_code == 422
    assert bad_ws.status_code == 422
    assert bad_expiry.status_code == 422


def test_connection_string_keeps_http_and_websocket_urls_separate():
    conn = create_connection_string(
        server_url="https://istara.example.com",
        ws_url="wss://relay.example.com/ws/relay",
        label="Planner Laptop",
    )
    payload = decode_connection_string(conn)
    assert payload is not None
    assert payload["server_url"] == "https://istara.example.com"
    assert payload["ws_url"] == "wss://relay.example.com/ws/relay"
    assert "jwt" not in payload
    assert payload["nonce"]


@pytest.mark.asyncio
async def test_connection_string_lifecycle_tracks_validation_and_redemption(auth_headers):
    await init_db()
    original_team_mode = settings.team_mode
    settings.team_mode = False
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            generated = await ac.post(
                "/api/connections/generate",
                headers=auth_headers,
                json={
                    "server_url": "http://server.test:3000",
                    "ws_url": "ws://server.test:8000/ws/relay",
                    "label": "Lifecycle Laptop",
                    "expires_hours": 24,
                },
            )
            assert generated.status_code == 200
            conn_str = generated.json()["connection_string"]

            validation = await ac.post(
                "/api/connections/validate",
                json={"connection_string": conn_str},
            )
            assert validation.status_code == 200
            assert validation.json()["valid"] is True

            async with async_session() as db:
                result = await db.execute(
                    select(ConnectionString).where(
                        ConnectionString.connection_string_hash == hash_connection_string(conn_str)
                    )
                )
                conn = result.scalar_one()
                assert conn.connection_string != conn_str
                assert conn.last_validated_at is not None
                assert conn.redeemed_username is None

            redemption = await ac.post(
                "/api/connections/redeem",
                json={
                    "connection_string": conn_str,
                    "username": "first_redeemer",
                    "password": "password123",
                },
            )
            assert redemption.status_code == 200
            assert redemption.json()["server_url"] == "http://server.test:3000"
            assert redemption.json()["ws_url"] == "ws://server.test:8000/ws/relay"

            second_redemption = await ac.post(
                "/api/connections/redeem",
                json={
                    "connection_string": conn_str,
                    "username": "second_redeemer",
                    "password": "password123",
                },
            )
            assert second_redemption.status_code == 400

            second_validation = await ac.post(
                "/api/connections/validate",
                json={"connection_string": conn_str},
            )
            assert second_validation.status_code == 200
            assert second_validation.json()["valid"] is False

            async with async_session() as db:
                result = await db.execute(
                    select(ConnectionString).where(
                        ConnectionString.connection_string_hash == hash_connection_string(conn_str)
                    )
                )
                conn = result.scalar_one()
                assert conn.is_redeemed is True
                assert conn.redeemed_by_user_id == "local"
                assert conn.redeemed_username == "first_redeemer"
                assert conn.redeemed_at is not None
    finally:
        settings.team_mode = original_team_mode


@pytest.mark.asyncio
async def test_team_connection_string_redemption_generates_recovery_codes(auth_headers):
    await init_db()
    settings.team_mode = True
    import uuid

    suffix = uuid.uuid4().hex[:8]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        generated = await ac.post(
            "/api/connections/generate",
            headers=auth_headers,
            json={
                "server_url": "http://server.test:3000",
                "label": "Team Invite",
                "expires_hours": 24,
            },
        )
        assert generated.status_code == 200
        redeemed = await ac.post(
            "/api/connections/redeem",
            json={
                "connection_string": generated.json()["connection_string"],
                "username": f"team_redeemer_{suffix}",
                "password": "xK9#mP2$vL7nQ4@wR1!",
                "email": f"team_redeemer_{suffix}@example.com",
            },
        )

    assert redeemed.status_code == 200
    body = redeemed.json()
    assert body["network_token"] == ""
    assert len(body["recovery_codes"]) == 8
    assert "token" in body

    from app.models.recovery_code import RecoveryCode
    from app.models.user import User

    async with async_session() as db:
        user = (
            await db.execute(select(User).where(User.username == f"team_redeemer_{suffix}"))
        ).scalar_one()
        records = (
            (await db.execute(select(RecoveryCode).where(RecoveryCode.user_id == user.id)))
            .scalars()
            .all()
        )
        assert len(records) == 8
        assert user.recovery_codes_hashed is None


@pytest.mark.asyncio
async def test_connection_string_revoked_and_expired_fail_clearly(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        generated = await ac.post(
            "/api/connections/generate",
            headers=auth_headers,
            json={
                "server_url": "http://server.test:3000",
                "label": "Revoked Laptop",
                "expires_hours": 24,
            },
        )
        assert generated.status_code == 200
        body = generated.json()

        revoked = await ac.delete(f"/api/connections/{body['id']}", headers=auth_headers)
        assert revoked.status_code == 200

        validation = await ac.post(
            "/api/connections/validate",
            json={"connection_string": body["connection_string"]},
        )
        assert validation.status_code == 200
        assert validation.json() == {"valid": False, "error": "Connection string has been revoked"}

        expired = create_connection_string(
            server_url="http://server.test:3000",
            label="Expired Laptop",
            expires_hours=-1,
        )
        expired_validation = await ac.post(
            "/api/connections/validate",
            json={"connection_string": expired},
        )
        assert expired_validation.status_code == 200
        assert expired_validation.json() == {
            "valid": False,
            "error": "Invalid or expired connection string",
        }


@pytest.mark.asyncio
async def test_network_token_rotation_invalidates_active_connection_strings(
    auth_headers, monkeypatch
):
    await init_db()
    original_network_token = settings.network_access_token
    monkeypatch.setattr("app.api.routes.settings._persist_env", lambda key, value: None)
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            generated = await ac.post(
                "/api/connections/generate",
                headers=auth_headers,
                json={
                    "server_url": "http://server.test:3000",
                    "label": "Rotation Laptop",
                    "expires_hours": 24,
                },
            )
            assert generated.status_code == 200
            conn_str = generated.json()["connection_string"]

            rotated = await ac.post("/api/connections/rotate-network-token", headers=auth_headers)
            assert rotated.status_code == 200

            validation = await ac.post(
                "/api/connections/validate",
                json={"connection_string": conn_str},
            )
            assert validation.status_code == 200
            assert validation.json()["valid"] is False

            async with async_session() as db:
                result = await db.execute(
                    select(ConnectionString).where(
                        ConnectionString.connection_string_hash == hash_connection_string(conn_str)
                    )
                )
                conn = result.scalar_one()
                assert conn.is_active is False
    finally:
        settings.network_access_token = original_network_token


@pytest.mark.asyncio
async def test_connection_string_validation_rate_limit(monkeypatch):
    await init_db()
    connection_routes._validation_limiter.clear()
    monkeypatch.setattr(connection_routes, "VALIDATION_RATE_LIMIT", 2)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for _ in range(2):
            response = await ac.post(
                "/api/connections/validate",
                json={"connection_string": "invalid"},
            )
            assert response.status_code == 200
            assert response.json()["error"] == "Invalid or expired connection string"

        limited = await ac.post(
            "/api/connections/validate",
            json={"connection_string": "invalid"},
        )
        assert limited.status_code == 200
        assert limited.json() == {
            "valid": False,
            "error": "Too many validation attempts. Try again shortly.",
        }


@pytest.mark.asyncio
async def test_connection_list_redacts_stored_secret(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        generated = await ac.post(
            "/api/connections/generate",
            headers=auth_headers,
            json={
                "server_url": "http://server.test:3000",
                "label": "Redacted Laptop",
                "expires_hours": 24,
            },
        )
        assert generated.status_code == 200
        conn_str = generated.json()["connection_string"]

        listed = await ac.get("/api/connections", headers=auth_headers)

    assert listed.status_code == 200
    rows = listed.json()
    assert rows
    assert all(row.get("connection_string") is None for row in rows)
    assert any(row.get("connection_string_preview") for row in rows)
    assert conn_str not in json_dumps(rows)


def json_dumps(value):
    import json

    return json.dumps(value, sort_keys=True)
