"""WhatsApp Business Cloud API channel adapter for Istara.

Webhook-based adapter using the Meta Graph API for sending messages and
receiving inbound messages via webhook callbacks.

Required config keys (or environment fallbacks):
    phone_number_id / WHATSAPP_PHONE_NUMBER_ID  -- Business phone number ID
    access_token / WHATSAPP_ACCESS_TOKEN        -- Permanent or system-user token
    verify_token / WHATSAPP_VERIFY_TOKEN        -- Webhook verification token
    app_secret / WHATSAPP_APP_SECRET            -- Meta app secret for POST HMAC
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import time
from pathlib import Path

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage
from app.config import settings
from app.core.channel_resilience import CircuitBreaker

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
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _audio_suffix_for_mime(mime_type: str | None) -> str:
    """Return a transcribable extension for a WhatsApp media MIME type."""
    mime = (mime_type or "").split(";", 1)[0].strip().lower()
    return {
        "audio/ogg": ".ogg",
        "audio/opus": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
        "audio/amr": ".amr",
    }.get(mime, ".ogg")


class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp Business Cloud API adapter using httpx."""

    def __init__(self, instance_id: str = "", config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        self._phone_number_id: str = self.config.get("phone_number_id", "") or os.getenv(
            "WHATSAPP_PHONE_NUMBER_ID", ""
        )
        self._access_token: str = self.config.get("access_token", "") or os.getenv(
            "WHATSAPP_ACCESS_TOKEN", ""
        )
        self._verify_token: str = self.config.get("verify_token", "") or os.getenv(
            "WHATSAPP_VERIFY_TOKEN", ""
        )
        self._app_secret: str = self.config.get("app_secret", "") or os.getenv(
            "WHATSAPP_APP_SECRET", ""
        )
        self._http: httpx.AsyncClient | None = None
        # Track last inbound timestamp per chat_id for 24-hour window
        self._last_inbound_at: dict[str, float] = {}
        # Circuit breaker for outbound Graph API calls
        self._breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        # Webhook idempotency — deduplicate by external message id
        self._seen_message_ids: set[str] = set()

    # -- ChannelAdapter interface ---------------------------------------------

    @property
    def platform(self) -> str:
        return "whatsapp"

    @property
    def enabled(self) -> bool:
        return bool(self._phone_number_id and self._access_token) and _HTTPX_AVAILABLE

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
            original = f"{unique_id or 'whatsapp'}{default_ext}"

        original_path = Path(original)
        suffix = self._safe_suffix(original_path.suffix, default_ext)
        stem = self._clean_path_component(original_path.stem, "whatsapp")
        safe_unique = self._clean_path_component(unique_id, "whatsapp")
        basename = stem if stem.startswith(safe_unique) else f"{safe_unique}_{stem}"
        max_basename_len = max(1, 180 - len(suffix))
        return f"{basename[:max_basename_len]}{suffix}"

    @staticmethod
    def _declared_size(item: dict | None) -> int | None:
        size = (item or {}).get("file_size")
        try:
            parsed = int(size)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    def _ensure_download_size(self, size: int | None, label: str) -> None:
        if size is not None and size > settings.channel_attachment_max_bytes:
            raise ValueError(
                f"{label} exceeds WhatsApp download limit "
                f"({size} > {settings.channel_attachment_max_bytes} bytes)"
            )

    async def _download_media(
        self,
        media_id: str,
        *,
        declared_size: int | None = None,
        mime_type: str | None = None,
        label: str = "WhatsApp media",
    ) -> tuple[Path, dict]:
        """Download WhatsApp media through the Graph API into local channel storage."""
        if self._http is None:
            raise RuntimeError("WhatsApp adapter is not running")

        self._ensure_download_size(declared_size, label)
        metadata_resp = await self._http.get(f"{GRAPH_API_BASE}/{media_id}")
        metadata_resp.raise_for_status()
        media_metadata = metadata_resp.json()

        media_size = self._declared_size(media_metadata) or declared_size
        self._ensure_download_size(media_size, label)

        media_url = media_metadata.get("url")
        if not media_url:
            raise RuntimeError("WhatsApp media metadata did not include a download URL")

        data_resp = await self._http.get(media_url)
        data_resp.raise_for_status()
        data = data_resp.content
        self._ensure_download_size(len(data), label)

        resolved_mime = media_metadata.get("mime_type") or mime_type
        suffix = _audio_suffix_for_mime(resolved_mime)
        storage_dir = self._channel_storage_dir("channel_audio")
        filename = self._safe_download_filename(
            f"{media_id}{suffix}",
            media_id,
            suffix,
        )
        media_path = storage_dir / filename
        media_path.write_bytes(data)
        return media_path, media_metadata

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
        """Send a message via WhatsApp Cloud API (with retry + circuit breaker)."""
        if self._http is None or not self._running:
            logger.warning("WhatsAppAdapter.send() called while not running.")
            return

        from app.core.channel_resilience import retry_with_backoff

        async def _do_send() -> None:
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

            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()

        await self._breaker.call(
            lambda: retry_with_backoff(_do_send, max_retries=3, base_delay=1.0)
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

    def verify_signature(self, raw_body: bytes, signature_header: str | None) -> bool:
        """Verify Meta's X-Hub-Signature-256 HMAC for POST callbacks."""
        if not self._app_secret or not signature_header:
            return False
        if not signature_header.startswith("sha256="):
            return False

        expected = (
            "sha256="
            + hmac.new(
                self._app_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
        )
        return hmac.compare_digest(signature_header, expected)

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

    async def _process_webhook_message(self, wa_msg: dict, contact_map: dict[str, str]) -> None:
        """Process a single WhatsApp message from webhook payload.

        Idempotent: duplicate deliveries (same external_message_id) are ignored.
        """
        msg_id = wa_msg.get("id", "")
        if msg_id:
            if msg_id in self._seen_message_ids:
                logger.debug("Deduplicating WhatsApp message %s", msg_id)
                return
            self._seen_message_ids.add(msg_id)
            # Prevent unbounded growth — cap cache size
            if len(self._seen_message_ids) > 10_000:
                self._seen_message_ids = set(list(self._seen_message_ids)[-5_000:])

        msg_type = wa_msg.get("type", "text")
        sender = wa_msg.get("from", "")
        sender_name = contact_map.get(sender, "")

        # Track inbound timestamp for conversation window
        self._last_inbound_at[sender] = time.time()

        text = ""
        content_type = "text"
        attachments: list[str] = []

        if msg_type == "text":
            text = wa_msg.get("text", {}).get("body", "")
        elif msg_type == "audio":
            # Download and transcribe audio messages before they enter routing.
            text = "[Audio message - transcription unavailable]"
            content_type = "audio"
            audio = wa_msg.get("audio", {})
            media_id = audio.get("id", "")
            transcription_metadata: dict = {}
            if media_id:
                try:
                    audio_path, media_metadata = await self._download_media(
                        media_id,
                        declared_size=self._declared_size(audio),
                        mime_type=audio.get("mime_type"),
                        label="WhatsApp audio message",
                    )
                    attachments.append(str(audio_path))

                    from app.core.transcription import convert_audio_to_wav, transcribe_audio

                    wav_path = convert_audio_to_wav(str(audio_path))
                    result = transcribe_audio(wav_path)
                    text = result.text
                    if result.needs_review and "transcription-error" not in result.tags:
                        text += "\n\n[Transcription may need review]"
                    transcription_metadata = {
                        "status": "error" if "transcription-error" in result.tags else "complete",
                        "text": result.text,
                        "language": result.language,
                        "confidence": result.confidence,
                        "icr_kappa": result.icr_kappa,
                        "icr_confidence": result.icr_confidence,
                        "needs_review": result.needs_review,
                        "tags": result.tags,
                        "media_id": media_id,
                        "media_mime_type": media_metadata.get("mime_type")
                        or audio.get("mime_type"),
                        "engine_metadata": result.metadata,
                    }
                except Exception as exc:
                    logger.exception(
                        "WhatsApp audio download/transcription failed on %s", self.name
                    )
                    attachments.append(f"whatsapp:media:{media_id}")
                    transcription_metadata = {
                        "status": "error",
                        "media_id": media_id,
                        "error": str(exc)[:500],
                    }
            else:
                transcription_metadata = {"status": "error", "error": "missing_media_id"}
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
                **({"transcription": transcription_metadata} if msg_type == "audio" else {}),
                **(
                    {"transcription_tags": transcription_metadata.get("tags", [])}
                    if msg_type == "audio"
                    else {}
                ),
                **({"original_text": "[audio message]"} if msg_type == "audio" else {}),
            },
        )
        await self._dispatch(msg)
