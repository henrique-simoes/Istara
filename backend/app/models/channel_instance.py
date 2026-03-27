"""Channel instance model — supports multiple instances per platform."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ChannelInstance(Base):
    """A configured messaging channel instance (e.g. one Telegram bot, one Slack workspace).

    Users can have multiple instances per platform — e.g. two different Telegram bots
    for different research projects.
    """

    __tablename__ = "channel_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # telegram|slack|whatsapp|google_chat
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}")  # encrypted credentials
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # optional project binding
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")  # healthy|unhealthy|unknown
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform,
            "name": self.name,
            "project_id": self.project_id,
            "is_active": self.is_active,
            "health_status": self.health_status,
            "last_health_at": self.last_health_at.isoformat() if self.last_health_at else None,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
