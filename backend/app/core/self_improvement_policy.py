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
) -> LearningSignal:
    """Return a spine-aware signal for Memento/ReasoningBank/telemetry.

    A tool can execute successfully while still producing only provisional
    research output.  Memento Skills may learn strongly only after verification
    or Research Spine reportability gates succeed.
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

    return LearningSignal(
        execution_success=True,
        verification_success=False,
        report_allowed=False,
        learning_success=False,
        research_quality_score=0.45,
        learning_state="candidate_provisional_output",
    )
