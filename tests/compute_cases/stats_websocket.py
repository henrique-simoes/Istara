from tests.compute_cases.common import *

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
