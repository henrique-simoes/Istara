"""Design screen, brief, and decision models for the Interfaces menu."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class DesignScreen(Base):
    """A generated or imported UI screen within a project.

    Screens can originate from Stitch AI generation, Figma imports,
    or manual uploads. They track the full lineage from research
    findings through to visual output.
    """

    __tablename__ = "design_screens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    device_type: Mapped[str] = mapped_column(String(20), default="DESKTOP")
    model_used: Mapped[str] = mapped_column(String(50), default="")
    html_content: Mapped[str] = mapped_column(Text, default="")
    screenshot_path: Mapped[str] = mapped_column(String(500), default="")

    # Stitch integration
    stitch_project_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stitch_screen_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Variant / iteration tracking
    parent_screen_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("design_screens.id"), nullable=True
    )
    variant_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Figma integration
    figma_file_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    figma_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="ready")
    # JSON-encoded list of finding IDs that informed this screen
    source_findings: Mapped[str] = mapped_column(Text, default="[]")
    # Arbitrary metadata as JSON
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project = relationship("Project", back_populates="design_screens")
    parent_screen = relationship("DesignScreen", remote_side="DesignScreen.id")

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "prompt": self.prompt,
            "device_type": self.device_type,
            "model_used": self.model_used,
            "html_content": self.html_content,
            "screenshot_path": self.screenshot_path,
            "stitch_project_id": self.stitch_project_id,
            "stitch_screen_id": self.stitch_screen_id,
            "parent_screen_id": self.parent_screen_id,
            "variant_type": self.variant_type,
            "figma_file_key": self.figma_file_key,
            "figma_node_id": self.figma_node_id,
            "status": self.status,
            "source_findings": self._parse_json_list(self.source_findings),
            "metadata_json": self._parse_json_dict(self.metadata_json),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def _parse_json_list(raw: str) -> list:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_json_dict(raw: str) -> dict:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}


class DesignBrief(Base):
    """A design brief synthesized from research insights and recommendations.

    Briefs capture the research-to-design handoff, linking back to the
    specific insights and recommendations that informed them.
    """

    __tablename__ = "design_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON-encoded lists of source IDs
    source_insight_ids: Mapped[str] = mapped_column(Text, default="[]")
    source_recommendation_ids: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project = relationship("Project", back_populates="design_briefs")

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "content": self.content,
            "source_insight_ids": self._parse_json_list(self.source_insight_ids),
            "source_recommendation_ids": self._parse_json_list(self.source_recommendation_ids),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def _parse_json_list(raw: str) -> list:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []


class DesignDecision(Base):
    """An atomic research decision linking recommendations to design screens.

    Extends the Atomic Research chain (Nugget -> Fact -> Insight ->
    Recommendation) with a final Decision node that records which
    recommendations were acted upon and which screens resulted.
    """

    __tablename__ = "design_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON-encoded lists
    recommendation_ids: Mapped[str] = mapped_column(Text, default="[]")
    screen_ids: Mapped[str] = mapped_column(Text, default="[]")
    rationale: Mapped[str] = mapped_column(Text, default="")
    phase: Mapped[str] = mapped_column(String(20), default="develop")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="design_decisions")

    def to_dict(self) -> dict:
        """Serialize to API-ready dict."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "text": self.text,
            "recommendation_ids": self._parse_json_list(self.recommendation_ids),
            "screen_ids": self._parse_json_list(self.screen_ids),
            "rationale": self.rationale,
            "phase": self.phase,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def _parse_json_list(raw: str) -> list:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
