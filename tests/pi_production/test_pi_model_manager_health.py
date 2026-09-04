"""PI catalog admission must exclude unhealthy and donor persisted endpoints."""

from __future__ import annotations

import json
import uuid

import pytest

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.pi_runtime.endpoints import PiEndpointResolutionError, PiEndpointResolver
from app.core.pi_runtime.model_manager import PiModelManager, _CatalogEntry
from app.models.database import async_session, init_db
from app.models.llm_server import LLMServer


def test_dispatcher_exposes_exactly_the_five_contract_verbs():
    for verb in ("chat_turn", "completion", "structured", "ensemble", "embed"):
        assert callable(getattr(AgenticDispatcher, verb, None)), f"missing verb {verb}"


def test_explicit_catalog_resolves_first_admitted_endpoint_when_unqualified():
    """An injected authority catalog must not fall back to the built-in default."""
    from dataclasses import replace

    from tests.pi_production.harness import faux_endpoint, final_text

    first = replace(
        faux_endpoint([final_text("answer")], endpoint_id="pi-explicit-first"),
        model="explicit-model",
    )
    manager = PiModelManager(endpoints=[first], include_local=False)

    assert manager.resolve().endpoint_id == "pi-explicit-first"


@pytest.mark.asyncio
async def test_llm_server_projection_admits_only_healthy_non_donors():
    """Only healthy, non-relay rows can consume a Pi/Research Spine slot."""
    await init_db()
    server_id = f"srv-{uuid.uuid4().hex[:8]}"
    relay_id = f"relay-{uuid.uuid4().hex[:8]}"
    unhealthy_id = f"unhealthy-{uuid.uuid4().hex[:8]}"
    async with async_session() as session:
        session.add(
            LLMServer(
                id=server_id,
                name="Contract Server",
                provider_type="openai_compat",
                host="http://127.0.0.1:9/v1",
                is_local=False,
                is_healthy=True,
                capabilities=json.dumps(
                    {
                        "models": ["contract-model"],
                        "context_window": 65536,
                        "vision": True,
                    }
                ),
            )
        )
        session.add(
            LLMServer(
                id=relay_id,
                name="Relay Donor",
                provider_type="openai_compat",
                host="http://donor.invalid:1234/v1",
                is_local=False,
                is_healthy=True,
                is_relay=True,
                capabilities=json.dumps({"models": ["contract-model"]}),
            )
        )
        session.add(
            LLMServer(
                id=unhealthy_id,
                name="Unhealthy compatibility server",
                provider_type="openai_compat",
                host="http://unhealthy.invalid/v1",
                is_local=False,
                is_healthy=False,
                capabilities='{"models": ["unhealthy-model"]}',
            )
        )
        await session.commit()
    try:
        manager = PiModelManager(resolver=PiEndpointResolver([]), include_local=False)
        await manager.ensure_db_projection()
        info = {entry.endpoint_id: entry for entry in manager.catalog()}
        projected = manager.resolve(endpoint_id=f"pi-llm-{server_id}")
        assert projected.model == "contract-model"
        assert projected.supports_vision is True
        assert projected.context_window == 65536
        assert f"pi-llm-{relay_id}" not in info
        assert f"pi-llm-{unhealthy_id}" not in info
        with pytest.raises(PiEndpointResolutionError):
            manager.resolve(endpoint_id=f"pi-llm-{relay_id}")
        with pytest.raises(PiEndpointResolutionError):
            manager.resolve(endpoint_id=f"pi-llm-{unhealthy_id}")
    finally:
        async with async_session() as session:
            for row_id in (server_id, relay_id, unhealthy_id):
                row = await session.get(LLMServer, row_id)
                if row is not None:
                    await session.delete(row)
            await session.commit()


def test_available_model_identities_is_project_scoped_without_materializing_secrets():
    """Adaptive method selection must share Pi admission without resolving keys."""
    settings_entry = _CatalogEntry(
        endpoint_id="pi-settings-a",
        provider_kind="openai_compat",
        base_url="https://example.invalid/v1",
        model="settings-model",
        source="settings",
    )
    authorized_petals = _CatalogEntry(
        endpoint_id="pi-petals-a",
        provider_kind="openai_compat",
        base_url="http://127.0.0.1:8000/v1",
        model="petals-a",
        source="petals",
        kind="petals",
        allowed_project_ids=("project-a",),
    )
    unauthorized_petals = _CatalogEntry(
        endpoint_id="pi-petals-b",
        provider_kind="openai_compat",
        base_url="http://127.0.0.1:8000/v1",
        model="petals-b",
        source="petals",
        kind="petals",
        allowed_project_ids=("project-b",),
    )
    manager = PiModelManager(endpoints=[], include_local=False)
    manager._entries = {
        entry.endpoint_id: entry
        for entry in (settings_entry, authorized_petals, unauthorized_petals)
    }

    assert manager.available_model_identities(project_id="project-a") == (
        "settings-model",
        "petals-a",
    )
    assert manager.available_model_identities(project_id="project-b") == (
        "settings-model",
        "petals-b",
    )
    assert settings_entry.resolved is None


def test_catalog_is_project_scoped_for_chat_without_materializing_secrets():
    """Chat must not advertise a Petals donor outside its project allowlist."""
    settings_entry = _CatalogEntry(
        endpoint_id="pi-settings-a",
        provider_kind="openai_compat",
        base_url="https://example.invalid/v1",
        model="settings-model",
        source="settings",
    )
    authorized_petals = _CatalogEntry(
        endpoint_id="pi-petals-a",
        provider_kind="openai_compat",
        base_url="http://127.0.0.1:8000/v1",
        model="petals-a",
        source="petals",
        kind="petals",
        allowed_project_ids=("project-a",),
    )
    unauthorized_petals = _CatalogEntry(
        endpoint_id="pi-petals-b",
        provider_kind="openai_compat",
        base_url="http://127.0.0.1:8000/v1",
        model="petals-b",
        source="petals",
        kind="petals",
        allowed_project_ids=("project-b",),
    )
    manager = PiModelManager(endpoints=[], include_local=False)
    manager._entries = {
        entry.endpoint_id: entry
        for entry in (settings_entry, authorized_petals, unauthorized_petals)
    }

    assert {entry.endpoint_id for entry in manager.catalog(project_id="project-a")} == {
        "pi-settings-a",
        "pi-petals-a",
    }
    assert {entry.endpoint_id for entry in manager.catalog(project_id="project-b")} == {
        "pi-settings-a",
        "pi-petals-b",
    }
    assert settings_entry.resolved is None
