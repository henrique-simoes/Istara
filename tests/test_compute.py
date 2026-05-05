"""Tests for Compute API routes — nodes, stats."""

import asyncio

import pytest
from starlette.websockets import WebSocketDisconnect
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token
from app.core.compute_registry import ComputeNode, ComputeRegistry, compute_registry
from app.api.routes.compute import relay_websocket


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_compute_nodes_returns_list(auth_headers):
    """GET /api/compute/nodes returns compute nodes."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/nodes", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert "nodes" in body
        assert "total_nodes" in body


@pytest.mark.asyncio
async def test_compute_nodes_requires_auth():
    """Compute nodes requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/nodes")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_compute_stats_returns_response(auth_headers):
    """GET /api/compute/stats returns compute stats."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/compute/stats", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "total_nodes" in body


class FakeWebSocket:
    def __init__(self):
        self.sent: list[dict] = []
        self.sent_event = asyncio.Event()

    async def send_json(self, payload: dict):
        self.sent.append(payload)
        self.sent_event.set()


@pytest.mark.asyncio
async def test_relay_node_chat_uses_websocket_response_path():
    """Relay nodes must execute over the authenticated websocket, not backend HTTP."""
    fake_ws = FakeWebSocket()
    node = ComputeNode(
        node_id="relay-1",
        name="Relay Test",
        host="http://10.0.0.5:11434",
        source="relay",
        provider_type="ollama",
        is_healthy=True,
        websocket=fake_ws,
        loaded_models=["llama3"],
    )

    task = asyncio.create_task(node.chat([{"role": "user", "content": "hi"}], model="llama3"))
    await asyncio.wait_for(fake_ws.sent_event.wait(), timeout=1)
    request = fake_ws.sent[0]
    assert request["type"] == "llm_request"
    assert request["request_id"].startswith("relay-")

    node.pending_requests[request["request_id"]].set_result(
        {
            "request_id": request["request_id"],
            "result": {"message": {"role": "assistant", "content": "ok"}},
        }
    )
    result = await asyncio.wait_for(task, timeout=1)
    assert result["message"]["content"] == "ok"
    assert node.pending_requests == {}


@pytest.mark.asyncio
async def test_relay_node_chat_timeout_cleans_pending_request():
    fake_ws = FakeWebSocket()
    node = ComputeNode(
        node_id="relay-timeout",
        name="Relay Timeout",
        host="http://10.0.0.5:11434",
        source="relay",
        provider_type="ollama",
        is_healthy=True,
        websocket=fake_ws,
        loaded_models=["llama3"],
        relay_request_timeout_s=0.01,
    )

    with pytest.raises(RuntimeError, match="timed out"):
        await node.chat([{"role": "user", "content": "hi"}], model="llama3")
    assert node.pending_requests == {}
    assert "timed out" in node.health_error


@pytest.mark.asyncio
async def test_relay_node_embed_uses_websocket_response_path():
    fake_ws = FakeWebSocket()
    node = ComputeNode(
        node_id="relay-embed",
        name="Relay Embed",
        host="http://10.0.0.5:11434",
        source="relay",
        provider_type="ollama",
        is_healthy=True,
        websocket=fake_ws,
        loaded_models=["nomic-embed-text"],
    )

    task = asyncio.create_task(node.embed("hello", model="nomic-embed-text"))
    await asyncio.wait_for(fake_ws.sent_event.wait(), timeout=1)
    request = fake_ws.sent[0]
    assert request["type"] == "embed_request"
    node.pending_requests[request["request_id"]].set_result(
        {"request_id": request["request_id"], "result": [0.1, 0.2, 0.3]}
    )
    assert await asyncio.wait_for(task, timeout=1) == [0.1, 0.2, 0.3]
    assert node.pending_requests == {}


def test_relay_disconnect_fails_pending_requests():
    loop = asyncio.new_event_loop()
    try:
        future = loop.create_future()
        node = ComputeNode(
            node_id="relay-disconnect",
            name="Relay Disconnect",
            host="",
            source="relay",
            provider_type="ollama",
            pending_requests={"req-1": future},
        )
        node.fail_pending_requests("Relay disconnected before responding")
        assert node.pending_requests == {}
        assert future.done()
        with pytest.raises(RuntimeError, match="Relay disconnected"):
            future.result()
    finally:
        loop.close()


def test_total_capacity_counts_relay_and_browser_nodes():
    original_nodes = dict(compute_registry._nodes)
    try:
        compute_registry._nodes.clear()
        compute_registry.register_node(
            ComputeNode(
                node_id="relay-1",
                name="Relay",
                host="",
                source="relay",
                provider_type="ollama",
                is_healthy=True,
                last_heartbeat=9999999999,
            )
        )
        compute_registry.register_node(
            ComputeNode(
                node_id="browser-1",
                name="Browser",
                host="",
                source="browser",
                provider_type="lmstudio",
                is_healthy=True,
                last_heartbeat=9999999999,
            )
        )
        compute_registry.register_node(
            ComputeNode(
                node_id="network-1",
                name="Network",
                host="",
                source="network",
                provider_type="ollama",
                is_healthy=True,
            )
        )
        assert compute_registry.total_capacity() == 2
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


def test_select_candidates_filters_saturated_nodes_and_prefers_score():
    registry = ComputeRegistry()
    saturated = ComputeNode(
        node_id="saturated",
        name="Saturated",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        active_requests=4,
        max_active_requests=4,
    )
    available = ComputeNode(
        node_id="available",
        name="Available",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        active_requests=1,
        max_active_requests=4,
        ram_available_gb=8,
    )
    registry.register_node(saturated)
    registry.register_node(available)

    candidates = registry._select_candidates()

    assert [node.node_id for node in candidates] == ["available"]


def test_openai_compatible_endpoint_paths_respect_provider_base_url():
    gemini = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="network",
        provider_type="gemini_openai",
    )
    lmstudio = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
    )
    explicit_v1 = ComputeNode(
        node_id="openai",
        name="OpenAI-compatible",
        host="https://api.example.com/v1",
        source="network",
        provider_type="openai_compat",
    )

    assert gemini._openai_endpoint("chat/completions") == "chat/completions"
    assert lmstudio._openai_endpoint("chat/completions") == "v1/chat/completions"
    assert explicit_v1._openai_endpoint("models") == "models"


def test_select_candidates_prefers_requested_model_before_score():
    registry = ComputeRegistry()
    fast_wrong_model = ComputeNode(
        node_id="fast-wrong",
        name="Fast Wrong",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        priority=0,
        ram_available_gb=10,
        loaded_models=["other-model"],
    )
    slower_requested_model = ComputeNode(
        node_id="slower-requested",
        name="Slower Requested",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        priority=25,
        loaded_models=["llama3:latest"],
    )
    registry.register_node(fast_wrong_model)
    registry.register_node(slower_requested_model)

    candidates = registry._select_candidates(model="llama3")

    assert [node.node_id for node in candidates] == ["slower-requested", "fast-wrong"]


def test_select_candidates_strict_model_filters_missing_models():
    registry = ComputeRegistry()
    wrong_model = ComputeNode(
        node_id="wrong",
        name="Wrong",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["other-model"],
    )
    requested_model = ComputeNode(
        node_id="requested",
        name="Requested",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["llama3"],
    )
    registry.register_node(wrong_model)
    registry.register_node(requested_model)

    candidates = registry._select_candidates(model="llama3", strict_model=True)

    assert [node.node_id for node in candidates] == ["requested"]


def test_record_failure_degrades_before_cooldown():
    node = ComputeNode(
        node_id="node",
        name="Node",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
    )

    ComputeRegistry._record_failure(node, RuntimeError("temporary"))

    assert node.is_healthy is True
    assert node.health_state == "degraded"
    assert node.consecutive_failures == 1

    ComputeRegistry._record_failure(node, RuntimeError("temporary"))
    ComputeRegistry._record_failure(node, RuntimeError("temporary"))

    assert node.is_healthy is False
    assert node.health_state == "cooldown"


def test_compute_stats_include_capacity_envelope():
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="busy-local",
            name="Busy Local",
            host="http://localhost:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=True,
            active_requests=2,
            max_active_requests=4,
            ram_total_gb=16,
            ram_available_gb=4,
            cpu_cores=8,
            cpu_load_pct=80,
            loaded_models=["llama3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="saturated-relay",
            name="Saturated Relay",
            host="",
            source="relay",
            provider_type="ollama",
            is_healthy=True,
            active_requests=2,
            max_active_requests=2,
            cpu_load_pct=50,
        )
    )

    stats = registry.get_stats()

    assert stats["request_slots_total"] == 6
    assert stats["request_slots_used"] == 4
    assert stats["request_slots_available"] == 2
    assert stats["saturated_nodes"] == 1
    assert stats["hardware_load_pct"] == 65.0


class FakeRelayWebSocket:
    def __init__(self, *, headers=None, query_params=None, messages=None):
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.client = type("Client", (), {"host": "10.0.0.22"})()
        self.messages = list(messages or [])
        self.accepted = False
        self.close_code = None
        self.close_reason = ""
        self.sent: list[dict] = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=""):
        self.close_code = code
        self.close_reason = reason

    async def receive_text(self):
        if not self.messages:
            raise WebSocketDisconnect()
        return self.messages.pop(0)

    async def send_json(self, payload: dict):
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_relay_websocket_rejects_missing_auth():
    ws = FakeRelayWebSocket()

    await relay_websocket(ws)

    assert not ws.accepted
    assert ws.close_code == 4001
    assert "Authentication required" in ws.close_reason


@pytest.mark.asyncio
async def test_relay_websocket_accepts_network_token_and_cleans_up_node():
    original_nodes = dict(compute_registry._nodes)
    original_network_token = settings.network_access_token
    try:
        compute_registry._nodes.clear()
        settings.network_access_token = "relay-test-token"
        ws = FakeRelayWebSocket(
            headers={"x-access-token": "relay-test-token"},
            messages=[
                '{"type":"register","hostname":"relay-host","user_id":"relay-user",'
                '"provider_type":"ollama","provider_host":"http://localhost:11434",'
                '"loaded_models":["llama3"],"ram_total_gb":16,"cpu_cores":8}'
            ],
        )

        await relay_websocket(ws)

        assert ws.accepted
        assert ws.sent[0]["type"] == "registered"
        assert compute_registry._nodes == {}
    finally:
        settings.network_access_token = original_network_token
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)


@pytest.mark.asyncio
async def test_relay_websocket_accepts_browser_jwt():
    original_nodes = dict(compute_registry._nodes)
    try:
        compute_registry._nodes.clear()
        token = create_token("browser-user", "donor", "researcher")
        ws = FakeRelayWebSocket(
            query_params={"token": token},
            messages=[
                '{"type":"register","hostname":"browser","user_id":"browser",'
                '"provider_type":"lmstudio","provider_host":"http://localhost:1234",'
                '"loaded_models":["local-model"]}'
            ],
        )

        await relay_websocket(ws)

        assert ws.accepted
        assert ws.sent[0]["type"] == "registered"
        assert compute_registry._nodes == {}
    finally:
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)
