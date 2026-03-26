"""Loop execution records for scheduled tasks and agent loops."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class LoopExecution(Base):
    """Records a single execution of a scheduled task or agent loop cycle."""

    __tablename__ = "loop_executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_type: Mapped[str] = mapped_column(String(50))  # "scheduled_task" | "agent_loop"
    source_id: Mapped[str] = mapped_column(String(100))
    source_name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(
        String(20), default="success"
    )  # success | failure | running | skipped
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "findings_count": self.findings_count,
            "metadata_json": self._parse_json_dict(self.metadata_json),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def _parse_json_dict(raw: str) -> dict:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
