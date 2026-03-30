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
import logging
import os

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

# Optional dependency -- graceful degradation if not installed.
try:
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    from slack_bolt.async_app import AsyncApp
    from slack_sdk.web.async_client import AsyncWebClient

    _SLACK_AVAILABLE = True
except ImportError:
    _SLACK_AVAILABLE = False
    logger.warning(
        "slack-bolt is not installed. "
        "Install with: pip install 'slack-bolt[async]>=1.20.0'"
    )


class SlackAdapter(ChannelAdapter):
    """Slack channel adapter using slack-bolt async API."""

    def __init__(self, instance_id: str = "", config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        self._bot_token: str = self.config.get("bot_token", "") or os.getenv(
            "SLACK_BOT_TOKEN", ""
        )
        self._signing_secret: str = self.config.get("signing_secret", "") or os.getenv(
            "SLACK_SIGNING_SECRET", ""
        )
        self._app_token: str = self.config.get("app_token", "") or os.getenv(
            "SLACK_APP_TOKEN", ""
        )
        self._slack_app = None  # slack_bolt AsyncApp
        self._client: AsyncWebClient | None = None
        self._socket_handler = None
        self._bg_task: asyncio.Task | None = None

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def platform(self) -> str:
        return "slack"

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token and self._signing_secret) and _SLACK_AVAILABLE

    async def start(self) -> None:
        """Start the Slack event listener."""
        if not _SLACK_AVAILABLE:
            raise RuntimeError(
                "slack-bolt is not installed. "
                "Install with: pip install 'slack-bolt[async]>=1.20.0'"
            )
        if not self._bot_token or not self._signing_secret:
            raise RuntimeError(
                "SlackAdapter is not enabled (missing bot_token or signing_secret)"
            )

        self._slack_app = AsyncApp(
            token=self._bot_token,
            signing_secret=self._signing_secret,
        )
        self._client = AsyncWebClient(token=self._bot_token)

        # Register event handlers
        @self._slack_app.event("message")
        async def handle_message(event, say, context):
            await self._on_message_event(event)

        @self._slack_app.event("app_mention")
        async def handle_mention(event, say, context):
            await self._on_message_event(event)

        # Start Socket Mode if app_token is available
        if self._app_token:
            self._socket_handler = AsyncSocketModeHandler(
                self._slack_app, self._app_token
            )
            self._bg_task = asyncio.create_task(self._socket_handler.start_async())
            logger.info(
                "Slack adapter started in Socket Mode (instance=%s).", self.name
            )
        else:
            # HTTP mode: the app needs to be mounted externally or events
            # routed via a webhook. We mark as running but note the limitation.
            logger.info(
                "Slack adapter started in HTTP mode (instance=%s). "
                "Events must be routed externally via /slack/events.",
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
        """Send a message to a Slack channel or thread."""
        if self._client is None or not self._running:
            logger.warning("SlackAdapter.send() called while not running.")
            return

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

        try:
            await self._client.chat_postMessage(**kwargs)
        except Exception:
            logger.exception(
                "Failed to send Slack message to channel %s", message.channel_id
            )

        # Handle file attachments via files_upload_v2
        if message.attachments:
            for file_path in message.attachments:
                try:
                    await self._client.files_upload_v2(
                        channel=message.channel_id,
                        file=file_path,
                        thread_ts=thread_ts,
                    )
                except Exception:
                    logger.exception(
                        "Failed to upload attachment %s to Slack channel %s",
                        file_path,
                        message.channel_id,
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
