"""Atomic Research finding models — Nuggets, Facts, Insights, Recommendations."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Nugget(Base):
    """Raw evidence extracted from a source — the atomic unit of research.

    A nugget is a direct quote, observation, or data point from a research source.
    Example: "P1 said 'I hate giving my phone number to random sites'" @ interview_p1.mp3 4:32
    """

    __tablename__ = "nuggets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    source_location: Mapped[str] = mapped_column(String(255), default="")
    tags: Mapped[str] = mapped_column(Text, default="")  # JSON array of tag strings
    phase: Mapped[str] = mapped_column(String(20), default="discover")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="nuggets")


class Fact(Base):
    """A verified claim derived from one or more nuggets.

    A fact is a statement that has been validated against evidence.
    Example: "4/5 users hesitated at the SMS verification step"
    """

    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    nugget_ids: Mapped[str] = mapped_column(Text, default="")  # JSON array of nugget IDs
    phase: Mapped[str] = mapped_column(String(20), default="discover")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="facts")


class Insight(Base):
    """A pattern or conclusion synthesized from multiple facts.

    An insight is a higher-level understanding derived from the evidence.
    Example: "Users don't trust the verification process"
    """

    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    fact_ids: Mapped[str] = mapped_column(Text, default="")  # JSON array of fact IDs
    phase: Mapped[str] = mapped_column(String(20), default="define")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    impact: Mapped[str] = mapped_column(String(20), default="medium")  # low/medium/high/critical
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="insights")


class Recommendation(Base):
    """An actionable recommendation based on insights.

    A recommendation is a specific action suggested based on research findings.
    Example: "Replace SMS verification with email magic link"
    """

    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    insight_ids: Mapped[str] = mapped_column(Text, default="")  # JSON array of insight IDs
    phase: Mapped[str] = mapped_column(String(20), default="deliver")
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low/medium/high/critical
    effort: Mapped[str] = mapped_column(String(20), default="medium")  # low/medium/high
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed/accepted/rejected/implemented
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="recommendations")
