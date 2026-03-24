"""Task database model."""

import enum
import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class TaskStatus(str, enum.Enum):
    """Kanban task statuses."""

    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class Task(Base):
    """A research task on the Kanban board."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.BACKLOG)
    skill_name: Mapped[str] = mapped_column(String(100), default="")
    agent_notes: Mapped[str] = mapped_column(Text, default="")
    user_context: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    position: Mapped[int] = mapped_column(default=0)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    input_document_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of document IDs
    output_document_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of document IDs
    urls: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of URLs to fetch
    instructions: Mapped[str] = mapped_column(Text, default="")  # Specific instructions from user

    # Task locking (multi-user)
    locked_by: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    # Validation / consensus
    validation_method: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    validation_result: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # JSON
    consensus_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project = relationship("Project", back_populates="tasks")

    # --- JSON helpers ---

    def get_input_document_ids(self) -> list[str]:
        try:
            return json.loads(self.input_document_ids or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_input_document_ids(self, ids: list[str]):
        self.input_document_ids = json.dumps(ids)

    def get_output_document_ids(self) -> list[str]:
        try:
            return json.loads(self.output_document_ids or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_output_document_ids(self, ids: list[str]):
        self.output_document_ids = json.dumps(ids)

    def get_urls(self) -> list[str]:
        try:
            return json.loads(self.urls or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_urls(self, urls: list[str]):
        self.urls = json.dumps(urls)
