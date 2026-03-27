"""Channel message model — stores message history for all channel instances."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ChannelMessage(Base):
    """A single message sent or received on a messaging channel."""

    __tablename__ = "channel_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    channel_instance_id: Mapped[str] = mapped_column(
        ForeignKey("channel_instances.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound|outbound
    sender_id: Mapped[str] = mapped_column(String(200), default="")
    sender_name: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    content_type: Mapped[str] = mapped_column(String(20), default="text")  # text|audio|image|file
    thread_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel_instance_id": self.channel_instance_id,
            "project_id": self.project_id,
            "direction": self.direction,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "content_type": self.content_type,
            "thread_id": self.thread_id,
            "external_message_id": self.external_message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
