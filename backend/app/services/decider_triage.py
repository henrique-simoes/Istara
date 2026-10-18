"""Decision-model triage of code applications (layer 2 at the Research Spine seam).

Runs after a coding run has committed its applications, reliability gate and item statuses, on
its own session, so it cannot change acceptance states or the kappa matrix. For each application a
decider answers one choice: does the evidence unit support, contradict, or say nothing about the
applied code? An untrusted scope only records (shadow). A trusted scope may mark an item for
priority human review (``abstain`` when uncertain or order-sensitive, ``flag`` when it judges the
code unsupported). Nothing here accepts, rejects or promotes evidence.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from app.core.assurance import ProjectAssurance
from app.core.decision.calibration import temperature_scale
from app.core.decision.decision_rule import binary_threshold, merge_order_flip

logger = logging.getLogger(__name__)

QUESTION_SET_ID = "code-application-triage"
QUESTION_SET_VERSION = "1"
QUESTION_ID = "relation"
TASK_FAMILY = "deductive_coding"
UNDETERMINED_LANGUAGE = "und"
POSITIVE = frozenset({"supports"})
TRIAGE_MODES = frozenset({"auto", "decision_models", "both"})
MAX_PER_RUN = 200
CONCURRENCY = 8
TIME_BUDGET_S = 120.0
_TEXT_LIMIT = 6000
_TAU = binary_threshold(9.0, 1.0)


def _question(code: dict[str, str]) -> Any:
    from app.core.decider.contract import Choice

    return Choice(
        f"How does the evidence unit relate to applying the code `{code['name']}` to it?",
        {
            "supports": "The evidence unit expresses the code as its definition describes.",
            "contradicts": (
                "The evidence unit expresses the opposite of the code, or meets an exclusion "
                "criterion."
            ),
            "says_nothing": "The evidence unit does not address what the code describes.",
        },
    )


async def _code_context(session: Any, code_id: str, project_id: str) -> dict[str, str]:
    """The code's name and criteria, by id, then by name in the project's codebooks."""
    from sqlalchemy import select

    from app.models.codebook import Code, Codebook

    code = await session.get(Code, code_id)
    if code is None:
        result = await session.execute(
            select(Code)
            .join(Codebook, Codebook.id == Code.codebook_id)
            .where(Codebook.project_id == project_id, Code.name == code_id)
            .limit(1)
        )
        code = result.scalar_one_or_none()
    if code is None:
        return {"name": code_id, "definition": "", "inclusion": "", "exclusion": "", "found": ""}
    return {
        "name": code.name,
        "definition": code.definition or "",
        "inclusion": code.inclusion_criteria or "",
        "exclusion": code.exclusion_criteria or "",
        "found": "yes",
    }


def _state(application: Any, unit_text: str, code: dict[str, str]) -> dict[str, Any]:
    """The evidence unit, the coder's quote (``source_text`` holds the quote) and the code."""
    return {
        "evidence_unit": (unit_text or application.source_text or "")[:_TEXT_LIMIT],
        "coder_quote": (application.source_text or "")[:_TEXT_LIMIT],
        "code": {
            "name": code["name"],
            "definition": code["definition"],
            "inclusion_criteria": code["inclusion"],
            "exclusion_criteria": code["exclusion"],
        },
    }


def decide_action(
    merged: dict[str, float], order_flip_agree: bool, temperature: float | None, trusted: bool
) -> tuple[str, dict[str, float]]:
    """``(action, calibrated distribution)`` for one verdict. Untrusted scopes stay in shadow."""
    if not trusted or temperature is None:
        return "shadow", {}
    names = list(merged)
    calibrated = dict(zip(names, temperature_scale([merged[n] for n in names], temperature)))
    top = max(calibrated, key=lambda name: calibrated[name])
    if not order_flip_agree or calibrated[top] < _TAU:
        return "abstain", calibrated
    if top != "supports":
        return "flag", calibrated
    return "none", calibrated


