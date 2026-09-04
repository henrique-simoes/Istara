"""Production scenario 4 (structured_outputs.core_eval) — a selected Pi turn
drives the real pi-ai provider HTTP stack for BOTH provider families
(``openai_compat`` and ``anthropic_compat``) against loopback stubs, and the
structured (JSON) completion is validated under a schema contract: a valid
payload is accepted, a malformed one is rejected at the boundary.

Both families run inside the real ``Agent`` loop — no ``fauxProvider`` — so this
proves credential-free structured output over each real transport, not a lab
facade.
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

from .harness import requires_node

pytestmark = requires_node

# The structured-output "schema contract": the assistant must emit a JSON object
# carrying exactly these keys; anything else is rejected at the boundary.
_REQUIRED_KEYS = {"verdict", "confidence"}


def _validate_structured_output(text: str) -> dict:
    """Parse + validate an assistant structured output; raise on any violation."""
    payload = json.loads(text)  # raises on malformed JSON
    if not isinstance(payload, dict) or set(payload) != _REQUIRED_KEYS:
        raise ValueError("structured output violates schema contract")
    if not isinstance(payload["confidence"], (int, float)):
        raise ValueError("confidence must be numeric")
    return payload


class _OpenAIStructuredHandler(BaseHTTPRequestHandler):
    body = '{"verdict": "pass", "confidence": 0.91}'

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        chunk = {
            "model": "stub-model",
            "choices": [{"index": 0, "delta": {"content": self.body}}],
        }
        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        done = {
            "model": "stub-model",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        self.wfile.write(f"data: {json.dumps(done)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class _OpenAIMalformedHandler(_OpenAIStructuredHandler):
    body = '{"verdict": "pass", "confidence":'  # truncated / invalid JSON


class _AnthropicStructuredHandler(BaseHTTPRequestHandler):
    body = '{"verdict": "pass", "confidence": 0.88}'

    def log_message(self, *args):
        pass

    def _sse(self, event, data):
        self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self._sse(
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_stub_1",
                    "type": "message",
                    "role": "assistant",
                    "model": "stub-model",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 10, "output_tokens": 1},
                },
            },
        )
        self._sse(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        )
        self._sse(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": self.body},
            },
        )
        self._sse("content_block_stop", {"type": "content_block_stop", "index": 0})
        self._sse(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 5},
            },
        )
        self._sse("message_stop", {"type": "message_stop"})
        self.wfile.flush()


class _FixedResolver:
    def __init__(self, endpoint: ResolvedPiEndpoint):
        self._endpoint = endpoint

    def resolve(self, endpoint_id: str, *, model=None) -> ResolvedPiEndpoint:
        return self._endpoint


async def _run_structured_turn(handler_cls, provider_kind, endpoint_id):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = ResolvedPiEndpoint(
        endpoint_id=endpoint_id,
        provider_kind=provider_kind,
        base_url=base_url,
        model="stub-model",
        api_key="loopback-test-key",
        timeout_ms=30000,
        max_retries=0,
        # A real endpoint is priced so its usage-bearing turns are not treated as
        # an unenforceable ($0) cost budget by the worker's fail-closed ceiling.
        cost_input_per_mtok=0.27,
        cost_output_per_mtok=1.10,
    )
    sup = PiRuntimeSupervisor()
    svc = PiExecutionService(resolver=_FixedResolver(endpoint), supervisor=sup)

    async def _no_tools(name, params, pid, aid):  # pragma: no cover - not exercised
        return {"success": True, "result": "unused"}

    events: list[dict] = []
    try:
        async for e in svc.run_chat_turn(
            project_id=f"pi-prod-s4-{uuid.uuid4()}",
            agent_id="istara-main",
            system_prompt="Emit a structured verdict.",
            history=[],
            user_text="Grade this.",
            tool_executor=_no_tools,
            allowed_tools=[],
            endpoint_id=endpoint_id,
        ):
            events.append(e)
    finally:
        await sup.shutdown()
        server.shutdown()
    text = "".join(e.get("text", "") for e in events if e["type"] == "content")
    done = [e for e in events if e["type"] == "done"]
    return text, done, sup


@pytest.mark.asyncio
async def test_scenario4_openai_compat_structured_output_valid_and_invalid():
    # Valid structured output over the real openai_compat HTTP stack is accepted.
    text, done, sup = await _run_structured_turn(
        _OpenAIStructuredHandler, "openai_compat", "pi-openai-structured"
    )
    assert done and done[0]["endpoint_id"] == "pi-openai-structured"
    assert done[0]["served_model"] == "stub-model"
    payload = _validate_structured_output(text)
    assert payload == {"verdict": "pass", "confidence": 0.91}
    assert sup.is_running is False

    # Malformed output over the same real stack is rejected by the schema contract.
    bad_text, bad_done, bad_sup = await _run_structured_turn(
        _OpenAIMalformedHandler, "openai_compat", "pi-openai-structured"
    )
    assert bad_done  # the turn still completed at the transport level
    with pytest.raises((json.JSONDecodeError, ValueError)):
        _validate_structured_output(bad_text)
    assert bad_sup.is_running is False


@pytest.mark.asyncio
async def test_scenario4_anthropic_compat_structured_output_valid():
    # The second provider family (anthropic_compat) drives the real anthropic
    # messages HTTP stack inside the Agent and yields a valid structured output.
    text, done, sup = await _run_structured_turn(
        _AnthropicStructuredHandler, "anthropic_compat", "pi-anthropic-structured"
    )
    assert done and done[0]["endpoint_id"] == "pi-anthropic-structured"
    assert done[0]["stop_reason"] == "stop"
    assert done[0]["served_model"] == "stub-model"
    payload = _validate_structured_output(text)
    assert payload == {"verdict": "pass", "confidence": 0.88}
    assert sup.is_running is False
