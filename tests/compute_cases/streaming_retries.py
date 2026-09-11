from tests.compute_cases.common import *


class _FailingStreamResponse:
    def __init__(self, path: str, status_code: int):
        self.path = path
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        request = httpx.Request("POST", f"http://test/{self.path}")
        response = httpx.Response(
            self.status_code,
            request=request,
            json={"error": {"message": "stream provider overloaded"}},
        )
        raise httpx.HTTPStatusError(
            "stream provider overloaded", request=request, response=response
        )

    async def aiter_lines(self):
        if False:
            yield ""


class _FailingStreamClient:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.calls = 0

    def stream(self, method: str, path: str, json: dict, timeout=None):
        self.calls += 1
        return _FailingStreamResponse(path, self.status_code)


class _SuccessfulStreamResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        yield 'data: {"choices":[{"delta":{"content":"fallback streamed"}}]}'
        yield "data: [DONE]"


class _SuccessfulStreamClient:
    def __init__(self):
        self.calls = 0
        self.paths: list[str] = []

    def stream(self, method: str, path: str, json: dict, timeout=None):
        self.calls += 1
        self.paths.append(path)
        return _SuccessfulStreamResponse()


async def test_chat_stream_retries_transient_errors_before_fallback(monkeypatch):
    registry = ComputeRegistry()
    primary_client = _FailingStreamClient(status_code=503)
    fallback_client = _SuccessfulStreamClient()

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

    chunks = [
        chunk
        async for chunk in registry.chat_stream([{"role": "user", "content": "hello"}])
    ]

    assert chunks == ["fallback streamed"]
    assert primary_client.calls == 5
    assert primary.cb_state == "open"
    assert fallback_client.calls == 1
    assert fallback_client.paths == ["v1/chat/completions"]
    assert fallback.is_healthy is True


@pytest.mark.asyncio
async def test_strict_model_stream_does_not_fallback_after_pinned_node_fails(
    monkeypatch,
):
    registry = ComputeRegistry()
    deepseek_client = _FailingStreamClient(status_code=503)
    fallback_client = _SuccessfulStreamClient()
    deepseek = ComputeNode(
        node_id="pi-deepseek-candidate",
        name="Pi DeepSeek",
        host="https://api.deepseek.example",
        source="network",
        provider_type="openai_compat",
        is_healthy=True,
        priority=0,
        loaded_models=["deepseek-v4-pro"],
    )
    fallback = ComputeNode(
        node_id="local-fallback",
        name="Local fallback",
        host="http://192.0.2.142:1234",
        source="network",
        provider_type="openai_compat",
        is_healthy=True,
        priority=10,
        loaded_models=["local-model"],
    )

    async def deepseek_get_client():
        return deepseek_client

    async def fallback_get_client():
        return fallback_client

    monkeypatch.setattr(deepseek, "_get_client", deepseek_get_client)
    monkeypatch.setattr(fallback, "_get_client", fallback_get_client)
    registry.register_node(deepseek)
    registry.register_node(fallback)

    with pytest.raises(RuntimeError, match="No compute nodes available for streaming"):
        async for _ in registry.chat_stream(
            [{"role": "user", "content": "hello"}],
            model="deepseek-v4-pro",
            strict_model_routing=True,
        ):
            pass

    assert deepseek_client.calls == 5
    assert fallback_client.calls == 0
