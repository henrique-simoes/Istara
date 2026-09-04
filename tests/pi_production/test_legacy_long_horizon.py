"""Deterministic legacy-loop horizon parity over Pi Model Management."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import TurnParams
from app.core.pi_runtime.model_manager import PiModelManager

from .harness import faux_endpoint, final_text


def _isolated(manager: PiModelManager) -> PiModelManager:
    """Keep the deterministic catalog database-independent like other W1 tests."""
    manager._db_projected = True  # noqa: SLF001
    return manager


@pytest.mark.asyncio
async def test_legacy_chat_tool_loop_survives_pi_worker_horizon_with_shared_manager(
    monkeypatch,
):
    """Seven canonical tool rounds and a final answer stay Pi-governed."""

    endpoint = replace(
        faux_endpoint([final_text("unused")], endpoint_id="pi-legacy-horizon"),
        model="legacy-horizon-model",
    )
    manager = _isolated(PiModelManager(endpoints=[endpoint], include_local=False))

    def _provider_message(call_id: str, title: str) -> dict:
        return {
            "text": "",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": "create_task",
                        "arguments": '{"title": "' + title + '"}',
                    },
                }
            ],
            "status": "success",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "stop_reason": "tool_calls",
        }

    scripted = [
        _provider_message(f"legacy-horizon-{index}", f"legacy horizon step {index}")
        for index in range(1, 8)
    ]
    scripted.append(
        {
            "text": "Legacy loop completed the full governed horizon.",
            "tool_calls": [],
            "status": "success",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "stop_reason": "stop",
        }
    )

    class _ManagedProviderService:
        def __init__(self):
            self.calls: list[dict] = []

        def model_manager(self):
            return manager

        async def run_provider_turn(self, **kwargs):
            resolved = manager.resolve(
                endpoint_id=kwargs["params"].endpoint_id,
                project_id=kwargs["project_id"],
            )
            self.calls.append(
                {
                    "messages": list(kwargs["messages"]),
                    "endpoint_id": resolved.endpoint_id,
                    "model": resolved.model,
                }
            )
            result = scripted[len(self.calls) - 1]
            return {
                **result,
                "endpoint_id": resolved.endpoint_id,
                "model": resolved.model,
                "served_model": resolved.model,
                "route_evidence": {
                    "plane": "pi-managed",
                    "endpoint_id": resolved.endpoint_id,
                    "model": resolved.model,
                    "served_model": resolved.model,
                },
            }

    service = _ManagedProviderService()
    recorded: list[dict] = []

    async def capture(**kwargs):
        recorded.append(kwargs)

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", capture)

    async def tool_executor(name, params, project_id, agent_id):
        assert (name, project_id, agent_id) == ("create_task", "p1", "istara-main")
        return {"success": True, "result": f"created {params['title']}"}

    result = await AgenticDispatcher(pi_service=service).chat_turn(
        project_id="p1",
        agent_id="istara-main",
        session_key="p1:legacy-horizon",
        system_prompt="Istara owns the loop; Pi owns provider authority.",
        messages=[],
        user_text="Complete the seven-step task chain.",
        tool_executor=tool_executor,
        tool_names=["create_task"],
        params=TurnParams(endpoint_id=endpoint.endpoint_id, max_turns=8),
        engine="legacy",
        session_id="session-legacy-horizon",
    )

    assert result.status == "success"
    assert result.text == "Legacy loop completed the full governed horizon."
    assert result.endpoint_id == endpoint.endpoint_id
    assert result.model == endpoint.model
    assert result.served_model == endpoint.model
    assert len(service.calls) == 8
    assert [call["endpoint_id"] for call in service.calls] == [endpoint.endpoint_id] * 8
    assert [call["model"] for call in service.calls] == [endpoint.model] * 8
    assert service.calls[0]["messages"] == [
        {"role": "user", "content": "Complete the seven-step task chain."}
    ]
    assert [message["role"] for message in service.calls[-1]["messages"]] == (
        ["user"] + [role for _ in range(7) for role in ("assistant", "tool")]
    )
    assert len(result.tool_calls) == 7
    assert [call["params"]["title"] for call in result.tool_calls] == [
        f"legacy horizon step {index}" for index in range(1, 8)
    ]
    assert len(recorded) == 1
    assert recorded[0]["engine"] == "legacy"
    assert recorded[0]["model"] == endpoint.model
    assert recorded[0]["session_id"] == "session-legacy-horizon"
    assert recorded[0]["outcome"]["usage"] == {
        "input_tokens": 8,
        "output_tokens": 8,
        "total_tokens": 16,
        "turns": 8,
        "estimate": False,
    }
