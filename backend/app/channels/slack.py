"""Slack channel adapter stub for ReClaw.

This module provides the structural pattern for integrating with Slack.
A full implementation would use the ``slack_bolt`` async adapter or the
``slack_sdk`` WebClient to listen for events and post messages.

Required environment variables:
    SLACK_BOT_TOKEN       – xoxb-... Bot User OAuth Token
    SLACK_SIGNING_SECRET  – Used to verify incoming webhook requests

To fully implement:
    1. Install ``slack-bolt[async]`` (pip install slack-bolt[async]).
    2. In ``start()``, create an ``AsyncApp`` and register event listeners
       (``message``, ``app_mention``) that call ``self._dispatch()``.
    3. Run the app's built-in socket-mode or HTTP handler in a background task.
    4. In ``send()``, use ``AsyncWebClient.chat_postMessage()`` to reply.
    5. Handle rich Slack formatting (blocks, attachments, threads).
"""

from __future__ import annotations

import logging
import os

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class SlackAdapter(ChannelAdapter):
    """Slack channel adapter (stub)."""

    def __init__(self) -> None:
        super().__init__()
        self._bot_token: str | None = os.getenv("SLACK_BOT_TOKEN")
        self._signing_secret: str | None = os.getenv("SLACK_SIGNING_SECRET")

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def name(self) -> str:
        return "slack"

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token and self._signing_secret)

    async def start(self) -> None:
        """Start the Slack event listener.

        A full implementation would:
        - Initialise an ``AsyncApp`` with the bot token and signing secret.
        - Register ``@app.event("message")`` / ``@app.event("app_mention")``
          handlers that normalise incoming Slack events into ``IncomingMessage``
          and call ``await self._dispatch(msg)``.
        - Start the app in socket mode (``AsyncSocketModeHandler``) or as an
          ASGI mount so FastAPI can forward ``/slack/events`` to it.
        """
        if not self.enabled:
            raise RuntimeError("SlackAdapter is not enabled (missing env vars)")
        self._running = True
        logger.info("Slack adapter started (stub — no real connection).")

    async def stop(self) -> None:
        """Stop the Slack event listener."""
        self._running = False
        logger.info("Slack adapter stopped.")

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message to a Slack channel or thread.

        A full implementation would call:
            await client.chat_postMessage(
                channel=message.channel_id,
                text=message.text,
            )
        File attachments would use ``files_upload_v2``.
        """
        if not self._running:
            logger.warning("SlackAdapter.send() called while not running.")
            return
        logger.info(
            "Slack send (stub) -> channel=%s text=%s",
            message.channel_id,
            message.text[:80],
        )
