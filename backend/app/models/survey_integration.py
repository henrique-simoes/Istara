"""Survey integration models — connects SurveyMonkey, Google Forms, Typeform."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class SurveyIntegration(Base):
    """A configured connection to an external survey platform."""

    __tablename__ = "survey_integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # surveymonkey|google_forms|typeform
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}")  # API keys, OAuth tokens
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform,
            "name": self.name,
            "project_id": self.project_id,
            "is_active": self.is_active,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SurveyLink(Base):
    """A link between an external survey and a Istara project for response ingestion."""

    __tablename__ = "survey_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    integration_id: Mapped[str] = mapped_column(
        ForeignKey("survey_integrations.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    external_survey_id: Mapped[str] = mapped_column(String(200), nullable=False)
    external_survey_name: Mapped[str] = mapped_column(String(300), default="")
    webhook_secret: Mapped[str] = mapped_column(String(200), default="")
    response_count: Mapped[int] = mapped_column(Integer, default=0)
    last_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "integration_id": self.integration_id,
            "project_id": self.project_id,
            "external_survey_id": self.external_survey_id,
            "external_survey_name": self.external_survey_name,
            "response_count": self.response_count,
            "last_response_at": self.last_response_at.isoformat() if self.last_response_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
