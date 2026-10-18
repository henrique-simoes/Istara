"""Calibration drift for a trusted decider scope (one-sided CUSUM on Brier contributions).

A scope earned trust with some held-out Brier score. New human labels keep arriving; if the
decider's per-item squared error drifts upward (a provider update, a new kind of research data), a
one-sided CUSUM (Page 1954) crosses its threshold and the scope returns to shadow mode. Drift
detection only ever removes routing power; it never grants it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DriftResult:
    drifted: bool
    statistic: float
    alarm_index: int | None
    reference: float


def brier_contribution(p_positive: float, label: int) -> float:
    """Binary Brier contribution of one labelled verdict, ``(p - y)^2``."""
    return (p_positive - (1.0 if label else 0.0)) ** 2


def cusum_upward(
    contributions: Sequence[float],
    reference: float,
    *,
    slack: float = 0.05,
    threshold: float = 1.5,
) -> DriftResult:
    """Page's CUSUM for an upward shift: ``S_t = max(0, S_{t-1} + x_t - reference - slack)``.

    ``reference`` is the Brier score the scope was trusted at. ``slack`` ignores shifts smaller
    than itself; ``threshold`` trades detection delay against false alarms.
    """
    if threshold <= 0 or slack < 0:
        raise ValueError("threshold must be positive and slack non-negative")
    statistic = 0.0
    for index, value in enumerate(contributions):
        statistic = max(0.0, statistic + value - reference - slack)
        if statistic > threshold:
            return DriftResult(True, statistic, index, reference)
    return DriftResult(False, statistic, None, reference)
