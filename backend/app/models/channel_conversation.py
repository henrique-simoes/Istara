"""Channel conversation model — tracks multi-turn conversations with participants."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ChannelConversation(Base):
    """A tracked conversation with a participant on a messaging channel.

    Links to a research deployment when the conversation is part of
    an interview, survey, or diary study.
    """

    __tablename__ = "channel_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    channel_instance_id: Mapped[str] = mapped_column(
        ForeignKey("channel_instances.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    participant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    participant_name: Mapped[str] = mapped_column(String(200), default="")
    deployment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="active")  # active|completed|paused|expired
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel_instance_id": self.channel_instance_id,
            "project_id": self.project_id,
            "participant_id": self.participant_id,
            "participant_name": self.participant_name,
            "deployment_id": self.deployment_id,
            "state": self.state,
            "current_question_index": self.current_question_index,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
