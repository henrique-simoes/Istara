"""Engine-level proof that a selected Pi turn drives the real pi-ai provider HTTP
stack (openai_compat) against a loopback endpoint, resolves by exact endpoint
identity, and records endpoint-identity-only telemetry — never ComputeRegistry.
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import select

from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
from app.core.pi_runtime.engine import PiExecutionService, _map_frame
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.database import async_session, init_db
from app.models.telemetry_span import TelemetrySpan

from .harness import requires_node

pytestmark = requires_node


@pytest.mark.parametrize("identity_field", ["model", "served_model"])
def test_map_frame_rejects_contradictory_provider_route_identity(identity_field):
    """A provider route cannot override the top-level served-model receipt."""

    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-loopback",
        provider_kind="openai_compat",
        base_url="http://127.0.0.1:1",
        model="configured-model",
        api_key="loopback-test-key",
        timeout_ms=30000,
        max_retries=0,
    )
    event = _map_frame(
        {
            "type": "run.completed",
            "served_model": "provider-model",
            "route_evidence": {identity_field: "spoofed-model"},
        },
        endpoint,
    )

    assert event == {
        "type": "error",
        "error": "pi_provider_route_identity_mismatch",
    }


class _OpenAIStubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for piece in ["Hello from ", "the Istara Pi endpoint."]:
            # The model identity must come from the provider response, not the
            # endpoint request label.  This loopback receipt exercises the
            # worker's SSE observer and the Python engine propagation path.
            chunk = {"model": "stub-model", "choices": [{"index": 0, "delta": {"content": piece}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        done = {"model": "stub-model", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        self.wfile.write(f"data: {json.dumps(done)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class _FixedResolver:
    def __init__(self, endpoint: ResolvedPiEndpoint):
        self._endpoint = endpoint

    def resolve(self, endpoint_id: str, *, model=None) -> ResolvedPiEndpoint:
        return self._endpoint


@pytest.mark.asyncio
async def test_engine_drives_real_openai_compat_http_stack_and_records_endpoint_telemetry():
    await init_db()
    project_id = f"pi-prod-http-{uuid.uuid4()}"

    server = ThreadingHTTPServer(("127.0.0.1", 0), _OpenAIStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-loopback",
        provider_kind="openai_compat",
        base_url=base_url,
        model="stub-model",
        api_key="loopback-test-key",
        timeout_ms=30000,
        max_retries=0,
    )
    supervisor = PiRuntimeSupervisor()
    service = PiExecutionService(resolver=_FixedResolver(endpoint), supervisor=supervisor)

    events: list[dict] = []

    async def _no_tools(name, params, pid, aid):  # pragma: no cover - not exercised
        return {"success": True, "result": "unused"}

    try:
        async for event in service.run_chat_turn(
            project_id=project_id,
            agent_id="istara-main",
            system_prompt="Pi owns the loop.",
            history=[],
            user_text="Say hello.",
            tool_executor=_no_tools,
            allowed_tools=[],
        ):
            events.append(event)
    finally:
        await supervisor.shutdown()
        server.shutdown()

    text = "".join(e.get("text", "") for e in events if e["type"] == "content")
    assert "Istara Pi endpoint" in text  # streamed through the real HTTP stack

    done = [e for e in events if e["type"] == "done"]
    assert done and done[0]["endpoint_id"] == "pi-loopback"
    assert done[0]["stop_reason"] == "stop"
    assert done[0]["served_model"] == "stub-model"
    assert supervisor.is_running is False

    # Telemetry is keyed by endpoint identity only — never base URL/key/host.
    async with async_session() as db:
        span = await db.scalar(
            select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.operation == "pi_runtime_chat_turn",
            )
        )
    assert span is not None
    assert "pi-loopback" in span.route_id
    assert base_url not in span.route_id
    assert "loopback-test-key" not in span.route_id
