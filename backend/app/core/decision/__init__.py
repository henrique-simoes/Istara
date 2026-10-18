"""Typed decision models (layer 2 of the evaluation stack): pure decision mathematics.

A typed decider maps an input to a probability vector over a closed set of answers. Istara
recomputes confidence, calibrates the probabilities, takes a Bayes-risk decision with a reject
option, and trusts a decider only after calibration is measured. This package holds the
mathematics only: no I/O, no network, no model calls.

Design and derivations: ``docs/scientific_audit/decision-model-judge-research.md``. Deciders never
accept or promote research evidence; they can only route items to human review
(``docs/architecture/research-validity-contract.md``).
"""

from app.core.decision.calibration import (
    BrierDecomposition,
    CrossFitResult,
    brier_decomposition,
    brier_score,
    cross_fit_calibration,
    effective_sample_size,
    expected_calibration_error,
    fit_temperature,
    risk_coverage,
    temperature_scale,
)
from app.core.decision.confidence import (
    choice_confidence,
    noul_confidence,
    score_confidence,
    top_label,
)
from app.core.decision.decision_rule import (
    ABSTAIN,
    OrderFlipResult,
    bayes_decision,
    binary_threshold,
    chow_threshold,
    merge_order_flip,
    selective_decision,
)
from app.core.decision.ensemble import (
    DawidSkeneResult,
    dawid_skene,
    effective_evaluators,
    error_correlation,
    yules_q,
)
from app.core.decision.reliability import (
    ReliabilityPosterior,
    beta_cdf,
    beta_quantile,
    binomial_cdf,
    learn_then_test_threshold,
    reliability_posterior,
)

__all__ = [
    "ABSTAIN",
    "BrierDecomposition",
    "CrossFitResult",
    "DawidSkeneResult",
    "OrderFlipResult",
    "ReliabilityPosterior",
    "bayes_decision",
    "beta_cdf",
    "beta_quantile",
    "binary_threshold",
    "binomial_cdf",
    "brier_decomposition",
    "brier_score",
    "choice_confidence",
    "chow_threshold",
    "cross_fit_calibration",
    "dawid_skene",
    "effective_evaluators",
    "effective_sample_size",
    "error_correlation",
    "expected_calibration_error",
    "fit_temperature",
    "learn_then_test_threshold",
    "merge_order_flip",
    "noul_confidence",
    "reliability_posterior",
    "risk_coverage",
    "score_confidence",
    "selective_decision",
    "temperature_scale",
    "top_label",
    "yules_q",
]
