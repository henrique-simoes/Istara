"""The decision-model learning loop: re-evaluate trust as labels arrive, detect drift, keep lessons.

* A scope is re-evaluated when enough new human labels have arrived since its last evaluation (or
  when it first reaches the minimum). The gate is ``app.core.decision.trust``; nothing else grants
  routing power.
* A trusted scope whose new labels drift above the Brier score it was trusted at (one-sided CUSUM)
  returns to shadow mode with the reason recorded.
* Each evaluation leaves a content-free ReasoningBank lesson (source kind ``decision_review``,
  process memory only): scope handles, trusted or not, reasons and headline metrics. Lessons never
  carry research text and are never report evidence.

Every entry point that a Research Spine hook calls never raises.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decision.calibration import temperature_scale
from app.core.decision.drift import brier_contribution, cusum_upward
from app.core.decision.labels import positive_probability
from app.core.decision.trust import TrustReport
from app.models.decision_trajectory import DecisionTrajectory, DecisionTrustEvaluation
from app.services.decision_trajectories import evaluate_scope

logger = logging.getLogger(__name__)

FIRST_EVALUATION_MIN_LABELS = 50
REEVALUATE_EVERY = 10
_LESSON_METRICS = ("effective_n", "held_out_ece", "held_out_brier", "kappa", "order_flip_rate")


async def _latest_evaluation(session: AsyncSession, key: str) -> DecisionTrustEvaluation | None:
    result = await session.execute(
        select(DecisionTrustEvaluation)
        .where(DecisionTrustEvaluation.scope_key == key)
        .order_by(DecisionTrustEvaluation.evaluated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _labelled_count(session: AsyncSession, key: str) -> int:
    result = await session.execute(
        select(func.count(DecisionTrajectory.id)).where(
            DecisionTrajectory.scope_key == key,
            DecisionTrajectory.status == "ok",
            DecisionTrajectory.human_label.is_not(None),
        )
    )
    return int(result.scalar_one() or 0)


def _due(labelled: int, latest: DecisionTrustEvaluation | None) -> bool:
    if latest is None:
        return labelled >= FIRST_EVALUATION_MIN_LABELS
    return labelled - (latest.labelled_count or 0) >= REEVALUATE_EVERY


async def check_drift(session: AsyncSession, key: str) -> bool:
    """Return True (and record an untrusted evaluation) when a trusted scope has drifted."""
    latest = await _latest_evaluation(session, key)
    if latest is None or not latest.trusted:
        return False
    metrics = json.loads(latest.metrics_json or "{}")
    reference = metrics.get("held_out_brier")
    temperature = metrics.get("median_temperature")
    if not isinstance(reference, (int, float)) or not isinstance(temperature, (int, float)):
        return False
    result = await session.execute(
        select(DecisionTrajectory)
        .where(
            DecisionTrajectory.scope_key == key,
            DecisionTrajectory.status == "ok",
            DecisionTrajectory.human_label.is_not(None),
            DecisionTrajectory.labelled_at > latest.evaluated_at,
        )
        .order_by(DecisionTrajectory.labelled_at.asc())
    )
    contributions = []
    for row in result.scalars().all():
        p = positive_probability(row.raw_distribution(), row.positive_outcomes())
        calibrated = temperature_scale([1.0 - p, p], float(temperature))[1]
        contributions.append(brier_contribution(calibrated, row.human_label))
    # Binary Brier is half the two-class multiclass Brier the gate reports.
    drift = cusum_upward(contributions, float(reference) / 2.0)
    if not drift.drifted:
        return False
    session.add(
        DecisionTrustEvaluation(
            scope_key=key,
            trusted=False,
            reasons_json=json.dumps(["calibration_drift"]),
            metrics_json=json.dumps(
                {**metrics, "drift_statistic": drift.statistic, "drift_at": drift.alarm_index}
            ),
            policy_json=latest.policy_json,
            labelled_count=latest.labelled_count + len(contributions),
        )
    )
    await session.flush()
    return True


async def _record_lesson(project_id: str, key: str, report: TrustReport) -> None:
    from app.core.reasoning_bank import reasoning_bank

    headline = {m: report.metrics.get(m) for m in _LESSON_METRICS if m in report.metrics}
    verdict = "trusted" if report.trusted else "not trusted: " + ", ".join(report.reasons)
    await reasoning_bank.record_memory(
        project_id=project_id,
        source_kind="decision_review",
        source_id=key,
        outcome="observed",
        title=f"Decision-model scope {key[:8]} {verdict}"[:255],
        description="Calibration trust-gate evaluation of a decision-model scope.",
        content=json.dumps({"scope_key": key, "trusted": report.trusted, **headline}),
        tags=["decision_model", "trust_gate", "process-memory-only"],
        domain="decision_models",
        confidence=0.5,
    )


async def reevaluate_scope_if_due(session: AsyncSession, project_id: str, key: str) -> str:
    """``evaluated``, ``drifted`` or ``not_due``."""
    if await check_drift(session, key):
        await session.commit()
        return "drifted"
    latest = await _latest_evaluation(session, key)
    if not _due(await _labelled_count(session, key), latest):
        return "not_due"
    report = await evaluate_scope(session, key)
    await session.commit()
    await _record_lesson(project_id, key, report)
    return "evaluated"


async def reevaluate_subject_scopes_safely(
    project_id: str, subject_kind: str, subject_id: str
) -> dict[str, str]:
    """Hook after a human label lands on a subject; never raises."""
    try:
        from app.models.database import async_session

        async with async_session() as session:
            result = await session.execute(
                select(DecisionTrajectory.scope_key)
                .where(
                    DecisionTrajectory.project_id == project_id,
                    DecisionTrajectory.subject_kind == subject_kind,
                    DecisionTrajectory.subject_id == subject_id,
                )
                .distinct()
            )
            keys = [row[0] for row in result.all()]
            return {key: await reevaluate_scope_if_due(session, project_id, key) for key in keys}
    except Exception as exc:
        logger.debug("Decision-model re-evaluation skipped: %s", exc)
        return {}


def lesson_metrics(report: TrustReport) -> dict[str, Any]:
    """The content-free fields a ReasoningBank lesson keeps (exposed for tests and audits)."""
    return {m: report.metrics.get(m) for m in _LESSON_METRICS if m in report.metrics}


async def learn_from_reconciliation(decision: Any) -> None:
    """Spine hook after a committed reconciliation: label, then re-evaluate. Never raises."""
    from app.services.decision_trajectories import label_after_reconciliation

    if await label_after_reconciliation(decision):
        await reevaluate_subject_scopes_safely(
            decision.project_id, "code_application", decision.code_application_id
        )
