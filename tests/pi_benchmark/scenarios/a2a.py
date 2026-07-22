"""A2A pack — agent-to-agent collaboration scenarios (task B0-5, axis 10).

Collaboration, debate, and delegation-chain scenarios that exercise multi-agent rounds,
inter-agent messages, and dominance analysis. Like the spine pack these are behavioural
and declare ``min_tier="T2"``; they yield records only behind owner gate G1.
"""

from __future__ import annotations

from .base import Scenario

_A2A_SCENARIOS = (
    ("a2a.debate_report", "Two agents debate a recommendation, then converge on a report"),
    ("a2a.delegation_chain", "Lead delegates subtasks down a chain and reconciles results"),
    ("a2a.collaboration_handoff", "Agents hand off partial findings and preserve evidence handles"),
)


def scenarios() -> tuple[Scenario, ...]:
    return tuple(
        Scenario(
            id=scenario_id,
            title=title,
            pack="a2a",
            min_tier="T2",
            contract_check=None,
            tags=("a2a", "behavioural"),
        )
        for scenario_id, title in _A2A_SCENARIOS
    )
