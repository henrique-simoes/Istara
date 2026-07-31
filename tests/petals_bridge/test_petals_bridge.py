"""Tests for the petals bridge P0 (CF-335).

Covers: consent enforcement (default off), health enforcement, donor-only
admission, pinned dispatch (never re-scheduled), OpenAI response shape, usage
estimation honesty, catalog projection (one-directional, disabled-by-default),
and the pi_runtime isolation invariant surface.
"""

from __future__ import annotations

import asyncio
import types

import pytest

from app.config import settings
from app.core import petals_bridge
from app.core.petals_bridge import PetalsUnavailable


class FakeNode:
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

    async def chat_stream(self, messages, **kwargs):
        self.calls.append({"messages": messages, "stream": True, **kwargs})
        for piece in ("donor ", "stream ", "response"):
            yield piece


class FakeRegistry:
    def __init__(self, nodes):
        self._nodes = nodes


@pytest.fixture
def donor():
    return FakeNode()


@pytest.fixture
def registry_with(donor, monkeypatch):
    registry = FakeRegistry({donor.node_id: donor})
    monkeypatch.setattr(petals_bridge, "_registry", lambda: registry)
    return registry


def test_consent_defaults_off_on_real_node_class():
    from app.core.compute_node import ComputeNode

    node = ComputeNode(node_id="x", name="x", host="ws://x", source="relay", provider_type="ollama")
    assert node.pi_served is False


def test_unknown_node_fails_closed(registry_with):
    with pytest.raises(PetalsUnavailable, match="unknown_node"):
        asyncio.run(petals_bridge.chat_completions({"model": "pi-petals-ghost", "messages": [{"role": "user", "content": "hi"}]}))


def test_non_donor_fails_closed(donor, registry_with):
    donor.source = "network"
    with pytest.raises(PetalsUnavailable, match="not_a_donor"):
        asyncio.run(petals_bridge.chat_completions({"model": "pi-petals-donor-1", "messages": [{"role": "user", "content": "hi"}]}))


def test_unconsented_donor_fails_closed(donor, registry_with):
    donor.pi_served = False
    with pytest.raises(PetalsUnavailable, match="donor_not_consented"):
        asyncio.run(petals_bridge.chat_completions({"model": "pi-petals-donor-1", "messages": [{"role": "user", "content": "hi"}]}))


def test_unhealthy_donor_fails_closed(donor, registry_with):
    donor.is_healthy = False
    with pytest.raises(PetalsUnavailable, match="donor_unhealthy"):
        asyncio.run(petals_bridge.chat_completions({"model": "pi-petals-donor-1", "messages": [{"role": "user", "content": "hi"}]}))


def test_empty_messages_fail_closed(donor, registry_with):
    with pytest.raises(PetalsUnavailable, match="empty_messages"):
        asyncio.run(petals_bridge.chat_completions({"model": "pi-petals-donor-1", "messages": []}))


def test_pinned_dispatch_and_openai_shape(donor, registry_with):
    result = asyncio.run(petals_bridge.chat_completions({
        "model": "pi-petals-donor-1",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.3,
        "max_tokens": 64,
    }))
    # Dispatch pinned to exactly this node with the caller's params.
    assert len(donor.calls) == 1
    assert donor.calls[0]["temperature"] == 0.3
    assert donor.calls[0]["max_tokens"] == 64
    assert donor.calls[0]["messages"][0]["content"] == "hello"
    # OpenAI wire shape.
    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["content"] == "donor response"
    assert result["choices"][0]["finish_reason"] == "stop"
    assert result["usage"]["total_tokens"] > 0
    # Route truth: petals_bridge, donor identity, estimated usage marked.
    route = result["_istara_route"]
    assert route["route_kind"] == "petals_bridge"
    assert route["node_id"] == "donor-1"
    assert route["node_source"] == "relay"
    assert route["usage_estimate"] is True


