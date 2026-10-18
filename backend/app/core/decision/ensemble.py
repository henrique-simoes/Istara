"""Error structure across evaluators (decision models and LLM judges alike).

Agreement between evaluators is not evidence of correctness when their errors are correlated
(Rao & Callison-Burch 2026; Kim et al., ICML 2025). These estimators are computed on
human-labelled items: error correlation, Yule's Q (Kuncheva & Whitaker 2003), the effective number
of independent evaluators, and Dawid-Skene (1979) class-conditional confusion matrices, which
tolerate missing labels.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


def _weights(n: int, weights: Sequence[float] | None) -> list[float]:
    if weights is None:
        return [1.0] * n
    if len(weights) != n:
        raise ValueError("weights must match the number of items")
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("weights must be non-negative with a positive total")
    return [float(w) for w in weights]


def error_correlation(
    errors_a: Sequence[bool],
    errors_b: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> float | None:
    """Weighted Pearson (phi) correlation of two evaluators' error indicators.

    None when either evaluator never errs or always errs on these items: the correlation is then
    undefined, which is different from zero.
    """
    if len(errors_a) != len(errors_b) or not errors_a:
        raise ValueError("error sequences must be non-empty and the same length")
    w = _weights(len(errors_a), weights)
    total = sum(w)
    xs = [1.0 if e else 0.0 for e in errors_a]
    ys = [1.0 if e else 0.0 for e in errors_b]
    mean_x = sum(wi * x for wi, x in zip(w, xs)) / total
    mean_y = sum(wi * y for wi, y in zip(w, ys)) / total
    cov = sum(wi * (x - mean_x) * (y - mean_y) for wi, x, y in zip(w, xs, ys)) / total
    var_x = sum(wi * (x - mean_x) ** 2 for wi, x in zip(w, xs)) / total
    var_y = sum(wi * (y - mean_y) ** 2 for wi, y in zip(w, ys)) / total
    if var_x <= 0 or var_y <= 0:
        return None
    return cov / math.sqrt(var_x * var_y)


def yules_q(
    correct_a: Sequence[bool],
    correct_b: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> float | None:
    """``(N11 N00 - N01 N10) / (N11 N00 + N01 N10)``; 1 = errors always coincide, 0 = independent.

    ``N11`` counts items both evaluators got right and ``N00`` items both got wrong. None when the
    denominator is zero.
    """
    if len(correct_a) != len(correct_b):
        raise ValueError("sequences must be the same length")
    w = _weights(len(correct_a), weights)
    n11 = n00 = n10 = n01 = 0.0
    for a, b, wi in zip(correct_a, correct_b, w):
        if a and b:
            n11 += wi
        elif not a and not b:
            n00 += wi
        elif a:
            n10 += wi
        else:
            n01 += wi
    denominator = n11 * n00 + n01 * n10
    if denominator == 0:
        return None
    return (n11 * n00 - n01 * n10) / denominator


def effective_evaluators(count: int, mean_error_correlation: float) -> float:
    """``J / (1 + (J - 1) * max(0, rho))``: how many independent evaluators the panel is worth.

    By analogy with the design effect of clustered samples. Negative mean correlation is clamped to
    zero, so the result never exceeds ``J`` (a conservative report).
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    rho = max(0.0, min(1.0, mean_error_correlation))
    return count / (1.0 + (count - 1) * rho)


@dataclass(frozen=True)
class DawidSkeneResult:
    """Estimated class priors, per-evaluator confusion matrices and per-item class posteriors.

    ``confusion[evaluator][true][given]`` is the probability that the evaluator answers ``given``
    when the truth is ``true``. ``log_likelihood`` holds the observed-data log-likelihood after
    each M-step; EM never decreases it (up to the smoothing pseudo-counts).
    """

    priors: list[float]
    confusion: dict[str, list[list[float]]]
    posteriors: list[list[float]]
    iterations: int
    converged: bool
    log_likelihood: list[float]


