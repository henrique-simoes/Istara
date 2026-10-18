"""Keep-or-revert statistics for autoresearch experiments.

A candidate is kept only when the 95% Welch interval on (candidate mean - incumbent mean) lies above
the minimum improvement, with at least two samples on each side, and only after an independent
confirmation block passes the same test. Comparing a candidate with a single baseline sample, or
with the best noisy score seen so far, accepts noise as improvement (audit findings AR-1, AR-2).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

MIN_SAMPLES = 2
# Two-sided 95% Student t critical values t_{0.975, df} for df = 1..30; normal beyond.
# fmt: off
_T975 = (
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
)
# fmt: on


def t_critical_975(df: float) -> float:
    """t_{0.975} for (possibly fractional) degrees of freedom, conservatively rounded down."""
    if df < 1:
        raise ValueError("degrees of freedom must be at least 1")
    whole = int(math.floor(df))
    return _T975[whole - 1] if whole <= len(_T975) else 1.96


@dataclass(frozen=True)
class Comparison:
    delta: float
    low: float
    high: float
    df: float
    incumbent_mean: float
    candidate_mean: float


def welch_interval(incumbent: Sequence[float], candidate: Sequence[float]) -> Comparison:
    """95% Welch-Satterthwaite interval for mean(candidate) - mean(incumbent)."""
    if len(incumbent) < MIN_SAMPLES or len(candidate) < MIN_SAMPLES:
        raise ValueError(f"need at least {MIN_SAMPLES} samples on each side")
    mean_i, mean_c = statistics.fmean(incumbent), statistics.fmean(candidate)
    var_i = statistics.variance(incumbent) / len(incumbent)
    var_c = statistics.variance(candidate) / len(candidate)
    delta = mean_c - mean_i
    se2 = var_i + var_c
    if se2 == 0:
        return Comparison(delta, delta, delta, float("inf"), mean_i, mean_c)
    denominator = 0.0
    if var_i:
        denominator += var_i**2 / (len(incumbent) - 1)
    if var_c:
        denominator += var_c**2 / (len(candidate) - 1)
    df = se2**2 / denominator
    half = t_critical_975(df) * math.sqrt(se2)
    return Comparison(delta, delta - half, delta + half, df, mean_i, mean_c)


def keep_decision(
    incumbent: Sequence[float], candidate: Sequence[float], min_delta: float
) -> tuple[bool, str, Comparison | None]:
    """Keep when the whole interval clears ``min_delta``; explain every refusal."""
    if len(incumbent) < MIN_SAMPLES or len(candidate) < MIN_SAMPLES:
        return False, f"fewer than {MIN_SAMPLES} samples on a side", None
    comparison = welch_interval(incumbent, candidate)
    if comparison.delta < min_delta:
        return False, f"delta {comparison.delta:.4f} below minimum {min_delta:.4f}", comparison
    if comparison.low < min_delta:
        return (
            False,
            f"95% CI lower bound {comparison.low:.4f} does not clear minimum {min_delta:.4f}",
            comparison,
        )
    return True, "95% CI lies above the minimum improvement", comparison
