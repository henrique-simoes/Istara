"""Multi-channel adapter framework for Istara.

Provides abstract base classes for channel adapters (Slack, Telegram, WhatsApp, etc.)
and a router that manages adapter lifecycle and message routing.

Supports multiple instances per platform (e.g. two Telegram bots).
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    """Normalized message from any channel."""

    channel: str  # "slack", "telegram", "whatsapp", "google_chat", "web"
    channel_id: str  # channel/chat identifier
    sender_id: str  # user identifier
    sender_name: str
    text: str
    instance_id: str = ""  # UUID of the ChannelInstance
    attachments: list[str] = field(default_factory=list)  # file paths
    metadata: dict = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    """Normalized response to send back."""

    channel: str
    channel_id: str
    text: str
    instance_id: str = ""  # UUID of the ChannelInstance
    attachments: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# Type alias for the message handler callback.
MessageCallback = Callable[[IncomingMessage], Awaitable[OutgoingMessage | None]]


class ChannelAdapter(ABC):
    """Base class for all channel adapters.

    Each adapter instance represents one configured connection (e.g. one Telegram bot).
    Multiple instances of the same platform can coexist with different instance_ids.
    """

    def __init__(self, instance_id: str = "", config: dict | None = None) -> None:
        self.instance_id = instance_id
        self.config = config or {}
        self._callback: MessageCallback | None = None
        self._running: bool = False

    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform identifier (e.g. 'telegram', 'slack', 'whatsapp', 'google_chat')."""
        ...

    @property
    def name(self) -> str:
        """Display name combining platform and instance."""
        short_id = self.instance_id[:8] if self.instance_id else "default"
        return f"{self.platform}-{short_id}"

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the adapter has the required configuration to run."""
        ...

    @property
    def is_running(self) -> bool:
        return self._running

    @abstractmethod
    async def start(self) -> None:
        """Start listening for messages."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening."""

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> None:
        """Send a message to the channel."""

    async def health_check(self) -> dict:
        """Check connection health. Override for platform-specific checks."""
        return {"status": "healthy" if self._running else "stopped", "platform": self.platform}

    def on_message(self, callback: MessageCallback) -> None:
        """Register a callback for incoming messages."""
        self._callback = callback

    async def _dispatch(self, message: IncomingMessage) -> None:
        """Dispatch an incoming message to the registered callback."""
        # Tag the message with our instance_id
        message.instance_id = self.instance_id
        if self._callback is None:
            logger.warning(
                "Channel %s received a message but no callback is registered.", self.name
            )
            return
        try:
            response = await self._callback(message)
            if response is not None:
                response.instance_id = self.instance_id
                await self.send(response)
        except Exception:
            logger.exception("Error handling message on channel %s", self.name)


class ChannelRouter:
    """Manages multiple channel adapters and routes messages to the agent system.

    Adapters are keyed by instance_id (UUID) to support multiple instances per platform.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, ChannelAdapter] = {}  # keyed by instance_id
        self._handler: MessageCallback | None = None

    # -- Adapter management --------------------------------------------------

    def register(self, adapter: ChannelAdapter) -> None:
        """Register a channel adapter by its instance_id."""
        key = adapter.instance_id or adapter.platform
        if key in self._adapters:
            logger.warning("Adapter '%s' is already registered; replacing.", key)
        self._adapters[key] = adapter
        # Wire up the message callback so incoming messages flow through the router.
        adapter.on_message(self._handle_message)
        logger.info("Registered channel adapter: %s (enabled=%s)", adapter.name, adapter.enabled)

    def unregister(self, instance_id: str) -> None:
        """Remove a channel adapter by instance_id."""
        adapter = self._adapters.pop(instance_id, None)
        if adapter and adapter.is_running:
            logger.warning(
                "Unregistering running adapter '%s'; call stop first to be safe.", instance_id
            )

    def get(self, instance_id: str) -> ChannelAdapter | None:
        return self._adapters.get(instance_id)

    def get_by_instance_id(self, instance_id: str) -> ChannelAdapter | None:
        """Get adapter by instance_id."""
        return self._adapters.get(instance_id)

    def list_by_platform(self, platform: str) -> list[ChannelAdapter]:
        """Return all adapters for a given platform."""
        return [a for a in self._adapters.values() if a.platform == platform]

    def list_adapters(self) -> list[dict]:
        """Return status info for every registered adapter."""
        return [
            {
                "instance_id": a.instance_id,
                "platform": a.platform,
                "name": a.name,
                "enabled": a.enabled,
                "running": a.is_running,
            }
            for a in self._adapters.values()
        ]

    # -- Message handler ------------------------------------------------------

    def set_handler(self, handler: MessageCallback) -> None:
        """Set the function that processes incoming messages (typically the agent/chat system)."""
        self._handler = handler
        # Propagate to all adapters.
        for adapter in self._adapters.values():
            adapter.on_message(self._handle_message)

    async def _handle_message(self, message: IncomingMessage) -> OutgoingMessage | None:
        """Route an incoming message through the configured handler."""
        if self._handler is None:
            logger.warning("ChannelRouter has no handler set; dropping message from %s", message.channel)
            return None
        return await self._handler(message)

    # -- Lifecycle ------------------------------------------------------------

    async def start_adapter(self, instance_id: str) -> None:
        """Start a single adapter by instance_id."""
        adapter = self._adapters.get(instance_id)
        if adapter is None:
            raise KeyError(f"No adapter registered with instance_id '{instance_id}'")
        if not adapter.enabled:
            raise RuntimeError(f"Adapter '{adapter.name}' is not enabled (missing configuration)")
        if adapter.is_running:
            logger.info("Adapter '%s' is already running.", adapter.name)
            return
        await adapter.start()
        logger.info("Started channel adapter: %s", adapter.name)

    async def stop_adapter(self, instance_id: str) -> None:
        """Stop a single adapter by instance_id."""
        adapter = self._adapters.get(instance_id)
        if adapter is None:
            raise KeyError(f"No adapter registered with instance_id '{instance_id}'")
        if not adapter.is_running:
            logger.info("Adapter '%s' is not running.", adapter.name)
            return
        await adapter.stop()
        logger.info("Stopped channel adapter: %s", adapter.name)

    async def start_all(self) -> None:
        """Start all enabled adapters."""
        for adapter in self._adapters.values():
            if adapter.enabled and not adapter.is_running:
                try:
                    await adapter.start()
                    logger.info("Started channel adapter: %s", adapter.name)
                except Exception:
                    logger.exception("Failed to start adapter: %s", adapter.name)

    async def stop_all(self) -> None:
        """Stop all running adapters."""
        for adapter in self._adapters.values():
            if adapter.is_running:
                try:
                    await adapter.stop()
                    logger.info("Stopped channel adapter: %s", adapter.name)
                except Exception:
                    logger.exception("Failed to stop adapter: %s", adapter.name)


# ---------------------------------------------------------------------------
# Singleton router instance shared across the application.
# ---------------------------------------------------------------------------
channel_router = ChannelRouter()
