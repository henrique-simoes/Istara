"""Notification and notification preference models."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class NotificationSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class Notification(Base):
    """A persisted notification created from a WebSocket broadcast event."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    type: Mapped[str] = mapped_column(String(50))  # WS event type
    title: Mapped[str] = mapped_column(String(500), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="system")
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    action_type: Mapped[str] = mapped_column(String(50), default="")
    action_target: Mapped[str] = mapped_column(String(500), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "severity": self.severity,
            "read": self.read,
            "action_type": self.action_type,
            "action_target": self.action_target,
            "metadata_json": self._parse_json_dict(self.metadata_json),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def _parse_json_dict(raw: str) -> dict:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}


class NotificationPreference(Base):
    """User preferences for notification delivery per category."""

    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[str] = mapped_column(String(50))
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    show_toast: Mapped[bool] = mapped_column(Boolean, default=True)
    show_center: Mapped[bool] = mapped_column(Boolean, default=True)
    email_forward: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "category": self.category,
            "agent_id": self.agent_id,
            "show_toast": self.show_toast,
            "show_center": self.show_center,
            "email_forward": self.email_forward,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
