"""Operational validation of a skill's candidate output, governed by the project's assurance mode.

This is a quality signal over one candidate summary, not formal qualitative-coding reliability:
task-linked coding runs and the kappa gate happen later through the Research Spine, in every mode.
Whatever runs here, the task still ends In Review and only a researcher moves it to Done.

* LLM judges run the method the adaptive selector picks among those the mode allows.
* Decision models answer one typed question (``operational-output`` v1, ``acceptable``) labelled
  by the researcher's later approve / send-back decision. Their verdicts are stored as
  trajectories and never route anything here; a trusted scope is marked ``advisory``.
* ``both`` keeps the two halves side by side; nothing merges them into one verdict.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.assurance import ProjectAssurance, ValidationPlan, plan_validation

logger = logging.getLogger(__name__)

QUESTION_SET_ID = "operational-output"
QUESTION_SET_VERSION = "1"
QUESTION_ID = "acceptable"
TASK_FAMILY = "operational_validation"
UNDETERMINED_LANGUAGE = "und"
_STATE_LIMIT = 8000
_VALIDATION_SYSTEM = (
    "Validate the candidate UX research output for accuracy, "
    "completeness, evidence fit, and actionability."
)


@dataclass
class OperationalValidation:
    plan: ValidationPlan
    requested_method: str | None = None
    llm_method: str | None = None
    llm: dict[str, Any] | None = None
    consensus_score: float | None = None
    deciders: list[dict[str, Any]] = field(default_factory=list)
    hook_payload: dict[str, Any] | None = None

    @property
    def validation_method(self) -> str:
        if self.llm_method:
            return self.llm_method
        if self.deciders:
            return "decision_models"
        return "unvalidated"

    def result(self) -> dict[str, Any]:
        """The ``task.validation_result`` payload. LLM keys stay top-level for older readers."""
        payload: dict[str, Any] = dict(self.llm or {})
        payload["assurance_mode"] = self.plan.mode
        payload["llm"] = self.llm
        payload["deciders"] = self.deciders
        if not self.llm and not self.deciders:
            payload["status"] = "unvalidated"
            payload["unvalidated_reason"] = self.plan.unvalidated_reason or "nothing_ran"
        if self.plan.notes:
            payload["notes"] = list(self.plan.notes)
        return payload

    @property
    def should_record(self) -> bool:
        """Something ran, or the mode made the task explicitly unvalidated.

        A failed LLM run in ``auto`` mode leaves the task untouched, as before modes existed.
        """
        return bool(self.llm or self.deciders or self.plan.unvalidated_reason)

    def apply_to(self, task: Any) -> None:
        task.validation_method = self.validation_method
        task.validation_result = json.dumps(self.result())
        task.consensus_score = self.consensus_score


async def load_project_assurance(project_id: str) -> ProjectAssurance:
    """The project's stored choice, or ``auto`` (the pre-modes behaviour) when it has none."""
    from app.models.assurance_policy import ProjectAssurancePolicy
    from app.models.database import async_session

    async with async_session() as session:
        row = await session.get(ProjectAssurancePolicy, project_id)
    if row is None:
        return ProjectAssurance()
    return ProjectAssurance(
        mode=row.mode,
        llm_method=row.llm_method,
        llm_judges=row.llm_judges,
        decider_endpoint_ids=tuple(row.decider_endpoint_ids()),
    )


def _validation_functions() -> dict[str, Callable[..., Awaitable[Any]]]:
    from app.core.validation import (
        adversarial_review,
        debate_rounds,
        dual_run,
        full_ensemble,
        self_moa,
    )

    return {
        "self_moa": self_moa,
        "adversarial_review": adversarial_review,
        "dual_run": dual_run,
        "full_ensemble": full_ensemble,
        "debate_rounds": debate_rounds,
    }


async def _run_llm(
    result: OperationalValidation,
    *,
    project_id: str,
    skill_name: str,
    agent_id: str,
    task_text: str,
    candidate: str,
    progress: Callable[[str], Awaitable[Any]] | None,
) -> None:
    from app.config import settings
    from app.core.adaptive_validation import AdaptiveSelector

    selector = AdaptiveSelector()
    method = await selector.select_method(
        project_id, skill_name, agent_id, allowed=result.plan.llm_methods
    )
    fn = _validation_functions().get(method)
    if fn is None:
        return
    if progress is not None:
        await progress(f"Validating ({method})...")
    kwargs: dict[str, Any] = {
        "prompt": task_text,
        "system": _VALIDATION_SYSTEM,
        "project_id": project_id,
    }
    if method == "adversarial_review":
        kwargs["initial_response"] = candidate
    else:
        kwargs["prompt"] = f"Task:\n{task_text}\n\nCandidate output to validate:\n{candidate}"
    if method == "full_ensemble":
        kwargs["min_responses"] = result.plan.llm_judges
    timeout = max(1, int(getattr(settings, "validation_timeout_seconds", 120)))
    val = await asyncio.wait_for(fn(**kwargs), timeout=timeout)
    actual = val.method or method
    agreement = val.consensus.agreement_score
    result.requested_method = method
    result.llm_method = actual
    result.consensus_score = agreement
    result.llm = {
        "requested_method": method,
        "actual_method": actual,
        "agreement_score": agreement,
        "kappa": val.consensus.kappa,
        "cosine_sim": val.consensus.cosine_sim,
        "confidence": val.consensus.confidence,
        "best_response": val.best_response,
        "response_count": len(val.responses),
        "route_evidence": val.metadata.get("route_evidence", []),
        "models_used": val.metadata.get("models_used", []),
        "assurance": val.metadata.get("assurance", actual),
    }
    await selector.record_outcome(
        project_id, skill_name, agent_id, actual, agreement, agreement >= 0.5
    )
    logger.info("Validation [%s]: score=%.2f", actual, agreement)
    result.hook_payload = {
        "validation_method": actual,
        "requested_validation_method": method,
        "validation_passed": agreement >= 0.5,
        "consensus_score": agreement,
        "validation_quality": agreement,
        "route_evidence": val.metadata.get("route_evidence", []),
        "models_used": val.metadata.get("models_used", []),
    }


