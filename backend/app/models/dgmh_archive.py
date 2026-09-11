"""DGM-H archive variants for governed self-evolution."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _loads_json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return fallback


def _dumps_json(value: Any, fallback: Any) -> str:
    try:
        return json.dumps(value if value is not None else fallback, default=str)
    except TypeError:
        return json.dumps(fallback)


class DGMHArchiveVariant(Base):
    """A HyperAgents/DGM-H evolution candidate with lineage and evidence."""

    __tablename__ = "dgmh_archive_variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    root_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    generation: Mapped[int] = mapped_column(Integer, default=0, index=True)
    source_system: Mapped[str] = mapped_column(String(60), default="manual", index=True)
    source_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    project_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    agent_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    governance_proposal_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    target_system: Mapped[str] = mapped_column(String(120), default="", index=True)
    mutation_kind: Mapped[str] = mapped_column(String(80), default="proposal", index=True)
    mutation_surface: Mapped[str] = mapped_column(String(80), default="evaluation", index=True)
    artifact_kind: Mapped[str] = mapped_column(String(80), default="evidence_trace", index=True)
    artifact_ref: Mapped[str] = mapped_column(String(255), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="candidate", index=True)
    lineage_json: Mapped[str] = mapped_column(Text, default="[]")
    mutation_json: Mapped[str] = mapped_column(Text, default="{}")
    rollback_plan_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    metrics_before_json: Mapped[str] = mapped_column(Text, default="{}")
    metrics_after_json: Mapped[str] = mapped_column(Text, default="{}")
    evaluation_json: Mapped[str] = mapped_column(Text, default="[]")
    reasoning_memory_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    ucb_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def get_lineage(self) -> list[str]:
        parsed = _loads_json(self.lineage_json, [])
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def set_lineage(self, lineage: list[str] | None) -> None:
        self.lineage_json = _dumps_json(lineage, [])

    def get_mutation(self) -> dict:
        parsed = _loads_json(self.mutation_json, {})
        return parsed if isinstance(parsed, dict) else {}

    def set_mutation(self, mutation: dict | None) -> None:
        self.mutation_json = _dumps_json(mutation, {})

    def get_rollback_plan(self) -> dict:
        parsed = _loads_json(self.rollback_plan_json, {})
        return parsed if isinstance(parsed, dict) else {}

    def set_rollback_plan(self, plan: dict | None) -> None:
        self.rollback_plan_json = _dumps_json(plan, {})

    def get_evidence(self) -> list:
        parsed = _loads_json(self.evidence_json, [])
        return parsed if isinstance(parsed, list) else []

    def set_evidence(self, evidence: list | None) -> None:
        self.evidence_json = _dumps_json(evidence, [])

    def get_metrics_before(self) -> dict:
        parsed = _loads_json(self.metrics_before_json, {})
        return parsed if isinstance(parsed, dict) else {}

    def set_metrics_before(self, metrics: dict | None) -> None:
        self.metrics_before_json = _dumps_json(metrics, {})

    def get_metrics_after(self) -> dict:
        parsed = _loads_json(self.metrics_after_json, {})
        return parsed if isinstance(parsed, dict) else {}

    def set_metrics_after(self, metrics: dict | None) -> None:
        self.metrics_after_json = _dumps_json(metrics, {})

    def get_evaluation(self) -> list:
        parsed = _loads_json(self.evaluation_json, [])
        return parsed if isinstance(parsed, list) else []

    def set_evaluation(self, evaluation: list | None) -> None:
        self.evaluation_json = _dumps_json(evaluation, [])

    def get_reasoning_memory_ids(self) -> list[str]:
        parsed = _loads_json(self.reasoning_memory_ids_json, [])
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def set_reasoning_memory_ids(self, memory_ids: list[str] | None) -> None:
        self.reasoning_memory_ids_json = _dumps_json(memory_ids, [])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "generation": self.generation,
            "source_system": self.source_system,
            "source_id": self.source_id,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "governance_proposal_id": self.governance_proposal_id,
            "target_system": self.target_system,
            "mutation_kind": self.mutation_kind,
            "mutation_surface": self.mutation_surface,
            "artifact_kind": self.artifact_kind,
            "artifact_ref": self.artifact_ref,
            "title": self.title,
            "summary": self.summary,
            "status": self.status,
            "lineage": self.get_lineage(),
            "mutation": self.get_mutation(),
            "rollback_plan": self.get_rollback_plan(),
            "evidence": self.get_evidence(),
            "metrics_before": self.get_metrics_before(),
            "metrics_after": self.get_metrics_after(),
            "evaluation": self.get_evaluation(),
            "reasoning_memory_ids": self.get_reasoning_memory_ids(),
            "score": self.score,
            "confidence": self.confidence,
            "ucb_score": self.ucb_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "reverted_at": self.reverted_at.isoformat() if self.reverted_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
