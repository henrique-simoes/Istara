"""Code application records — every code applied to source text.

Full audit trail: WHO coded WHAT, WHERE in source, WHY that code,
and whether it was human-reviewed. Based on O'Connor & Joffe (2020)
ICR guidelines and Lincoln & Guba (1985) audit trail requirements.
"""

from datetime import datetime, timezone
import json

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class CodeApplication(Base):
    __tablename__ = "code_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    codebook_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    code_id: Mapped[str] = mapped_column(String(100), nullable=False)

    evidence_unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    coding_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_text: Mapped[str] = mapped_column(Text, default="")
    source_location: Mapped[str] = mapped_column(String(200), default="")
    start_offset: Mapped[int | None] = mapped_column(nullable=True)
    end_offset: Mapped[int | None] = mapped_column(nullable=True)

    coder_id: Mapped[str] = mapped_column(String(100), default="")
    coder_type: Mapped[str] = mapped_column(String(20), default="llm")
    model_name: Mapped[str] = mapped_column(String(200), default="")
    donor_id: Mapped[str] = mapped_column(String(120), default="")
    route_id: Mapped[str] = mapped_column(String(120), default="")
    route_evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    reasoning: Mapped[str] = mapped_column(Text, default="")

    reliability_status: Mapped[str] = mapped_column(String(40), default="unknown")
    reconciliation_status: Mapped[str] = mapped_column(String(40), default="unreconciled")
    promotion_status: Mapped[str] = mapped_column(String(40), default="blocked")
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        try:
            route_evidence = json.loads(self.route_evidence_json or "{}")
        except json.JSONDecodeError:
            route_evidence = {}
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "codebook_version_id": self.codebook_version_id,
            "code_id": self.code_id,
            "evidence_unit_id": self.evidence_unit_id,
            "coding_run_id": self.coding_run_id,
            "source_text": self.source_text,
            "source_document_id": self.source_document_id,
            "source_location": self.source_location,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "coder_id": self.coder_id,
            "coder_type": self.coder_type,
            "model_name": self.model_name,
            "donor_id": self.donor_id,
            "route_id": self.route_id,
            "route_evidence": route_evidence,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "reliability_status": self.reliability_status,
            "reconciliation_status": self.reconciliation_status,
            "promotion_status": self.promotion_status,
            "review_status": self.review_status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
