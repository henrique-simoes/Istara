"""Webhook receiver endpoints for WhatsApp, Google Chat, and future integrations."""

from __future__ import annotations

import logging
import hashlib
import json

from fastapi import APIRouter, HTTPException, Query, Request

from app.channels.base import channel_router
from app.config import settings
from app.core.replay_cache import BoundedReplayCache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks")
_webhook_replay_cache = BoundedReplayCache(max_entries=8192)


def _replay_key(
    *,
    channel: str,
    instance_id: str,
    authenticator: str,
    raw_body: bytes,
) -> str:
    body_hash = hashlib.sha256(raw_body).hexdigest()
    authenticator_hash = hashlib.sha256(authenticator.encode("utf-8")).hexdigest()
    return f"{channel}:{instance_id}:{authenticator_hash}:{body_hash}"


def _reject_replay(
    *,
    channel: str,
    instance_id: str,
    authenticator: str,
    raw_body: bytes,
) -> None:
    key = _replay_key(
        channel=channel,
        instance_id=instance_id,
        authenticator=authenticator,
        raw_body=raw_body,
    )
    if _webhook_replay_cache.seen_or_store(
        key,
        ttl_seconds=max(1, int(settings.webhook_replay_ttl_seconds)),
    ):
        raise HTTPException(status_code=409, detail="Webhook replay detected")


# ---------------------------------------------------------------------------
# WhatsApp webhooks
# ---------------------------------------------------------------------------

@router.get("/whatsapp/{instance_id}")
async def whatsapp_verify(
    instance_id: str,
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
) -> str | dict:
    """WhatsApp webhook verification challenge (GET).

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    We must return hub.challenge if the verify_token matches.
    """
    from app.channels.whatsapp import WhatsAppAdapter

    adapter = channel_router.get(instance_id)
    if adapter is None or not isinstance(adapter, WhatsAppAdapter):
        raise HTTPException(status_code=404, detail="WhatsApp instance not found")

    challenge = adapter.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge is not None:
        return challenge

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp/{instance_id}")
async def whatsapp_webhook(instance_id: str, request: Request) -> dict:
    """WhatsApp webhook receiver (POST).

    Meta POSTs JSON payloads for incoming messages and status updates.
    """
    from app.channels.whatsapp import WhatsAppAdapter

    adapter = channel_router.get(instance_id)
    if adapter is None or not isinstance(adapter, WhatsAppAdapter):
        raise HTTPException(status_code=404, detail="WhatsApp instance not found")

    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    if not adapter.verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid WhatsApp webhook signature")
    _reject_replay(
        channel="whatsapp",
        instance_id=instance_id,
        authenticator=signature or "",
        raw_body=raw_body,
    )

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    await adapter.handle_webhook(data)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Google Chat webhooks
# ---------------------------------------------------------------------------

@router.post("/google-chat/{instance_id}")
async def google_chat_webhook(instance_id: str, request: Request) -> dict:
    """Google Chat webhook receiver (POST).

    Google Chat sends JSON event payloads for messages, space events, etc.
    """
    from app.channels.google_chat import GoogleChatAdapter

    adapter = channel_router.get(instance_id)
    if adapter is None or not isinstance(adapter, GoogleChatAdapter):
        raise HTTPException(status_code=404, detail="Google Chat instance not found")

    token = (
        request.headers.get("x-goog-chat-token")
        or request.headers.get("x-webhook-token")
        or request.query_params.get("token")
    )
    if not adapter.verify_webhook_token(token):
        raise HTTPException(status_code=403, detail="Invalid Google Chat webhook token")

    raw_body = await request.body()
    _reject_replay(
        channel="google-chat",
        instance_id=instance_id,
        authenticator=token or "",
        raw_body=raw_body,
    )

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    await adapter.handle_webhook(data)
    return {"status": "ok"}
