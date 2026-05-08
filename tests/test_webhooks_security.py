"""Webhook authenticity tests for globally auth-exempt inbound integrations."""

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.channels.base import channel_router
from app.channels.google_chat import GoogleChatAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.main import app
from app.api.routes.webhooks import _webhook_replay_cache


@pytest.fixture(autouse=True)
def cleanup_webhook_adapters():
    _webhook_replay_cache.clear()
    yield
    for instance_id in ("wa-test", "gc-test"):
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
    signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
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
    signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
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
        response = await ac.post("/webhooks/google-chat/gc-test", json={"type": "MESSAGE"})

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
