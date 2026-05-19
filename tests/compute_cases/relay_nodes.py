from tests.compute_cases.common import *

class FakeWebSocket:
    def __init__(self):
        self.sent: list[dict] = []
        self.sent_event = asyncio.Event()

    async def send_json(self, payload: dict):
        self.sent.append(payload)
        self.sent_event.set()


class FakeStreamResponse:
    def __init__(self, lines: list[str]):
        self.lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class FakeStreamingClient:
    def __init__(self):
        self.requests: list[dict] = []

    def stream(self, method: str, path: str, json: dict, timeout=None):
        self.requests.append(
            {
                "method": method,
                "path": path,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeStreamResponse(
            [
                'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}',
                "data: [DONE]",
            ]
        )


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
        allowed_project_ids=["project-a"],
    )

    task = asyncio.create_task(
        node.chat(
            [{"role": "user", "content": "hi"}],
            model="llama3",
            project_id="project-a",
        )
    )
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
        allowed_project_ids=["project-a"],
        relay_request_timeout_s=0.01,
    )

    with pytest.raises(RuntimeError, match="timed out"):
        await node.chat(
            [{"role": "user", "content": "hi"}],
            model="llama3",
            project_id="project-a",
        )
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
        allowed_project_ids=["project-a"],
    )

    task = asyncio.create_task(
        node.embed("hello", model="nomic-embed-text", project_id="project-a")
    )
    await asyncio.wait_for(fake_ws.sent_event.wait(), timeout=1)
    request = fake_ws.sent[0]
    assert request["type"] == "embed_request"
    node.pending_requests[request["request_id"]].set_result(
        {"request_id": request["request_id"], "result": [0.1, 0.2, 0.3]}
    )
    assert await asyncio.wait_for(task, timeout=1) == [0.1, 0.2, 0.3]
    assert node.pending_requests == {}


@pytest.mark.asyncio
async def test_relay_node_chat_requires_project_scope_before_websocket_dispatch():
    fake_ws = FakeWebSocket()
    node = ComputeNode(
        node_id="relay-unauthorized",
        name="Relay Unauthorized",
        host="http://10.0.0.5:11434",
        source="relay",
        provider_type="ollama",
        is_healthy=True,
        websocket=fake_ws,
        loaded_models=["llama3"],
        allowed_project_ids=["project-a"],
    )

    with pytest.raises(RuntimeError, match="project_id is required"):
        await node.chat([{"role": "user", "content": "hi"}], model="llama3")
    with pytest.raises(RuntimeError, match="not authorized"):
        await node.chat(
            [{"role": "user", "content": "hi"}],
            model="llama3",
            project_id="project-b",
        )
    assert fake_ws.sent == []
    assert node.pending_requests == {}


@pytest.mark.asyncio
async def test_relay_node_chat_stream_requires_project_scope_before_direct_dispatch():
    node = ComputeNode(
        node_id="relay-stream-unauthorized",
        name="Relay Stream Unauthorized",
        host="http://10.0.0.5:1234",
        source="relay",
        provider_type="lmstudio",
        is_healthy=True,
        websocket=None,
        loaded_models=["llama3"],
        allowed_project_ids=["project-a"],
    )

    async def fail_get_client():
        raise AssertionError("unauthorized stream opened an HTTP client")

    node._get_client = fail_get_client

    with pytest.raises(RuntimeError, match="project_id is required"):
        async for _ in node.chat_stream([{"role": "user", "content": "secret"}], model="llama3"):
            pass
    with pytest.raises(RuntimeError, match="not authorized"):
        async for _ in node.chat_stream(
            [{"role": "user", "content": "secret"}],
            model="llama3",
            project_id="project-b",
        ):
            pass
    assert node.pending_requests == {}


@pytest.mark.asyncio
async def test_relay_node_chat_stream_allows_authorized_direct_dispatch():
    fake_client = FakeStreamingClient()
    node = ComputeNode(
        node_id="relay-stream-authorized",
        name="Relay Stream Authorized",
        host="http://10.0.0.5:1234",
        source="relay",
        provider_type="lmstudio",
        is_healthy=True,
        websocket=None,
        loaded_models=["llama3"],
        allowed_project_ids=["project-a"],
    )

    async def get_client():
        return fake_client

    node._get_client = get_client

    chunks = []
    async for chunk in node.chat_stream(
        [{"role": "user", "content": "allowed"}],
        model="llama3",
        project_id="project-a",
    ):
        chunks.append(chunk)

    assert chunks == ["ok"]
    assert len(fake_client.requests) == 1
    assert fake_client.requests[0]["json"]["messages"] == [
        {"role": "user", "content": "allowed"}
    ]


@pytest.mark.asyncio
async def test_relay_node_embeddings_require_authorized_project_scope():
    fake_ws = FakeWebSocket()
    node = ComputeNode(
        node_id="relay-embed-unauthorized",
        name="Relay Embed Unauthorized",
        host="http://10.0.0.5:11434",
        source="relay",
        provider_type="ollama",
        is_healthy=True,
        websocket=fake_ws,
        loaded_models=["nomic-embed-text"],
        allowed_project_ids=["project-a"],
    )

    with pytest.raises(RuntimeError, match="project_id is required"):
        await node.embed("secret project text", model="nomic-embed-text")
    with pytest.raises(RuntimeError, match="not authorized"):
        await node.embed(
            "secret project text",
            model="nomic-embed-text",
            project_id="project-b",
        )
    with pytest.raises(RuntimeError, match="not authorized"):
        await node.embed_batch(
            ["secret project text"],
            model="nomic-embed-text",
            project_id="project-b",
        )
    assert fake_ws.sent == []
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
