"""W1 contracts: dispatcher accounting, structured revalidation and Pi catalog isolation."""

from __future__ import annotations

import pytest

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import TurnParams
from app.core.pi_runtime.endpoints import PiEndpointResolutionError
from app.core.pi_runtime.model_manager import PiModelManager
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.core.pi_runtime.engine import PiExecutionService
from tests.pi_production.harness import faux_service


@pytest.mark.asyncio
async def test_completion_uses_pi_service_and_records_one_usage_row(monkeypatch):
    supervisor = PiRuntimeSupervisor()
    service = faux_service([{"text": "done", "stop_reason": "stop"}], supervisor)
    recorded = []

    async def capture(**kwargs):
        recorded.append(kwargs)

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", capture)
    try:
        result = await AgenticDispatcher(pi_service=service).completion(
            purpose="w1.contract", project_id="p1", system="system",
            messages=[{"role": "user", "content": "hello"}], params=TurnParams(), engine="pi",
        )
    finally:
        await supervisor.shutdown()
    assert result.text == "done"
    assert len(recorded) == 1
    assert recorded[0]["engine"] == "pi"
    assert recorded[0]["purpose"] == "w1.contract"


@pytest.mark.asyncio
async def test_structured_rejects_invalid_json_after_one_repair(monkeypatch):
    class RepairingService(PiExecutionService):
        def __init__(self):
            self.calls = 0

        async def run_completion(self, **_kwargs):
            self.calls += 1
            return {"text": "not json" if self.calls == 1 else '{"accepted": true}', "status": "success"}

    service = RepairingService()

    async def no_op(**kwargs):
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op)
    result = await AgenticDispatcher(pi_service=service).structured(
        purpose="w1.structured", project_id="p1", system="return JSON",
        messages=[{"role": "user", "content": "go"}], schema={"type": "object", "required": ["accepted"]},
        params=TurnParams(), engine="pi",
    )
    assert result.value == {"accepted": True}
    assert service.calls == 2


def test_model_manager_fails_closed_for_unavailable_distinct_catalog():
    manager = PiModelManager(endpoints=[])
    with pytest.raises(PiEndpointResolutionError, match="insufficient_distinct"):
        manager.resolve_distinct(2)
