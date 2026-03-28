"""Project reports — convergent, progressively refined deliverables.

Four-layer Convergence Pyramid (based on Minto Pyramid Principle + Weick Sensemaking):
  L1: Raw artifacts (codebooks, intermediate outputs — not user-facing)
  L2: Analysis reports (1 per study method — snapshots)
  L3: Synthesis (cross-method, triangulation — living)
  L4: Final deliverable (MECE-structured — versioned snapshot)

Reports are NOT created per skill execution. They are created per study scope
and progressively refined as analyses complete.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ProjectReport(Base):
    __tablename__ = "project_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    layer: Mapped[int] = mapped_column(Integer, default=2)
    report_type: Mapped[str] = mapped_column(String(30), default="study_analysis")
    scope: Mapped[str] = mapped_column(String(200), default="")

    content_json: Mapped[str] = mapped_column(Text, default="{}")
    executive_summary: Mapped[str] = mapped_column(Text, default="")

    finding_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_document_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    codebook_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)

    mece_categories_json: Mapped[str] = mapped_column(Text, default="[]")
    triangulation_matrix_json: Mapped[str] = mapped_column(Text, default="{}")

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
            "id": self.id, "project_id": self.project_id,
            "title": self.title, "layer": self.layer,
            "report_type": self.report_type, "scope": self.scope,
            "executive_summary": self.executive_summary,
            "status": self.status, "version": self.version,
            "finding_count": len(json.loads(self.finding_ids_json)) if self.finding_ids_json else 0,
            "mece_categories": json.loads(self.mece_categories_json) if self.mece_categories_json else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
