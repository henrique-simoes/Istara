"""Backup record model for tracking backup operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class BackupRecord(Base):
    """A record of a backup operation (full or incremental)."""

    __tablename__ = "backup_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    backup_type: Mapped[str] = mapped_column(String(20), default="full")  # full | incremental
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # completed | failed | in_progress | verified
    error_message: Mapped[str] = mapped_column(Text, default="")
    components: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    checksum: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "filename": self.filename,
            "backup_type": self.backup_type,
            "parent_id": self.parent_id,
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "status": self.status,
            "error_message": self.error_message,
            "components": self._parse_json(self.components),
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
