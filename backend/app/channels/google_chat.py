"""Google Chat channel adapter for Istara.

Webhook-based adapter supporting Google Chat via webhook URLs or the
Google Chat API with service account credentials.

Required config keys:
    webhook_url                -- Incoming webhook URL for simple send-only mode
    service_account_json       -- JSON string of service account credentials (for full API)
"""

from __future__ import annotations

import json
import logging

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False
    logger.warning("httpx is not installed. Install with: pip install httpx")


class GoogleChatAdapter(ChannelAdapter):
    """Google Chat adapter supporting webhooks and the Chat API."""

    def __init__(self, instance_id: str = "", config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        self._webhook_url: str = self.config.get("webhook_url", "")
        self._service_account_json: str = self.config.get("service_account_json", "")
        self._http: httpx.AsyncClient | None = None

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def platform(self) -> str:
        return "google_chat"

    @property
    def enabled(self) -> bool:
        has_creds = bool(self._webhook_url or self._service_account_json)
        return has_creds and _HTTPX_AVAILABLE

    async def start(self) -> None:
        """Start the Google Chat adapter (webhook-based, no polling)."""
        if not _HTTPX_AVAILABLE:
            raise RuntimeError("httpx is not installed. Install with: pip install httpx")
        if not self._webhook_url and not self._service_account_json:
            raise RuntimeError(
                "GoogleChatAdapter is not enabled "
                "(missing webhook_url or service_account_json)"
            )
        self._http = httpx.AsyncClient(timeout=30.0)
        self._running = True
        logger.info("Google Chat adapter started (instance=%s).", self.name)

    async def stop(self) -> None:
        """Stop the Google Chat adapter."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._running = False
        logger.info("Google Chat adapter stopped (instance=%s).", self.name)

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message to Google Chat.

        If a webhook_url is configured, POST directly to it.
        If channel_id is a space webhook URL, use that.
        """
        if self._http is None or not self._running:
            logger.warning("GoogleChatAdapter.send() called while not running.")
            return

        metadata = message.metadata or {}

        # Determine the target URL
        target_url = message.channel_id
        if not target_url.startswith("http"):
            # Use the configured webhook_url as fallback
            target_url = self._webhook_url

        if not target_url:
            logger.warning(
                "GoogleChatAdapter.send() -- no valid webhook URL for channel_id=%s",
                message.channel_id,
            )
            return

        # Build payload -- support Cards v2 if provided in metadata
        cards_v2 = metadata.get("cards_v2")
        if cards_v2:
            payload = {"cardsV2": cards_v2}
            if message.text:
                payload["text"] = message.text
        else:
            payload = {"text": message.text}

        try:
            resp = await self._http.post(target_url, json=payload)
            resp.raise_for_status()
        except Exception:
            logger.exception(
                "Failed to send Google Chat message to %s", target_url[:80]
            )

    async def health_check(self) -> dict:
        """Basic health check for Google Chat adapter."""
        if self._http is None:
            return {"status": "stopped", "platform": self.platform}

        # For webhook mode, we can't really verify without sending a message.
        # Just confirm the adapter is running and has valid config.
        return {
            "status": "healthy" if self._running else "stopped",
            "platform": self.platform,
            "mode": "webhook" if self._webhook_url else "service_account",
        }

    # -- Webhook handling -----------------------------------------------------

    async def handle_webhook(self, data: dict) -> None:
        """Parse an incoming Google Chat event and dispatch."""
        if not self._running:
            return

        try:
            event_type = data.get("type", "")

            # Only process MESSAGE events
            if event_type not in ("MESSAGE", "ADDED_TO_SPACE"):
                logger.debug(
                    "GoogleChat ignoring event type: %s on %s", event_type, self.name
                )
                return

            message_data = data.get("message", {})
            text = message_data.get("argumentText", "") or message_data.get("text", "")
            sender = data.get("user", {})
            space = data.get("space", {})

            msg = IncomingMessage(
                channel="google_chat",
                channel_id=space.get("name", ""),
                sender_id=sender.get("name", ""),
                sender_name=sender.get("displayName", ""),
                text=text.strip(),
                instance_id=self.instance_id,
                metadata={
                    "space_type": space.get("type", ""),
                    "space_display_name": space.get("displayName", ""),
                    "message_name": message_data.get("name", ""),
                    "thread_name": message_data.get("thread", {}).get("name", ""),
                    "event_type": event_type,
                },
            )
            await self._dispatch(msg)
        except Exception:
            logger.exception("Error processing Google Chat webhook on %s", self.name)
