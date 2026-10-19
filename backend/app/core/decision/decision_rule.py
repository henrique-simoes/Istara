"""Bayes-risk decisions with a reject option (thesis Eq. 7-8; Chow 1970).

A decider in Istara never accepts research evidence. "Accept" here means the decider's label may
be used for triage; "abstain" sends the item to human review.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

ABSTAIN = "__abstain__"


def chow_threshold(reject_cost: float, error_cost: float) -> float:
    """``tau = 1 - C_R / C_E``: abstain when ``1 - max_k p_k > C_R / C_E``."""
    if error_cost <= 0 or reject_cost < 0:
        raise ValueError("error_cost must be positive and reject_cost non-negative")
    if reject_cost > error_cost:
        raise ValueError("a reject costing more than an error is never chosen; check the costs")
    return 1.0 - reject_cost / error_cost


def binary_threshold(false_positive_cost: float, false_negative_cost: float) -> float:
    """``tau* = C_FP / (C_FP + C_FN)``: accept a positive verdict only at or above this probability.

    Accepting costs ``(1 - p) C_FP`` in expectation and routing costs ``p C_FN``, so accepting is
    the cheaper action exactly when ``p >= C_FP / (C_FP + C_FN)``.
    """
    if false_positive_cost <= 0 or false_negative_cost <= 0:
        raise ValueError("costs must be positive")
    return false_positive_cost / (false_positive_cost + false_negative_cost)


def bayes_decision(
    probabilities: Sequence[float],
    loss: Sequence[Sequence[float]],
    reject_cost: float | None = None,
) -> tuple[int | str, list[float]]:
    """Minimum-expected-risk action.

    ``loss[k][j]`` is the cost of predicting ``j`` when the truth is ``k``. Returns the chosen
    index (or :data:`ABSTAIN` when a reject cost is given and every action is riskier than it)
    and the expected risk of each predict action. Ties go to the lowest index.
    """
    k = len(probabilities)
    if len(loss) != k or any(len(row) != k for row in loss):
        raise ValueError("loss must be a K x K matrix matching the probabilities")
    risks = [sum(loss[t][j] * probabilities[t] for t in range(k)) for j in range(k)]
    best = min(range(k), key=lambda j: (risks[j], j))
    if reject_cost is not None and risks[best] > reject_cost:
        return ABSTAIN, risks
    return best, risks


def selective_decision(probabilities: Mapping[str, float], tau: float) -> str:
    """Top label when its probability reaches ``tau``, otherwise :data:`ABSTAIN` (thesis Eq. 8)."""
    if not probabilities:
        raise ValueError("probabilities must not be empty")
    label = max(probabilities, key=lambda name: probabilities[name])
    return label if probabilities[label] >= tau else ABSTAIN


@dataclass(frozen=True)
class OrderFlipResult:
    """A choice asked in two option orders."""

    agree: bool
    forward_label: str
    reversed_label: str
    merged: dict[str, float]


def merge_order_flip(
    forward: Mapping[str, float], reversed_order: Mapping[str, float]
) -> OrderFlipResult:
    """Combine one choice asked with options in order and in reverse.

    Decision models can favour the option listed first. When the two argmaxes differ the item
    should abstain; when they agree the averaged distribution is the position-balanced estimate.
    An exact tie is broken by mapping order in each direction, so it can read as disagreement;
    abstaining on an exact tie is the conservative outcome.
    """
    if set(forward) != set(reversed_order):
        raise ValueError("both orders must cover the same options")
    forward_label = max(forward, key=lambda name: forward[name])
    reversed_label = max(reversed_order, key=lambda name: reversed_order[name])
    merged = {name: (forward[name] + reversed_order[name]) / 2.0 for name in forward}
    return OrderFlipResult(
        agree=forward_label == reversed_label,
        forward_label=forward_label,
        reversed_label=reversed_label,
        merged=merged,
    )
