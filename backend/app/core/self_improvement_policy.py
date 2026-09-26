"""Research Spine policy helpers for governed self-improvement.

Self-improvement signals may tune process routing, skill memory, and proposal
queues, but they are not report evidence.  These helpers keep execution
success separate from verified research quality so ReAct/manual runs cannot
train Memento Skills from provisional output.
"""

from __future__ import annotations

from dataclasses import dataclass

SELF_IMPROVEMENT_GOVERNANCE_CONTRACT = {
    "telemetry": "observation_only",
    "reasoning_bank": "process_memory_only",
    "memento_skills": "validated_skill_memory_only",
    "autoresearch": "sandboxed_proposals_only",
    "meta_hyperagent": "project_scoped_governed_proposals_only",
    "self_evolution": "governed_promotion_only",
    "rag": "exact_evidence_retrieval_only",
    "graphrag": "synthesis_traceability_only",
    "prompt_rag": "context_assist_only",
    "llmlingua": "protected_context_compression_only",
    "report_evidence": False,
    "can_bypass_research_spine": False,
}


@dataclass(frozen=True)
class LearningSignal:
    """Separated outcome signal for governed learning surfaces."""

    execution_success: bool
    verification_success: bool
    report_allowed: bool
    learning_success: bool
    research_quality_score: float
    learning_state: str

    def to_dict(self) -> dict:
        return {
            "execution_success": self.execution_success,
            "verification_success": self.verification_success,
            "report_allowed": self.report_allowed,
            "learning_success": self.learning_success,
            "research_quality_score": self.research_quality_score,
            "learning_state": self.learning_state,
        }


def learning_signal_for_research_output(
    *,
    execution_success: bool,
    verification_success: bool = False,
    report_allowed: bool = False,
    self_verified: bool | None = None,
) -> LearningSignal:
    """Return a spine-aware signal for Memento/ReasoningBank/telemetry.

    A tool can execute successfully while still producing only provisional research output.
    Memento Skills may learn strongly only from INDEPENDENT verification (human-approved review)
    or Research Spine reportability. ``self_verified`` is the agent's own reflection or heuristic
    check of its output: the same system grading itself. A successful-but-wrong run passes it
    (measurement 6), so it yields a provisional, undecided signal, never a strong positive one.
    ``self_verified=False`` (the self-check ran and rejected the output) stays a weak failure.
    ``None`` means no self-check ran. ``verification_success`` means independent verification.
    """

    if not execution_success:
        return LearningSignal(
            execution_success=False,
            verification_success=False,
            report_allowed=False,
            learning_success=False,
            research_quality_score=0.2,
            learning_state="failed_execution",
        )

    if verification_success or report_allowed:
        return LearningSignal(
            execution_success=True,
            verification_success=bool(verification_success),
            report_allowed=bool(report_allowed),
            learning_success=True,
            research_quality_score=0.85 if verification_success else 0.8,
            learning_state="verified_research_output"
            if verification_success
            else "reportable_research_output",
        )

    if self_verified is False:
        return LearningSignal(
            execution_success=True,
            verification_success=False,
            report_allowed=False,
            learning_success=False,
            research_quality_score=0.3,
            learning_state="self_verification_failed",
        )

    if self_verified:
        return LearningSignal(
            execution_success=True,
            verification_success=False,
            report_allowed=False,
            learning_success=False,
            research_quality_score=0.55,
            learning_state="self_verified_provisional",
        )

    return LearningSignal(
        execution_success=True,
        verification_success=False,
        report_allowed=False,
        learning_success=False,
        research_quality_score=0.45,
        learning_state="candidate_provisional_output",
    )


def is_undecided_learning_state(signal: LearningSignal) -> bool:
    """True when nothing independent has judged the output yet (neither success nor failure).

    Undecided outcomes must not move success or failure counts; human review decides later.
    """
    return signal.learning_state in {"self_verified_provisional", "candidate_provisional_output"}
