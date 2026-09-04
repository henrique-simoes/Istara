"""Contract tests for the MoA routing-validation logic (Lane B). Pure tier-T0 fakes."""

from __future__ import annotations

import pytest

from tests.pi_benchmark import moa
from tests.pi_benchmark.moa import (
    MoaEvidence,
    assess_validation_result,
    validate_topology,
)

pytestmark = pytest.mark.benchmark


class _Consensus:
    def __init__(self, agreement_score=0.82, confidence="high"):
        self.agreement_score = agreement_score
        self.confidence = confidence


class _Result:
    """Duck-typed ValidationResult stand-in (method/responses/consensus/metadata)."""

    def __init__(
        self, method, responses, endpoint_ids, consensus=None, route_evidence=None
    ):
        self.method = method
        self.responses = responses
        self.consensus = consensus if consensus is not None else _Consensus()
        self.metadata = {
            "endpoint_ids": endpoint_ids,
            "route_evidence": (
                route_evidence
                if route_evidence is not None
                else [
                    {
                        "endpoint_id": e,
                        "model": f"model-{e}",
                        "route_kind": "agentic_ensemble",
                    }
                    for e in endpoint_ids
                ]
            ),
        }


def test_self_moa_clean_pass_single_route_temperature_sweep():
    result = _Result("self_moa", ["r1", "r2", "r3"], ["pi-deepseek-default"] * 3)
    ev = assess_validation_result(
        requested_mode="self_moa",
        requested_samples=3,
        temperatures=(0.3, 0.7, 1.0),
        result=result,
    )
    assert ev.served_mode == "self_moa"
    assert ev.distinct_served_routes == 1  # one endpoint, three temperature samples
    assert ev.temperatures == (0.3, 0.7, 1.0)
    assert ev.response_count == 3 and ev.coder_count == 3
    assert ev.consensus_score == pytest.approx(0.82)
    assert ev.consensus_confidence == "high"
    assert ev.source_unit_ids == ("pi-deepseek-default",) * 3
    assert ev.downgrade is None and ev.degraded is False
    assert ev.reconciliation_status == "reconciled"
    assert moa.record_status_for(ev) == ("ok", None)


def test_full_ensemble_clean_three_distinct_routes():
    result = _Result("full_ensemble", ["r1", "r2", "r3"], ["ep-a", "ep-b", "ep-c"])
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.distinct_served_routes == 3
    assert ev.distinct_served_models == 3
    assert ev.formal_reliability is False
    assert ev.research_spine_eligible is False
    assert ev.downgrade is None and ev.degraded is False
    assert ev.reconciliation_status == "reconciled"
    assert moa.record_status_for(ev) == ("ok", None)


def test_full_ensemble_partial_success_ignores_failed_endpoint_ids():
    # The dispatcher can report all selected endpoints while only one response/route
    # succeeded. Failed endpoint ids are provenance, never proof of served coders.
    result = _Result(
        "full_ensemble",
        ["r1"],
        ["ep-a", "ep-b", "ep-c"],
        consensus=_Consensus(0.9, "high"),
        route_evidence=[{"endpoint_id": "ep-a"}],
    )
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.response_count == 1 and ev.coder_count == 1
    assert ev.served_route_ids == ("ep-a",)
    assert ev.source_unit_ids == ("ep-a", "ep-b", "ep-c")
    assert ev.consensus_score == pytest.approx(0.9)
    assert ev.consensus_confidence == "high"
    assert ev.downgrade == "partial_coder"
    assert ev.reconciliation_status == "degraded"
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_self_moa_partial_success_does_not_reconcile_from_selected_route_count():
    result = _Result(
        "self_moa",
        ["r1"],
        ["pi-deepseek-default"] * 3,
        consensus=_Consensus(0.9, "high"),
        route_evidence=[{"endpoint_id": "pi-deepseek-default"}],
    )
    ev = assess_validation_result(
        requested_mode="self_moa",
        requested_samples=3,
        result=result,
    )
    assert ev.response_count == 1 and ev.coder_count == 1
    assert ev.distinct_served_routes == 1
    assert ev.downgrade == "partial_coder"
    assert ev.reconciliation_status == "degraded"
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_full_ensemble_downgrade_to_dual_run_is_degraded_and_blocks_the_record():
    result = _Result("dual_run", ["r1", "r2"], ["ep-a", "ep-b"])
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.downgrade == "full_ensemble->dual_run"
    assert ev.degraded is True
    assert ev.reconciliation_status == "degraded"
    # A downgraded ensemble maps to not_runnable — never reported as success.
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_full_ensemble_downgrade_to_self_moa_is_degraded():
    result = _Result("self_moa", ["r1", "r2", "r3"], ["ep-a"] * 3)
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.downgrade == "full_ensemble->self_moa"
    assert ev.degraded is True
    assert ev.reconciliation_status == "degraded"
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_full_ensemble_served_but_diversity_collapsed_is_single_coder():
    # Method held (full_ensemble) but only 2 distinct routes for 3 requested slots.
    result = _Result("full_ensemble", ["r1", "r2", "r3"], ["ep-a", "ep-b", "ep-a"])
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.served_mode == "full_ensemble"
    assert ev.distinct_served_routes == 2
    assert ev.downgrade == "single_coder"
    assert ev.degraded is True
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_full_ensemble_distinct_endpoints_for_one_model_is_not_independent_ensemble():
    # Endpoint replicas can look diverse while every coder is the same served model.
    result = _Result(
        "full_ensemble",
        ["r1", "r2", "r3"],
        ["ep-a", "ep-b", "ep-c"],
        route_evidence=[
            {"endpoint_id": "ep-a", "model": "same-model"},
            {"endpoint_id": "ep-b", "model": "same-model"},
            {"endpoint_id": "ep-c", "model": "same-model"},
        ],
    )
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.distinct_served_routes == 3
    assert ev.distinct_served_models == 1
    assert ev.downgrade == "model_identity_collapse"
    assert ev.degraded is True
    assert ev.reconciliation_status == "degraded"
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_full_ensemble_missing_model_identity_fails_closed():
    result = _Result(
        "full_ensemble",
        ["r1", "r2", "r3"],
        ["ep-a", "ep-b", "ep-c"],
        route_evidence=[
            {"endpoint_id": "ep-a"},
            {"endpoint_id": "ep-b"},
            {"endpoint_id": "ep-c"},
        ],
    )
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.distinct_served_routes == 3
    assert ev.served_model_ids == ()
    assert ev.distinct_served_models == 0
    assert ev.downgrade == "model_identity_collapse"
    assert ev.degraded is True


