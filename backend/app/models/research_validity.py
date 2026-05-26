"""Research-validity models for evidence units, coding runs, and evidence graph.

These tables make Istara's qualitative analysis chain explicit:
raw source material is segmented into stable evidence units, independently
coded by models/humans, checked with reliability metrics, reconciled, and only
then promoted into downstream findings and reports.
"""

from datetime import datetime, timezone
import json

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _json_value(value: str | None, default):
    if not value:
        return default
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default
    return parsed


class EvidenceUnit(Base):
    """Stable phrase/segment unit used as the substrate for qualitative coding."""

    __tablename__ = "evidence_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(String(200), default="", index=True)
    stable_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    unit_index: Mapped[int] = mapped_column(Integer, default=0)
    unit_type: Mapped[str] = mapped_column(String(40), default="segment")
    source_type: Mapped[str] = mapped_column(String(60), default="document")
    method: Mapped[str] = mapped_column(String(80), default="")
    phase: Mapped[str] = mapped_column(String(40), default="")
    participant_id: Mapped[str] = mapped_column(String(100), default="")
    speaker: Mapped[str] = mapped_column(String(120), default="")
    source_text: Mapped[str] = mapped_column(Text, default="")
    source_location: Mapped[str] = mapped_column(String(250), default="")
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "source_document_id": self.source_document_id,
            "source_id": self.source_id,
            "stable_id": self.stable_id,
            "unit_index": self.unit_index,
            "unit_type": self.unit_type,
            "source_type": self.source_type,
            "method": self.method,
            "phase": self.phase,
            "participant_id": self.participant_id,
            "speaker": self.speaker,
            "source_text": self.source_text,
            "source_location": self.source_location,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "metadata": _json_value(self.metadata_json, {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CodingRun(Base):
    """A governed coding/reliability pass over a set of evidence units."""

    __tablename__ = "coding_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    codebook_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    method: Mapped[str] = mapped_column(String(80), default="inductive_multi_model")
    reliability_method: Mapped[str] = mapped_column(String(60), default="")
    rater_count: Mapped[int] = mapped_column(Integer, default=0)
    distinct_model_count: Mapped[int] = mapped_column(Integer, default=0)
    kappa: Mapped[float | None] = mapped_column(Float, nullable=True)
    alpha: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float] = mapped_column(Float, default=0.60)
    promotion_status: Mapped[str] = mapped_column(String(40), default="blocked")
    fallback_reason: Mapped[str] = mapped_column(Text, default="")
    route_evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    matrix_json: Mapped[str] = mapped_column(Text, default="{}")
    disagreement_json: Mapped[str] = mapped_column(Text, default="[]")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "codebook_version_id": self.codebook_version_id,
            "status": self.status,
            "method": self.method,
            "reliability_method": self.reliability_method,
            "rater_count": self.rater_count,
            "distinct_model_count": self.distinct_model_count,
            "kappa": self.kappa,
            "alpha": self.alpha,
            "threshold": self.threshold,
            "promotion_status": self.promotion_status,
            "fallback_reason": self.fallback_reason,
            "route_evidence": _json_value(self.route_evidence_json, []),
            "matrix": _json_value(self.matrix_json, {}),
            "disagreements": _json_value(self.disagreement_json, []),
            "created_by": self.created_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CodingRunCoder(Base):
    """Model/human coder participating in a coding run."""

    __tablename__ = "coding_run_coders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    coding_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    coder_id: Mapped[str] = mapped_column(String(100), nullable=False)
    coder_type: Mapped[str] = mapped_column(String(30), default="llm")
    model_name: Mapped[str] = mapped_column(String(200), default="")
    donor_id: Mapped[str] = mapped_column(String(120), default="")
    route_id: Mapped[str] = mapped_column(String(120), default="")
    route_evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "coding_run_id": self.coding_run_id,
            "project_id": self.project_id,
            "coder_id": self.coder_id,
            "coder_type": self.coder_type,
            "model_name": self.model_name,
            "donor_id": self.donor_id,
            "route_id": self.route_id,
            "route_evidence": _json_value(self.route_evidence_json, {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ResearchEvidenceEdge(Base):
    """Traceability edge for the Evidence Graph / GraphRAG layer."""

    __tablename__ = "research_evidence_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    evidence_unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    coding_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    codebook_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reliability_status: Mapped[str] = mapped_column(String(40), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "relation": self.relation,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "evidence_unit_id": self.evidence_unit_id,
            "coding_run_id": self.coding_run_id,
            "task_id": self.task_id,
            "codebook_version_id": self.codebook_version_id,
            "reliability_status": self.reliability_status,
            "metadata": _json_value(self.metadata_json, {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ReconciliationDecision(Base):
    """Human/debate/adversarial decision that resolves coded-evidence disagreement."""

    __tablename__ = "reconciliation_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    coding_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    evidence_unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    code_application_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    decision_type: Mapped[str] = mapped_column(String(40), default="human_review", index=True)
    source: Mapped[str] = mapped_column(String(40), default="human_review")
    accepted_code_id: Mapped[str] = mapped_column(String(100), default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str] = mapped_column(String(100), default="")
    previous_state_json: Mapped[str] = mapped_column(Text, default="{}")
    resolved_state_json: Mapped[str] = mapped_column(Text, default="{}")
    route_evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "coding_run_id": self.coding_run_id,
            "evidence_unit_id": self.evidence_unit_id,
            "code_application_id": self.code_application_id,
            "decision_type": self.decision_type,
            "source": self.source,
            "accepted_code_id": self.accepted_code_id,
            "rationale": self.rationale,
            "decided_by": self.decided_by,
            "previous_state": _json_value(self.previous_state_json, {}),
            "resolved_state": _json_value(self.resolved_state_json, {}),
            "route_evidence": _json_value(self.route_evidence_json, {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
