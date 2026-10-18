"""Record decider verdicts, attach researchers' labels, and evaluate trust per scope.

Nothing here changes a research artifact. A trajectory is process evidence about a decider; a
trust evaluation decides only whether that decider's scope may add review routing (Phase 4), and a
scope without a passing evaluation stays in shadow mode (owner decision DEC-2).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decision.labels import (
    LABEL_MAPPING_VERSION,
    label_from_reconciliation,
    positive_probability,
)
from app.core.decision.sampling import AUDIT_RATE, audit_draw, inclusion_weight, scope_key
from app.core.decision.trust import (
    LabelledDecision,
    TrustPolicy,
    TrustReport,
    evaluate_trust,
    unversioned_alias_scope,
)
from app.models.decision_trajectory import DecisionTrajectory, DecisionTrustEvaluation

CODE_APPLICATION = "code_application"
logger = logging.getLogger(__name__)


async def record_trajectory(
    session: AsyncSession,
    *,
    outcome: Any,
    project_id: str,
    subject_kind: str,
    subject_id: str,
    question_set_id: str,
    question_set_version: str,
    question_id: str,
    positive_outcomes: frozenset[str],
    task_family: str,
    language: str,
    task_id: str | None = None,
    coding_run_id: str | None = None,
    evidence_unit_id: str | None = None,
    routed: bool = False,
    action: str = "shadow",
    calibrated: dict[str, float] | None = None,
    temperature: float | None = None,
    tau: float | None = None,
    order_flip_agree: bool | None = None,
    audit_rate: float = AUDIT_RATE,
) -> DecisionTrajectory:
    """Persist one verdict (``outcome`` is an ``app.core.decider.contract.DecisionOutcome``)."""
    served = outcome.served_model or outcome.requested_model
    sampled, rate = audit_draw(project_id, subject_id, audit_rate)
    row = DecisionTrajectory(
        project_id=project_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
        task_id=task_id,
        coding_run_id=coding_run_id,
        evidence_unit_id=evidence_unit_id,
        endpoint_id=outcome.endpoint_id,
        requested_model=outcome.requested_model,
        served_model=served,
        alias_requested=bool(outcome.alias_requested),
        question_set_id=question_set_id,
        question_set_version=question_set_version,
        question_id=question_id,
        task_family=task_family,
        language=language,
        scope_key=scope_key(
            project_id=project_id,
            provider=outcome.endpoint_id,
            served_model=served,
            question_set_id=question_set_id,
            question_set_version=question_set_version,
            task_family=task_family,
            language=language,
            label_mapping_version=LABEL_MAPPING_VERSION,
        ),
        status=outcome.status,
        reason=outcome.reason or "",
        raw_distribution_json=json.dumps(outcome.answers.get(question_id, {})),
        calibrated_distribution_json=json.dumps(calibrated or {}),
        positive_outcomes_json=json.dumps(sorted(positive_outcomes)),
        temperature=temperature,
        tau=tau,
        action=action,
        routed=routed,
        order_flip_agree=order_flip_agree,
        audit_sampled=sampled and not routed,
        audit_rate=rate,
        audit_blind=sampled and not routed,
        latency_ms=int(round(outcome.latency_s * 1000)),
        input_tokens=int(outcome.usage.get("input_tokens", 0)),
    )
    session.add(row)
    await session.flush()
    return row


async def attach_human_label(session: AsyncSession, decision: Any) -> int:
    """Label every unlabelled trajectory of the decision's code application; return how many.

    ``decision`` is a ``ReconciliationDecision``. Non-human sources and decision types without a
    v1 label change nothing.
    """
    label = label_from_reconciliation(decision.decision_type, decision.source)
    if label is None or not decision.code_application_id:
        return 0
    return await label_subject(
        session,
        project_id=decision.project_id,
        subject_kind=CODE_APPLICATION,
        subject_id=decision.code_application_id,
        label=label,
        source_id=decision.id,
    )


async def label_after_reconciliation(decision: Any) -> int:
    """Spine hook after a committed reconciliation decision; never raises."""
    try:
        from app.models.database import async_session

        async with async_session() as session:
            labelled = await attach_human_label(session, decision)
            await session.commit()
        return labelled
    except Exception as exc:
        logger.debug("Decision trajectory labelling skipped: %s", exc)
        return 0


async def label_subject(
    session: AsyncSession,
    *,
    project_id: str,
    subject_kind: str,
    subject_id: str,
    label: int,
    source_id: str,
) -> int:
    """Label a subject's unlabelled successful trajectories; earlier labels are never rewritten."""
    if label not in (0, 1):
        raise ValueError("label must be 0 or 1")
    result = await session.execute(
        select(DecisionTrajectory).where(
            DecisionTrajectory.project_id == project_id,
            DecisionTrajectory.subject_kind == subject_kind,
            DecisionTrajectory.subject_id == subject_id,
            DecisionTrajectory.status == "ok",
            DecisionTrajectory.human_label.is_(None),
        )
    )
    rows = result.scalars().all()
    now = datetime.now(UTC)
    for row in rows:
        row.human_label = label
        row.label_mapping_version = LABEL_MAPPING_VERSION
        row.label_decision_id = source_id
        row.labelled_at = now
    await session.flush()
    return len(rows)