def test_zero_responses_is_blocked():
    result = _Result("full_ensemble", [], [], consensus=_Consensus(0.0, "insufficient"))
    ev = assess_validation_result(
        requested_mode="full_ensemble",
        requested_samples=3,
        result=result,
    )
    assert ev.response_count == 0
    assert ev.reconciliation_status == "blocked"
    assert ev.degraded is True
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_insufficient_consensus_confidence_is_not_reconciled():
    result = _Result(
        "self_moa",
        ["r1", "r2", "r3"],
        ["ep-a"] * 3,
        consensus=_Consensus(0.2, "insufficient"),
    )
    ev = assess_validation_result(
        requested_mode="self_moa",
        requested_samples=3,
        result=result,
    )
    assert ev.downgrade is None and ev.degraded is False
    assert ev.reconciliation_status == "degraded"  # reconciled requires real confidence


def test_self_moa_served_on_multiple_routes_is_an_anomaly():
    result = _Result("self_moa", ["r1", "r2", "r3"], ["ep-a", "ep-b", "ep-a"])
    ev = assess_validation_result(
        requested_mode="self_moa",
        requested_samples=3,
        result=result,
    )
    assert ev.distinct_served_routes == 2
    assert ev.degraded is True
    assert ev.reconciliation_status == "degraded"


class _ExplodesIfCalled:
    def __call__(self):  # pragma: no cover - must never run
        raise AssertionError("validate_topology must not invoke endpoint ids")


@pytest.mark.parametrize(
    "n_ids,requested,expected_mode,expected_degrade,expected_downgrade",
    [
        (0, 3, "blocked", True, None),
        (1, 3, "self_moa", True, "full_ensemble->self_moa"),
        (2, 3, "dual_run", True, "full_ensemble->dual_run"),
        (3, 3, "full_ensemble", False, None),
        (5, 3, "full_ensemble", False, None),
        (2, 2, "full_ensemble", False, None),
    ],
)
def test_validate_topology_matrix(
    n_ids, requested, expected_mode, expected_degrade, expected_downgrade
):
    ids = [f"ep-{i}" for i in range(n_ids)]
    out = validate_topology(available_endpoint_ids=ids, requested_slots=requested)
    assert out == {
        "requested_slots": requested,
        "available_distinct": n_ids,
        "would_serve_mode": expected_mode,
        "would_degrade": expected_degrade,
        "downgrade": expected_downgrade,
    }


def test_validate_topology_dedupes_and_never_calls_the_ids():
    # Duplicate ids (the same endpoint admitted twice) count once; ids are opaque
    # sentinels that explode if invoked (no spend, no inspection).
    sentinel = _ExplodesIfCalled()
    ids = [sentinel, sentinel, sentinel]
    out = validate_topology(available_endpoint_ids=ids, requested_slots=3)
    assert out["available_distinct"] == 1
    assert out["would_serve_mode"] == "self_moa"
    assert out["would_degrade"] is True


def test_not_run_evidence_marks_blocked_before_dispatch_units():
    ev = moa.not_run_evidence(requested_mode="full_ensemble", requested_samples=3)
    assert isinstance(ev, MoaEvidence)
    assert ev.reconciliation_status == "not_run"
    assert ev.degraded is True
    assert moa.record_status_for(ev) == ("not_runnable", "other")


def test_requested_slots_mirrors_the_backend_call_shape():
    assert moa.requested_slots("self_moa", 3) == 3
    assert moa.requested_slots("full_ensemble", 3) == 3  # min_responses=2 -> n=3 slots
    assert moa.requested_slots("full_ensemble", 5) == 5  # min_responses=4 -> n=5 slots
    with pytest.raises(ValueError):
        moa.requested_slots("dual_run", 3)