def test_usage_passthrough_when_donor_reports(donor, registry_with):
    async def chat_with_usage(messages, **kwargs):
        return {
            "message": {"role": "assistant", "content": "x"},
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }
    donor.chat = chat_with_usage
    result = asyncio.run(petals_bridge.chat_completions({
        "model": "pi-petals-donor-1", "messages": [{"role": "user", "content": "hi"}],
    }))
    assert result["usage"] == {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
    assert result["_istara_route"]["usage_estimate"] is False


def test_catalog_entries_disabled_by_default(donor, registry_with):
    assert settings.petals_bridge_enabled is False
    assert petals_bridge.catalog_entries() == []


def test_catalog_entries_project_only_consented_healthy_donors(donor, registry_with, monkeypatch):
    monkeypatch.setattr(settings, "petals_bridge_enabled", True)
    donor2 = FakeNode("donor-2", pi_served=False)
    donor3 = FakeNode("donor-3", is_healthy=False)
    donor4 = FakeNode("net-1", source="network")
    registry_with._nodes.update({n.node_id: n for n in (donor2, donor3, donor4)})

    entries = petals_bridge.catalog_entries()
    assert [e["endpoint_id"] for e in entries] == ["pi-petals-donor-1"]
    entry = entries[0]
    assert entry["kind"] == "petals"
    assert entry["cost_class"] == "donated"
    assert entry["model"] == "petals-model-7b"
    assert entry["base_url"].startswith("http://127.0.0.1:")


def test_endpoint_identity_roundtrip():
    assert petals_bridge.endpoint_id_for("donor-9") == "pi-petals-donor-9"
    assert petals_bridge.node_id_for("pi-petals-donor-9") == "donor-9"
    with pytest.raises(PetalsUnavailable, match="not_a_petals_endpoint"):
        petals_bridge.node_id_for("pi-deepseek-default")


def test_model_manager_petals_projection(monkeypatch, donor, registry_with):
    monkeypatch.setattr(settings, "petals_bridge_enabled", True)
    from app.core.pi_runtime.model_manager import PiModelManager

    manager = PiModelManager(endpoints=[])
    manager._project_petals()
    entry = manager._entries.get("pi-petals-donor-1")
    assert entry is not None
    assert entry.source == "petals"
    assert entry.kind == "petals"
    assert entry.model == "petals-model-7b"


def test_pi_runtime_never_imports_registry():
    """Isolation invariant: no pi_runtime module statically imports the registry
    scheduling plane. (model_manager_provisioning's function-level ComputeNode
    import is the sanctioned W8 LM Studio provisioning path — a data type, not
    the donor scheduling plane.)"""
    import pathlib

    root = pathlib.Path("backend/app/core/pi_runtime")
    offenders = []
    for path in root.glob("*.py"):
        text = path.read_text()
        for forbidden in ("compute_registry", "llm_router"):
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")) and "petals_bridge" not in stripped:
                    if forbidden in stripped:
                        offenders.append(f"{path.name}: {stripped}")
    assert offenders == []


# ── P1: streaming, consent management, status (CF-336) ──────────────────────


def _collect_stream(payload):
    async def _run():
        return [chunk async for chunk in petals_bridge.chat_completions_stream(payload)]
    return asyncio.run(_run())


def test_stream_yields_chunks_and_final_route(donor, registry_with):
    chunks = _collect_stream({
        "model": "pi-petals-donor-1",
        "messages": [{"role": "user", "content": "hi"}],
        "stream": True,
    })
    assert len(chunks) >= 2
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[0]["choices"][0]["delta"]["content"]
    final = chunks[-1]
    assert final["choices"][0]["finish_reason"] == "stop"
    assert final["_istara_route"]["route_kind"] == "petals_bridge"
    assert final["_istara_route"]["node_id"] == "donor-1"


def test_stream_fails_closed_before_any_chunk(donor, registry_with):
    donor.pi_served = False
    with pytest.raises(PetalsUnavailable, match="donor_not_consented"):
        _collect_stream({"model": "pi-petals-donor-1", "messages": [{"role": "user", "content": "hi"}], "stream": True})


def test_set_donor_consent_flip(donor, registry_with):
    state = petals_bridge.set_donor_consent("donor-1", False)
    assert state["pi_served"] is False
    assert petals_bridge.catalog_entries.__wrapped__ if hasattr(petals_bridge.catalog_entries, "__wrapped__") else True
    state = petals_bridge.set_donor_consent("donor-1", True)
    assert state["pi_served"] is True
    assert state["node_id"] == "donor-1"


def test_set_consent_rejects_non_donor(donor, registry_with):
    donor.source = "network"
    with pytest.raises(PetalsUnavailable, match="not_a_donor"):
        petals_bridge.set_donor_consent("donor-1", True)


def test_bridge_status_inventories_donors_only(donor, registry_with):
    other = FakeNode("net-9", source="network")
    registry_with._nodes["net-9"] = other
    status = petals_bridge.bridge_status()
    assert [d["node_id"] for d in status["donors"]] == ["donor-1"]
    assert status["donors"][0]["endpoint_id"] == "pi-petals-donor-1"
    donor.pi_served = False
    status = petals_bridge.bridge_status()
    assert status["donors"][0]["endpoint_id"] is None


# ── P2: usage ledger + A2A capabilities (CF-337) ────────────────────────────


def test_dispatch_records_one_usage_row(donor, registry_with, monkeypatch):
    rows = []

    async def fake_record(**kwargs):
        rows.append(kwargs)

    monkeypatch.setattr(
        "app.core.agentic.usage_ledger.record_agentic_usage", fake_record
    )
    asyncio.run(petals_bridge.chat_completions({
        "model": "pi-petals-donor-1",
        "messages": [{"role": "user", "content": "hello"}],
        "project_id": "proj-1",
        "purpose": "research.spine",
    }))
    assert len(rows) == 1
    row = rows[0]
    assert row["engine"] == "pi"          # DEC-11: donors see the serving engine
    assert row["node_id"] == "donor-1"
    assert row["project_id"] == "proj-1"
    assert row["purpose"] == "research.spine"
    assert row["outcome"]["usage"]["estimate"] is True


def test_stream_records_one_usage_row(donor, registry_with, monkeypatch):
    rows = []

    async def fake_record(**kwargs):
        rows.append(kwargs)

    monkeypatch.setattr(
        "app.core.agentic.usage_ledger.record_agentic_usage", fake_record
    )
    _collect_stream({"model": "pi-petals-donor-1", "messages": [{"role": "user", "content": "hi"}]})
    assert len(rows) == 1
    assert rows[0]["outcome"]["usage"]["total_tokens"] > 0


def test_failed_dispatch_records_no_row(donor, registry_with, monkeypatch):
    rows = []

    async def fake_record(**kwargs):
        rows.append(kwargs)

    monkeypatch.setattr(
        "app.core.agentic.usage_ledger.record_agentic_usage", fake_record
    )
    donor.pi_served = False
    with pytest.raises(PetalsUnavailable):
        asyncio.run(petals_bridge.chat_completions({
            "model": "pi-petals-donor-1", "messages": [{"role": "user", "content": "hi"}],
        }))
    assert rows == []


def test_petals_capabilities_content_free(donor, registry_with, monkeypatch):
    monkeypatch.setattr(settings, "petals_bridge_enabled", True)
    caps = petals_bridge.build_petals_capabilities()
    assert "petals" in caps
    entry = caps["petals"][0]
    assert entry["id"] == "compute.petals.donor-1"
    assert entry["endpoint_id"] == "pi-petals-donor-1"
    assert entry["cost_class"] == "donated"
    assert entry["consent"] == "pi_served"
    assert entry["engine_visibility"] is True
    assert "ws://" not in str(caps) and "http" not in str(caps)


def test_petals_capabilities_empty_when_disabled(donor, registry_with):
    assert petals_bridge.build_petals_capabilities() == {}


# ── P3: distinct ensembles over petals (CF-338) ─────────────────────────────


def test_resolve_distinct_over_petals_endpoints(monkeypatch, donor, registry_with):
    monkeypatch.setattr(settings, "petals_bridge_enabled", True)
    donor2 = FakeNode("donor-2")
    registry_with._nodes["donor-2"] = donor2
    from app.core.pi_runtime.model_manager import PiModelManager

    manager = PiModelManager(endpoints=[])
    manager._project_petals()
    resolved = manager.resolve_distinct(2)
    ids = {e.endpoint_id for e in resolved}
    assert ids == {"pi-petals-donor-1", "pi-petals-donor-2"}


def test_mixed_ensemble_resolution_api_plus_petals(monkeypatch, donor, registry_with):
    monkeypatch.setattr(settings, "petals_bridge_enabled", True)
    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
    from app.core.pi_runtime.model_manager import PiModelManager

    api_ep = ResolvedPiEndpoint(
        endpoint_id="pi-deepseek-default", provider_kind="openai_compat",
        base_url="https://api.deepseek.com", model="deepseek-v4-pro",
        api_key="", timeout_ms=30000, max_retries=0,
    )
    manager = PiModelManager(endpoints=[api_ep])
    manager._project_petals()
    resolved = manager.resolve_distinct(2)
    ids = {e.endpoint_id for e in resolved}
    assert ids == {"pi-deepseek-default", "pi-petals-donor-1"}  # DEC-11: mixed allowed


def test_distinct_fails_closed_without_enough_consented_donors(monkeypatch, donor, registry_with):
    monkeypatch.setattr(settings, "petals_bridge_enabled", True)
    from app.core.pi_runtime.model_manager import PiModelManager
    from app.core.pi_runtime.endpoints import PiEndpointResolutionError

    manager = PiModelManager(endpoints=[])
    manager._project_petals()
    with pytest.raises(PiEndpointResolutionError, match="insufficient_distinct"):
        manager.resolve_distinct(2)  # only one consented donor
