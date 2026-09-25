"""Statistics for the measurement harnesses: graded ranking metrics and paired inference.

* nDCG with graded gains 2^g - 1 (Järvelin & Kekäläinen, TOIS 2002).
* Percentile bootstrap intervals for a mean (Efron & Tibshirani 1993).
* Two-sided paired randomization test by sign flips (Smucker, Allan & Carterette, CIKM 2007).
* Holm-Bonferroni step-down adjustment for a family of comparisons (Holm 1979).
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def dcg(grades: Sequence[int], k: int) -> float:
    return sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(grades[:k]))


def ndcg(grades: Sequence[int], ideal: Sequence[int], k: int) -> float:
    best = dcg(ideal, k)
    return dcg(grades, k) / best if best > 0 else 0.0


def bootstrap_ci(
    values: Sequence[float], *, resamples: int = 10_000, seed: int = 20260925, alpha: float = 0.05
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(resamples))
    low = means[int((alpha / 2) * resamples)]
    high = means[min(resamples - 1, int((1 - alpha / 2) * resamples))]
    return (low, high)


def paired_randomization_test(
    a: Sequence[float], b: Sequence[float], *, permutations: int = 20_000, seed: int = 20260925
) -> float:
    """Two-sided p-value for mean(a - b) != 0, by random sign flips of per-question differences."""
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    if not diffs:
        return 1.0
    observed = abs(sum(diffs) / len(diffs))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(permutations):
        flipped = sum(d if rng.random() < 0.5 else -d for d in diffs) / len(diffs)
        if abs(flipped) >= observed - 1e-12:
            extreme += 1
    return (extreme + 1) / (permutations + 1)


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni step-down adjustment for a family of comparisons."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted


def summarize(per_question: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    metrics = next(iter(per_question.values())).keys() if per_question else []
    out: dict[str, dict[str, float]] = {}
    for metric in metrics:
        values = [row[metric] for row in per_question.values()]
        low, high = bootstrap_ci(values)
        out[metric] = {
            "mean": round(sum(values) / len(values), 4),
            "ci95_low": round(low, 4),
            "ci95_high": round(high, 4),
        }
    return out
