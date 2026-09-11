"""Spine pack — full research-validity lifecycle scenarios (task B0-5).

Each scenario drives a task end-to-end across the research spine (Sources → Evidence →
… → In Review → Done → Reports, AGENTS.md) on a pinned document-corpus subset. These are
*behavioural* scenarios: they only yield meaningful records once a live engine executes
them, so they declare ``min_tier="T2"`` and carry no offline contract check. At T0/T1 the
runner records them ``not_runnable`` with a typed reason (never silently dropped), which
keeps the pack visible in every denominator ahead of owner gate G1.
"""

from __future__ import annotations

from .base import Scenario

# Pinned corpus subset each scenario draws its byte-identical fixtures from. Both engine
# arms of a pair share the same inputs, so fixture identity holds by construction.
CORPUS_SUBSET = ("tests/document_corpus/canonical",)

_SPINE_SCENARIOS = (
    (
        "spine.backlog_to_review",
        "Backlog task carried through define/develop/deliver to In Review",
    ),
    (
        "spine.evidence_grounding",
        "Evidence units stay source-grounded through reconciliation",
    ),
    (
        "spine.provisional_gate",
        "Provisional atoms cannot be reported until Done gates accept them",
    ),
    ("spine.report_generation", "Accepted facts/insights flow into a governed report"),
)


def scenarios() -> tuple[Scenario, ...]:
    return tuple(
        Scenario(
            id=scenario_id,
            title=title,
            pack="spine",
            min_tier="T2",
            contract_check=None,
            tags=("research-spine", "behavioural"),
        )
        for scenario_id, title in _SPINE_SCENARIOS
    )
