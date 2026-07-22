"""Scenario data model shared by every pack (task B0-5).

A :class:`Scenario` is a pure, engine-agnostic definition. It declares its pack, the
lowest determinism tier it can run at (``min_tier``), and — for tiers that need no live
model — a deterministic *contract check* that yields a stable pass/fail outcome class.
The check is a plain callable over already-loaded data, so it is safe at T0 and
reproducible across repeats of the same seed (acceptance A5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# Determinism tiers, ordered lowest → highest (master plan §10.1.2). A scenario whose
# ``min_tier`` is above the requested tier is recorded ``not_runnable`` rather than
# silently skipped (winning plan §2.2 principle 7).
TIER_ORDER: tuple[str, ...] = ("T0", "T1", "T2", "T3")


def tier_at_least(requested: str, minimum: str) -> bool:
    """True iff ``requested`` tier is at or above ``minimum`` in :data:`TIER_ORDER`."""
    return TIER_ORDER.index(requested) >= TIER_ORDER.index(minimum)


@dataclass(frozen=True)
class DeterministicResult:
    """Outcome of a scenario's offline contract check.

    ``outcome_class`` is the stable label compared across seed repeats (acceptance A5:
    "deterministic outcome classes match across repeats of the same seed"). ``detail``
    is diagnostic only and never enters the equality check.
    """

    passed: bool
    outcome_class: str
    detail: dict[str, Any] = field(default_factory=dict)


# A contract check receives the resolved engine label ("pi"|"legacy") and the seed, and
# returns a :class:`DeterministicResult`. It must be pure and offline.
ContractCheck = Callable[[str, int], DeterministicResult]


@dataclass(frozen=True)
class Scenario:
    """One engine-agnostic benchmark scenario definition."""

    id: str
    title: str
    pack: str
    # Lowest tier this scenario can execute at. Canonical contract scenarios run offline
    # from T0; spine/a2a behavioural scenarios need a live engine, so they declare T2.
    min_tier: str = "T0"
    # Deterministic offline check; None means the scenario has no tier-<T2 contract check
    # (it only yields records once a live engine runs it, gated behind G1).
    contract_check: ContractCheck | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.min_tier not in TIER_ORDER:
            raise ValueError(f"scenario {self.id!r}: invalid min_tier {self.min_tier!r}")
        if not self.id:
            raise ValueError("scenario id must be non-empty")


def deterministic_check_result(passed: bool, outcome_class: str, **detail: Any) -> DeterministicResult:
    """Ergonomic constructor used by pack modules."""
    return DeterministicResult(passed=passed, outcome_class=outcome_class, detail=detail)
