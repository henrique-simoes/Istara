"""Webhook authenticity tests for globally auth-exempt inbound integrations."""

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.channels.base import channel_router
from app.channels.google_chat import GoogleChatAdapter
from app.channels.slack import SlackAdapter
from app.channels.telegram import TelegramAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.main import app
from app.api.routes.webhooks import _webhook_replay_cache


@pytest.fixture(autouse=True)
def cleanup_webhook_adapters():
    _webhook_replay_cache.clear()
    yield
    for instance_id in ("wa-test", "gc-test", "slack-test", "tg-test"):
        channel_router.unregister(instance_id)
    _webhook_replay_cache.clear()


@pytest.mark.asyncio
async def test_whatsapp_webhook_rejects_missing_signature():
    adapter = WhatsAppAdapter(
        "wa-test",
        {
            "phone_number_id": "phone-id",
            "access_token": "access-token",
            "verify_token": "verify-token",
            "app_secret": "app-secret",
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/webhooks/whatsapp/wa-test", json={"entry": []})

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid WhatsApp webhook signature"


@pytest.mark.asyncio
async def test_whatsapp_webhook_accepts_valid_meta_signature():
    secret = "app-secret"
    raw_body = json.dumps({"entry": []}, separators=(",", ":")).encode("utf-8")
    signature = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
    )
    adapter = WhatsAppAdapter(
        "wa-test",
        {
            "phone_number_id": "phone-id",
            "access_token": "access-token",
            "verify_token": "verify-token",
            "app_secret": secret,
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/webhooks/whatsapp/wa-test",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_whatsapp_webhook_rejects_exact_replay():
    secret = "app-secret"
    raw_body = json.dumps({"entry": []}, separators=(",", ":")).encode("utf-8")
    signature = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
    )
    adapter = WhatsAppAdapter(
        "wa-test",
        {
            "phone_number_id": "phone-id",
            "access_token": "access-token",
            "verify_token": "verify-token",
            "app_secret": secret,
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/webhooks/whatsapp/wa-test",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )
        second = await ac.post(
            "/webhooks/whatsapp/wa-test",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Webhook replay detected"


@pytest.mark.asyncio
async def test_google_chat_webhook_requires_shared_token():
    adapter = GoogleChatAdapter(
        "gc-test",
        {
            "webhook_url": "https://chat.googleapis.com/v1/spaces/test/messages",
            "webhook_token": "chat-secret",
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/webhooks/google-chat/gc-test", json={"type": "MESSAGE"}
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Google Chat webhook token"


@pytest.mark.asyncio
async def test_google_chat_webhook_accepts_shared_token_header():
    adapter = GoogleChatAdapter(
        "gc-test",
        {
            "webhook_url": "https://chat.googleapis.com/v1/spaces/test/messages",
            "webhook_token": "chat-secret",
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    payload = {
        "type": "MESSAGE",
        "message": {"text": "hello"},
        "user": {"name": "users/1", "displayName": "Ada"},
        "space": {"name": "spaces/1", "type": "ROOM"},
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/webhooks/google-chat/gc-test",
            json=payload,
            headers={"X-Webhook-Token": "chat-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_google_chat_webhook_rejects_exact_replay():
    adapter = GoogleChatAdapter(
        "gc-test",
        {
            "webhook_url": "https://chat.googleapis.com/v1/spaces/test/messages",
            "webhook_token": "chat-secret",
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    payload = {
        "type": "MESSAGE",
        "message": {"text": "hello"},
        "user": {"name": "users/1", "displayName": "Ada"},
        "space": {"name": "spaces/1", "type": "ROOM"},
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/webhooks/google-chat/gc-test",
            json=payload,
            headers={"X-Webhook-Token": "chat-secret"},
        )
        second = await ac.post(
            "/webhooks/google-chat/gc-test",
            json=payload,
            headers={"X-Webhook-Token": "chat-secret"},
        )

    assert first.status_code == 200
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_slack_webhook_url_verification():
    adapter = SlackAdapter(
        "slack-test",
        {
            "bot_token": "xoxb-test-token",
            "signing_secret": "slack-secret-123",
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/webhooks/slack/slack-test",
            json={"type": "url_verification", "challenge": "test-challenge-abc"},
        )

    assert response.status_code == 200
    assert response.json() == {"challenge": "test-challenge-abc"}


@pytest.mark.asyncio
async def test_slack_webhook_accepts_valid_signature():
    import time
    secret = "slack-secret-123"
    timestamp = str(int(time.time()))
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": "hello from slack",
            "channel": "C12345",
            "user": "U67890",
            "ts": "1620000000.000200",
        },
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig_basestring = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
    signature = "v0=" + hmac.new(
        secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    adapter = SlackAdapter(
        "slack-test",
        {
            "bot_token": "xoxb-test-token",
            "signing_secret": secret,
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/webhooks/slack/slack-test",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_slack_webhook_rejects_invalid_signature():
    import time
    secret = "slack-secret-123"
    timestamp = str(int(time.time()))
    payload = {"type": "event_callback", "event": {"type": "message", "text": "spoofed"}}
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    adapter = SlackAdapter(
        "slack-test",
        {
            "bot_token": "xoxb-test-token",
            "signing_secret": secret,
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/webhooks/slack/slack-test",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": "v0=invalid-signature",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Slack webhook signature"


@pytest.mark.asyncio
async def test_telegram_webhook_accepts_update():
    adapter = TelegramAdapter(
        "tg-test",
        {
            "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        },
    )
    adapter._running = True
    channel_router.register(adapter)

    payload = {
        "update_id": 10001,
        "message": {
            "message_id": 42,
            "from": {"id": 99999, "first_name": "Ada"},
            "chat": {"id": 88888, "type": "private"},
            "text": "Hello Telegram bot",
        },
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/webhooks/telegram/tg-test", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
