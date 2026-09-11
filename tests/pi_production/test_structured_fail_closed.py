"""F-W1-2: forced structured-output protocol (v2) fail-closed contracts.

Covers the typed fail-closed behavior of ``PiExecutionService.run_structured``
and the both-side protocol version validation:

* the forced ``emit_structured_output`` call is captured (never executed
  host-side) and revalidated against the ORIGINAL schema;
* free-form JSON text is never accepted as structured output;
* an unsupported schema fails before any model call;
* exactly one bounded repair is allowed, then a typed ``PiRuntimeTurnError``
  is raised (no error-shaped artifact, no partial value);
* a worker answering the handshake with a mismatched protocol version is
  refused with a typed ``PiWorkerError``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core.agentic.types import TurnParams
from app.core.pi_runtime.endpoints import PiRuntimeTurnError
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor, PiWorkerError

from .harness import faux_service, final_text, requires_node, tool_call

_SCHEMA = {
    "type": "object",
    "properties": {"accepted": {"type": "boolean"}},
    "required": ["accepted"],
    "additionalProperties": False,
}

_KWARGS: dict[str, Any] = {
    "purpose": "w1.structured",
    "project_id": "p1",
    "agent_id": "istara-main",
    "system": "return JSON",
    "messages": [{"role": "user", "content": "go"}],
    "params": TurnParams(),
}


@requires_node
@pytest.mark.asyncio
async def test_structured_captures_forced_tool_without_authority_round_trip():
    supervisor = PiRuntimeSupervisor()
    service = faux_service(
        [tool_call("emit_structured_output", {"accepted": True})], supervisor
    )
    try:
        result = await service.run_structured(schema=_SCHEMA, **_KWARGS)
    finally:
        await supervisor.shutdown()
    assert result["value"] == {"accepted": True}
    # Captured, not executed: the forced tool never reached the authority.
    assert result["tool_calls"] == []


@requires_node
@pytest.mark.asyncio
async def test_freeform_json_text_is_never_accepted_and_fails_closed():
    # Both the initial turn and the one bounded repair answer with free-form
    # JSON text only — never the forced tool. The outcome must be a typed
    # failure, not a parsed artifact.
    supervisor = PiRuntimeSupervisor()
    service = faux_service(
        [final_text('{"accepted": true}'), final_text('{"accepted": true}')], supervisor
    )
    try:
        with pytest.raises(PiRuntimeTurnError, match="structured_output_missing"):
            await service.run_structured(schema=_SCHEMA, **_KWARGS)
    finally:
        await supervisor.shutdown()


@pytest.mark.asyncio
async def test_second_invalid_object_raises_typed_failure_with_no_partial_artifact():
    class InvalidTwiceService(PiExecutionService):
        def __init__(self) -> None:
            self.calls = 0

        async def _collect_turn(self, **kwargs: Any) -> dict[str, Any]:
            self.calls += 1
            return {
                "text": "",
                "tool_calls": [],
                "status": "success",
                "usage": {},
                "stop_reason": "toolUse",
                "endpoint_id": "pi-faux",
                "structured": {"wrong": True},  # fails the original schema
                "error": None,
            }

    service = InvalidTwiceService()
    with pytest.raises(
        PiRuntimeTurnError, match="structured_output_invalid"
    ) as excinfo:
        await service.run_structured(schema=_SCHEMA, **_KWARGS)
    # Exactly one bounded repair (two attempts), then the typed failure — and
    # the failure carries no value payload a caller could mistake for output.
    assert service.calls == 2
    assert not hasattr(excinfo.value, "value")


@pytest.mark.asyncio
async def test_missing_capture_on_success_frame_is_an_invalid_result():
    class NoCaptureService(PiExecutionService):
        async def _collect_turn(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "text": '{"accepted": true}',  # free-form text, no capture
                "tool_calls": [],
                "status": "success",
                "usage": {},
                "stop_reason": "stop",
                "endpoint_id": "pi-faux",
                "structured": None,
                "error": None,
            }

    service = NoCaptureService()
    with pytest.raises(
        PiRuntimeTurnError, match="structured_output_invalid:structured_output_missing"
    ):
        await service.run_structured(schema=_SCHEMA, **_KWARGS)


@pytest.mark.asyncio
async def test_unsupported_schema_fails_before_any_model_call():
    supervisor = PiRuntimeSupervisor()
    service = faux_service([], supervisor)
    try:
        with pytest.raises(
            PiRuntimeTurnError, match=r"structured_output_schema_unsupported:.*\$ref"
        ):
            await service.run_structured(
                schema={"type": "object", "properties": {"a": {"$ref": "#/$defs/x"}}},
                **_KWARGS,
            )
        # The precheck fires before the turn driver: no worker was started.
        assert supervisor.is_running is False
    finally:
        await supervisor.shutdown()


@requires_node
@pytest.mark.asyncio
async def test_worker_with_mismatched_protocol_version_is_refused():
    stub = Path(__file__).parent / "adversarial_worker_v1.mjs"
    supervisor = PiRuntimeSupervisor(worker_entry=stub)
    try:
        with pytest.raises(PiWorkerError, match="protocol_version_mismatch"):
            await supervisor.ensure_started()
        assert supervisor.is_running is False
    finally:
        await supervisor.shutdown()
