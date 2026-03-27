"""Research deployment model — tracks interviews, surveys, diary studies deployed via messaging."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ResearchDeployment(Base):
    """A research study deployment across one or more messaging channels.

    Deployments orchestrate the collection of research data by sending
    questions to participants on Telegram, Slack, WhatsApp, or Google Chat
    and tracking their responses with adaptive follow-up.
    """

    __tablename__ = "research_deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    deployment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # interview|survey|diary_study
    skill_name: Mapped[str] = mapped_column(String(100), default="")
    questions_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of question objects
    config_json: Mapped[str] = mapped_column(Text, default="{}")  # adaptive rules, branching, rate limits
    channel_instance_ids_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of channel IDs
    state: Mapped[str] = mapped_column(String(20), default="draft")  # draft|active|paused|completed
    target_responses: Mapped[int] = mapped_column(Integer, default=0)
    current_responses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "deployment_type": self.deployment_type,
            "skill_name": self.skill_name,
            "questions": json.loads(self.questions_json) if self.questions_json else [],
            "config": json.loads(self.config_json) if self.config_json else {},
            "channel_instance_ids": json.loads(self.channel_instance_ids_json) if self.channel_instance_ids_json else [],
            "state": self.state,
            "target_responses": self.target_responses,
            "current_responses": self.current_responses,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
