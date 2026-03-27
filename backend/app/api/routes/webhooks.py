"""Webhook receiver endpoints for WhatsApp, Google Chat, and future integrations."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.channels.base import channel_router

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks")


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

    try:
        data = await request.json()
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

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    await adapter.handle_webhook(data)
    return {"status": "ok"}
