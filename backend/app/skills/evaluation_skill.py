"""Formal Evaluation Skill — standalone LLM-as-Judge framework.

Implements P2 from the roadmap: a user-facing evaluation skill that benchmarks
research quality using multi-model consensus and adversarial review.
"""

import logging
from typing import Any, Optional

from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType
from app.core import validation

logger = logging.getLogger(__name__)

class EvaluationSkill(BaseSkill):
    @property
    def name(self) -> str: return "evaluate-research"
    @property
    def display_name(self) -> str: return "Evaluate Research Quality"
    @property
    def description(self) -> str: return "LLM-as-Judge framework benchmarking research outputs."
    @property
    def phase(self) -> SkillPhase: return SkillPhase.DELIVER
    @property
    def skill_type(self) -> SkillType: return SkillType.MIXED

    async def plan(self, skill_input: SkillInput) -> dict:
        return {
            "steps": ["Adversarial review round", "Multi-model ensemble scoring", "Consensus synthesis"],
            "estimated_duration_minutes": 5
        }

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        """Evaluate the provided research content."""
        content = skill_input.user_context or ""
        logger.info("EvaluationSkill executing LLM-as-Judge benchmark...")
        
        # 1. Run Adversarial Review (one model critiques the content)
        adv_result = await validation.adversarial_review(
            prompt="Critique this research output for methodological rigor, evidence traceability, and actionable clarity.",
            initial_response=content,
            system="You are a senior UX research auditor."
        )
        
        # 2. Run Full Ensemble (3 models provide independent scores)
        ensemble_prompt = (
            f"Rate the following research output on a scale of 1-10 for:\n"
            f"1. Rigor\n2. Clarity\n3. Evidence strength\n\nContent:\n{content}\n\n"
            f"Provide scores and a brief justification."
        )
        ens_result = await validation.full_ensemble(
            prompt=ensemble_prompt,
            system="You are a research quality rater."
        )
        
        # 3. Combine results
        combined_report = (
            f"## Quality Audit Report\n\n"
            f"**Consensus Score**: {ens_result.consensus.agreement_score:.2f}\n"
            f"**Inter-Rater Reliability (Kappa)**: {ens_result.consensus.kappa or 'N/A'}\n\n"
            f"### Adversarial Critique\n{adv_result.metadata.get('review_text')}\n\n"
            f"### Unified Quality Benchmark\n{ens_result.best_response}"
        )
        
        return SkillOutput(
            success=True,
            summary="Research quality evaluation completed.",
            artifacts={"evaluation_report.md": combined_report}
        )