async def _scope_trust(session: Any, scope_key: str) -> tuple[bool, float | None]:
    from sqlalchemy import select

    from app.models.decision_trajectory import DecisionTrustEvaluation

    result = await session.execute(
        select(DecisionTrustEvaluation)
        .where(DecisionTrustEvaluation.scope_key == scope_key)
        .order_by(DecisionTrustEvaluation.evaluated_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None or not latest.trusted:
        return False, None
    metrics = json.loads(latest.metrics_json or "{}")
    temperature = metrics.get("median_temperature")
    return True, float(temperature) if isinstance(temperature, (int, float)) else None


async def _triage_one(client: Any, application: Any, project_id: str, run_id: str) -> str:
    from app.core.decider.contract import with_reversed_choices
    from app.models.database import async_session
    from app.services.decision_trajectories import record_trajectory

    from app.models.research_validity import EvidenceUnit

    async with async_session() as session:
        code = await _code_context(session, application.code_id, project_id)
        unit = (
            await session.get(EvidenceUnit, application.evidence_unit_id)
            if application.evidence_unit_id
            else None
        )
    questions = with_reversed_choices({QUESTION_ID: _question(code)})
    state = _state(application, unit.source_text if unit is not None else "", code)
    outcome = await client.decide(state, questions)
    flip = None
    merged: dict[str, float] = {}
    if outcome.ok:
        result = merge_order_flip(
            outcome.answers[QUESTION_ID], outcome.answers[QUESTION_ID + "__reversed"]
        )
        flip, merged = result.agree, result.merged
    async with async_session() as session:
        row = await record_trajectory(
            session,
            outcome=outcome,
            project_id=project_id,
            subject_kind="code_application",
            subject_id=application.id,
            task_id=application.task_id,
            coding_run_id=run_id,
            evidence_unit_id=application.evidence_unit_id,
            question_set_id=QUESTION_SET_ID,
            question_set_version=QUESTION_SET_VERSION,
            question_id=QUESTION_ID,
            positive_outcomes=POSITIVE,
            task_family=TASK_FAMILY,
            language=UNDETERMINED_LANGUAGE,
            order_flip_agree=flip,
        )
        if outcome.ok:
            row.raw_distribution_json = json.dumps(merged)
            trusted, temperature = await _scope_trust(session, row.scope_key)
            action, calibrated = decide_action(merged, bool(flip), temperature, trusted)
            row.action = action
            row.calibrated_distribution_json = json.dumps(calibrated)
            row.temperature = temperature
            row.tau = _TAU if trusted else None
            if action in ("abstain", "flag"):
                row.routed = True
                row.audit_sampled = False
                row.audit_blind = False
        if not code["found"]:
            row.reason = (row.reason or "code_not_found")[:60]
        action = row.action if outcome.ok else "not_runnable"
        await session.commit()
    return action


def _active(policy: ProjectAssurance) -> bool:
    return policy.mode in TRIAGE_MODES and bool(policy.decider_endpoint_ids)


async def triage_coding_run(
    project_id: str,
    run_id: str,
    *,
    policy: ProjectAssurance | None = None,
    max_items: int = MAX_PER_RUN,
    time_budget_s: float = TIME_BUDGET_S,
) -> dict[str, Any]:
    """Triage a committed coding run's applications; returns counts by action."""
    from sqlalchemy import select

    from app.core.decider.access import open_decider
    from app.core.decider.registry import DeciderUnavailableError
    from app.models.code_application import CodeApplication
    from app.models.database import async_session
    from app.services.assurance_policies import load_project_assurance

    policy = policy or await load_project_assurance(project_id)
    summary: dict[str, Any] = {"run_id": run_id, "counts": {}, "skipped": 0, "unavailable": {}}
    if not _active(policy):
        summary["inactive"] = True
        return summary
    async with async_session() as session:
        result = await session.execute(
            select(CodeApplication).where(
                CodeApplication.project_id == project_id,
                CodeApplication.coding_run_id == run_id,
            )
        )
        applications = list(result.scalars().all())
    summary["skipped"] = max(0, len(applications) - max_items)
    applications = applications[:max_items]
    deadline = time.monotonic() + time_budget_s
    gate = asyncio.Semaphore(CONCURRENCY)

    async def run(client: Any, application: Any) -> str:
        async with gate:
            if time.monotonic() > deadline:
                return "skipped_time_budget"
            try:
                return await _triage_one(client, application, project_id, run_id)
            except Exception as exc:
                logger.debug("Decider triage failed for %s: %s", application.id, exc)
                return "error"

    for endpoint_id in policy.decider_endpoint_ids:
        try:
            client = await open_decider(endpoint_id, project_id)
        except DeciderUnavailableError as error:
            summary["unavailable"][endpoint_id] = error.reason
            continue
        for action in await asyncio.gather(*(run(client, app) for app in applications)):
            summary["counts"][action] = summary["counts"].get(action, 0) + 1
    return summary


async def triage_coding_run_safely(project_id: str, run_id: str) -> dict[str, Any] | None:
    """Spine hook: never raises, so a decider problem can never fail a coding run."""
    try:
        return await triage_coding_run(project_id, run_id)
    except Exception as exc:
        logger.debug("Decider triage skipped for run %s: %s", run_id, exc)
        return None
