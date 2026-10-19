"""Decision math core (CF-SPEC-1, Phase 0): typed-decider confidence, decisions, calibration.

Fixtures are exact where a closed form exists (TypeSafe's documented confidence examples, Beta
CDFs, hand-computed ECE and Brier) and seeded planted-parameter recovery where it does not
(temperature, Dawid-Skene). Pure standard library; no backend services.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.decision import (  # noqa: E402
    ABSTAIN,
    bayes_decision,
    beta_cdf,
    beta_quantile,
    binary_threshold,
    binomial_cdf,
    brier_decomposition,
    brier_score,
    choice_confidence,
    chow_threshold,
    cross_fit_calibration,
    dawid_skene,
    effective_evaluators,
    effective_sample_size,
    error_correlation,
    expected_calibration_error,
    fit_temperature,
    learn_then_test_threshold,
    merge_order_flip,
    noul_confidence,
    reliability_posterior,
    risk_coverage,
    score_confidence,
    selective_decision,
    temperature_scale,
    top_label,
    yules_q,
)

TOL = 1e-9


def _raises(fn, *args, **kwargs) -> bool:
    try:
        fn(*args, **kwargs)
    except ValueError:
        return True
    return False


# ── confidence (TypeSafe docs examples, read 2026-10-17) ──


def test_choice_confidence_matches_documented_example():
    assert math.isclose(choice_confidence([0.9, 0.06, 0.04]), 0.85, abs_tol=TOL)
    assert math.isclose(choice_confidence([0.6, 0.3, 0.1]), 0.4, abs_tol=TOL)
    assert math.isclose(choice_confidence([0.6, 0.2, 0.2]), 0.4, abs_tol=TOL)
    assert math.isclose(choice_confidence([0.5, 0.5]), 0.0, abs_tol=TOL)


def test_score_confidence_matches_documented_examples():
    assert math.isclose(score_confidence([0.0, 0.57, 0.43]), 1 - 0.43 / (2 / 3), abs_tol=TOL)
    assert math.isclose(score_confidence([0.0, 0.5, 0.5]), 0.25, abs_tol=TOL)
    assert math.isclose(score_confidence([0.5, 0.0, 0.5]), 0.0, abs_tol=TOL)
    assert math.isclose(score_confidence([0.0, 1.0, 0.0]), 1.0, abs_tol=TOL)


def test_noul_confidence_and_top_label():
    assert math.isclose(noul_confidence(0.3), 0.4, abs_tol=TOL)
    assert noul_confidence(0.5) == 0.0
    assert _raises(noul_confidence, 1.2)
    assert top_label({"billing": 0.9, "sales": 0.1}) == ("billing", 0.9)
    assert top_label({"a": 0.5, "b": 0.5})[0] == "a"


# ── decision rule (thesis Eq. 7-8) ──


def test_thresholds_follow_the_cost_ratios():
    assert math.isclose(binary_threshold(9.0, 1.0), 0.9, abs_tol=TOL)
    assert math.isclose(binary_threshold(19.0, 1.0), 0.95, abs_tol=TOL)
    assert math.isclose(chow_threshold(0.1, 1.0), 0.9, abs_tol=TOL)
    assert _raises(chow_threshold, 2.0, 1.0)
    assert _raises(binary_threshold, 0.0, 1.0)


def test_bayes_reject_rule_equals_chow_rule_under_uniform_error_cost():
    error_cost, reject_cost = 1.0, 0.1
    zero_one = [[0.0 if t == j else error_cost for j in range(3)] for t in range(3)]
    tau = chow_threshold(reject_cost, error_cost)
    rng = random.Random(7)
    for _ in range(500):
        raw = [rng.random() for _ in range(3)]
        p = [v / sum(raw) for v in raw]
        action, _ = bayes_decision(p, zero_one, reject_cost)
        chow = selective_decision({str(k): v for k, v in enumerate(p)}, tau)
        assert (action == ABSTAIN) == (chow == ABSTAIN)
        if action != ABSTAIN:
            assert str(action) == chow


def test_bayes_decision_uses_asymmetric_losses():
    # Predicting "grounded" (0) when the truth is "hallucination" (1) costs 9; the reverse costs 1.
    loss = [[0.0, 1.0], [9.0, 0.0]]
    action, risks = bayes_decision([0.85, 0.15], loss)
    assert action == 1  # 0.15 * 9 = 1.35 > 0.85 * 1
    assert math.isclose(risks[0], 1.35, abs_tol=TOL)
    assert bayes_decision([0.95, 0.05], loss)[0] == 0


def test_order_flip_merge_detects_position_bias():
    agree = merge_order_flip({"a": 0.7, "b": 0.3}, {"a": 0.6, "b": 0.4})
    assert agree.agree and math.isclose(agree.merged["a"], 0.65, abs_tol=TOL)
    flipped = merge_order_flip({"a": 0.55, "b": 0.45}, {"a": 0.4, "b": 0.6})
    assert not flipped.agree
    assert _raises(merge_order_flip, {"a": 1.0}, {"b": 1.0})


# ── calibration (thesis Eq. 6, 9, 10) ──


def _planted_overconfident(n: int, seed: int, temperature: float):
    """True probabilities q; reported p = q^T renormalised (over-confident for T > 1)."""
    rng = random.Random(seed)
    rows, labels, truth = [], [], []
    for _ in range(n):
        logits = [rng.gauss(0.0, 1.2) for _ in range(3)]
        top = max(logits)
        exps = [math.exp(v - top) for v in logits]
        q = [e / sum(exps) for e in exps]
        draw, cumulative, label = rng.random(), 0.0, 2
        for k, value in enumerate(q):
            cumulative += value
            if draw < cumulative:
                label = k
                break
        rows.append(temperature_scale(q, 1.0 / temperature))
        labels.append(label)
        truth.append(q)
    return rows, labels, truth


def test_temperature_scaling_preserves_argmax_and_identity():
    p = [0.6, 0.3, 0.1]
    assert all(math.isclose(a, b, abs_tol=TOL) for a, b in zip(temperature_scale(p, 1.0), p))
    for t in (0.3, 2.0, 7.0):
        scaled = temperature_scale(p, t)
        assert scaled.index(max(scaled)) == 0
        assert math.isclose(sum(scaled), 1.0, abs_tol=TOL)
    assert max(temperature_scale(p, 3.0)) < 0.6 < max(temperature_scale(p, 0.5))
    assert temperature_scale([1.0, 0.0], 2.0)[1] > 0.0  # zero is floored, not -inf


def test_fit_temperature_recovers_planted_temperature():
    rows, labels, _ = _planted_overconfident(4000, seed=11, temperature=2.5)
    fitted = fit_temperature(rows, labels)
    assert abs(fitted - 2.5) < 0.25, fitted


def test_expected_calibration_error_hand_computed():
    confidences = [0.95, 0.95, 0.15, 0.15]
    correct = [True, False, False, False]
    # bin 9: acc 0.5, conf 0.95, mass 1/2; bin 1: acc 0, conf 0.15, mass 1/2.
    assert math.isclose(expected_calibration_error(confidences, correct), 0.3, abs_tol=TOL)
    # Horvitz-Thompson weights: the first item counts twice -> bin 9 acc 2/3, mass 3/5.
    weighted = expected_calibration_error(confidences, correct, [2.0, 1.0, 1.0, 1.0])
    assert math.isclose(weighted, (3 / 5) * abs(2 / 3 - 0.95) + (2 / 5) * 0.15, abs_tol=TOL)
    assert math.isclose(expected_calibration_error([1.0], [True]), 0.0, abs_tol=TOL)


def test_brier_score_hand_computed():
    assert math.isclose(brier_score([[1.0, 0.0], [0.5, 0.5]], [0, 0]), 0.25, abs_tol=TOL)
    assert math.isclose(brier_score([[0.0, 1.0]], [0]), 2.0, abs_tol=TOL)


def test_brier_decomposition_identity_is_exact():
    rows, labels, _ = _planted_overconfident(600, seed=3, temperature=1.7)
    weights = [1.0 + (i % 4) for i in range(len(rows))]
    for w in (None, weights):
        d = brier_decomposition(rows, labels, w)
        rebuilt = (
            d.reliability
            - d.resolution
            + d.uncertainty
            + d.within_bin_variance
            - 2.0 * d.within_bin_covariance
        )
        assert math.isclose(d.brier, rebuilt, abs_tol=1e-12), (d.brier, rebuilt)


def test_brier_decomposition_reduces_to_murphy_when_bins_are_constant():
    rows = [[0.85, 0.15]] * 4 + [[0.35, 0.65]] * 6
    labels = [0, 0, 0, 1, 1, 1, 0, 1, 1, 1]
    d = brier_decomposition(rows, labels)
    assert math.isclose(d.within_bin_variance, 0.0, abs_tol=TOL)
    assert math.isclose(d.within_bin_covariance, 0.0, abs_tol=TOL)
    assert math.isclose(d.brier, d.reliability - d.resolution + d.uncertainty, abs_tol=1e-12)


def test_effective_sample_size_and_risk_coverage():
    assert math.isclose(effective_sample_size([1, 1, 1, 1]), 4.0, abs_tol=TOL)
    assert math.isclose(effective_sample_size([1, 3]), 1.6, abs_tol=TOL)
    curve = risk_coverage([0.9, 0.8, 0.8, 0.3], [True, True, False, False])
    assert curve == [(0.9, 0.25, 0.0), (0.8, 0.75, 1 / 3), (0.3, 1.0, 0.5)]


def test_cross_fitting_lowers_held_out_calibration_error():
    rows, labels, _ = _planted_overconfident(1500, seed=5, temperature=2.5)
    raw_conf = [max(r) for r in rows]
    raw_ok = [r.index(max(r)) == y for r, y in zip(rows, labels)]
    raw_ece = expected_calibration_error(raw_conf, raw_ok)
    result = cross_fit_calibration(rows, labels, folds=5)
    assert len(result.temperatures) == 5
    assert all(1.8 < t < 3.4 for t in result.temperatures), result.temperatures
    assert result.held_out_ece < raw_ece / 2, (result.held_out_ece, raw_ece)
    assert result.held_out_brier < brier_score(rows, labels)
    assert math.isclose(result.effective_sample_size, 1500.0, abs_tol=TOL)


def test_degenerate_inputs_fail_with_value_errors():
    assert _raises(risk_coverage, [0.5], [True], [0.0])
    assert _raises(brier_score, [[0.5, 0.5]], [0], [0.0])
    assert _raises(expected_calibration_error, [0.5], [True], bins=0)
    assert _raises(error_correlation, [True, False], [False, True], [0.0, 0.0])
    assert _raises(dawid_skene, [{"a": 3}, {"a": 0}], 2)


def test_cross_fit_reports_unidentified_temperatures():
    # Every label matches a 0.6/0.4 argmax: sharpening always helps, so T runs to the bracket edge.
    result = cross_fit_calibration([[0.6, 0.4]] * 50, [0] * 50, folds=5)
    assert result.temperatures_at_bound == 5
    rows, labels, _ = _planted_overconfident(800, seed=9, temperature=2.0)
    assert cross_fit_calibration(rows, labels, folds=4).temperatures_at_bound == 0


# ── reliability: Beta posterior, binomial, Learn then Test ──


def test_beta_cdf_closed_forms_and_quantile_inverse():
    for x in (0.0, 0.1, 0.37, 0.5, 0.9, 1.0):
        assert math.isclose(beta_cdf(x, 1.0, 1.0), x, abs_tol=1e-12)
        assert math.isclose(beta_cdf(x, 2.0, 1.0), x * x, abs_tol=1e-12)
        assert math.isclose(beta_cdf(x, 1.0, 2.0), 1 - (1 - x) ** 2, abs_tol=1e-12)
    assert math.isclose(beta_cdf(0.5, 7.0, 7.0), 0.5, abs_tol=1e-12)
    for q in (0.05, 0.5, 0.95):
        x = beta_quantile(q, 12.0, 4.0)
        assert math.isclose(beta_cdf(x, 12.0, 4.0), q, abs_tol=1e-9)


def test_reliability_posterior_never_trusts_an_empty_cell():
    empty = reliability_posterior(0, 0)
    assert math.isclose(empty.lower, 0.05, abs_tol=1e-9)
    assert math.isclose(empty.mean, 0.5, abs_tol=TOL)
    strong = reliability_posterior(98, 100)
    weak = reliability_posterior(5, 5)
    assert strong.lower > 0.93 and weak.lower < strong.lower
    assert math.isclose(weak.lower, 0.05 ** (1 / 6), abs_tol=1e-9)  # Beta(6,1): CDF = x^6
    assert _raises(reliability_posterior, 3, 2)


def test_binomial_cdf_matches_direct_sum():
    n, p = 20, 0.13
    for k in (0, 1, 4, 19, 20):
        direct = sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))
        assert math.isclose(binomial_cdf(k, n, p), min(1.0, direct), abs_tol=1e-12)


def test_learn_then_test_certifies_only_low_risk_thresholds():
    rng = random.Random(17)
    confidences, correct = [], []
    for _ in range(2000):
        c = rng.random()
        confidences.append(c)
        correct.append(rng.random() < (0.995 if c >= 0.8 else 0.6))
    grid = [i / 20 for i in range(21)]
    tau = learn_then_test_threshold(confidences, correct, grid, alpha=0.05, delta=0.05)
    assert tau is not None and 0.7 <= tau <= 0.8, tau
    floored = learn_then_test_threshold(
        confidences, correct, grid, alpha=0.05, delta=0.05, floor=0.9
    )
    assert floored is not None and floored >= 0.9
    impossible = learn_then_test_threshold([0.99] * 10, [False] * 10, grid, alpha=0.05, delta=0.05)
    assert impossible is None


# ── ensemble error structure ──


def test_error_correlation_and_yules_q():
    errors = [True, False, True, False, False, True]
    assert math.isclose(error_correlation(errors, errors), 1.0, abs_tol=TOL)
    a = [True, True, False, False]
    b = [True, False, True, False]
    assert math.isclose(error_correlation(a, b), 0.0, abs_tol=TOL)
    assert error_correlation([False] * 4, b) is None
    correct_a = [not e for e in a]
    correct_b = [not e for e in b]
    assert math.isclose(yules_q(correct_a, correct_b), 0.0, abs_tol=TOL)
    assert math.isclose(yules_q(correct_a, correct_a), 1.0, abs_tol=TOL)


def test_effective_evaluators_is_conservative():
    assert math.isclose(effective_evaluators(9, 0.0), 9.0, abs_tol=TOL)
    assert math.isclose(effective_evaluators(9, 1.0), 1.0, abs_tol=TOL)
    assert math.isclose(effective_evaluators(9, 0.5), 1.8, abs_tol=TOL)
    assert math.isclose(effective_evaluators(3, -0.4), 3.0, abs_tol=TOL)


def _planted_panel(planted, n: int, seed: int):
    rng = random.Random(seed)
    items, truth = [], []
    for _ in range(n):
        true_class = 0 if rng.random() < 0.65 else 1
        truth.append(true_class)
        votes = {}
        for name, matrix in planted.items():
            if rng.random() < 0.9:  # some evaluators skip some items
                votes[name] = 0 if rng.random() < matrix[true_class][0] else 1
        items.append(votes)
    return items, truth


def test_dawid_skene_recovers_planted_confusion_matrices():
    planted = {
        "decider": [[0.9, 0.1], [0.2, 0.8]],
        "judge_a": [[0.7, 0.3], [0.3, 0.7]],
        "judge_b": [[0.95, 0.05], [0.4, 0.6]],
        "judge_c": [[0.8, 0.2], [0.25, 0.75]],
        "judge_d": [[0.85, 0.15], [0.15, 0.85]],
    }
    items, truth = _planted_panel(planted, 4000, seed=23)
    result = dawid_skene(items, classes=2, max_iterations=2000)
    assert result.converged
    assert abs(result.priors[0] - 0.65) < 0.04
    for name, matrix in planted.items():
        for k in range(2):
            for given in range(2):
                assert abs(result.confusion[name][k][given] - matrix[k][given]) < 0.05, name
    predicted = [post.index(max(post)) for post in result.posteriors]
    accuracy = sum(p == t for p, t in zip(predicted, truth)) / len(truth)
    assert accuracy > 0.9


def test_dawid_skene_likelihood_never_decreases():
    planted = {
        "decider": [[0.9, 0.1], [0.2, 0.8]],
        "judge_a": [[0.7, 0.3], [0.3, 0.7]],
        "judge_b": [[0.95, 0.05], [0.4, 0.6]],
    }
    items, _ = _planted_panel(planted, 1500, seed=29)
    trace = dawid_skene(items, classes=2, max_iterations=300).log_likelihood
    assert len(trace) > 1
    assert all(later >= earlier - 1e-6 for earlier, later in zip(trace, trace[1:]))
