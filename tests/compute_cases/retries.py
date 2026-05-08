from tests.compute_cases.common import *

class _FailingChatClient:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.calls = 0

    async def post(self, path: str, json: dict):
        self.calls += 1
        request = httpx.Request("POST", f"http://test/{path}")
        response = httpx.Response(
            self.status_code,
            request=request,
            json={"error": {"message": "provider overloaded"}},
        )
        raise httpx.HTTPStatusError("provider overloaded", request=request, response=response)


class _SuccessfulChatClient:
    def __init__(self):
        self.calls = 0
        self.paths: list[str] = []

    async def post(self, path: str, json: dict):
        self.calls += 1
        self.paths.append(path)
        return httpx.Response(
            200,
            request=httpx.Request("POST", f"http://test/{path}"),
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "fallback answered",
                        }
                    }
                ]
            },
        )

async def test_chat_retries_transient_errors_before_fallback(monkeypatch):
    registry = ComputeRegistry()
    primary_client = _FailingChatClient(status_code=503)
    fallback_client = _SuccessfulChatClient()

    primary = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="network",
        provider_type="gemini_openai",
        is_healthy=True,
        priority=0,
        loaded_models=["gemini-live"],
    )
    fallback = ComputeNode(
        node_id="secondary",
        name="Secondary",
        host="http://192.0.2.142:1234",
        source="network",
        provider_type="openai_compat",
        is_healthy=True,
        priority=10,
        loaded_models=["qwen-live"],
    )

    async def primary_get_client():
        return primary_client

    async def fallback_get_client():
        return fallback_client

    monkeypatch.setattr(primary, "_get_client", primary_get_client)
    monkeypatch.setattr(fallback, "_get_client", fallback_get_client)
    registry.register_node(primary)
    registry.register_node(fallback)

    response = await registry.chat([{"role": "user", "content": "hello"}])

    assert response["message"]["content"] == "fallback answered"
    assert primary_client.calls == 5
    assert primary.cb_state == "open"
    assert fallback_client.calls == 1
    assert fallback_client.paths == ["v1/chat/completions"]


@pytest.mark.asyncio
async def test_chat_can_rescue_registered_unhealthy_fallback_after_primary_failure(monkeypatch):
    registry = ComputeRegistry()
    primary_client = _FailingChatClient(status_code=503)
    fallback_client = _SuccessfulChatClient()

    primary = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="network",
        provider_type="gemini_openai",
        is_healthy=True,
        priority=0,
        loaded_models=["gemini-live"],
    )
    fallback = ComputeNode(
        node_id="secondary",
        name="Secondary",
        host="http://192.0.2.142:1234",
        source="network",
        provider_type="openai_compat",
        is_healthy=False,
        health_state="unreachable",
        priority=10,
        loaded_models=["qwen-live"],
    )

    async def primary_get_client():
        return primary_client

    async def fallback_get_client():
        return fallback_client

    monkeypatch.setattr(primary, "_get_client", primary_get_client)
    monkeypatch.setattr(fallback, "_get_client", fallback_get_client)
    registry.register_node(primary)
    registry.register_node(fallback)

    response = await registry.chat([{"role": "user", "content": "hello"}])

    assert response["message"]["content"] == "fallback answered"
    assert primary_client.calls == 5
    assert fallback_client.calls == 1
    assert fallback.is_healthy is True

class _MislabelledOpenAIHealthClient:
    def __init__(self):
        self.paths: list[str] = []

    async def get(self, path: str, timeout: float | None = None):
        self.paths.append(path)
        if path == "/api/tags":
            return httpx.Response(
                200,
                request=httpx.Request("GET", "http://test/api/tags"),
                json={"error": "Unexpected endpoint or method."},
            )
        if path == "v1/models":
            return httpx.Response(
                200,
                request=httpx.Request("GET", "http://test/v1/models"),
                json={"data": [{"id": "qwen3.6-35b-a3b@q5_k_xl"}]},
            )
        raise AssertionError(f"unexpected health path {path}")


@pytest.mark.asyncio
async def test_health_check_normalizes_ollama_label_for_openai_compatible_server(
    monkeypatch,
):
    node = ComputeNode(
        node_id="secondary",
        name="Secondary",
        host="http://192.0.2.142:1234",
        source="network",
        provider_type="ollama",
        is_healthy=False,
    )
    client = _MislabelledOpenAIHealthClient()

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)

    assert await node.check_health() is True
    assert node.provider_type == "lmstudio"
    assert node.loaded_models == ["qwen3.6-35b-a3b@q5_k_xl"]
    assert client.paths == ["v1/models"]


@pytest.mark.asyncio
async def test_chat_does_not_retry_non_transient_http_errors(monkeypatch):
    registry = ComputeRegistry()
    primary_client = _FailingChatClient(status_code=401)
    fallback_client = _SuccessfulChatClient()

    primary = ComputeNode(
        node_id="auth-fail",
        name="Auth Fail",
        host="https://api.example.com/v1",
        source="network",
        provider_type="openai_compat",
        is_healthy=True,
        priority=0,
        loaded_models=["primary"],
    )
    fallback = ComputeNode(
        node_id="fallback",
        name="Fallback",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        priority=10,
        loaded_models=["fallback"],
    )

    async def primary_get_client():
        return primary_client

    async def fallback_get_client():
        return fallback_client

    monkeypatch.setattr(primary, "_get_client", primary_get_client)
    monkeypatch.setattr(fallback, "_get_client", fallback_get_client)
    registry.register_node(primary)
    registry.register_node(fallback)

    response = await registry.chat([{"role": "user", "content": "hello"}])

    assert response["message"]["content"] == "fallback answered"
    assert primary_client.calls == 1
    assert fallback_client.calls == 1


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


def test_auxiliary_failure_does_not_trip_chat_availability():
    node = ComputeNode(
        node_id="node",
        name="Node",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
    )

    for _ in range(5):
        ComputeRegistry._record_auxiliary_failure(node, RuntimeError("embedding quota"))

    assert node.is_healthy is True
    assert node.health_state == "degraded"
    assert node.consecutive_failures == 0
    assert node.cb_state == "closed"


@pytest.mark.asyncio
async def test_embedding_failure_does_not_cooldown_chat_node(monkeypatch):
    registry = ComputeRegistry()
    embedding_client = _FailingChatClient(status_code=429)
    node = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="network",
        provider_type="gemini_openai",
        is_healthy=True,
        priority=0,
        loaded_models=["gemini-live"],
    )

    async def node_get_client():
        return embedding_client

    monkeypatch.setattr(node, "_get_client", node_get_client)
    registry.register_node(node)

    with pytest.raises(RuntimeError, match="No compute nodes available for batch embedding"):
        await registry.embed_batch(["quota-limited text"])

    assert embedding_client.calls == 1
    assert node.is_healthy is True
    assert node.health_state == "degraded"
    assert node.consecutive_failures == 0
    assert node.cb_state == "closed"
