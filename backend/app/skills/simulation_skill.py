"""Simulate Participant Response Skill — makes game-theory models user-facing.

Implements P2 from the roadmap: a skill that allows human researchers to 
test their questions against different participant archetypes (Satisficer, Skeptic, etc.)
before deploying real research.
"""

import logging
from typing import Any, Optional

from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType
from app.core.participant_simulation import (
    ParticipantProfile, 
    ParticipantStrategy, 
    GameScenario,
    run_simulation_round
)

logger = logging.getLogger(__name__)

class SimulationSkill(BaseSkill):
    @property
    def name(self) -> str: return "simulate-participant"
    @property
    def display_name(self) -> str: return "Game Theory Participant Simulation"
    @property
    def description(self) -> str: return "Test research designs against game-theory personas (Skeptic, Satisficer, etc.)."
    @property
    def phase(self) -> SkillPhase: return SkillPhase.DEFINE
    @property
    def skill_type(self) -> SkillType: return SkillType.QUANTITATIVE

    async def plan(self, skill_input: SkillInput) -> dict:
        return {
            "steps": ["Initialize participant cohort", "Define game-theory scenario", "Run multi-round simulation"],
            "estimated_duration_minutes": 2
        }

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        """Run a simulation based on user question/survey."""
        logger.info("SimulationSkill executing game-theory participant test...")
        
        # 1. Setup participants (Skeptic vs Satisficer vs Truthful)
        p1 = ParticipantProfile(id="P1", name="The Skeptic", strategy=ParticipantStrategy.ADVERSARIAL, patience=0.4)
        p2 = ParticipantProfile(id="P2", name="The Satisficer", strategy=ParticipantStrategy.SATFICING, engagement_level=0.3)
        p3 = ParticipantProfile(id="P3", name="The Idealist", strategy=ParticipantStrategy.COOPERATIVE, honesty_bias=1.0)
        
        # 2. Setup scenario based on user input
        scenario = GameScenario(
            id="user_test",
            name="Research Instrument Test",
            description=f"Testing robustness of: {skill_input.user_context[:100]}",
            scenario_type="prisoners_dilemma" # Use as base logic for response effort
        )
        
        # 3. Run simulation
        results = run_simulation_round([p1, p2, p3], scenario, rounds=5)
        
        # 4. Synthesize report
        summary_lines = ["### Simulation Results", ""]
        for res in results:
            summary_lines.append(f"- **{res.participant_id} ({res.strategy})**: Mode: {res.response_mode}, Choice: {res.choice}")
            
        return SkillOutput(
            success=True,
            summary="Participant simulation completed across 3 distinct archetypes.",
            artifacts={"simulation_report.md": "\n".join(summary_lines)},
            suggestions=["Refine the prompt to reduce social desirability bias in 'The Idealist'.", "Add more constraints to prevent low-effort responses from 'The Satisficer'."]
        )
