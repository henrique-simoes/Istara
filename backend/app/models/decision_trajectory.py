"""Decision trajectories and trust evaluations for typed decision models.

A trajectory records one decider verdict on one research item and, later, the researcher's label
for that item. It holds handles and numbers only: no prompt, quote or document text (Research Spine
telemetry contract). Distributions are keyed by option names from the versioned question set.
Trajectories are process evidence about the decider, never research evidence about the project.
"""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class DecisionTrajectory(Base):
    __tablename__ = "decision_trajectories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    coding_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evidence_unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    endpoint_id: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_model: Mapped[str] = mapped_column(String(200), default="")
    served_model: Mapped[str] = mapped_column(String(200), default="")
    alias_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    question_set_id: Mapped[str] = mapped_column(String(100), nullable=False)
    question_set_version: Mapped[str] = mapped_column(String(40), nullable=False)
    question_id: Mapped[str] = mapped_column(String(100), nullable=False)
    task_family: Mapped[str] = mapped_column(String(60), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(60), default="")
    raw_distribution_json: Mapped[str] = mapped_column(Text, default="{}")
    calibrated_distribution_json: Mapped[str] = mapped_column(Text, default="{}")
    positive_outcomes_json: Mapped[str] = mapped_column(Text, default="[]")
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    tau: Mapped[float | None] = mapped_column(Float, nullable=True)
    action: Mapped[str] = mapped_column(String(20), default="shadow")
    routed: Mapped[bool] = mapped_column(Boolean, default=False)
    order_flip_agree: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    audit_sampled: Mapped[bool] = mapped_column(Boolean, default=False)
    audit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    audit_blind: Mapped[bool] = mapped_column(Boolean, default=False)
    label_mapping_version: Mapped[str] = mapped_column(String(10), default="")
    human_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label_decision_id: Mapped[str] = mapped_column(String(36), default="")
    labelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def raw_distribution(self) -> dict[str, float]:
        return _float_map(self.raw_distribution_json)

    def positive_outcomes(self) -> frozenset[str]:
        try:
            parsed = json.loads(self.positive_outcomes_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return frozenset()
        return frozenset(str(item) for item in parsed) if isinstance(parsed, list) else frozenset()


class DecisionTrustEvaluation(Base):
    __tablename__ = "decision_trust_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    scope_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    policy_json: Mapped[str] = mapped_column(Text, default="{}")
    labelled_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def reasons(self) -> list[str]:
        try:
            parsed = json.loads(self.reasons_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
        return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _float_map(raw: str) -> dict[str, float]:
    try:
        parsed = json.loads(raw or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): float(v) for k, v in parsed.items() if isinstance(v, (int, float))}
