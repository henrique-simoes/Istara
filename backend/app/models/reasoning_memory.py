"""Reasoning memory items for cross-agent self-evolution."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ReasoningMemoryItem(Base):
    """A distilled reasoning trace that can be reused by agents and loops."""

    __tablename__ = "reasoning_memory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    agent_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    source_kind: Mapped[str] = mapped_column(String(50), default="manual", index=True)
    source_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    outcome: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    domain: Mapped[str] = mapped_column(String(100), default="", index=True)
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    judge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def get_tags(self) -> list[str]:
        try:
            parsed = json.loads(self.tags_json or "[]")
            return [str(tag) for tag in parsed] if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags: list[str]) -> None:
        self.tags_json = json.dumps([str(tag) for tag in tags])

    def get_evidence_refs(self) -> list[dict | str]:
        try:
            parsed = json.loads(self.evidence_refs_json or "[]")
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_evidence_refs(self, refs: list[dict | str]) -> None:
        self.evidence_refs_json = json.dumps(refs)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "outcome": self.outcome,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "tags": self.get_tags(),
            "domain": self.domain,
            "evidence_refs": self.get_evidence_refs(),
            "judge_score": self.judge_score,
            "confidence": self.confidence,
            "status": self.status,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
