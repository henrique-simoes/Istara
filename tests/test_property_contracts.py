"""Property-based tests for deterministic release contracts."""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest
from hypothesis import given, settings, strategies as st

from app.core.compute_capacity import compute_capacity_envelope, node_capacity_score


def _node(**overrides):
    values = {
        "is_healthy": True,
        "active_requests": 0,
        "max_active_requests": 4,
        "health_state": "ready",
        "cooldown_until": 0.0,
        "latency_ms": 0.0,
        "priority": 0,
        "ram_available_gb": 0.0,
        "ram_total_gb": 0.0,
        "cpu_load_pct": 0.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.mutation
@given(
    max_slots=st.integers(min_value=0, max_value=32),
    active=st.integers(min_value=0, max_value=32),
    healthy=st.booleans(),
)
@settings(max_examples=80)
def test_capacity_envelope_preserves_slot_invariants(max_slots, active, healthy):
    active = min(active, max_slots)
    node = _node(
        max_active_requests=max_slots, active_requests=active, is_healthy=healthy
    )

    envelope = compute_capacity_envelope([node])

    assert envelope["request_slots_total"] == max_slots
    assert envelope["request_slots_used"] == active
    assert 0 <= envelope["request_slots_available"] <= max_slots
    assert 0.0 <= envelope["request_slot_utilization_pct"] <= 100.0
    assert envelope["saturated_nodes"] == (
        1 if max_slots > 0 and active >= max_slots else 0
    )


@pytest.mark.mutation
@given(
    active=st.integers(min_value=0, max_value=4),
    latency=st.floats(
        min_value=0, max_value=2000, allow_nan=False, allow_infinity=False
    ),
    priority=st.integers(min_value=0, max_value=20),
    cpu_load=st.floats(
        min_value=0, max_value=100, allow_nan=False, allow_infinity=False
    ),
)
@settings(max_examples=80)
def test_node_capacity_score_is_available_and_bounded(
    active, latency, priority, cpu_load
):
    node = _node(
        active_requests=active,
        max_active_requests=5,
        latency_ms=latency,
        priority=priority,
        cpu_load_pct=cpu_load,
    )

    score = node_capacity_score(node, now=100.0)

    assert math.isfinite(score)
    assert score <= 120.0
    assert node_capacity_score(_node(is_healthy=False), now=100.0) == -1
    assert (
        node_capacity_score(_node(active_requests=5, max_active_requests=5), now=100.0)
        == -1
    )
    assert (
        node_capacity_score(
            _node(health_state="cooldown", cooldown_until=101.0), now=100.0
        )
        == -1
    )


@pytest.mark.mutation
def test_node_capacity_score_penalizes_active_requests_monotonically():
    idle = _node(active_requests=0, max_active_requests=5)
    busy = _node(active_requests=3, max_active_requests=5)

    assert node_capacity_score(idle, now=100.0) > node_capacity_score(busy, now=100.0)


@pytest.mark.mutation
def test_node_capacity_score_formula_components_are_stable():
    assert node_capacity_score(_node(), now=100.0) == 100.0
    assert (
        node_capacity_score(_node(active_requests=2, max_active_requests=5), now=100.0)
        == 70.0
    )
    assert node_capacity_score(_node(latency_ms=100), now=100.0) == 90.0
    assert node_capacity_score(_node(latency_ms=1000), now=100.0) == 70.0
    assert node_capacity_score(_node(priority=7), now=100.0) == 93.0
    assert (
        node_capacity_score(_node(ram_available_gb=6, ram_total_gb=24), now=100.0)
        == 112.0
    )
    assert (
        node_capacity_score(_node(ram_available_gb=2, ram_total_gb=32), now=100.0)
        == 84.0
    )
    assert node_capacity_score(_node(cpu_load_pct=80), now=100.0) == 92.5
    assert node_capacity_score(_node(cpu_load_pct=100), now=100.0) == 80.0


@pytest.mark.mutation
def test_node_capacity_score_combines_penalties_and_bonuses():
    node = _node(
        active_requests=1,
        max_active_requests=5,
        latency_ms=250,
        priority=3,
        ram_available_gb=8,
        ram_total_gb=32,
        cpu_load_pct=82,
    )

    assert node_capacity_score(node, now=100.0) == 64.0


@pytest.mark.mutation
def test_capacity_envelope_aggregates_pool_state_exactly():
    nodes = [
        _node(active_requests=1, max_active_requests=4, cpu_load_pct=0),
        _node(active_requests=4, max_active_requests=4, cpu_load_pct=50),
        _node(
            active_requests=2, max_active_requests=6, is_healthy=False, cpu_load_pct=100
        ),
    ]

    envelope = compute_capacity_envelope(nodes)

    assert envelope == {
        "request_slots_total": 14,
        "request_slots_used": 7,
        "request_slots_available": 3,
        "request_slot_utilization_pct": 50.0,
        "saturated_nodes": 1,
        "hardware_load_pct": 75.0,
    }
