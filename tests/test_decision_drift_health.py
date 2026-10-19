"""Calibration drift and the evaluator error structure (CF-SPEC-1, Phase 5). Pure; no database."""

import math
import random

from app.core.decision.drift import brier_contribution, cusum_upward
from app.core.decision.health import MIN_SHARED_ITEMS, error_structure


def test_brier_contribution():
    assert math.isclose(brier_contribution(0.9, 1), 0.01)
    assert math.isclose(brier_contribution(0.9, 0), 0.81)


def test_cusum_stays_quiet_on_a_stable_scope_and_fires_on_drift():
    rng = random.Random(5)
    stable = [rng.uniform(0.0, 0.2) for _ in range(300)]
    assert not cusum_upward(stable, reference=0.1).drifted
    drifted = stable[:50] + [rng.uniform(0.3, 0.6) for _ in range(50)]
    result = cusum_upward(drifted, reference=0.1)
    assert result.drifted and 50 <= result.alarm_index < 70


def test_cusum_rejects_bad_parameters():
    for kwargs in ({"threshold": 0}, {"slack": -0.1}):
        try:
            cusum_upward([0.1], 0.1, **kwargs)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def _panel(n: int, seed: int, error_rates: dict, shared_noise: float):
    """Evaluators err independently at their rate, plus a shared error on ``shared_noise`` items."""
    rng = random.Random(seed)
    labels = {f"t{i}": rng.randint(0, 1) for i in range(n)}
    verdicts = {name: {} for name in error_rates}
    for item, label in labels.items():
        shared = rng.random() < shared_noise
        for name, rate in error_rates.items():
            wrong = shared or rng.random() < rate
            verdicts[name][item] = 1 - label if wrong else label
    return verdicts, labels


def test_correlated_panel_has_fewer_effective_evaluators():
    rates = {"decider:jev": 0.05, "llm:self_moa": 0.05, "llm:full_ensemble": 0.05}
    independent = error_structure(*_panel(2000, 1, rates, shared_noise=0.0))
    correlated = error_structure(*_panel(2000, 2, rates, shared_noise=0.15))
    assert independent["effective_evaluators"] > 2.7
    assert correlated["effective_evaluators"] < 1.8
    assert correlated["mean_error_correlation"] > independent["mean_error_correlation"]
    assert len(correlated["pairs"]) == 3 and correlated["dawid_skene"]["panel_size"] == 3
    assert all(0.75 < acc < 0.85 for acc in correlated["accuracy_vs_human"].values())


def test_pairs_need_enough_shared_items():
    verdicts, labels = _panel(MIN_SHARED_ITEMS - 1, 3, {"a": 0.1, "b": 0.1}, 0.0)
    report = error_structure(verdicts, labels)
    assert report["pairs"] == [] and report["effective_evaluators"] is None
    assert report["dawid_skene"] is None
