"""Confidence statistics of a decider's probability distribution.

These are the definitions TypeSafe documents for JEV (https://docs.typesafe.ai/confidence, read
2026-10-17). They describe how concentrated a distribution is; they are not calibration claims.
Istara logs the provider's value for audit and recomputes its own from calibrated probabilities.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def top_label(probabilities: Mapping[str, float]) -> tuple[str, float]:
    """Highest-probability label and its probability. Ties go to the first label in order."""
    if not probabilities:
        raise ValueError("probabilities must not be empty")
    best_label, best_p = "", -1.0
    for label, p in probabilities.items():
        if p > best_p:
            best_label, best_p = label, float(p)
    return best_label, best_p


def choice_confidence(probabilities: Sequence[float]) -> float:
    """``(p_max - 1/n) / (1 - 1/n)``: 0 for a uniform distribution, 1 for a certain one."""
    n = len(probabilities)
    if n < 2:
        raise ValueError("a choice needs at least two options")
    p_max = max(probabilities)
    return (p_max - 1.0 / n) / (1.0 - 1.0 / n)


def score_confidence(probabilities: Sequence[float]) -> float:
    """``max(0, 1 - sum_i p_i |i - m| / MAD_unif)`` over ordered levels.

    ``m`` is the most likely level (the first on ties) and ``MAD_unif`` is the mean absolute
    deviation of a uniform distribution over the levels from its centre, ``(1/n) sum_i
    |i - (n-1)/2|``. Probability on a neighbouring level costs less confidence than probability
    far away.
    """
    n = len(probabilities)
    if n < 2:
        raise ValueError("a score needs at least two levels")
    m = max(range(n), key=lambda i: (probabilities[i], -i))
    spread = sum(p * abs(i - m) for i, p in enumerate(probabilities))
    centre = (n - 1) / 2.0
    mad_uniform = sum(abs(i - centre) for i in range(n)) / n
    return max(0.0, 1.0 - spread / mad_uniform)


def noul_confidence(p_yes: float) -> float:
    """``|2p - 1|``, the choice formula for a yes/no question (JEV returns no confidence here)."""
    if not 0.0 <= p_yes <= 1.0:
        raise ValueError("p_yes must lie in [0, 1]")
    return abs(2.0 * p_yes - 1.0)
