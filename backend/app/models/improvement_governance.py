"""Governed improvement proposals for self-evolving Istara systems."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


class ImprovementProposal(Base):
    """A tracked behavior or learning change proposed by Istara's agentic loops."""

    __tablename__ = "improvement_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_system: Mapped[str] = mapped_column(String(60), default="manual", index=True)
    source_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    project_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    agent_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    affected_surfaces_json: Mapped[str] = mapped_column(Text, default="[]")
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    approval_policy: Mapped[str] = mapped_column(
        String(30), default="approval_required", index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="proposed", index=True)
    before_state_json: Mapped[str] = mapped_column(Text, default="{}")
    proposed_change_json: Mapped[str] = mapped_column(Text, default="{}")
    rollback_plan_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    metrics_before_json: Mapped[str] = mapped_column(Text, default="{}")
    metrics_after_json: Mapped[str] = mapped_column(Text, default="{}")
    evaluation_runs_json: Mapped[str] = mapped_column(Text, default="[]")
    reasoning_memory_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    improvement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_apply_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(100), default="")
    approved_by: Mapped[str] = mapped_column(String(100), default="")
    applied_by: Mapped[str] = mapped_column(String(100), default="")
    reverted_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def get_affected_surfaces(self) -> list[str]:
        parsed = _loads_json(self.affected_surfaces_json, [])
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def set_affected_surfaces(self, surfaces: list[str]) -> None:
        self.affected_surfaces_json = _dumps_json(surfaces, [])

    def get_before_state(self) -> dict:
        parsed = _loads_json(self.before_state_json, {})
        return parsed if isinstance(parsed, dict) else {}

    def set_before_state(self, state: dict | None) -> None:
        self.before_state_json = _dumps_json(state, {})

    def get_proposed_change(self) -> dict:
        parsed = _loads_json(self.proposed_change_json, {})
        return parsed if isinstance(parsed, dict) else {}

    def set_proposed_change(self, change: dict | None) -> None:
        self.proposed_change_json = _dumps_json(change, {})

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

    def get_evaluation_runs(self) -> list:
        parsed = _loads_json(self.evaluation_runs_json, [])
        return parsed if isinstance(parsed, list) else []

    def set_evaluation_runs(self, runs: list | None) -> None:
        self.evaluation_runs_json = _dumps_json(runs, [])

    def get_reasoning_memory_ids(self) -> list[str]:
        parsed = _loads_json(self.reasoning_memory_ids_json, [])
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def set_reasoning_memory_ids(self, memory_ids: list[str] | None) -> None:
        self.reasoning_memory_ids_json = _dumps_json(memory_ids, [])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_system": self.source_system,
            "source_id": self.source_id,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "summary": self.summary,
            "rationale": self.rationale,
            "affected_surfaces": self.get_affected_surfaces(),
            "risk_level": self.risk_level,
            "approval_policy": self.approval_policy,
            "status": self.status,
            "before_state": self.get_before_state(),
            "proposed_change": self.get_proposed_change(),
            "rollback_plan": self.get_rollback_plan(),
            "evidence": self.get_evidence(),
            "metrics_before": self.get_metrics_before(),
            "metrics_after": self.get_metrics_after(),
            "evaluation_runs": self.get_evaluation_runs(),
            "reasoning_memory_ids": self.get_reasoning_memory_ids(),
            "improvement_score": self.improvement_score,
            "confidence": self.confidence,
            "requires_human_approval": self.requires_human_approval,
            "auto_apply_allowed": self.auto_apply_allowed,
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "applied_by": self.applied_by,
            "reverted_by": self.reverted_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "reverted_at": self.reverted_at.isoformat() if self.reverted_at else None,
        }
