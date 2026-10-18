"""Calibration of decider probabilities (thesis Eq. 6, 9, 10).

Every estimator accepts optional per-item weights. Istara labels a blind random audit sample of the
items a decider did not route, so labelled items have unequal inclusion probabilities pi_i;
Horvitz-Thompson weights ``w_i = 1 / pi_i`` make the estimates refer to all decisions rather than to
the ones humans happened to see. Unweighted use passes no weights.

Labels are class indices into each probability row.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

PROBABILITY_FLOOR = 1e-12
_GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0


def _weights(n: int, weights: Sequence[float] | None) -> list[float]:
    if weights is None:
        return [1.0] * n
    if len(weights) != n:
        raise ValueError("weights must match the number of items")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    if sum(weights) <= 0:
        raise ValueError("total weight must be positive")
    return [float(w) for w in weights]


def _floored(probabilities: Sequence[float]) -> list[float]:
    """Floor zeros at PROBABILITY_FLOOR and renormalise, so logarithms stay finite."""
    raised = [max(float(p), PROBABILITY_FLOOR) for p in probabilities]
    total = sum(raised)
    return [p / total for p in raised]


def temperature_scale(probabilities: Sequence[float], temperature: float) -> list[float]:
    """``softmax(log p / T)``, i.e. ``p^(1/T)`` renormalised. Monotone, so the argmax is unchanged.

    Hosted deciders return probabilities rather than logits; ``log p`` recovers the logits up to a
    constant, which softmax ignores.
    """
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    logs = [math.log(p) / temperature for p in _floored(probabilities)]
    top = max(logs)
    exps = [math.exp(v - top) for v in logs]
    total = sum(exps)
    return [e / total for e in exps]


def _nll(
    beta: float, rows: Sequence[Sequence[float]], labels: Sequence[int], w: Sequence[float]
) -> float:
    total = 0.0
    for row, label, weight in zip(rows, labels, w):
        logs = [beta * math.log(p) for p in _floored(row)]
        top = max(logs)
        log_norm = top + math.log(sum(math.exp(v - top) for v in logs))
        total -= weight * (logs[label] - log_norm)
    return total


def fit_temperature(
    rows: Sequence[Sequence[float]],
    labels: Sequence[int],
    weights: Sequence[float] | None = None,
    *,
    bounds: tuple[float, float] = (0.05, 20.0),
    tolerance: float = 1e-9,
) -> float:
    """Temperature minimising the weighted negative log-likelihood (Guo et al. 2017).

    The search runs over ``beta = 1/T`` because the NLL is convex in beta (a log-sum-exp minus a
    linear term), so golden-section search finds the unique minimum on the bracket.
    """
    if len(rows) != len(labels) or not rows:
        raise ValueError("rows and labels must be non-empty and the same length")
    w = _weights(len(rows), weights)
    low, high = 1.0 / bounds[1], 1.0 / bounds[0]
    a, b = low, high
    c, d = b - _GOLDEN * (b - a), a + _GOLDEN * (b - a)
    fc, fd = _nll(c, rows, labels, w), _nll(d, rows, labels, w)
    while b - a > tolerance:
        if fc <= fd:
            b, d, fd = d, c, fc
            c = b - _GOLDEN * (b - a)
            fc = _nll(c, rows, labels, w)
        else:
            a, c, fc = c, d, fd
            d = a + _GOLDEN * (b - a)
            fd = _nll(d, rows, labels, w)
    return 1.0 / ((a + b) / 2.0)


def _check_bins(bins: int) -> None:
    if bins < 1:
        raise ValueError("bins must be at least 1")


def _bin_index(confidence: float, bins: int) -> int:
    return min(bins - 1, max(0, int(confidence * bins)))


def expected_calibration_error(
    confidences: Sequence[float],
    correct: Sequence[bool],
    weights: Sequence[float] | None = None,
    *,
    bins: int = 10,
) -> float:
    """``sum_m (W_m / W) |acc_w(B_m) - conf_w(B_m)|`` over equal-width confidence bins.

    Bin m holds confidences in ``[m/M, (m+1)/M)``; a confidence of exactly 1 joins the last bin.
    """
    if len(confidences) != len(correct) or not confidences:
        raise ValueError("confidences and correct must be non-empty and the same length")
    _check_bins(bins)
    w = _weights(len(confidences), weights)
    mass = [0.0] * bins
    hits = [0.0] * bins
    conf_sum = [0.0] * bins
    for c, ok, weight in zip(confidences, correct, w):
        m = _bin_index(c, bins)
        mass[m] += weight
        hits[m] += weight * (1.0 if ok else 0.0)
        conf_sum[m] += weight * c
    total = sum(mass)
    return sum(abs(hits[m] - conf_sum[m]) / total for m in range(bins) if mass[m] > 0)


def brier_score(
    rows: Sequence[Sequence[float]],
    labels: Sequence[int],
    weights: Sequence[float] | None = None,
) -> float:
    """Multiclass Brier score, ``(1/W) sum_i w_i sum_k (p_ik - 1[y_i = k])^2`` (thesis Eq. 10)."""
    if len(rows) != len(labels) or not rows:
        raise ValueError("rows and labels must be non-empty and the same length")
    w = _weights(len(rows), weights)
    total = sum(w)
    score = 0.0
    for row, label, weight in zip(rows, labels, w):
        score += weight * sum((p - (1.0 if k == label else 0.0)) ** 2 for k, p in enumerate(row))
    return score / total


@dataclass(frozen=True)
class BrierDecomposition:
    """Exact binned Brier decomposition.

    ``brier = reliability - resolution + uncertainty + within_bin_variance
    - 2 * within_bin_covariance``.

    Murphy's (1973) three terms are exact only when every forecast in a bin is equal. The two
    within-bin terms (Stephenson et al. 2008) make the identity exact for binned forecasts. Each
    term is summed over classes, one-vs-rest, so the total equals :func:`brier_score`.
    """

    brier: float
    reliability: float
    resolution: float
    uncertainty: float
    within_bin_variance: float
    within_bin_covariance: float


def _binary_terms(
    forecasts: Sequence[float], outcomes: Sequence[float], w: Sequence[float], bins: int
) -> tuple[float, float, float, float, float]:
    total = sum(w)
    base_rate = sum(wi * o for wi, o in zip(w, outcomes)) / total
    groups: dict[int, list[int]] = {}
    for i, f in enumerate(forecasts):
        groups.setdefault(_bin_index(f, bins), []).append(i)
    rel = res = wbv = wbc = 0.0
    for members in groups.values():
        mass = sum(w[i] for i in members)
        if mass <= 0:
            continue
        mean_f = sum(w[i] * forecasts[i] for i in members) / mass
        mean_o = sum(w[i] * outcomes[i] for i in members) / mass
        rel += mass * (mean_f - mean_o) ** 2
        res += mass * (mean_o - base_rate) ** 2
        wbv += sum(w[i] * (forecasts[i] - mean_f) ** 2 for i in members)
        wbc += sum(w[i] * (forecasts[i] - mean_f) * (outcomes[i] - mean_o) for i in members)
    uncertainty = base_rate * (1.0 - base_rate)
    return rel / total, res / total, uncertainty, wbv / total, wbc / total


def brier_decomposition(
    rows: Sequence[Sequence[float]],
    labels: Sequence[int],
    weights: Sequence[float] | None = None,
    *,
    bins: int = 10,
) -> BrierDecomposition:
    """Exact binned decomposition of the multiclass Brier score (:class:`BrierDecomposition`)."""
    if len(rows) != len(labels) or not rows:
        raise ValueError("rows and labels must be non-empty and the same length")
    _check_bins(bins)
    w = _weights(len(rows), weights)
    terms = [0.0] * 5
    for k in range(len(rows[0])):
        forecasts = [row[k] for row in rows]
        outcomes = [1.0 if label == k else 0.0 for label in labels]
        for index, value in enumerate(_binary_terms(forecasts, outcomes, w, bins)):
            terms[index] += value
    return BrierDecomposition(
        brier=brier_score(rows, labels, w),
        reliability=terms[0],
        resolution=terms[1],
        uncertainty=terms[2],
        within_bin_variance=terms[3],
        within_bin_covariance=terms[4],
    )


def effective_sample_size(weights: Sequence[float]) -> float:
    """Kish's ``(sum w)^2 / sum w^2``: how many equally weighted items the sample is worth."""
    squares = sum(w * w for w in weights)
    if squares <= 0:
        return 0.0
    return sum(weights) ** 2 / squares


