"""Telegram channel adapter stub for ReClaw.

This module provides the structural pattern for integrating with Telegram.
A full implementation would use the ``python-telegram-bot`` library (v20+)
with its async application class.

Required environment variables:
    TELEGRAM_BOT_TOKEN  – The token obtained from @BotFather

To fully implement:
    1. Install ``python-telegram-bot`` (pip install python-telegram-bot).
    2. In ``start()``, create an ``Application`` and add a ``MessageHandler``
       that normalises incoming updates into ``IncomingMessage`` and calls
       ``await self._dispatch(msg)``.
    3. Run the application's polling loop in a background asyncio task
       (``application.run_polling()`` or manual ``application.updater.start_polling()``).
    4. In ``send()``, use ``bot.send_message()`` to reply.
    5. Handle Telegram-specific features (inline keyboards, markdown, media groups).
"""

from __future__ import annotations

import logging
import os

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class TelegramAdapter(ChannelAdapter):
    """Telegram channel adapter (stub)."""

    def __init__(self) -> None:
        super().__init__()
        self._bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token)

    async def start(self) -> None:
        """Start polling for Telegram updates.

        A full implementation would:
        - Build a ``telegram.ext.Application`` with ``ApplicationBuilder().token(...).build()``.
        - Register a ``MessageHandler(filters.TEXT & ~filters.COMMAND, handler)``
          where ``handler`` normalises the ``Update`` into ``IncomingMessage`` and
          calls ``await self._dispatch(msg)``.
        - Start the polling loop: ``await application.updater.start_polling()``.
        - Store the application and updater so ``stop()`` can shut them down.
        """
        if not self.enabled:
            raise RuntimeError("TelegramAdapter is not enabled (missing TELEGRAM_BOT_TOKEN)")
        self._running = True
        logger.info("Telegram adapter started (stub — no real connection).")

    async def stop(self) -> None:
        """Stop the Telegram polling loop."""
        self._running = False
        logger.info("Telegram adapter stopped.")

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message to a Telegram chat.

        A full implementation would call:
            await bot.send_message(
                chat_id=message.channel_id,
                text=message.text,
                parse_mode="Markdown",
            )
        File attachments would use ``bot.send_document`` or ``bot.send_photo``.
        """
        if not self._running:
            logger.warning("TelegramAdapter.send() called while not running.")
            return
        logger.info(
            "Telegram send (stub) -> chat_id=%s text=%s",
            message.channel_id,
            message.text[:80],
        )
