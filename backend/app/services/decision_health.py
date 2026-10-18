"""Ensemble health for decision models and LLM judges in one error model (research doc section 7).

Agreement between evaluators is not evidence of correctness when their errors coincide. On items a
researcher has reviewed, this service reports each decider scope's trust status, each LLM method's
human-verified accuracy, and how often evaluators are wrong together: pairwise error correlation,
Yule's Q, the effective number of independent evaluators and, for panels of three or more,
Dawid-Skene class-conditional reliabilities. Handles and numbers only; no research text.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decision.health import error_structure
from app.core.decision.labels import positive_probability
from app.models.decision_trajectory import DecisionTrajectory, DecisionTrustEvaluation

_TRUST_METRICS = ("effective_n", "held_out_ece", "held_out_brier", "kappa", "order_flip_rate")


async def scope_summaries(session: AsyncSession, project_id: str) -> list[dict[str, Any]]:
    rows = (
        (
            await session.execute(
                select(DecisionTrajectory).where(DecisionTrajectory.project_id == project_id)
            )
        )
        .scalars()
        .all()
    )
    scopes: dict[str, dict[str, Any]] = {}
    for row in rows:
        scope = scopes.setdefault(
            row.scope_key,
            {
                "scope_key": row.scope_key,
                "endpoint_id": row.endpoint_id,
                "served_model": row.served_model,
                "question_set": f"{row.question_set_id}@{row.question_set_version}",
                "task_family": row.task_family,
                "verdicts": 0,
                "labelled": 0,
                "routed": 0,
            },
        )
        scope["verdicts"] += 1
        scope["labelled"] += row.human_label is not None
        scope["routed"] += bool(row.routed)
    for key, scope in scopes.items():
        latest = (
            await session.execute(
                select(DecisionTrustEvaluation)
                .where(DecisionTrustEvaluation.scope_key == key)
                .order_by(DecisionTrustEvaluation.evaluated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        metrics = json.loads(latest.metrics_json or "{}") if latest else {}
        scope["trusted"] = bool(latest and latest.trusted)
        scope["reasons"] = latest.reasons() if latest else ["not_evaluated"]
        scope["metrics"] = {m: metrics.get(m) for m in _TRUST_METRICS if m in metrics}
    return list(scopes.values())


async def _llm_methods(session: AsyncSession, project_id: str) -> list[dict[str, Any]]:
    from app.models.method_metric import MethodMetric

    rows = (
        (await session.execute(select(MethodMetric).where(MethodMetric.project_id == project_id)))
        .scalars()
        .all()
    )
    totals: dict[str, list[int]] = {}
    for row in rows:
        agree, disagree = totals.setdefault(row.method, [0, 0])
        totals[row.method] = [
            agree + (row.human_agree_count or 0),
            disagree + (row.human_disagree_count or 0),
        ]
    return [
        {
            "method": method,
            "human_agree": agree,
            "human_disagree": disagree,
            "human_accuracy": agree / (agree + disagree) if agree + disagree else None,
        }
        for method, (agree, disagree) in sorted(totals.items())
    ]


def _llm_verdict(validation_result: str | None) -> tuple[str, int] | None:
    try:
        payload = json.loads(validation_result or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    llm = payload.get("llm") if isinstance(payload.get("llm"), dict) else payload
    method = llm.get("actual_method")
    agreement = llm.get("agreement_score")
    if not method or not isinstance(agreement, (int, float)):
        return None
    return f"llm:{method}", int(agreement >= 0.5)


async def _verdicts(session: AsyncSession, project_id: str) -> tuple[dict[str, dict], dict]:
    """Evaluator -> {task id: verdict}, and task id -> human label, on reviewed task outputs."""
    from app.models.task import Task

    rows = (
        (
            await session.execute(
                select(DecisionTrajectory).where(
                    DecisionTrajectory.project_id == project_id,
                    DecisionTrajectory.subject_kind == "task_output",
                    DecisionTrajectory.status == "ok",
                    DecisionTrajectory.human_label.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    verdicts: dict[str, dict[str, int]] = {}
    labels: dict[str, int] = {}
    for row in rows:
        labels[row.subject_id] = int(row.human_label)
        p = positive_probability(row.raw_distribution(), row.positive_outcomes())
        verdicts.setdefault(f"decider:{row.endpoint_id}", {})[row.subject_id] = int(p >= 0.5)
    if labels:
        tasks = (
            (await session.execute(select(Task).where(Task.id.in_(list(labels))))).scalars().all()
        )
        for task in tasks:
            llm = _llm_verdict(task.validation_result)
            if llm is not None:
                verdicts.setdefault(llm[0], {})[task.id] = llm[1]
    return verdicts, labels


async def decision_model_health(session: AsyncSession, project_id: str) -> dict[str, Any]:
    verdicts, labels = await _verdicts(session, project_id)
    return {
        "project_id": project_id,
        "scopes": await scope_summaries(session, project_id),
        "llm_methods": await _llm_methods(session, project_id),
        "error_structure": error_structure(verdicts, labels),
    }
