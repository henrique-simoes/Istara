"""Credential-free local channel adapter for Pi replacement benchmarking."""

from __future__ import annotations

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage


class PiLocalAdapter(ChannelAdapter):
    """Local-only adapter that exercises the real channel router contract."""

    @property
    def platform(self) -> str:
        return "pi_local"

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", True))

    async def start(self) -> None:
        self._running = True
        self.sent_messages: list[OutgoingMessage] = []

    async def stop(self) -> None:
        self._running = False

    async def send(self, message: OutgoingMessage) -> None:
        if not hasattr(self, "sent_messages"):
            self.sent_messages = []
        self.sent_messages.append(message)

    async def inject(
        self,
        *,
        sender_id: str,
        text: str,
        channel_id: str = "pi-local",
        sender_name: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Inject a benchmark message through the same callback as live adapters."""
        if not self.is_running:
            return
        await self._dispatch(
            IncomingMessage(
                channel=self.platform,
                channel_id=channel_id,
                sender_id=sender_id,
                sender_name=sender_name or sender_id,
                text=text,
                instance_id=self.instance_id,
                metadata={"pi_candidate": True, **(metadata or {})},
            )
        )
