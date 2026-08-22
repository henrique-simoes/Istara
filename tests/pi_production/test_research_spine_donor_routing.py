"""Research-spine donor routing contract (master plan invariant I6, W4).

Couples the Petals donor admission/dispatch surface with the research spine's
route-evidence and fail-closed requirements:

* research-scoped payloads (``project_id`` + purpose) are pinned to the exact
  admitted donor and return the full ``_istara_route`` evidence handle
  (route_kind, donor node identity, source, served model, usage estimate)
  that reports and reconciliation trace;
* any missing admission condition (unknown node, non-donor source, missing
  consent, unhealthy donor, empty messages) raises the typed
  :class:`PetalsUnavailable` that the API layer maps to HTTP 503 with
  ``error.type=petals_unavailable`` — never a paid fallback, for research
  traffic exactly like any other traffic;
* the disabled-bridge state fails closed the same way.

The donor-never-ordinary-Pi-capacity direction is proven separately by
``tests/pi_production/test_same_model_donor_isolation.py`` (I1); this file
covers the spine-facing routing contract (I6).
"""

from __future__ import annotations

import asyncio
import json

import pytest
from app.core import petals_bridge
from app.core.petals_bridge import PetalsUnavailable


class FakeDonorNode:
    def __init__(self, node_id="donor-1", *, source="relay", pi_served=True, is_healthy=True):
        self.node_id = node_id
        self.source = source
        self.pi_served = pi_served
        self.is_healthy = is_healthy
        self.loaded_models = ["petals-model-7b"]
        self.calls = []

    async def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"message": {"role": "assistant", "content": "donor response"}}


class FakeRegistry:
    def __init__(self, nodes):
        self._nodes = nodes


@pytest.fixture
def donor():
    return FakeDonorNode()


@pytest.fixture
def registry_with(donor, monkeypatch):
    registry = FakeRegistry({donor.node_id: donor})
    monkeypatch.setattr(petals_bridge, "_registry", lambda: registry)
    return registry


def test_research_scoped_donor_dispatch_keeps_route_evidence(registry_with):
    """Spine traffic is pinned to the donor and stamps the full evidence handle."""
    result = asyncio.run(petals_bridge.chat_completions({
        "model": "pi-petals-donor-1",
        "messages": [{"role": "user", "content": "interview transcript chunk"}],
        "project_id": "project-spine-1",
        "purpose": "research_analysis",
    }))
    route = result["_istara_route"]
    assert route["route_kind"] == "petals_bridge"
    assert route["node_id"] == "donor-1"
    assert route["node_source"] == "relay"
    assert route["model"] == "petals-model-7b"
    assert route["usage_estimate"] is True
    # The donor itself received the project-scoped request (project authorization).
    assert len(registry_with._nodes["donor-1"].calls) == 1
    assert registry_with._nodes["donor-1"].calls[0]["project_id"] == "project-spine-1"


def test_missing_admission_condition_is_typed_unavailable_never_paid_fallback(donor, registry_with):
    """Every admission condition is enforced for spine traffic — typed 503, no fallback."""
    cases = [
        (lambda d: setattr(d, "source", "network"), "not_a_donor"),
        (lambda d: setattr(d, "pi_served", False), "donor_not_consented"),
        (lambda d: setattr(d, "is_healthy", False), "donor_unhealthy"),
    ]
    for mutate, reason_fragment in cases:
        donor.source = "relay"
        donor.pi_served = True
        donor.is_healthy = True
        mutate(donor)
        with pytest.raises(PetalsUnavailable, match=reason_fragment):
            asyncio.run(petals_bridge.chat_completions({
                "model": "pi-petals-donor-1",
                "messages": [{"role": "user", "content": "research input"}],
                "project_id": "project-spine-1",
            }))
        # No dispatch ever reached the donor while failing closed.
        assert donor.calls == []


def test_unknown_node_fails_closed_for_research_traffic(registry_with):
    with pytest.raises(PetalsUnavailable, match="unknown_node"):
        asyncio.run(petals_bridge.chat_completions({
            "model": "pi-petals-ghost",
            "messages": [{"role": "user", "content": "research input"}],
            "project_id": "project-spine-1",
        }))


def test_api_layer_maps_donor_failure_to_typed_503():
    """PetalsUnavailable -> HTTP 503 with error.type=petals_unavailable (no fallback)."""
    from app.api.routes.petals_bridge import _unavailable

    response = _unavailable(PetalsUnavailable("donor_unhealthy:donor-1"))
    assert response.status_code == 503
    body = json.loads(response.body)
    assert body == {"error": {"type": "petals_unavailable", "reason": "donor_unhealthy:donor-1"}}


def test_bridge_disabled_fails_closed_with_typed_503(monkeypatch):
    """Bridge disabled -> typed 503, never a silent paid route for spine traffic."""
    from app.api.routes.petals_bridge import petals_chat_completions
    from app.config import settings

    monkeypatch.setattr(settings, "petals_bridge_enabled", False)
    response = asyncio.run(petals_chat_completions({
        "model": "pi-petals-donor-1",
        "messages": [{"role": "user", "content": "research input"}],
    }))
    assert response.status_code == 503
    body = json.loads(response.body)
    assert body == {"error": {"type": "petals_unavailable", "reason": "bridge_disabled"}}
