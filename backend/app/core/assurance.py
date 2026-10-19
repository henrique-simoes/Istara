"""Project assurance modes: which evaluators validate a candidate output.

Researchers choose between LLM-as-judge methods (Self-MoA, two judges, an ensemble of three or more,
adversarial review, debate), typed decision models, both, or neither. The choice governs operational
validation of skill outputs only. In every mode the task still ends In Review and only a human moves
it to Done, and the Research Spine's coding-run reliability gate (three or more distinct model
coders) is unchanged (owner decision DEC-6).

Without a stored policy the mode is ``auto``, which is exactly the behaviour before modes existed.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field

MODES = ("auto", "llm_judges", "decision_models", "both", "none")
LLM_METHODS = ("self_moa", "dual_run", "full_ensemble", "adversarial_review", "debate_rounds")
MIN_ENSEMBLE_JUDGES = 3
MAX_ENSEMBLE_JUDGES = 7


@dataclass(frozen=True)
class ProjectAssurance:
    """A project's choice. ``llm_method`` is ``auto`` or one of :data:`LLM_METHODS`."""

    mode: str = "auto"
    llm_method: str = "auto"
    llm_judges: int = MIN_ENSEMBLE_JUDGES
    decider_endpoint_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"unknown assurance mode {self.mode!r}")
        if self.llm_method != "auto" and self.llm_method not in LLM_METHODS:
            raise ValueError(f"unknown LLM judge method {self.llm_method!r}")
        if not MIN_ENSEMBLE_JUDGES <= self.llm_judges <= MAX_ENSEMBLE_JUDGES:
            raise ValueError(
                f"llm_judges must be in [{MIN_ENSEMBLE_JUDGES}, {MAX_ENSEMBLE_JUDGES}]"
            )
        cleaned = tuple(dict.fromkeys(e.strip() for e in self.decider_endpoint_ids if e.strip()))
        object.__setattr__(self, "decider_endpoint_ids", cleaned)


@dataclass(frozen=True)
class ValidationPlan:
    """What operational validation will run for one task."""

    mode: str
    run_llm: bool
    llm_methods: tuple[str, ...] = ()
    llm_judges: int = MIN_ENSEMBLE_JUDGES
    run_deciders: bool = False
    decider_endpoint_ids: tuple[str, ...] = ()
    unvalidated_reason: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def validates(self) -> bool:
        return self.run_llm or self.run_deciders


def _llm_methods(policy: ProjectAssurance) -> tuple[str, ...]:
    return LLM_METHODS if policy.llm_method == "auto" else (policy.llm_method,)


def plan_validation(policy: ProjectAssurance | None) -> ValidationPlan:
    """Turn a project's choice into the evaluators to run."""
    policy = policy or ProjectAssurance()
    deciders = policy.decider_endpoint_ids
    if policy.mode == "none":
        return ValidationPlan("none", run_llm=False, unvalidated_reason="assurance_disabled")
    if policy.mode == "decision_models":
        if not deciders:
            return ValidationPlan(
                "decision_models", run_llm=False, unvalidated_reason="no_decider_configured"
            )
        return ValidationPlan(
            "decision_models", run_llm=False, run_deciders=True, decider_endpoint_ids=deciders
        )
    llm = _llm_methods(policy)
    if policy.mode == "llm_judges":
        return ValidationPlan(
            "llm_judges", run_llm=True, llm_methods=llm, llm_judges=policy.llm_judges
        )
    notes = [] if deciders or policy.mode == "auto" else ["no_decider_configured"]
    return ValidationPlan(
        policy.mode,
        run_llm=True,
        llm_methods=llm,
        llm_judges=policy.llm_judges,
        run_deciders=bool(deciders),
        decider_endpoint_ids=deciders,
        notes=notes,
    )


def method_agreed_with_human(validation_passed: bool, review_outcome: str) -> bool | None:
    """Whether a validation verdict matched the researcher's decision (the AV-1 learning signal).

    Approval means the output was acceptable; sending it back means it was not. ``system_failed``
    and unknown outcomes say nothing about the validation and give no signal.
    """
    acceptable = {"approved": True, "needs_revision": False, "rejected_after_done": False}.get(
        review_outcome
    )
    if acceptable is None:
        return None
    return validation_passed == acceptable


def thompson_choice(
    allowed: Sequence[str],
    counts: dict[str, tuple[int, int]],
    rng: random.Random,
) -> str | None:
    """Beta-Bernoulli Thompson sampling over human-verified (agree, disagree) counts.

    Returns None when no allowed method has any human-verified outcome yet, so the caller falls
    back to its compute-aware default instead of learning from nothing.
    """
    candidates = [m for m in allowed if sum(counts.get(m, (0, 0))) > 0]
    if not candidates:
        return None
    draws = {
        method: rng.betavariate(1 + counts[method][0], 1 + counts[method][1])
        for method in candidates
    }
    return max(candidates, key=lambda method: (draws[method], -allowed.index(method)))