def risk_coverage(
    confidences: Sequence[float],
    correct: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> list[tuple[float, float, float]]:
    """``(threshold, coverage, risk)`` for every distinct confidence, most confident first.

    Accepting items at or above ``threshold`` covers ``coverage`` of the weight with error rate
    ``risk`` among the accepted (Geifman & El-Yaniv 2017).
    """
    if len(confidences) != len(correct) or not confidences:
        raise ValueError("confidences and correct must be non-empty and the same length")
    w = _weights(len(confidences), weights)
    order = sorted(range(len(confidences)), key=lambda i: -confidences[i])
    total = sum(w)
    curve: list[tuple[float, float, float]] = []
    covered = errors = 0.0
    for position, i in enumerate(order):
        covered += w[i]
        errors += 0.0 if correct[i] else w[i]
        last = position + 1 == len(order)
        if last or confidences[order[position + 1]] != confidences[i]:
            curve.append((confidences[i], covered / total, errors / covered if covered else 0.0))
    return curve


@dataclass(frozen=True)
class CrossFitResult:
    """Held-out calibration of a temperature fitted on the other folds.

    ``temperatures_at_bound`` counts folds whose fit stopped at the edge of the search bracket.
    That happens when the likelihood keeps improving as probabilities sharpen (for example when
    every training label matches the argmax), so the temperature is not identified; a trust gate
    should not accept such a fit.
    """

    temperatures: list[float]
    temperatures_at_bound: int
    held_out_ece: float
    held_out_brier: float
    effective_sample_size: float


def _at_bound(temperature: float, bounds: tuple[float, float] = (0.05, 20.0)) -> bool:
    return any(math.isclose(temperature, edge, rel_tol=1e-6) for edge in bounds)


def _fold_assignment(n: int, folds: int, seed: int) -> list[int]:
    order = list(range(n))
    random.Random(seed).shuffle(order)
    assignment = [0] * n
    for position, i in enumerate(order):
        assignment[i] = position % folds
    return assignment


def cross_fit_calibration(
    rows: Sequence[Sequence[float]],
    labels: Sequence[int],
    weights: Sequence[float] | None = None,
    *,
    folds: int = 5,
    seed: int = 20261017,
    bins: int = 10,
) -> CrossFitResult:
    """Fit a temperature on k - 1 folds and score the held-out fold, for every fold.

    The trust gate uses these held-out numbers only, so a temperature never grades itself.
    """
    n = len(rows)
    if n < folds or folds < 2:
        raise ValueError("need at least two folds and one item per fold")
    w = _weights(n, weights)
    assignment = _fold_assignment(n, folds, seed)
    calibrated: list[list[float]] = [[] for _ in range(n)]
    temperatures: list[float] = []
    for fold in range(folds):
        train = [i for i in range(n) if assignment[i] != fold]
        temperature = fit_temperature(
            [rows[i] for i in train], [labels[i] for i in train], [w[i] for i in train]
        )
        temperatures.append(temperature)
        for i in range(n):
            if assignment[i] == fold:
                calibrated[i] = temperature_scale(rows[i], temperature)
    confidences = [max(row) for row in calibrated]
    correct = [row.index(max(row)) == label for row, label in zip(calibrated, labels)]
    return CrossFitResult(
        temperatures=temperatures,
        temperatures_at_bound=sum(1 for t in temperatures if _at_bound(t)),
        held_out_ece=expected_calibration_error(confidences, correct, w, bins=bins),
        held_out_brier=brier_score(calibrated, labels, w),
        effective_sample_size=effective_sample_size(w),
    )
