"""Strategic Simulation Personas — game-theory inspired participant strategies.

Implements P2 from the roadmap: enhanced participant simulation using strategies
like 'The Satisficer' (minimal effort) and 'The Skeptic' (adversarial/critical)
to test research instrument robustness.
"""

from enum import Enum
from typing import Dict, Any

class SimulationStrategy(str, Enum):
    TRUTHFUL = "truthful"      # High effort, honest responses
    SATISFICER = "satisficer"  # Low effort, short responses, "good enough"
    ADVERSARIAL = "adversarial" # Intentional edge cases, contradictory
    SKEPTIC = "skeptic"        # Highly critical, demands evidence

class ParticipantSimulationStrategy:
    """Configures model behavior based on game-theory strategy."""
    
    @staticmethod
    def get_strategy_prompt(strategy: SimulationStrategy) -> str:
        """Get the system prompt modifier for a given strategy."""
        
        prompts = {
            SimulationStrategy.TRUTHFUL: (
                "You are an ideal research participant. Provide detailed, honest, "
                "and thoughtful responses. Think aloud and share your inner reasoning."
            ),
            SimulationStrategy.SATISFICER: (
                "You are a tired participant in a hurry. Provide the shortest possible "
                "answers that still satisfy the question. Avoid detail or deep reflection."
            ),
            SimulationStrategy.ADVERSARIAL: (
                "You are testing the limits of this research tool. Provide contradictory "
                "responses, use extreme edge cases, and try to confuse the interviewer."
            ),
            SimulationStrategy.SKEPTIC: (
                "You are a highly skeptical participant. Question the interviewer's "
                "assumptions, point out flaws in the product, and demand high value "
                "before providing positive feedback."
            )
        }
        
        return prompts.get(strategy, prompts[SimulationStrategy.TRUTHFUL])

    @staticmethod
    def apply_to_context(context: Dict[str, Any], strategy: SimulationStrategy) -> Dict[str, Any]:
        """Apply strategy constraints to the simulation context."""
        context["simulation_strategy"] = strategy.value
        context["strategy_modifier"] = ParticipantSimulationStrategy.get_strategy_prompt(strategy)
        return context
