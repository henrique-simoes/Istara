"""WhatsApp Business Cloud API channel adapter for Istara.

Webhook-based adapter using the Meta Graph API for sending messages and
receiving inbound messages via webhook callbacks.

Required config keys (or environment fallbacks):
    phone_number_id / WHATSAPP_PHONE_NUMBER_ID  -- Business phone number ID
    access_token / WHATSAPP_ACCESS_TOKEN        -- Permanent or system-user token
    verify_token / WHATSAPP_VERIFY_TOKEN        -- Webhook verification token
"""

from __future__ import annotations

import logging
import os
import time

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False
    logger.warning("httpx is not installed. Install with: pip install httpx")

GRAPH_API_BASE = "https://graph.facebook.com/v22.0"

# WhatsApp enforces a 24-hour conversation window for business-initiated messages.
_CONVERSATION_WINDOW_SECONDS = 24 * 60 * 60


class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp Business Cloud API adapter using httpx."""

    def __init__(self, instance_id: str = "", config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        self._phone_number_id: str = self.config.get(
            "phone_number_id", ""
        ) or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self._access_token: str = self.config.get("access_token", "") or os.getenv(
            "WHATSAPP_ACCESS_TOKEN", ""
        )
        self._verify_token: str = self.config.get("verify_token", "") or os.getenv(
            "WHATSAPP_VERIFY_TOKEN", ""
        )
        self._http: httpx.AsyncClient | None = None
        # Track last inbound timestamp per chat_id for 24-hour window
        self._last_inbound_at: dict[str, float] = {}

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def platform(self) -> str:
        return "whatsapp"

    @property
    def enabled(self) -> bool:
        return bool(self._phone_number_id and self._access_token) and _HTTPX_AVAILABLE

    async def start(self) -> None:
        """Start the WhatsApp adapter (webhook-based, no polling)."""
        if not _HTTPX_AVAILABLE:
            raise RuntimeError("httpx is not installed. Install with: pip install httpx")
        if not self._phone_number_id or not self._access_token:
            raise RuntimeError(
                "WhatsAppAdapter is not enabled (missing phone_number_id or access_token)"
            )
        self._http = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._running = True
        logger.info("WhatsApp adapter started (instance=%s).", self.name)

    async def stop(self) -> None:
        """Stop the WhatsApp adapter."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._running = False
        logger.info("WhatsApp adapter stopped (instance=%s).", self.name)

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message via WhatsApp Cloud API."""
        if self._http is None or not self._running:
            logger.warning("WhatsAppAdapter.send() called while not running.")
            return

        url = f"{GRAPH_API_BASE}/{self._phone_number_id}/messages"
        metadata = message.metadata or {}

        # Check 24-hour conversation window
        recipient = message.channel_id
        last_inbound = self._last_inbound_at.get(recipient, 0)
        if time.time() - last_inbound > _CONVERSATION_WINDOW_SECONDS:
            logger.warning(
                "WhatsApp 24-hour window may have expired for %s. "
                "Message may require a template.",
                recipient,
            )

        # Build payload
        if metadata.get("type") == "template":
            # Template message (for outside 24-hour window)
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": metadata.get("template", {}),
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": message.text},
            }

        try:
            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()
        except Exception:
            logger.exception(
                "Failed to send WhatsApp message to %s", recipient
            )

    async def health_check(self) -> dict:
        """Check WhatsApp connection by querying the phone number info."""
        if self._http is None:
            return {"status": "stopped", "platform": self.platform}
        try:
            url = f"{GRAPH_API_BASE}/{self._phone_number_id}"
            resp = await self._http.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "healthy",
                "platform": self.platform,
                "phone_number": data.get("display_phone_number", ""),
                "quality_rating": data.get("quality_rating", ""),
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "platform": self.platform,
                "error": str(exc),
            }

    # -- Webhook handling -----------------------------------------------------

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """Verify the WhatsApp webhook subscription.

        Returns the challenge string if verification succeeds, None otherwise.
        """
        if mode == "subscribe" and token == self._verify_token:
            return challenge
        return None

    async def handle_webhook(self, data: dict) -> None:
        """Parse an incoming WhatsApp webhook payload and dispatch messages."""
        if not self._running:
            return

        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    contacts = value.get("contacts", [])

                    # Build contact lookup
                    contact_map: dict[str, str] = {}
                    for contact in contacts:
                        wa_id = contact.get("wa_id", "")
                        name = contact.get("profile", {}).get("name", "")
                        if wa_id:
                            contact_map[wa_id] = name

                    for wa_msg in messages:
                        await self._process_webhook_message(wa_msg, contact_map)
        except Exception:
            logger.exception("Error processing WhatsApp webhook on %s", self.name)

    async def _process_webhook_message(
        self, wa_msg: dict, contact_map: dict[str, str]
    ) -> None:
        """Process a single WhatsApp message from webhook payload."""
        msg_type = wa_msg.get("type", "text")
        sender = wa_msg.get("from", "")
        sender_name = contact_map.get(sender, "")
        msg_id = wa_msg.get("id", "")

        # Track inbound timestamp for conversation window
        self._last_inbound_at[sender] = time.time()

        text = ""
        content_type = "text"
        attachments: list[str] = []

        if msg_type == "text":
            text = wa_msg.get("text", {}).get("body", "")
        elif msg_type == "audio":
            # Auto-transcribe audio messages
            text = "[Audio message — transcription pending]"
            content_type = "audio"
            media_id = wa_msg.get("audio", {}).get("id", "")
            if media_id:
                attachments.append(f"whatsapp:media:{media_id}")
                # Note: Actual transcription happens in the interview pipeline
                # when the audio file is downloaded and processed
        elif msg_type == "image":
            text = wa_msg.get("image", {}).get("caption", "") or "[image]"
            content_type = "image"
            media_id = wa_msg.get("image", {}).get("id", "")
            if media_id:
                attachments.append(f"whatsapp:media:{media_id}")
        elif msg_type == "document":
            filename = wa_msg.get("document", {}).get("filename", "document")
            text = wa_msg.get("document", {}).get("caption", "") or f"[file: {filename}]"
            content_type = "file"
            media_id = wa_msg.get("document", {}).get("id", "")
            if media_id:
                attachments.append(f"whatsapp:media:{media_id}")
        else:
            text = f"[{msg_type} message]"

        msg = IncomingMessage(
            channel="whatsapp",
            channel_id=sender,
            sender_id=sender,
            sender_name=sender_name,
            text=text,
            instance_id=self.instance_id,
            attachments=attachments,
            metadata={
                "content_type": content_type,
                "external_message_id": msg_id,
                "message_type": msg_type,
            },
        )
        await self._dispatch(msg)
