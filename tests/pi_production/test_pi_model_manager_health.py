"""PI catalog admission must exclude unhealthy and donor persisted endpoints."""

from __future__ import annotations

import json
import uuid

import pytest

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.pi_runtime.endpoints import PiEndpointResolutionError, PiEndpointResolver
from app.core.pi_runtime.model_manager import PiModelManager
from app.models.database import async_session, init_db
from app.models.llm_server import LLMServer


def test_dispatcher_exposes_exactly_the_five_contract_verbs():
    for verb in ("chat_turn", "completion", "structured", "ensemble", "embed"):
        assert callable(getattr(AgenticDispatcher, verb, None)), f"missing verb {verb}"


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
