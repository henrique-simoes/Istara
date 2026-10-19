"""Decider labels, audit sampling and the calibration trust gate (CF-SPEC-1, Phase 2).

Planted data: labels drawn from a known probability, so we know whether a decider's reported
probability is calibrated, miscalibrated in a way temperature scaling can repair, or biased in a way
it cannot. The gate must trust only what held-out calibration supports, and name every refusal.
"""

import math
import random

from app.core.decision.labels import (
    LABEL_MAPPING_VERSION,
    label_from_reconciliation,
    positive_probability,
)
from app.core.decision.sampling import AUDIT_RATE, audit_draw, inclusion_weight, scope_key
from app.core.decision.trust import (
    LabelledDecision,
    TrustPolicy,
    evaluate_trust,
    weighted_cohen_kappa,
)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _planted(
    n: int,
    seed: int,
    *,
    spread: float = 4.0,
    sharpen: float = 1.0,
    shift: float = 0.0,
    flip_rate=None,
):
    """True P(acceptable) = sigmoid(z), z ~ N(0, spread); the decider reports
    sigmoid(sharpen * z + shift). Spread 4 is an informative decider (accuracy about 0.87)."""
    rng = random.Random(seed)
    items = []
    for _ in range(n):
        z = rng.gauss(0.0, spread)
        label = 1 if rng.random() < _sigmoid(z) else 0
        flip = None if flip_rate is None else rng.random() >= flip_rate
        p = _sigmoid(sharpen * z + shift)
        items.append(LabelledDecision(p_positive=p, label=label, order_flip_agree=flip))
    return items


# ── labels (mapping v1) ──


def test_only_human_review_produces_labels():
    assert LABEL_MAPPING_VERSION == "v1"
    assert label_from_reconciliation("accepted", "human_review") == 1
    assert label_from_reconciliation("rejected", "human_review") == 0
    assert label_from_reconciliation("Revised", " human_review ") == 0
    assert label_from_reconciliation("needs_human_review", "human_review") is None
    assert label_from_reconciliation("accepted", "synthetic_benchmark") is None
    assert label_from_reconciliation("accepted", "debate") is None
    assert label_from_reconciliation("accepted", "") is None


def test_positive_probability_sums_the_acceptable_outcomes():
    dist = {"supports": 0.7, "contradicts": 0.1, "says_nothing": 0.2}
    assert math.isclose(positive_probability(dist, frozenset({"supports"})), 0.7)
    assert math.isclose(positive_probability({"true": 0.9, "false": 0.1}, frozenset({"true"})), 0.9)
    for bad in (
        lambda: positive_probability({}, frozenset({"a"})),
        lambda: positive_probability(dist, frozenset({"grounded"})),
    ):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


# ── audit sampling ──


def test_audit_draw_is_deterministic_and_hits_the_rate():
    assert audit_draw("p1", "item-1", 0.1) == audit_draw("p1", "item-1", 0.1)
    drawn = sum(audit_draw("p1", f"item-{i}", AUDIT_RATE)[0] for i in range(20000))
    assert abs(drawn / 20000 - AUDIT_RATE) < 0.01, drawn
    assert audit_draw("p1", "x", 1.0)[0] is True
    try:
        audit_draw("p1", "x", 0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("rate 0 must be refused")


def test_inclusion_weights_follow_horvitz_thompson():
    # Non-routed: always reviewed blind (weight 1), sampled or not.
    assert inclusion_weight(False, False, 0.1) == 1.0
    assert inclusion_weight(False, True, 0.1) == 1.0
    # Routed: only the blind audit sample counts; a shown verdict never does.
    assert math.isclose(inclusion_weight(True, True, 0.1), 10.0)
    assert inclusion_weight(True, False, 0.1) is None


def test_scope_key_changes_with_every_scope_field():
    base = dict(
        project_id="p1",
        provider="jev",
        served_model="jev-1.13.0",
        question_set_id="code-application-triage",
        question_set_version="1",
        task_family="deductive_coding",
        language="pt",
        label_mapping_version="v1",
    )
    key = scope_key(**base)
    assert key == scope_key(**{**base, "served_model": " JEV-1.13.0 "})
    for field, value in (
        ("project_id", "p2"),
        ("served_model", "jev-1.14.0"),
        ("question_set_version", "2"),
        ("language", "en"),
        ("label_mapping_version", "v2"),
        ("task_family", "claim_support"),
    ):
        assert scope_key(**{**base, field: value}) != key, field


# ── trust gate ──


def test_weighted_kappa_hand_computed():
    assert math.isclose(weighted_cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0], [1, 1, 1, 1]), 1.0)
    assert math.isclose(weighted_cohen_kappa([1, 0, 1, 0], [1, 1, 0, 0], [1, 1, 1, 1]), 0.0)
    assert weighted_cohen_kappa([1, 1], [1, 1], [1, 1]) is None