def _labelled_decision(row: DecisionTrajectory) -> LabelledDecision | None:
    weight = inclusion_weight(row.routed, row.audit_sampled, row.audit_rate or AUDIT_RATE)
    if weight is None or row.human_label is None:
        return None
    p = positive_probability(row.raw_distribution(), row.positive_outcomes())
    return LabelledDecision(
        p_positive=p, label=row.human_label, weight=weight, order_flip_agree=row.order_flip_agree
    )


async def evaluate_scope(
    session: AsyncSession,
    key: str,
    policy: TrustPolicy | None = None,
    *,
    needs_order_flip: bool | None = None,
) -> TrustReport:
    """Run the trust gate on a scope's labelled trajectories and store the result.

    Items labelled outside the routed set and the random audit have no known inclusion
    probability, so they are left out rather than biasing the estimate.
    """
    result = await session.execute(
        select(DecisionTrajectory).where(
            DecisionTrajectory.scope_key == key,
            DecisionTrajectory.status == "ok",
            DecisionTrajectory.human_label.is_not(None),
        )
    )
    rows = result.scalars().all()
    items = [item for item in (_labelled_decision(row) for row in rows) if item is not None]
    if needs_order_flip is None:
        needs_order_flip = any(row.order_flip_agree is not None for row in rows)
    report = evaluate_trust(
        items,
        policy,
        alias_scope=unversioned_alias_scope(
            (bool(row.alias_requested), row.served_model) for row in rows
        ),
        needs_order_flip=needs_order_flip,
    )
    session.add(
        DecisionTrustEvaluation(
            scope_key=key,
            trusted=report.trusted,
            reasons_json=json.dumps(report.reasons),
            metrics_json=json.dumps(report.metrics),
            policy_json=json.dumps(report.policy or asdict(policy or TrustPolicy())),
            labelled_count=len(items),
        )
    )
    await session.flush()
    return report


async def scope_is_trusted(session: AsyncSession, key: str) -> bool:
    """True only when the latest evaluation of the scope passed; no evaluation means shadow mode."""
    result = await session.execute(
        select(DecisionTrustEvaluation)
        .where(DecisionTrustEvaluation.scope_key == key)
        .order_by(DecisionTrustEvaluation.evaluated_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return bool(latest and latest.trusted)


async def routed_triage(
    session: AsyncSession, project_id: str, subject_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Latest routed verdict per code application, for the review queue.

    Only items a trusted scope routed (``abstain`` or ``flag``) appear; shadow verdicts and blind
    audit items are never shown to reviewers, so they cannot anchor the human label.
    """
    if not subject_ids:
        return {}
    result = await session.execute(
        select(DecisionTrajectory)
        .where(
            DecisionTrajectory.project_id == project_id,
            DecisionTrajectory.subject_kind == CODE_APPLICATION,
            DecisionTrajectory.subject_id.in_(subject_ids),
            DecisionTrajectory.routed.is_(True),
            DecisionTrajectory.audit_blind.is_(False),
            DecisionTrajectory.status == "ok",
        )
        .order_by(DecisionTrajectory.created_at.desc())
    )
    triage: dict[str, dict[str, Any]] = {}
    for row in result.scalars().all():
        if row.subject_id in triage:
            continue
        calibrated = json.loads(row.calibrated_distribution_json or "{}")
        top = max(calibrated, key=lambda name: calibrated[name]) if calibrated else None
        triage[row.subject_id] = {
            "action": row.action,
            "top_outcome": top,
            "p_supports": calibrated.get("supports"),
            "endpoint_id": row.endpoint_id,
            "served_model": row.served_model,
        }
    return triage
