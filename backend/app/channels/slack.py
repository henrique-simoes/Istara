"""Slack channel adapter for Istara.

Real implementation using ``slack-bolt[async]>=1.20.0`` with Socket Mode or HTTP.
Handles message events and app_mention events.

Required config keys (or environment fallbacks):
    bot_token / SLACK_BOT_TOKEN         -- xoxb-... Bot User OAuth Token
    signing_secret / SLACK_SIGNING_SECRET -- Webhook signature verification
    app_token / SLACK_APP_TOKEN          -- xapp-... for Socket Mode (optional)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import time
import httpx

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage
from app.core.channel_resilience import CircuitBreaker

logger = logging.getLogger(__name__)

# Optional slack_bolt / slack_sdk dependencies -- graceful degradation
_SOCKET_MODE_AVAILABLE = False
_SLACK_SDK_CLIENT_AVAILABLE = False
try:
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    from slack_bolt.async_app import AsyncApp
    _SOCKET_MODE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    pass

try:
    from slack_sdk.web.async_client import AsyncWebClient
    _SLACK_SDK_CLIENT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    pass

# Slack HTTP webhook mode is always available via httpx
_SLACK_AVAILABLE = True


class _HttpxSlackClient:
    """Lightweight async Slack Web API client backed by httpx.

    Avoids runtime failures when aiohttp or slack-bolt are not installed
    in the execution environment while retaining full compatibility with
    auth_test, chat_postMessage, and file uploads.
    """

    def __init__(self, token: str, base_url: str | None = None) -> None:
        self.token = token
        raw_base = (base_url or "https://slack.com/api").rstrip("/")
        if not raw_base.endswith("/api") and "slack.com" in raw_base:
            raw_base = f"{raw_base}/api"
        self.base_url = raw_base

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def auth_test(self) -> dict:
        url = f"{self.base_url}/auth.test"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self._headers(), json={})
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "Slack auth.test failed"))
            return data

    async def chat_postMessage(self, **kwargs) -> dict:
        url = f"{self.base_url}/chat.postMessage"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self._headers(), json=kwargs)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "Slack chat_postMessage failed"))
            return data

    async def files_upload_v2(self, channel: str, file: str, thread_ts: str | None = None) -> dict:
        url = f"{self.base_url}/files.upload"
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {"channels": channel}
        if thread_ts:
            data["thread_ts"] = thread_ts
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(file, "rb") as f:
                resp = await client.post(url, headers=headers, data=data, files={"file": f})
                resp.raise_for_status()
                return resp.json()


class SlackAdapter(ChannelAdapter):
    """Slack channel adapter using slack-bolt or httpx async API."""

    def __init__(self, instance_id: str = "", config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        self._bot_token: str = self.config.get("bot_token", "") or os.getenv("SLACK_BOT_TOKEN", "")
        self._signing_secret: str = self.config.get("signing_secret", "") or os.getenv(
            "SLACK_SIGNING_SECRET", ""
        )
        self._app_token: str = self.config.get("app_token", "") or os.getenv("SLACK_APP_TOKEN", "")
        self._base_url: str | None = (
            self.config.get("base_url")
            or self.config.get("api_base")
            or os.getenv("SLACK_API_BASE")
        )
        self._slack_app = None
        self._client = None
        self._socket_handler = None
        self._bg_task: asyncio.Task | None = None
        self._breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def platform(self) -> str:
        return "slack"

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token and self._signing_secret) and _SLACK_AVAILABLE

    def _create_client(self):
        client_kwargs = {"token": self._bot_token}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        if _SLACK_SDK_CLIENT_AVAILABLE:
            try:
                return AsyncWebClient(**client_kwargs)
            except Exception:
                pass
        return _HttpxSlackClient(self._bot_token, base_url=self._base_url)

    async def start(self) -> None:
        """Start the Slack event listener or client."""
        if not self._bot_token or not self._signing_secret:
            raise RuntimeError("SlackAdapter is not enabled (missing bot_token or signing_secret)")

        self._client = self._create_client()

        # Start Socket Mode if app_token is available and supported
        if self._app_token:
            if not _SOCKET_MODE_AVAILABLE:
                raise RuntimeError(
                    "slack-bolt and aiohttp are required for Socket Mode. "
                    "Install with: pip install 'slack-bolt[async]>=1.20.0' or use HTTP webhook mode."
                )
            self._slack_app = AsyncApp(
                token=self._bot_token,
                signing_secret=self._signing_secret,
            )
            @self._slack_app.event("message")
            async def handle_message(event, say, context):
                await self._on_message_event(event)

            @self._slack_app.event("app_mention")
            async def handle_mention(event, say, context):
                await self._on_message_event(event)

            self._socket_handler = AsyncSocketModeHandler(self._slack_app, self._app_token)
            self._bg_task = asyncio.create_task(self._socket_handler.start_async())
            logger.info("Slack adapter started in Socket Mode (instance=%s).", self.name)
        else:
            # HTTP mode: events routed via webhooks endpoint
            logger.info(
                "Slack adapter started in HTTP mode (instance=%s). "
                "Events are routed via /webhooks/slack/{instance_id}.",
                self.name,
            )

        self._running = True

    async def stop(self) -> None:
        """Stop the Slack event listener."""
        if self._socket_handler is not None:
            try:
                await self._socket_handler.close_async()
            except Exception:
                logger.exception("Error closing Slack socket handler %s", self.name)
            self._socket_handler = None

        if self._bg_task is not None:
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass
            self._bg_task = None

        self._slack_app = None
        self._client = None
        self._running = False
        logger.info("Slack adapter stopped (instance=%s).", self.name)

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message to a Slack channel or thread (with retry + circuit breaker)."""
        if self._client is None or not self._running:
            logger.warning("SlackAdapter.send() called while not running.")
            return

        from app.core.channel_resilience import retry_with_backoff

        metadata = message.metadata or {}
        kwargs: dict = {
            "channel": message.channel_id,
            "text": message.text,
        }

        # Support thread replies
        thread_ts = metadata.get("thread_ts")
        if thread_ts:
            kwargs["thread_ts"] = thread_ts

        # Support Block Kit
        blocks = metadata.get("blocks")
        if blocks:
            kwargs["blocks"] = blocks

        async def _send_text() -> None:
            await self._client.chat_postMessage(**kwargs)

        await self._breaker.call(
            lambda: retry_with_backoff(_send_text, max_retries=3, base_delay=1.0)
        )

        # Retry each attachment independently so a later upload failure does not
        # resend already-delivered text or previous files.
        if message.attachments:
            for file_path in message.attachments:

                async def _upload_file(path: str = file_path) -> None:
                    await self._client.files_upload_v2(
                        channel=message.channel_id,
                        file=path,
                        thread_ts=thread_ts,
                    )

                await self._breaker.call(
                    lambda: retry_with_backoff(_upload_file, max_retries=3, base_delay=1.0)
                )

    async def health_check(self) -> dict:
        """Check Slack connection health."""
        if self._client is None:
            return {"status": "stopped", "platform": self.platform}
        try:
            result = await self._client.auth_test()
            return {
                "status": "healthy",
                "platform": self.platform,
                "team": result.get("team", ""),
                "user": result.get("user", ""),
                "bot_id": result.get("bot_id", ""),
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "platform": self.platform,
                "error": str(exc),
            }

    def verify_signature(self, raw_body: bytes, timestamp: str | None, signature: str | None) -> bool:
        """Verify Slack HMAC SHA-256 webhook signature."""
        if not self._signing_secret or not timestamp or not signature:
            return False
        try:
            ts = float(timestamp)
            if abs(time.time() - ts) > 300:
                logger.warning("Slack webhook timestamp expired: %s", timestamp)
                return False
        except (ValueError, TypeError):
            return False

        sig_basestring = f"v0:{timestamp}:{raw_body.decode('utf-8', errors='replace')}"
        computed = "v0=" + hmac.new(
            self._signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    async def handle_webhook(self, payload: dict) -> None:
        """Handle an incoming Slack event from an HTTP webhook."""
        event = payload.get("event")
        if event and isinstance(event, dict):
            await self._on_message_event(event)

    # -- Internal handlers ----------------------------------------------------

    async def _on_message_event(self, event: dict) -> None:
        """Normalise a Slack event into IncomingMessage and dispatch."""
        # Ignore bot messages to prevent loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        text = event.get("text", "")
        channel_id = event.get("channel", "")
        sender_id = event.get("user", "")
        thread_ts = event.get("thread_ts") or event.get("ts", "")

        msg = IncomingMessage(
            channel="slack",
            channel_id=channel_id,
            sender_id=sender_id,
            sender_name=sender_id,  # Slack doesn't include display name in events
            text=text,
            instance_id=self.instance_id,
            metadata={
                "thread_ts": thread_ts,
                "event_ts": event.get("ts", ""),
            },
        )
        await self._dispatch(msg)