def test_calibrated_decider_is_trusted():
    report = evaluate_trust(_planted(800, seed=1))
    assert report.trusted, report.reasons
    assert report.metrics["held_out_ece"] <= 0.05
    assert report.metrics["kappa"] >= 0.6
    assert math.isclose(report.metrics["tau"], 0.9)


def test_overconfidence_that_temperature_repairs_is_trusted_after_recalibration():
    report = evaluate_trust(_planted(800, seed=2, sharpen=3.0))
    assert report.metrics["raw_ece"] > 0.05
    assert report.trusted, report.reasons
    assert 2.5 < report.metrics["median_temperature"] < 3.5


def test_bias_that_temperature_cannot_repair_is_refused():
    report = evaluate_trust(_planted(800, seed=3, shift=2.5))
    assert not report.trusted
    assert "ece_above_ceiling" in report.reasons


def test_calibrated_but_weakly_discriminating_decider_is_refused():
    # Calibration alone does not earn trust: at spread 2 a perfectly calibrated decider is right
    # only about 77% of the time, and kappa against the labels falls below the 0.60 floor.
    report = evaluate_trust(_planted(800, seed=1, spread=2.0))
    assert report.metrics["held_out_ece"] <= 0.05
    assert report.reasons == ["kappa_below_floor"]


def test_uninformative_decider_is_refused_on_kappa():
    rng = random.Random(4)
    items = [LabelledDecision(rng.random(), rng.randint(0, 1)) for _ in range(800)]
    report = evaluate_trust(items)
    assert "kappa_below_floor" in report.reasons and not report.trusted


def test_small_samples_alias_scopes_and_single_class_are_refused():
    small = evaluate_trust(_planted(30, seed=5))
    assert small.reasons == ["insufficient_labelled_data"]
    # 65 items, but five audit items carry weight 50: effective n is about 7.7.
    weighted_small = evaluate_trust(
        [LabelledDecision(i.p_positive, i.label, weight=50.0) for i in _planted(5, seed=6)]
        + _planted(60, seed=7)
    )
    assert weighted_small.reasons == ["insufficient_labelled_data"]
    assert weighted_small.metrics["effective_n"] < 10
    alias = evaluate_trust(_planted(800, seed=1), alias_scope=True)
    assert "alias_model_scope" in alias.reasons and not alias.trusted
    single = evaluate_trust([LabelledDecision(0.8, 1) for _ in range(100)])
    assert single.reasons == ["single_class_labels"]


def test_order_flip_disagreement_is_refused_and_must_be_measured():
    flipping = evaluate_trust(_planted(800, seed=1, flip_rate=0.12), needs_order_flip=True)
    assert "order_flip_above_ceiling" in flipping.reasons
    steady = evaluate_trust(_planted(800, seed=1, flip_rate=0.0), needs_order_flip=True)
    assert steady.trusted, steady.reasons
    unmeasured = evaluate_trust(_planted(800, seed=1), needs_order_flip=True)
    assert "order_flip_unmeasured" in unmeasured.reasons


def test_unidentified_temperature_is_refused():
    rng = random.Random(8)
    items = []
    for _ in range(200):
        label = rng.randint(0, 1)
        p = 0.6 + 0.3 * rng.random() if label else 0.1 + 0.3 * rng.random()
        items.append(LabelledDecision(p, label))
    report = evaluate_trust(items)
    assert "temperature_not_identified" in report.reasons and not report.trusted


def test_policy_is_recorded_and_tightening_it_refuses_more():
    items = _planted(800, seed=1)
    strict = evaluate_trust(items, TrustPolicy(max_ece=0.001))
    assert strict.policy["max_ece"] == 0.001 and "ece_above_ceiling" in strict.reasons


def test_an_alias_is_trusted_per_served_version_unless_the_version_is_unknown():
    from app.core.decision.trust import unversioned_alias_scope

    # jev-latest answered by a versioned model: that version earns trust like a pinned id.
    assert unversioned_alias_scope([(True, "jev-1.13.0"), (True, "jev-1.13.0")]) is False
    assert unversioned_alias_scope([(False, "kev-4b")]) is False
    # An alias answered under an alias name could mix versions in one scope: refused.
    assert unversioned_alias_scope([(True, "jev-1.13.0"), (True, "jev-latest")]) is True
