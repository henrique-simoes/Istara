"""Chat session model — groups messages into conversations."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class InferencePreset(str, enum.Enum):
    LIGHTWEIGHT = "lightweight"
    MEDIUM = "medium"
    HIGH = "high"
    CUSTOM = "custom"


class ChatSession(Base):
    """A chat session/conversation within a project."""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # assigned agent
    model_override: Mapped[str | None] = mapped_column(String(255), nullable=True)  # model name override
    inference_preset: Mapped[InferencePreset] = mapped_column(
        Enum(InferencePreset), default=InferencePreset.MEDIUM
    )
    custom_temperature: Mapped[float | None] = mapped_column(nullable=True)
    custom_max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_type: Mapped[str] = mapped_column(String(20), default="chat")
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project = relationship("Project", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "agent_id": self.agent_id,
            "model_override": self.model_override,
            "session_type": self.session_type,
            "inference_preset": self.inference_preset.value if self.inference_preset else "medium",
            "custom_temperature": self.custom_temperature,
            "custom_max_tokens": self.custom_max_tokens,
            "custom_context_window": self.custom_context_window,
            "starred": self.starred,
            "archived": self.archived,
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Hardware preset definitions (used by frontend and API)
INFERENCE_PRESETS = {
    "lightweight": {
        "label": "Lightweight",
        "description": "Fast responses, minimal reasoning. Best for quick questions and simple tasks.",
        "temperature": 0.3,
        "max_tokens": 1024,
        "context_window": 2048,
    },
    "medium": {
        "label": "Medium",
        "description": "Balanced reasoning and speed. Good for most research tasks.",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 8192,
    },
    "high": {
        "label": "High",
        "description": "Deep reasoning, larger context. Best for complex analysis and synthesis.",
        "temperature": 0.9,
        "max_tokens": 8192,
        "context_window": 16384,
    },
    "custom": {
        "label": "Custom",
        "description": "Define your own settings for temperature, token limits, and context window.",
        "temperature": None,
        "max_tokens": None,
        "context_window": None,
    },
}
