"""Agent loop configuration model for per-agent loop settings."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class AgentLoopConfig(Base):
    """Per-agent loop configuration — interval, pause state, skill filters."""

    __tablename__ = "agent_loop_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(String(36), unique=True)
    loop_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    skills_to_run: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    project_filter: Mapped[str] = mapped_column(String(36), default="")
    last_cycle_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cycle_count: Mapped[int] = mapped_column(Integer, default=0)
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
            "agent_id": self.agent_id,
            "loop_interval_seconds": self.loop_interval_seconds,
            "paused": self.paused,
            "skills_to_run": self._parse_json_list(self.skills_to_run),
            "project_filter": self.project_filter,
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
            "cycle_count": self.cycle_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def _parse_json_list(raw: str) -> list:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
