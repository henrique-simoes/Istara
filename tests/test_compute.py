"""Tests for Compute API routes — nodes, stats."""

import asyncio

import pytest
from starlette.websockets import WebSocketDisconnect
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.models.database import init_db
from app.core.auth import create_token
from app.core.compute_registry import ComputeNode, compute_registry
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
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            assert isinstance(response.json(), dict)


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
        assert response.status_code in (200, 404, 500)


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
