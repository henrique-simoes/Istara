"""
Game Theory Participant Simulation — strategy models for simulating
participant behavior in UX research scenarios.

Implements bounded rationality, satisficing, social desirability bias,
and strategic response patterns derived from game theory and behavioral
economics literature.

References:
- Nash (1950): Equilibrium points in n-person games
- Simon (1956): Rational choice and the structure of environments
- Kahneman & Tversky (1979): Prospect theory
- Prisoner's Dilemma: Rapoport & Chammah (1965)
- Stag Hunt: Rousseau / Skyrms (2004)
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ParticipantStrategy(str, Enum):
    COOPERATIVE = "cooperative"
    SELFISH = "selfish"
    RECIPROCATING = "reciprocating"
    RANDOM = "random"
    SATFICING = "satisficing"
    SOCIAL_DESIRABILITY = "social_desirability"
    ADVERSARIAL = "adversarial"


class ResponseMode(str, Enum):
    HONEST = "honest"
    STRATEGIC = "strategic"
    BIASED = "biased"
    WITHHELD = "withheld"
    EXAGGERATED = "exaggerated"


@dataclass
class ParticipantProfile:
    """A simulated research participant with game-theory behavioral traits."""

    id: str
    name: str
    strategy: ParticipantStrategy
    patience: float = 0.7
    honesty_bias: float = 0.8
    social_desirability_bias: float = 0.3
    tech_savviness: float = 0.5
    engagement_level: float = 0.7
    risk_aversion: float = 0.5
    satisficing_threshold: float = 0.6

    def __post_init__(self):
        self.patience = max(0.0, min(1.0, self.patience))
        self.honesty_bias = max(0.0, min(1.0, self.honesty_bias))
        self.social_desirability_bias = max(0.0, min(1.0, self.social_desirability_bias))
        self.tech_savviness = max(0.0, min(1.0, self.tech_savviness))
        self.engagement_level = max(0.0, min(1.0, self.engagement_level))
        self.risk_aversion = max(0.0, min(1.0, self.risk_aversion))
        self.satisficing_threshold = max(0.1, min(1.0, self.satisficing_threshold))


@dataclass
class GameScenario:
    """A game-theory scenario for participant simulation."""

    id: str
    name: str
    description: str
    scenario_type: str
    payoffs: dict[str, dict[str, float]] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Result of a game-theory simulation round."""

    participant_id: str
    scenario_id: str
    strategy: str
    response_mode: str
    choice: str
    payoff: float
    honesty_score: float
    engagement_score: float
    notes: str = ""


def prisoner_dilemma_payoffs() -> dict[str, dict[str, float]]:
    """Standard Prisoner's Dilemma payoff matrix.

    T > R > P > S and 2R > T + S (Nash, 1950).
    """
    return {
        "cooperate": {"cooperate": 3.0, "defect": 0.0},
        "defect": {"cooperate": 5.0, "defect": 1.0},
    }


def stag_hunt_payoffs() -> dict[str, dict[str, float]]:
    """Stag Hunt payoff matrix (Rousseau / Skyrms, 2004).

    Coordination game — both players prefer stag but hare is safe solo.
    """
    return {
        "stag": {"stag": 4.0, "hare": 0.0},
        "hare": {"stag": 3.0, "hare": 2.0},
    }


def payoff_matrix(scenario_type: str) -> dict[str, dict[str, float]]:
    """Get payoff matrix for a scenario type."""
    matrices = {
        "prisoners_dilemma": prisoner_dilemma_payoffs(),
        "stag_hunt": stag_hunt_payoffs(),
    }
    return matrices.get(scenario_type, prisoner_dilemma_payoffs())


def choose_action(
    participant: ParticipantProfile, scenario: GameScenario, opponent_last_action: str | None = None
) -> str:
    """Choose an action based on the participant's strategy and game context.

    Implements bounded rationality: participants don't always play optimally.
    Noise is proportional to (1 - engagement_level) and (1 - patience).
    """
    payoffs = scenario.payoffs if scenario.payoffs else payoff_matrix(scenario.scenario_type)
    actions = list(payoffs.keys())

    if not actions:
        return "cooperate"

    noise = random.random() * (1 - participant.engagement_level) * (1 - participant.patience)

    if noise > 0.8:
        return random.choice(actions)

    match participant.strategy:
        case ParticipantStrategy.COOPERATIVE:
            choice = "cooperate" if "cooperate" in actions else actions[0]

        case ParticipantStrategy.SELFISH:
            dominant = _find_dominant_strategy(participant, payoffs)
            choice = dominant if dominant else ("defect" if "defect" in actions else actions[-1])

        case ParticipantStrategy.RECIPROCATING:
            if opponent_last_action:
                choice = opponent_last_action
            else:
                choice = "cooperate" if "cooperate" in actions else actions[0]

        case ParticipantStrategy.RANDOM:
            choice = random.choice(actions)

        case ParticipantStrategy.SATFICING:
            choice = _satisficing_choice(participant, payoffs, actions)

        case ParticipantStrategy.SOCIAL_DESIRABILITY:
            choice = "cooperate" if "cooperate" in actions else actions[0]
            if random.random() < participant.social_desirability_bias:
                choice = "cooperate" if "cooperate" in actions else actions[0]

        case ParticipantStrategy.ADVERSARIAL:
            choice = _find_worst_for_opponent(participant, payoffs, actions)

        case _:
            choice = random.choice(actions)

    return choice


