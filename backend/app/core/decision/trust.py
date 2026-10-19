"""The calibration trust gate for a decider scope (thesis: calibration is an acceptance criterion).

A scope is trusted only when held-out calibration meets the pre-registered policy (owner decision
DEC-1). An untrusted scope runs in shadow mode: its verdicts are recorded and have no routing
effect (DEC-2). The gate works on the binary event the v1 labels describe: whether the decider's
"acceptable" outcome was right.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field

from app.core.decision.calibration import (
    brier_decomposition,
    cross_fit_calibration,
    effective_sample_size,
    expected_calibration_error,
)
from app.core.decision.decision_rule import binary_threshold


@dataclass(frozen=True)
class TrustPolicy:
    """Pre-registered ceilings (DEC-1); a governed project policy may tighten them."""

    max_ece: float = 0.05
    min_kappa: float = 0.60
    min_effective_n: float = 50.0
    max_order_flip_rate: float = 0.05
    false_positive_cost: float = 9.0
    false_negative_cost: float = 1.0
    folds: int = 5
    bins: int = 10


@dataclass(frozen=True)
class LabelledDecision:
    """One decider verdict with its human label.

    ``p_positive`` is the provider's raw probability of the acceptable outcome; ``weight`` is the
    Horvitz-Thompson weight; ``order_flip_agree`` is None when the question had no option order.
    """

    p_positive: float
    label: int
    weight: float = 1.0
    order_flip_agree: bool | None = None


@dataclass
class TrustReport:
    trusted: bool
    reasons: list[str]
    metrics: dict[str, float | int | None] = field(default_factory=dict)
    policy: dict[str, float | int] = field(default_factory=dict)


def weighted_cohen_kappa(
    predicted: Sequence[int], actual: Sequence[int], weights: Sequence[float]
) -> float | None:
    """Cohen's kappa for two binary raters with item weights; None when chance agreement is 1."""
    total = sum(weights)
    observed = sum(w for p, a, w in zip(predicted, actual, weights) if p == a) / total
    p_pred = sum(w for p, w in zip(predicted, weights) if p == 1) / total
    p_act = sum(w for a, w in zip(actual, weights) if a == 1) / total
    expected = p_pred * p_act + (1 - p_pred) * (1 - p_act)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def _order_flip_rate(items: Sequence[LabelledDecision]) -> float | None:
    flips = [item.order_flip_agree for item in items if item.order_flip_agree is not None]
    if not flips:
        return None
    return sum(1 for agree in flips if not agree) / len(flips)


def _coverage_at(
    probs: Sequence[float], labels: Sequence[int], weights: Sequence[float], tau: float
) -> tuple[float, float | None]:
    accepted = [(p, y, w) for p, y, w in zip(probs, labels, weights) if p >= tau]
    total = sum(weights)
    mass = sum(w for _, _, w in accepted)
    errors = sum(w for _, y, w in accepted if y != 1)
    return mass / total, (errors / mass if mass else None)


def _metrics(items: Sequence[LabelledDecision], policy: TrustPolicy) -> dict[str, float | None]:
    rows = [[1.0 - item.p_positive, item.p_positive] for item in items]
    labels = [item.label for item in items]
    weights = [item.weight for item in items]
    fit = cross_fit_calibration(rows, labels, weights, folds=policy.folds, bins=policy.bins)
    held = [row[1] for row in fit.held_out_rows]
    predicted = [1 if p >= 0.5 else 0 for p in held]
    confidences = [max(p, 1.0 - p) for p in held]
    correct = [pred == label for pred, label in zip(predicted, labels)]
    decomposition = brier_decomposition(fit.held_out_rows, labels, weights, bins=policy.bins)
    tau = binary_threshold(policy.false_positive_cost, policy.false_negative_cost)
    coverage, risk = _coverage_at(held, labels, weights, tau)
    return {
        "n": len(items),
        "effective_n": effective_sample_size(weights),
        "held_out_ece": fit.held_out_ece,
        "raw_ece": expected_calibration_error(
            [max(i.p_positive, 1 - i.p_positive) for i in items],
            [(i.p_positive >= 0.5) == (i.label == 1) for i in items],
            weights,
            bins=policy.bins,
        ),
        "held_out_brier": fit.held_out_brier,
        "brier_reliability": decomposition.reliability,
        "brier_resolution": decomposition.resolution,
        "held_out_accuracy": sum(w for ok, w in zip(correct, weights) if ok) / sum(weights),
        "kappa": weighted_cohen_kappa(predicted, labels, weights),
        "tau": tau,
        "coverage_at_tau": coverage,
        "risk_at_tau": risk,
        "order_flip_rate": _order_flip_rate(items),
        "temperatures_at_bound": fit.temperatures_at_bound,
        "median_temperature": sorted(fit.temperatures)[len(fit.temperatures) // 2],
        "mean_confidence": sum(confidences) / len(confidences),
    }


def _reasons(
    metrics: dict[str, float | None], policy: TrustPolicy, needs_order_flip: bool
) -> list[str]:
    reasons = []
    if metrics["held_out_ece"] > policy.max_ece:
        reasons.append("ece_above_ceiling")
    if metrics["kappa"] is None or metrics["kappa"] < policy.min_kappa:
        reasons.append("kappa_below_floor")
    if metrics["temperatures_at_bound"]:
        reasons.append("temperature_not_identified")
    flip = metrics["order_flip_rate"]
    if needs_order_flip and flip is None:
        reasons.append("order_flip_unmeasured")
    elif flip is not None and flip > policy.max_order_flip_rate:
        reasons.append("order_flip_above_ceiling")
    return reasons


def unversioned_alias_scope(calls: Iterable[tuple[bool, str]]) -> bool:
    """True when a scope's evidence cannot be tied to one model version.

    ``calls`` holds ``(alias_requested, served_model)`` per verdict. Scopes are keyed by the served
    model, so asking for a moving alias such as ``jev-latest`` is fine when the provider names the
    versioned model that answered (``jev-1.13.0``): that version earns its own trust, and a new
    version behind the alias starts a new, untrusted scope. Only an alias answered under an alias
    name could mix versions in one scope, and only that is refused.
    """
    from app.core.decider.contract import is_alias_model_id

    return any(requested and is_alias_model_id(served or "") for requested, served in calls)


def evaluate_trust(
    items: Sequence[LabelledDecision],
    policy: TrustPolicy | None = None,
    *,
    alias_scope: bool = False,
    needs_order_flip: bool = False,
) -> TrustReport:
    """Decide whether a scope may route items. Every refusal names its reason."""
    policy = policy or TrustPolicy()
    report = TrustReport(trusted=False, reasons=[], policy=asdict(policy))
    if alias_scope:
        report.reasons.append("alias_model_scope")
    weights = [item.weight for item in items]
    effective_n = effective_sample_size(weights) if items else 0.0
    if effective_n < policy.min_effective_n or len(items) < policy.folds:
        report.reasons.append("insufficient_labelled_data")
        report.metrics = {"n": len(items), "effective_n": effective_n}
        return report
    if len({item.label for item in items}) < 2:
        report.reasons.append("single_class_labels")
        report.metrics = {"n": len(items), "effective_n": effective_n}
        return report
    report.metrics = _metrics(items, policy)
    report.reasons.extend(_reasons(report.metrics, policy, needs_order_flip))
    report.trusted = not report.reasons
    return report
