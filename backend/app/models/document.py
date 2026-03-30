"""Document database model — source of truth for all project outputs."""

import enum
import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class DocumentStatus(str, enum.Enum):
    """Document lifecycle states."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class DocumentSource(str, enum.Enum):
    """How the document was created."""

    USER_UPLOAD = "user_upload"
    AGENT_OUTPUT = "agent_output"
    TASK_OUTPUT = "task_output"
    EXTERNAL = "external"
    PROJECT_FILE = "project_file"


class Document(Base):
    """A document produced by or provided to Istara.

    Every file the user puts in the project folder and every output
    an agent or task produces is tracked as a Document. Documents
    are the final outputs of everything in Istara and form the
    source of truth for agents and users.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(1000), default="")
    file_name: Mapped[str] = mapped_column(String(500), default="")
    file_type: Mapped[str] = mapped_column(String(20), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.READY
    )
    source: Mapped[DocumentSource] = mapped_column(
        Enum(DocumentSource), default=DocumentSource.USER_UPLOAD
    )
    # Linked task (nullable — not all docs come from tasks)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # JSON-encoded lists
    agent_ids: Mapped[str] = mapped_column(Text, default="[]")
    skill_names: Mapped[str] = mapped_column(Text, default="[]")
    tags: Mapped[str] = mapped_column(Text, default="[]")
    # Double Diamond phase
    phase: Mapped[str] = mapped_column(String(20), default="discover")
    # Atomic research path — JSON object describing lineage
    atomic_path: Mapped[str] = mapped_column(Text, default="{}")
    # Searchable content preview (first ~2000 chars)
    content_preview: Mapped[str] = mapped_column(Text, default="")
    # Full content for text-based documents (stored for search)
    content_text: Mapped[str] = mapped_column(Text, default="")
    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project = relationship("Project", back_populates="documents")

    # --- JSON helpers ---

    def get_agent_ids(self) -> list[str]:
        try:
            return json.loads(self.agent_ids)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_agent_ids(self, ids: list[str]) -> None:
        self.agent_ids = json.dumps(ids)

    def get_skill_names(self) -> list[str]:
        try:
            return json.loads(self.skill_names)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_skill_names(self, names: list[str]) -> None:
        self.skill_names = json.dumps(names)

    def get_tags(self) -> list[str]:
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags: list[str]) -> None:
        self.tags = json.dumps(tags)

    def get_atomic_path(self) -> dict:
        try:
            return json.loads(self.atomic_path)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_atomic_path(self, path: dict) -> None:
        self.atomic_path = json.dumps(path)

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status.value if self.status else "ready",
            "source": self.source.value if self.source else "user_upload",
            "task_id": self.task_id,
            "agent_ids": self.get_agent_ids(),
            "skill_names": self.get_skill_names(),
            "tags": self.get_tags(),
            "phase": self.phase,
            "atomic_path": self.get_atomic_path(),
            "content_preview": self.content_preview[:500] if self.content_preview else "",
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