def _majority_posteriors(items: Sequence[Mapping[str, int]], classes: int) -> list[list[float]]:
    posteriors = []
    for votes in items:
        counts = [0.0] * classes
        for label in votes.values():
            counts[label] += 1.0
        total = sum(counts)
        posteriors.append([c / total for c in counts] if total else [1.0 / classes] * classes)
    return posteriors


def _m_step(
    items: Sequence[Mapping[str, int]],
    posteriors: Sequence[Sequence[float]],
    evaluators: Sequence[str],
    classes: int,
    smoothing: float,
) -> tuple[list[float], dict[str, list[list[float]]]]:
    mass = [smoothing + sum(post[k] for post in posteriors) for k in range(classes)]
    priors = [m / sum(mass) for m in mass]
    confusion: dict[str, list[list[float]]] = {}
    for evaluator in evaluators:
        counts = [[smoothing] * classes for _ in range(classes)]
        for votes, post in zip(items, posteriors):
            given = votes.get(evaluator)
            if given is None:
                continue
            for k in range(classes):
                counts[k][given] += post[k]
        confusion[evaluator] = [[c / sum(row) for c in row] for row in counts]
    return priors, confusion


def _log_likelihood(
    items: Sequence[Mapping[str, int]],
    priors: Sequence[float],
    confusion: Mapping[str, Sequence[Sequence[float]]],
    classes: int,
) -> float:
    total = 0.0
    for votes in items:
        logs = [math.log(priors[k]) for k in range(classes)]
        for evaluator, given in votes.items():
            for k in range(classes):
                logs[k] += math.log(confusion[evaluator][k][given])
        top = max(logs)
        total += top + math.log(sum(math.exp(v - top) for v in logs))
    return total


def _e_step(
    items: Sequence[Mapping[str, int]],
    priors: Sequence[float],
    confusion: Mapping[str, Sequence[Sequence[float]]],
    classes: int,
) -> list[list[float]]:
    posteriors = []
    for votes in items:
        logs = [math.log(priors[k]) for k in range(classes)]
        for evaluator, given in votes.items():
            for k in range(classes):
                logs[k] += math.log(confusion[evaluator][k][given])
        top = max(logs)
        exps = [math.exp(v - top) for v in logs]
        total = sum(exps)
        posteriors.append([e / total for e in exps])
    return posteriors


def dawid_skene(
    items: Sequence[Mapping[str, int]],
    classes: int,
    *,
    max_iterations: int = 200,
    tolerance: float = 1e-8,
    smoothing: float = 0.01,
) -> DawidSkeneResult:
    """EM estimate of evaluator confusion matrices from unlabelled multi-evaluator answers.

    ``items[i]`` maps evaluator name to the class index it gave item i; an evaluator absent from
    an item simply did not answer it. Initialised from majority-vote proportions.

    Identifiability: with binary classes, three evaluators give exactly as many free parameters
    (one prior, six error rates) as observable answer patterns, so the likelihood is nearly flat
    and estimates are imprecise even with thousands of items. Report the panel size beside any
    estimate; five or more evaluators recover planted rates closely.
    """
    if classes < 2 or not items:
        raise ValueError("need at least two classes and one item")
    if any(not 0 <= label < classes for votes in items for label in votes.values()):
        raise ValueError("every answer must be a class index in [0, classes)")
    evaluators = sorted({name for votes in items for name in votes})
    posteriors = _majority_posteriors(items, classes)
    priors: list[float] = []
    confusion: dict[str, list[list[float]]] = {}
    converged = False
    iteration = 0
    trace: list[float] = []
    for iteration in range(1, max_iterations + 1):
        priors, confusion = _m_step(items, posteriors, evaluators, classes, smoothing)
        trace.append(_log_likelihood(items, priors, confusion, classes))
        updated = _e_step(items, priors, confusion, classes)
        change = max(abs(a - b) for new, old in zip(updated, posteriors) for a, b in zip(new, old))
        posteriors = updated
        if change < tolerance:
            converged = True
            break
    return DawidSkeneResult(
        priors=priors,
        confusion=confusion,
        posteriors=posteriors,
        iterations=iteration,
        converged=converged,
        log_likelihood=trace,
    )