def _find_dominant_strategy(participant: ParticipantProfile, payoffs: dict) -> str | None:
    """Find dominant strategy accounting for risk aversion."""
    if not payoffs:
        return None
    row_actions = list(payoffs.keys())
    if not row_actions:
        return None

    best = None
    best_expected = float("-inf")
    for action in row_actions:
        outcomes = list(payoffs[action].values())
        expected = sum(outcomes) / len(outcomes) if outcomes else 0
        risk_penalty = (
            participant.risk_aversion * (max(outcomes) - min(outcomes)) * 0.5 if outcomes else 0
        )
        score = expected - risk_penalty
        if score > best_expected:
            best_expected = score
            best = action
    return best


def _satisficing_choice(participant: ParticipantProfile, payoffs: dict, actions: list[str]) -> str:
    """Simon's satisficing — pick the first action above threshold."""
    for action in actions:
        outcomes = list(payoffs.get(action, {}).values())
        if outcomes:
            avg = sum(outcomes) / len(outcomes)
            if avg >= participant.satisficing_threshold * max(
                sum(list(payoffs.get(a, {}).values()))
                / max(len(list(payoffs.get(a, {}).values())), 1)
                for a in actions
                if payoffs.get(a, {})
            ):
                return action
    return actions[0] if actions else "cooperate"


def _find_worst_for_opponent(
    participant: ParticipantProfile, payoffs: dict, actions: list[str]
) -> str:
    """Adversarial strategy — minimize opponent's payoff."""
    if not payoffs:
        return actions[0] if actions else "defect"

    opponent_actions = set()
    for action_data in payoffs.values():
        opponent_actions.update(action_data.keys())

    worst_action = actions[0]
    min_opponent_max = float("inf")
    for action in actions:
        opp_vals = list(payoffs.get(action, {}).values())
        opp_max = max(opp_vals) if opp_vals else 0
        if opp_max < min_opponent_max:
            min_opponent_max = opp_max
            worst_action = action
    return worst_action


def simulate_response_mode(participant: ParticipantProfile) -> ResponseMode:
    """Determine how a participant responds based on behavioral traits."""
    r = random.random()
    if r < participant.honesty_bias * 0.7:
        return ResponseMode.HONEST
    if r < participant.honesty_bias * 0.7 + participant.social_desirability_bias * 0.5:
        return ResponseMode.BIASED
    if r < participant.honesty_bias * 0.7 + participant.social_desirability_bias * 0.5 + 0.15:
        return ResponseMode.STRATEGIC
    if r < 0.95:
        return ResponseMode.EXAGGERATED
    return ResponseMode.WITHHELD


def generate_participant_cohort(n: int, scenario_type: str = "mixed") -> list[ParticipantProfile]:
    """Generate a diverse cohort of simulated participants."""
    strategies = list(ParticipantStrategy)
    if scenario_type == "mixed":
        weights = [0.3, 0.1, 0.2, 0.1, 0.15, 0.1, 0.05]
    elif scenario_type == "adversarial":
        weights = [0.1, 0.3, 0.1, 0.05, 0.1, 0.05, 0.3]
    elif scenario_type == "cooperative":
        weights = [0.5, 0.05, 0.25, 0.05, 0.1, 0.05, 0.0]
    else:
        weights = [1 / len(strategies)] * len(strategies)

    participants = []
    names = [
        "Alex",
        "Jordan",
        "Sam",
        "Casey",
        "Morgan",
        "Riley",
        "Taylor",
        "Quinn",
        "Avery",
        "Blake",
        "Cameron",
        "Drew",
        "Emery",
        "Finley",
        "Harper",
        "Kai",
    ]
    for i in range(n):
        strategy = random.choices(strategies, weights=weights, k=1)[0]
        participants.append(
            ParticipantProfile(
                id=f"P{i + 1:02d}",
                name=random.choice(names),
                strategy=strategy,
                patience=round(random.uniform(0.3, 1.0), 2),
                honesty_bias=round(random.uniform(0.4, 1.0), 2),
                social_desirability_bias=round(random.uniform(0.1, 0.7), 2),
                tech_savviness=round(random.uniform(0.2, 0.9), 2),
                engagement_level=round(random.uniform(0.3, 1.0), 2),
                risk_aversion=round(random.uniform(0.2, 0.9), 2),
                satisficing_threshold=round(random.uniform(0.4, 0.8), 2),
            )
        )
    return participants


def run_simulation_round(
    participants: list[ParticipantProfile],
    scenario: GameScenario,
    rounds: int = 10,
) -> list[SimulationResult]:
    """Run a multi-round game-theory simulation with a cohort."""
    results: list[SimulationResult] = []
    last_actions: dict[str, str] = {}

    for round_num in range(rounds):
        for p in participants:
            opponent_action = last_actions.get(f"opponent_{p.id}", None)
            choice = choose_action(p, scenario, opponent_action)
            payoffs = (
                scenario.payoffs if scenario.payoffs else payoff_matrix(scenario.scenario_type)
            )
            opp_choices = list(payoffs.get(choice, {}).keys())
            payoff = (
                payoffs.get(choice, {}).get(opponent_action or "cooperate", 0.0)
                if opp_choices
                else 0.0
            )
            response_mode = simulate_response_mode(p)

            result = SimulationResult(
                participant_id=p.id,
                scenario_id=scenario.id,
                strategy=p.strategy.value,
                response_mode=response_mode.value,
                choice=choice,
                payoff=payoff,
                honesty_score=round(p.honesty_bias * (1 - p.social_desirability_bias), 3),
                engagement_score=round(
                    p.engagement_level * (1 - max(0, round_num / rounds - p.patience)), 3
                ),
                notes=f"Round {round_num + 1}/{rounds}",
            )
            results.append(result)
            last_actions[p.id] = choice

    return results
