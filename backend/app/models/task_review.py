"""Task review event model.

Human review events are the reward ledger for autonomous task work. They
separate Kanban execution state from the user's judgment of whether an
agent attempt was actually useful.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class TaskReviewEvent(Base):
    """Immutable-ish review event for a task attempt or rework decision."""

    __tablename__ = "task_review_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(100), default="")
    skill_name: Mapped[str] = mapped_column(String(100), default="")
    model_name: Mapped[str] = mapped_column(String(200), default="")
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)

    previous_status: Mapped[str] = mapped_column(String(30), default="")
    next_status: Mapped[str] = mapped_column(String(30), default="")
    previous_review_state: Mapped[str] = mapped_column(String(30), default="")
    next_review_state: Mapped[str] = mapped_column(String(30), default="")
    outcome: Mapped[str] = mapped_column(String(50), index=True)

    what_to_review: Mapped[str] = mapped_column(Text, default="")
    feedback_summary: Mapped[str] = mapped_column(Text, default="")
    context_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    atomic_snapshot: Mapped[str] = mapped_column(Text, default="{}")

    validation_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consensus_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    failure_subcategory: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    human_feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    failure_streak_after: Mapped[int] = mapped_column(Integer, default=0)
    review_cycle_after: Mapped[int] = mapped_column(Integer, default=0)
    trace_id: Mapped[str] = mapped_column(String(36), default="")
    created_by: Mapped[str] = mapped_column(String(36), default="local")
    diagnosis_status: Mapped[str] = mapped_column(String(20), default="pending")
    diagnosis_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def get_context_snapshot(self) -> dict:
        try:
            return json.loads(self.context_snapshot or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_atomic_snapshot(self) -> dict:
        try:
            return json.loads(self.atomic_snapshot or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_diagnosis(self) -> dict:
        try:
            return json.loads(self.diagnosis_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "skill_name": self.skill_name,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "previous_status": self.previous_status,
            "next_status": self.next_status,
            "previous_review_state": self.previous_review_state,
            "next_review_state": self.next_review_state,
            "outcome": self.outcome,
            "what_to_review": self.what_to_review,
            "feedback_summary": self.feedback_summary,
            "context_snapshot": self.get_context_snapshot(),
            "atomic_snapshot": self.get_atomic_snapshot(),
            "validation_method": self.validation_method,
            "consensus_score": self.consensus_score,
            "quality_score": self.quality_score,
            "failure_category": self.failure_category,
            "failure_subcategory": self.failure_subcategory,
            "severity": self.severity,
            "human_feedback_score": self.human_feedback_score,
            "failure_streak_after": self.failure_streak_after,
            "review_cycle_after": self.review_cycle_after,
            "trace_id": self.trace_id,
            "created_by": self.created_by,
            "diagnosis_status": self.diagnosis_status,
            "diagnosis": self.get_diagnosis(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
