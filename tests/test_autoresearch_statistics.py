"""Autoresearch keep-or-revert statistics and strict scoring (CF-SPEC-1, Phase 6). Pure.

Audit findings AR-1, AR-2, AR-4 and AR-5: a candidate whose true effect is zero must be kept at
most at the nominal error rate, a single sample can never be kept, and a judge reply that is not a
plain number in [0, 1] is not a score.
"""

import math
import random

from app.core.autoresearch_runners.scoring import parse_unit_score
from app.core.autoresearch_statistics import (
    keep_decision,
    t_critical_975,
    welch_interval,
)


def test_t_critical_values():
    assert t_critical_975(1) == 12.706 and t_critical_975(10) == 2.228
    assert t_critical_975(10.9) == 2.228  # fractional df rounds down: conservative
    assert t_critical_975(500) == 1.96
    try:
        t_critical_975(0.5)
    except ValueError:
        pass
    else:
        raise AssertionError("df < 1 must be refused")


def test_welch_interval_matches_a_hand_computation():
    a, b = [0.50, 0.52, 0.48], [0.60, 0.64, 0.62]
    result = welch_interval(a, b)
    assert math.isclose(result.delta, 0.12, abs_tol=1e-12)
    # var/n = 0.0004/3 each side; df = 4 by Welch-Satterthwaite; t = 2.776.
    half = 2.776 * math.sqrt(0.0004 / 3 * 2)
    assert math.isclose(result.low, 0.12 - half, abs_tol=1e-9)
    assert math.isclose(result.df, 4.0, abs_tol=1e-9)


def test_single_samples_are_never_kept():
    keep, reason, comparison = keep_decision([0.5], [0.9], 0.01)
    assert keep is False and comparison is None and "fewer than 2" in reason


def test_zero_effect_candidates_are_rarely_kept():
    rng = random.Random(42)
    kept = 0
    trials = 2000
    for _ in range(trials):
        incumbent = [rng.gauss(0.6, 0.08) for _ in range(3)]
        candidate = [rng.gauss(0.6, 0.08) for _ in range(3)]
        kept += keep_decision(incumbent, candidate, 0.01)[0]
    # A one-sided 2.5% tail, shrunk further by the 0.01 minimum gain.
    assert kept / trials < 0.03, kept


def test_a_real_gain_is_usually_kept():
    rng = random.Random(7)
    kept = sum(
        keep_decision(
            [rng.gauss(0.5, 0.03) for _ in range(4)], [rng.gauss(0.7, 0.03) for _ in range(4)], 0.01
        )[0]
        for _ in range(500)
    )
    assert kept / 500 > 0.95


def test_parse_unit_score_is_strict():
    assert parse_unit_score("0.7") == 0.7 and parse_unit_score(" 1 ") == 1.0
    assert parse_unit_score("0") == 0.0 and parse_unit_score(".25") == 0.25
    for bad in ("8/10", "Score: 0.7", "1. Completeness", "0.7 because", "1.5", "-0.1", "", None):
        assert parse_unit_score(bad) is None, bad
