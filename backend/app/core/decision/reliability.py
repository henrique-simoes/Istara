"""Reliability posteriors and guaranteed thresholds.

* A Beta-Binomial posterior per (scope, predicted class, confidence bin) turns a history of
  human-checked decisions into a reliability estimate whose lower credible bound is used for
  routing, so a bin with little evidence cannot look reliable. This is the conjugate form of the
  beta-binomial model in the owner's thesis (Eq. 14).
* Learn then Test (Angelopoulos, Bates, Candes, Jordan & Lei; arXiv:2110.01052) picks the most
  permissive confidence threshold whose error rate among accepted items is at most ``alpha`` with
  probability at least ``1 - delta``, by fixed-sequence testing of binomial nulls.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

_CF_MAX_ITERATIONS = 300
_CF_EPSILON = 3e-16
_TINY = 1e-300


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Lentz's evaluation of the incomplete-beta continued fraction."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > _TINY else _TINY)
    h = d
    for m in range(1, _CF_MAX_ITERATIONS + 1):
        m2 = 2 * m
        for numerator in (
            m * (b - m) * x / ((qam + m2) * (a + m2)),
            -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2)),
        ):
            d = 1.0 + numerator * d
            d = 1.0 / (d if abs(d) > _TINY else _TINY)
            c = 1.0 + numerator / c
            c = c if abs(c) > _TINY else _TINY
            h *= d * c
        if abs(d * c - 1.0) < _CF_EPSILON:
            break
    return h


def beta_cdf(x: float, a: float, b: float) -> float:
    """Regularised incomplete beta ``I_x(a, b)``, the CDF of Beta(a, b) at x."""
    if a <= 0 or b <= 0:
        raise ValueError("Beta parameters must be positive")
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def beta_quantile(q: float, a: float, b: float, *, tolerance: float = 1e-12) -> float:
    """Inverse of :func:`beta_cdf` by bisection (the CDF is monotone on [0, 1])."""
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must lie in [0, 1]")
    low, high = 0.0, 1.0
    while high - low > tolerance:
        mid = (low + high) / 2.0
        if beta_cdf(mid, a, b) < q:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


@dataclass(frozen=True)
class ReliabilityPosterior:
    """Posterior Beta(alpha, beta) for the probability that the decider is right in a cell."""

    alpha: float
    beta: float
    mean: float
    lower: float
    credibility: float


def reliability_posterior(
    correct: int,
    total: int,
    *,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    credibility: float = 0.95,
) -> ReliabilityPosterior:
    """``Beta(prior_alpha + correct, prior_beta + total - correct)`` with its lower credible bound.

    ``lower`` is the ``(1 - credibility)`` quantile: with a uniform prior and no data it is 0.05, so
    an untested cell never looks reliable.
    """
    if total < 0 or not 0 <= correct <= total:
        raise ValueError("need 0 <= correct <= total")
    alpha = prior_alpha + correct
    beta = prior_beta + total - correct
    return ReliabilityPosterior(
        alpha=alpha,
        beta=beta,
        mean=alpha / (alpha + beta),
        lower=beta_quantile(1.0 - credibility, alpha, beta),
        credibility=credibility,
    )


def binomial_cdf(k: int, n: int, p: float) -> float:
    """``P(X <= k)`` for ``X ~ Binomial(n, p)``, summed exactly in log space."""
    if n < 0 or not 0.0 <= p <= 1.0:
        raise ValueError("need n >= 0 and p in [0, 1]")
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p == 0.0:
        return 1.0
    if p == 1.0:
        return 0.0
    log_p, log_q = math.log(p), math.log(1.0 - p)
    total = 0.0
    for i in range(k + 1):
        log_term = (
            math.lgamma(n + 1)
            - math.lgamma(i + 1)
            - math.lgamma(n - i + 1)
            + i * log_p
            + (n - i) * log_q
        )
        total += math.exp(log_term)
    return min(1.0, total)


def learn_then_test_threshold(
    confidences: Sequence[float],
    correct: Sequence[bool],
    candidate_thresholds: Sequence[float],
    *,
    alpha: float,
    delta: float,
    floor: float = 0.0,
) -> float | None:
    """Lowest threshold whose accepted-item error rate is provably at most ``alpha``.

    Pairs must be an iid labelled sample (exchangeable with future decisions). Thresholds are
    tested from the most conservative down; for each, the null "error rate among accepted items
    exceeds alpha" is rejected when ``P(Binomial(n, alpha) <= errors) <= delta``. Testing stops at
    the first null that is not rejected (fixed-sequence testing controls the family-wise error at
    ``delta``). Returns None when not even the strictest threshold can be certified. Thresholds
    below ``floor`` (for example the Bayes threshold tau*) are never returned.
    """
    if len(confidences) != len(correct):
        raise ValueError("confidences and correct must be the same length")
    if not 0.0 < alpha < 1.0 or not 0.0 < delta < 1.0:
        raise ValueError("alpha and delta must lie in (0, 1)")
    certified: float | None = None
    for tau in sorted({t for t in candidate_thresholds if t >= floor}, reverse=True):
        accepted = [ok for c, ok in zip(confidences, correct) if c >= tau]
        n = len(accepted)
        if n == 0:
            continue
        errors = sum(1 for ok in accepted if not ok)
        if binomial_cdf(errors, n, alpha) > delta:
            break
        certified = tau
    return certified
