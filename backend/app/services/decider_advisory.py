"""One advisory seam for decision models at the integration sites (CF-SPEC-1, Phase 8, I4–I14).

A site describes one closed question about one subject; this module asks the project's decider,
records a shadow trajectory (so the answer can be calibrated against later human labels), and
returns the answer as **advice**. It is the only way those sites reach a decider.

Rules every caller relies on:

* It does nothing unless the project's assurance mode includes decision models and names at least
  one decider (no call, no egress, no cost). Hosted deciders still need the project's opt-in
  (``open_decider``).
* It never raises. Any failure returns ``None`` and the site keeps its existing behaviour.
* Choice questions are asked in both option orders and merged (first-option bias, research doc
  §3). The answer says whether its scope is ``trusted``; untrusted advice is for the record only.
* Advice never accepts, rejects or promotes research evidence, never replaces a deterministic
  floor, and may only make a guard *more* cautious (I14).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.decider.contract import NOUL_TRUE, Choice, Noul, Score

logger = logging.getLogger(__name__)

ADVISORY_MODES = frozenset({"decision_models", "both"})
QUESTION_ID = "advice"


@dataclass(frozen=True)
class Advice:
    """A decider's answer to one site question, as recorded."""

    site: str
    endpoint_id: str
    served_model: str
    distribution: dict[str, float]
    top: str
    trusted: bool
    trajectory_id: str
    order_flip_agree: bool | None = None

    @property
    def p_true(self) -> float | None:
        """For yes/no questions, the probability of yes."""
        return self.distribution.get(NOUL_TRUE)

    def as_dict(self) -> dict[str, Any]:
        """Content-free summary for API payloads and metadata (no state, no prompts)."""
        return {
            "site": self.site,
            "endpoint_id": self.endpoint_id,
            "served_model": self.served_model,
            "distribution": dict(self.distribution),
            "top": self.top,
            "trusted": self.trusted,
            "trajectory_id": self.trajectory_id,
            "order_flip_agree": self.order_flip_agree,
            "advisory_only": True,
        }


async def _deciders(project_id: str) -> tuple[str, ...]:
    from app.services.assurance_policies import load_project_assurance

    policy = await load_project_assurance(project_id)
    if policy.mode not in ADVISORY_MODES:
        return ()
    return policy.decider_endpoint_ids


async def _ask(client: Any, state: Any, question: Choice | Score | Noul) -> tuple[Any, Any, Any]:
    """``(outcome, distribution, order_flip_agree)``; distribution is None when not runnable."""
    from app.core.decider.contract import REVERSED_SUFFIX, with_reversed_choices
    from app.core.decision.decision_rule import merge_order_flip

    questions = with_reversed_choices({QUESTION_ID: question})
    outcome = await client.decide(state, questions)
    if not outcome.ok:
        return outcome, None, None
    if isinstance(question, Choice):
        merged = merge_order_flip(
            outcome.answers[QUESTION_ID], outcome.answers[QUESTION_ID + REVERSED_SUFFIX]
        )
        return outcome, dict(merged.merged), merged.agree
    return outcome, dict(outcome.answers[QUESTION_ID]), None


async def advise(
    project_id: str,
    *,
    site: str,
    subject_kind: str,
    subject_id: str,
    state: Any,
    question: Choice | Score | Noul,
    question_set_version: str = "v1",
    positive_outcomes: frozenset[str] = frozenset({NOUL_TRUE}),
    task_family: str | None = None,
    language: str = "und",
    task_id: str | None = None,
) -> Advice | None:
    """Ask the project's first usable decider; record a shadow trajectory; return the advice."""
    try:
        return await _advise(
            project_id,
            site=site,
            subject_kind=subject_kind,
            subject_id=subject_id,
            state=state,
            question=question,
            question_set_version=question_set_version,
            positive_outcomes=positive_outcomes,
            task_family=task_family or site,
            language=language,
            task_id=task_id,
        )
    except Exception as exc:  # advice must never break the site
        logger.debug("Decider advice unavailable at %s: %s", site, type(exc).__name__)
        return None


async def _advise(
    project_id: str,
    *,
    site: str,
    subject_kind: str,
    subject_id: str,
    state: Any,
    question: Choice | Score | Noul,
    question_set_version: str,
    positive_outcomes: frozenset[str],
    task_family: str,
    language: str,
    task_id: str | None,
) -> Advice | None:
    if not str(project_id or "").strip():
        return None
    endpoint_ids = await _deciders(project_id)
    if not endpoint_ids:
        return None
    from app.core.decider.access import open_decider
    from app.core.decider.registry import DeciderUnavailableError
    from app.models.database import async_session
    from app.services.decision_trajectories import record_trajectory, scope_is_trusted

    for endpoint_id in endpoint_ids:
        try:
            client = await open_decider(endpoint_id, project_id)
        except DeciderUnavailableError:
            continue
        outcome, distribution, flip = await _ask(client, state, question)
        async with async_session() as session:
            row = await record_trajectory(
                session,
                outcome=outcome,
                project_id=project_id,
                subject_kind=subject_kind,
                subject_id=subject_id,
                question_set_id=f"advisory.{site}",
                question_set_version=question_set_version,
                question_id=QUESTION_ID,
                positive_outcomes=positive_outcomes,
                task_family=task_family,
                language=language,
                task_id=task_id,
                calibrated=distribution,
                order_flip_agree=flip,
            )
            trusted = await scope_is_trusted(session, row.scope_key) if distribution else False
            await session.commit()
        if distribution is None:
            continue
        return Advice(
            site=site,
            endpoint_id=endpoint_id,
            served_model=outcome.served_model or "",
            distribution=distribution,
            top=max(distribution, key=lambda name: distribution[name]),
            trusted=trusted,
            trajectory_id=row.id,
            order_flip_agree=flip,
        )
    return None


async def audit_trajectory_with_decider(
    project_id: str,
    task_id: str,
    transitions: list[Any],
    tools: dict[str, Any],
) -> dict[str, Any]:
    """I8: the deterministic per-transition audit plus, when the project opted in, a decision
    model's yes/no on whether each observation supports the agent's next step (advice only).
    """
    from app.core.decision.trajectory_audit import audit_summary, audit_trajectory

    findings = audit_trajectory(transitions, tools)
    summary = audit_summary(findings)
    supported: list[float | None] = []
    for index, step in enumerate(transitions):
        if not step.next_step or not (step.observation or "").strip():
            supported.append(None)
            continue
        advice = await advise(
            project_id,
            site="agent.trajectory",
            subject_kind="agent_transition",
            subject_id=f"{task_id}:{index}"[:36],
            task_id=task_id,
            state={
                "tool": step.tool,
                "observation": step.observation[:4000],
                "next_step": step.next_step[:2000],
            },
            question=Noul(
                "Does the tool observation support what the agent says or does next?",
                true_criterion="The next step follows from the observation.",
                false_criterion="The next step ignores, contradicts or goes beyond it.",
            ),
        )
        supported.append(advice.p_true if advice is not None else None)
    return {
        **summary,
        "findings": [{"index": f.index, "tool": f.tool, "flags": f.flags} for f in findings],
        "decider_supports_next_step": supported,
    }
