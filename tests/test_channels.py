"""Tests for Channels API routes — CRUD, start/stop, health, messages, conversations, send."""

import json

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.channels.base import channel_router
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.models.database import async_session
from app.models.channel_instance import ChannelInstance
from app.core.field_encryption import decrypt_field
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


@pytest.mark.asyncio
async def test_channels_list_returns_list(auth_headers):
    """GET /api/channels returns a list."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/channels", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_channels_list_requires_auth():
    """Channels listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/channels")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_channel_create_normalizes_ui_credential_labels(auth_headers):
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/channels",
            headers=auth_headers,
            json={
                "platform": "slack",
                "name": "Research Slack",
                "config": {
                    "Bot Token": " xoxb-test ",
                    "Signing Secret": " secret ",
                    "App Token": "",
                },
            },
        )

    assert response.status_code == 200
    instance_id = response.json()["id"]
    async with async_session() as db:
        result = await db.execute(select(ChannelInstance).where(ChannelInstance.id == instance_id))
        instance = result.scalar_one()
        stored = json.loads(decrypt_field(instance.config_json))

    assert stored == {"bot_token": "xoxb-test", "signing_secret": "secret"}


@pytest.mark.asyncio
async def test_channel_start_missing_config_reports_not_enabled(auth_headers, monkeypatch):
    await init_db()
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setattr("app.channels.telegram._TELEGRAM_AVAILABLE", True)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/channels",
            headers=auth_headers,
            json={"platform": "telegram", "name": "Missing Token", "config": {}},
        )
        assert created.status_code == 200
        instance_id = created.json()["id"]

        started = await ac.post(f"/api/channels/{instance_id}/start", headers=auth_headers)
        health = await ac.get(f"/api/channels/{instance_id}/health", headers=auth_headers)

    assert started.status_code == 200
    assert started.json()["status"] == "not_enabled"
    assert health.status_code == 200
    assert health.json()["status"] == "not_enabled"
    assert channel_router.get(instance_id) is None