def _question() -> Any:
    from app.core.decider.contract import Noul

    return Noul(
        "Would a careful senior UX researcher accept the candidate output as it stands, given "
        "the task and its evidence?",
        true_criterion=(
            "It answers the task, claims nothing its evidence does not support, and keeps "
            "facts, inferences and recommendations apart."
        ),
        false_criterion=(
            "It misses the task, claims more than its evidence supports, or presents inferences "
            "or recommendations as facts."
        ),
    )


async def _run_one_decider(
    endpoint_id: str, *, project_id: str, task_id: str, task_text: str, candidate: str
) -> dict[str, Any]:
    from app.core.decider.access import open_decider
    from app.core.decider.registry import DeciderUnavailableError
    from app.models.database import async_session
    from app.services.decision_trajectories import record_trajectory, scope_is_trusted

    try:
        client = await open_decider(endpoint_id, project_id)
    except DeciderUnavailableError as error:
        return {"endpoint_id": endpoint_id, "status": "not_runnable", "reason": error.reason}
    state = {"task": task_text[:_STATE_LIMIT], "candidate_output": candidate[:_STATE_LIMIT]}
    outcome = await client.decide(state, {QUESTION_ID: _question()})
    async with async_session() as session:
        row = await record_trajectory(
            session,
            outcome=outcome,
            project_id=project_id,
            subject_kind="task_output",
            subject_id=task_id,
            task_id=task_id,
            question_set_id=QUESTION_SET_ID,
            question_set_version=QUESTION_SET_VERSION,
            question_id=QUESTION_ID,
            positive_outcomes=frozenset({"true"}),
            task_family=TASK_FAMILY,
            language=UNDETERMINED_LANGUAGE,
        )
        trusted = outcome.ok and await scope_is_trusted(session, row.scope_key)
        if trusted:
            row.action = "advisory"
        await session.commit()
    return {
        "endpoint_id": endpoint_id,
        "status": outcome.status,
        "reason": outcome.reason,
        "served_model": outcome.served_model,
        "p_acceptable": outcome.answers.get(QUESTION_ID, {}).get("true"),
        "scope_trusted": trusted,
        "action": row.action,
        "trajectory_id": row.id,
    }


async def run_operational_validation(
    *,
    project_id: str,
    skill_name: str,
    agent_id: str,
    task_id: str,
    task_text: str,
    candidate: str,
    policy: ProjectAssurance | None = None,
    progress: Callable[[str], Awaitable[Any]] | None = None,
) -> OperationalValidation:
    """Run what the project's assurance mode allows on one candidate output."""
    if policy is None:
        policy = await load_project_assurance(project_id)
    result = OperationalValidation(plan=plan_validation(policy))
    if result.plan.run_llm:
        try:
            await _run_llm(
                result,
                project_id=project_id,
                skill_name=skill_name,
                agent_id=agent_id,
                task_text=task_text,
                candidate=candidate,
                progress=progress,
            )
        except Exception as exc:
            logger.debug("LLM-judge validation skipped: %s", exc)
    if result.plan.run_deciders:
        if progress is not None:
            await progress("Validating (decision models)...")
        for endpoint_id in result.plan.decider_endpoint_ids:
            try:
                result.deciders.append(
                    await _run_one_decider(
                        endpoint_id,
                        project_id=project_id,
                        task_id=task_id,
                        task_text=task_text,
                        candidate=candidate,
                    )
                )
            except Exception as exc:
                logger.debug("Decider validation failed for %s: %s", endpoint_id, exc)
                result.deciders.append(
                    {"endpoint_id": endpoint_id, "status": "not_runnable", "reason": "error"}
                )
    return result


TASK_REVIEW_LABELS = {"approved": 1, "needs_revision": 0, "rejected_after_done": 0}


async def record_assurance_review_signals(event: Any) -> None:
    """Learn from a researcher's task review (``TaskReviewEvent``); never raises.

    Labels the task's decision-model trajectories (approved = acceptable) and tells the adaptive
    selector whether the LLM method's verdict matched the review. ``system_failed`` and other
    outcomes are not human judgements of the output and teach nothing.
    """
    try:
        await _record_assurance_review_signals(event)
    except Exception as exc:
        logger.debug("Review assurance learning side effect failed: %s", exc)


async def _record_assurance_review_signals(event: Any) -> None:
    from app.core.adaptive_validation import AdaptiveSelector
    from app.core.assurance import LLM_METHODS, method_agreed_with_human
    from app.models.database import async_session
    from app.services.decision_trajectories import label_subject

    label = TASK_REVIEW_LABELS.get(getattr(event, "outcome", ""))
    if label is None or not event.task_id or not event.project_id:
        return
    async with async_session() as session:
        await label_subject(
            session,
            project_id=event.project_id,
            subject_kind="task_output",
            subject_id=event.task_id,
            label=label,
            source_id=str(event.id),
        )
        await session.commit()
    method = getattr(event, "validation_method", None)
    consensus = getattr(event, "consensus_score", None)
    if method in LLM_METHODS and consensus is not None:
        agreed = method_agreed_with_human(consensus >= 0.5, event.outcome)
        if agreed is not None:
            await AdaptiveSelector().record_human_outcome(
                event.project_id,
                event.skill_name or "",
                event.agent_id or "",
                method,
                agreed,
            )
