"""Telegram channel adapter for Istara.

Real implementation using ``python-telegram-bot>=22.0`` with async polling.
Handles text, voice, photo, and document messages.

Required config keys (or environment fallbacks):
    bot_token / TELEGRAM_BOT_TOKEN  -- The token obtained from @BotFather
"""

from __future__ import annotations

import io
import logging
import os
import re
from pathlib import Path

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage
from app.config import settings
from app.core.channel_resilience import CircuitBreaker

logger = logging.getLogger(__name__)
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

# Optional dependency -- graceful degradation if not installed.
try:
    from telegram import InlineKeyboardMarkup, Update
    from telegram.ext import (
        ApplicationBuilder,
        ContextTypes,
        MessageHandler,
        filters,
    )

    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False
    logger.warning(
        "python-telegram-bot is not installed. "
        "Install with: pip install 'python-telegram-bot>=22.0'"
    )


class TelegramAdapter(ChannelAdapter):
    """Telegram channel adapter using python-telegram-bot v22+ async API."""

    def __init__(self, instance_id: str = "", config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        self._bot_token: str = self.config.get("bot_token", "") or os.getenv(
            "TELEGRAM_BOT_TOKEN", ""
        )
        self._app = None  # telegram.ext.Application instance
        self._breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def platform(self) -> str:
        return "telegram"

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token) and _TELEGRAM_AVAILABLE

    @staticmethod
    def _clean_path_component(value: str | None, default: str = "file") -> str:
        """Return a filesystem-safe single path component."""
        cleaned = _SAFE_NAME_RE.sub("_", value or "").strip("._-")
        return cleaned[:120] if cleaned else default

    @staticmethod
    def _safe_suffix(suffix: str | None, default: str = ".bin") -> str:
        suffix = (suffix or default).lower()
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        if re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
            return suffix
        return default

    def _channel_storage_dir(self, kind: str) -> Path:
        segment = self._clean_path_component(self.instance_id or "default", "default")
        storage_dir = Path(settings.data_dir) / kind / segment
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    def _safe_download_filename(
        self,
        filename: str | None,
        unique_id: str | None,
        default_ext: str = ".bin",
    ) -> str:
        default_ext = self._safe_suffix(default_ext)
        original = Path(filename or "").name
        if not original or original in {".", ".."}:
            original = f"{unique_id or 'telegram'}{default_ext}"

        original_path = Path(original)
        suffix = self._safe_suffix(original_path.suffix, default_ext)
        stem = self._clean_path_component(original_path.stem, "telegram")
        safe_unique = self._clean_path_component(unique_id, "telegram")
        basename = stem if stem.startswith(safe_unique) else f"{safe_unique}_{stem}"
        max_basename_len = max(1, 180 - len(suffix))
        return f"{basename[:max_basename_len]}{suffix}"

    @staticmethod
    def _declared_size(item: object) -> int | None:
        size = getattr(item, "file_size", None)
        return int(size) if isinstance(size, int) and size >= 0 else None

    def _ensure_download_size(self, size: int | None, label: str) -> None:
        if size is not None and size > settings.channel_attachment_max_bytes:
            raise ValueError(
                f"{label} exceeds Telegram download limit "
                f"({size} > {settings.channel_attachment_max_bytes} bytes)"
            )

    async def _download_telegram_file(
        self,
        tg_file: object,
        *,
        declared_size: int | None,
        label: str,
    ) -> bytes:
        self._ensure_download_size(declared_size, label)
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        data = buf.getvalue()
        self._ensure_download_size(len(data), label)
        return data

    async def start(self) -> None:
        """Start polling for Telegram updates."""
        if not _TELEGRAM_AVAILABLE:
            raise RuntimeError(
                "python-telegram-bot is not installed. "
                "Install with: pip install 'python-telegram-bot>=22.0'"
            )
        if not self._bot_token:
            raise RuntimeError(
                "TelegramAdapter is not enabled (missing bot_token / TELEGRAM_BOT_TOKEN)"
            )

        self._app = ApplicationBuilder().token(self._bot_token).build()

        # Register handlers for different message types
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self._app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        self._app.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))
        self._app.add_handler(MessageHandler(filters.Document.ALL, self._handle_document))

        # Manual startup sequence (run_polling blocks, so we do it step-by-step)
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()

        self._running = True
        logger.info("Telegram adapter started (instance=%s).", self.name)

    async def stop(self) -> None:
        """Stop the Telegram polling loop."""
        if self._app is not None:
            try:
                await self._app.updater.stop()
                await self._app.stop()
                await self._app.shutdown()
            except Exception:
                logger.exception("Error stopping Telegram adapter %s", self.name)
            self._app = None
        self._running = False
        logger.info("Telegram adapter stopped (instance=%s).", self.name)

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message to a Telegram chat (with retry + circuit breaker)."""
        if self._app is None or not self._running:
            logger.warning("TelegramAdapter.send() called while not running.")
            return

        from app.core.channel_resilience import retry_with_backoff

        chat_id = int(message.channel_id)
        metadata = message.metadata or {}

        # Handle attachments one at a time so a text-send failure does not resend files.
        if message.attachments:
            for file_path in message.attachments:

                async def _send_document(path: str = file_path) -> None:
                    with open(path, "rb") as document:
                        await self._app.bot.send_document(chat_id=chat_id, document=document)

                await self._breaker.call(
                    lambda: retry_with_backoff(_send_document, max_retries=3, base_delay=1.0)
                )

        # Build optional reply markup
        reply_markup = None
        if "reply_markup" in metadata:
            try:
                reply_markup = InlineKeyboardMarkup(metadata["reply_markup"])
            except Exception:
                logger.warning("Invalid reply_markup in metadata, ignoring.")

        # Send text message
        if message.text:

            async def _send_text() -> None:
                try:
                    await self._app.bot.send_message(
                        chat_id=chat_id,
                        text=message.text,
                        parse_mode="Markdown",
                        reply_markup=reply_markup,
                    )
                except Exception:
                    # Retry without Markdown if parsing fails
                    await self._app.bot.send_message(
                        chat_id=chat_id,
                        text=message.text,
                        reply_markup=reply_markup,
                    )

            await self._breaker.call(
                lambda: retry_with_backoff(_send_text, max_retries=3, base_delay=1.0)
            )

    async def health_check(self) -> dict:
        """Check Telegram bot connection health."""
        if self._app is None:
            return {"status": "stopped", "platform": self.platform}
        try:
            me = await self._app.bot.get_me()
            return {
                "status": "healthy",
                "platform": self.platform,
                "bot_username": me.username,
                "bot_id": me.id,
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "platform": self.platform,
                "error": str(exc),
            }

    # -- Internal handlers ----------------------------------------------------

    def _build_incoming(
        self,
        update: Update,
        text: str = "",
        content_type: str = "text",
        attachments: list[str] | None = None,
    ) -> IncomingMessage:
        """Normalise a Telegram Update into an IncomingMessage."""
        return IncomingMessage(
            channel="telegram",
            channel_id=str(update.effective_chat.id),
            sender_id=str(update.effective_user.id),
            sender_name=update.effective_user.first_name or "",
            text=text,
            instance_id=self.instance_id,
            attachments=attachments or [],
            metadata={"content_type": content_type},
        )

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle plain text messages."""
        msg = self._build_incoming(update, text=update.message.text or "")
        await self._dispatch(msg)

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle voice messages -- download, transcribe, and dispatch."""
        try:
            voice = update.message.voice
            tg_file = await voice.get_file()

            audio_dir = self._channel_storage_dir("channel_audio")
            audio_path = audio_dir / self._safe_download_filename(
                None,
                getattr(tg_file, "file_unique_id", None),
                ".ogg",
            )
            audio_path.write_bytes(
                await self._download_telegram_file(
                    tg_file,
                    declared_size=self._declared_size(voice),
                    label="Telegram voice message",
                )
            )

            # Auto-transcribe voice message
            transcription_text = "[Voice message — transcription unavailable]"
            transcription_tags = []
            try:
                from app.core.transcription import convert_audio_to_wav, transcribe_audio

                wav_path = convert_audio_to_wav(str(audio_path))
                result = transcribe_audio(wav_path)
                transcription_text = result.text
                transcription_tags = result.tags
                if result.needs_review:
                    transcription_text += "\n\n[⚠️ Transcription may need review]"
            except Exception:
                logger.exception("Voice transcription failed on %s", self.name)

            msg = self._build_incoming(
                update,
                text=transcription_text,
                content_type="audio",
                attachments=[str(audio_path)],
            )
            # Add transcription metadata for interview pipeline
            msg.metadata["transcription"] = transcription_text
            msg.metadata["transcription_tags"] = transcription_tags
            msg.metadata["original_text"] = "[voice message]"

            await self._dispatch(msg)
        except Exception:
            logger.exception("Error handling voice message on %s", self.name)

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo messages."""
        try:
            # Get the largest photo size
            photo = update.message.photo[-1]
            tg_file = await photo.get_file()

            img_dir = self._channel_storage_dir("channel_images")
            img_path = img_dir / self._safe_download_filename(
                None,
                getattr(tg_file, "file_unique_id", None),
                ".jpg",
            )
            img_path.write_bytes(
                await self._download_telegram_file(
                    tg_file,
                    declared_size=self._declared_size(photo),
                    label="Telegram photo",
                )
            )

            caption = update.message.caption or ""
            msg = self._build_incoming(
                update,
                text=caption or "[photo]",
                content_type="image",
                attachments=[str(img_path)],
            )
            await self._dispatch(msg)
        except Exception:
            logger.exception("Error handling photo message on %s", self.name)

    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle document/file messages."""
        try:
            doc = update.message.document
            tg_file = await doc.get_file()

            doc_dir = self._channel_storage_dir("channel_files")
            filename = self._safe_download_filename(
                doc.file_name,
                getattr(tg_file, "file_unique_id", None),
                ".bin",
            )
            doc_path = doc_dir / filename

            doc_path.write_bytes(
                await self._download_telegram_file(
                    tg_file,
                    declared_size=self._declared_size(doc),
                    label="Telegram document",
                )
            )

            caption = update.message.caption or ""
            msg = self._build_incoming(
                update,
                text=caption or f"[file: {filename}]",
                content_type="file",
                attachments=[str(doc_path)],
            )
            await self._dispatch(msg)
        except Exception:
            logger.exception("Error handling document message on %s", self.name)
