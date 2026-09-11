"""Coupled adversarial same-model isolation proof (AC-3 / Plan C D-C4).

This is the mandated one-fixture proof for finding F-2 / RF-2: a Pi-private API
endpoint and an authorized relay donor that advertise the *exact same model
alias* are configured together, and both isolation directions are asserted with
transport spies in a single test:

  * Direction 1 — a selected Pi request drives the real pi-agent-core worker
    straight to the pinned API endpoint (a loopback HTTP server records the
    call), produces **zero donor frames** (the same-model donor's transport is
    never invoked and it is never even scheduled), and the Pi endpoint never
    enters ``ComputeRegistry``.
  * Direction 2 — an ordinary Istara request for that same model alias still
    selects and is served by the donor through ordinary donated scheduling.

Negative twin: donated scheduling (``ComputeRegistry._select_candidates`` /
``_nodes``) never contains the Pi resolver's endpoint entries or its base URL.

Prior tests proved these facts *separately* (resolver identity, a loopback Pi
HTTP turn, and ordinary donor preference); this test couples them so a
regression that re-routes selected Pi traffic through the shared registry — the
exact F-2 collision — makes the donor spy fire and fails the isolation
acceptance.
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.config import PiApiEndpoint, settings
from app.core.compute_node import ComputeNode
from app.core.compute_registry import compute_registry
from app.core.pi_runtime.endpoints import DEFAULT_ENDPOINT_ID, PiEndpointResolver
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.database import init_db

from .harness import requires_node

pytestmark = requires_node


@pytest.mark.asyncio
async def test_same_model_pi_endpoint_and_donor_prove_bidirectional_isolation(
    monkeypatch,
):
    await init_db()

    # One shared model alias advertised by BOTH the Pi endpoint and the donor.
    shared_model = f"pi-shared-collision-{uuid.uuid4().hex}"
    project_id = f"pi-collision-project-{uuid.uuid4().hex}"
    pi_endpoint_id = f"pi-collision-endpoint-{uuid.uuid4().hex}"
    donor_id = f"relay-collision-donor-{uuid.uuid4().hex}"

    # ---- Pinned Pi API endpoint: real loopback HTTP transport spy ----------
    pi_endpoint_requests: list[str] = []

    class _PiEndpointStub(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence
            pass

        def do_POST(self):
            pi_endpoint_requests.append(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for piece in ["Hello from ", "the pinned Istara Pi endpoint."]:
                chunk = {"choices": [{"index": 0, "delta": {"content": piece}}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            done = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            self.wfile.write(f"data: {json.dumps(done)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    pi_server = ThreadingHTTPServer(("127.0.0.1", 0), _PiEndpointStub)
    threading.Thread(target=pi_server.serve_forever, daemon=True).start()
    pi_base_url = f"http://127.0.0.1:{pi_server.server_address[1]}"

    # The real resolver — the Pi-private plane. The Keychain read is stubbed so
    # no real secret is required; the secret never leaves the private bind frame.
    monkeypatch.setattr(
        "app.core.pi_runtime.endpoints._read_macos_keychain_secret",
        lambda *_: "collision-test-key",
    )
    resolver = PiEndpointResolver(
        [
            PiApiEndpoint(
                endpoint_id=pi_endpoint_id,
                provider_kind="openai_compat",
                base_url=pi_base_url,
                model=shared_model,
                keychain_service="pi-collision-test",
            )
        ]
    )

    # ---- Authorized same-model donor in ordinary donated scheduling --------
    donor = ComputeNode(
        node_id=donor_id,
        name="Same-Model Relay Donor",
        host="http://donor.invalid:1234/v1",
        source="relay",
        provider_type="openai_compat",
        is_relay=True,
        is_healthy=True,
        health_state="ready",
        priority=1,
        loaded_models=[shared_model],
        allowed_project_ids=[project_id],
        last_heartbeat=9999999999,
        websocket=object(),
    )
    # Transport spy: every invocation of the donor's transport is a "donor frame".
    donor_frames: list[tuple[str, str | None]] = []

    async def _spy_chat(messages, **kwargs):
        donor_frames.append(("chat", kwargs.get("model")))
        return {"message": {"role": "assistant", "content": "donor served the request"}}

    async def _spy_chat_stream(messages, **kwargs):
        donor_frames.append(("chat_stream", kwargs.get("model")))
        yield "donor served the request"

    monkeypatch.setattr(donor, "chat", _spy_chat)
    monkeypatch.setattr(donor, "chat_stream", _spy_chat_stream)

    original_strict = settings.strict_auto_routing
    settings.strict_auto_routing = True
    compute_registry.register_node(donor)

    supervisor = PiRuntimeSupervisor()
    service = PiExecutionService(resolver=resolver, supervisor=supervisor)

    async def _no_tools(name, params, pid, aid):  # pragma: no cover - no tools bound
        return {"success": True, "result": "unused"}

    pi_events: list[dict] = []
    try:
        # ---- Negative twin: donated scheduling never holds resolver entries -
        assert pi_endpoint_id not in compute_registry._nodes
        assert DEFAULT_ENDPOINT_ID not in compute_registry._nodes
        assert all(
            getattr(node, "host", "") != pi_base_url
            for node in compute_registry._nodes.values()
        )
        # The Pi-private plane resolves the shared alias by exact identity...
        resolved = resolver.resolve(pi_endpoint_id, model=shared_model)
        assert resolved.endpoint_id == pi_endpoint_id
        assert resolved.model == shared_model
        # ...yet that identity is invisible to donated candidate selection: the
        # only candidate for the shared alias is the ordinary donor.
        pre_candidates = compute_registry._select_candidates(
            model=shared_model, strict_model=True, project_id=project_id
        )
        assert [node.node_id for node in pre_candidates] == [donor_id]

        # ---- Direction 1: selected Pi request → pinned endpoint, zero donor -
        async for event in service.run_chat_turn(
            project_id=project_id,
            agent_id="istara-main",
            system_prompt="Pi owns the loop; Istara owns state.",
            history=[],
            user_text="Say hello.",
            tool_executor=_no_tools,
            endpoint_id=pi_endpoint_id,
            allowed_tools=[],
        ):
            pi_events.append(event)

        # The Pi turn genuinely reached its pinned API endpoint over real HTTP...
        assert pi_endpoint_requests, "Pi request never reached the pinned API endpoint"
        pi_text = "".join(
            e.get("text", "") for e in pi_events if e["type"] == "content"
        )
        assert "pinned Istara Pi endpoint" in pi_text
        done = [e for e in pi_events if e["type"] == "done"]
        assert done and done[0]["endpoint_id"] == pi_endpoint_id
        # ...and never produced a single donor frame or donor scheduling event.
        assert donor_frames == [], "selected Pi traffic reached the same-model donor"
        assert donor.selected_request_count == 0
        assert donor.served_request_count == 0
        pi_calls_after_pi_turn = len(pi_endpoint_requests)

        # ---- Direction 2: ordinary Istara request → donor selected & serves -
        result = await compute_registry.chat(
            [{"role": "user", "content": "hello"}],
            model=shared_model,
            project_id=project_id,
        )
        assert donor_frames and donor_frames[0][0] == "chat"
        assert result["_istara_route"]["node_id"] == donor_id
        assert donor.selected_request_count == 1
        assert donor.served_request_count == 1
        # The ordinary same-model request never leaked onto the Pi endpoint.
        assert len(pi_endpoint_requests) == pi_calls_after_pi_turn
    finally:
        compute_registry.remove_node(donor_id)
        settings.strict_auto_routing = original_strict
        await supervisor.shutdown()
        pi_server.shutdown()

    # Owned teardown: no live Pi worker survives the test.
    assert supervisor.is_running is False
