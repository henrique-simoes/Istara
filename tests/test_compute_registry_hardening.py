"""Focused hardening tests for compute registry safety paths."""

from types import SimpleNamespace

import httpx
import pytest

from app.config import settings
from app.core.compute_registry import ComputeNode, ComputeRegistry


@pytest.fixture(autouse=True)
def reset_settings():
    original_lmstudio_host = settings.lmstudio_host
    original_lmstudio_model = settings.lmstudio_model
    original_active_probe = settings.llm_capability_active_probe_enabled
    yield
    settings.lmstudio_host = original_lmstudio_host
    settings.lmstudio_model = original_lmstudio_model
    settings.llm_capability_active_probe_enabled = original_active_probe


class _SuccessfulChatClient:
    def __init__(self):
        self.calls = 0
        self.paths: list[str] = []
        self.payloads: list[dict] = []

    async def post(self, path: str, json: dict):
        self.calls += 1
        self.paths.append(path)
        self.payloads.append(json)
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


class _ReasoningOnlyChatClient:
    async def post(self, path: str, json: dict):
        return httpx.Response(
            200,
            request=httpx.Request("POST", f"http://test/{path}"),
            json={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "reasoning_content": "private reasoning",
                        },
                    }
                ]
            },
        )


class _InlineThinkingChatClient:
    async def post(self, path: str, json: dict):
        return httpx.Response(
            200,
            request=httpx.Request("POST", f"http://test/{path}"),
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "<think>\nprivate reasoning\n</think>\n\nFinal answer",
                        }
                    }
                ]
            },
        )


class _OllamaThinkingChatClient:
    async def post(self, path: str, json: dict):
        return httpx.Response(
            200,
            request=httpx.Request("POST", f"http://test{path}"),
            json={
                "message": {
                    "role": "assistant",
                    "content": "<think>\nprivate reasoning\n</think>\n\nFinal answer",
                    "reasoning_content": "private reasoning",
                    "thinking": "also private",
                },
                "done": True,
            },
        )


class _InlineThinkingStreamResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        yield 'data: {"choices":[{"delta":{"content":"<thi"}}]}'
        yield 'data: {"choices":[{"delta":{"content":"nk>private"}}]}'
        yield 'data: {"choices":[{"delta":{"reasoning_content":"also private"}}]}'
        yield 'data: {"choices":[{"delta":{"content":"</thi"}}]}'
        yield 'data: {"choices":[{"delta":{"content":"nk>\\n\\nFinal streamed"}}]}'
        yield "data: [DONE]"


class _InlineThinkingStreamClient:
    def stream(self, method: str, path: str, json: dict, timeout=None):
        return _InlineThinkingStreamResponse()


def test_local_compute_node_hydrates_hardware_resources(monkeypatch):
    import app.core.compute_registry_helpers as compute_registry_helpers

    monkeypatch.setattr(compute_registry_helpers, "_LOCAL_RESOURCE_SNAPSHOT", None)
    profile = SimpleNamespace(
        total_ram_gb=64.0,
        available_ram_gb=42.5,
        cpu_cores=12,
        gpu=SimpleNamespace(name="Test GPU", vram_mb=24576),
    )
    monkeypatch.setattr("app.core.hardware.detect_hardware", lambda: profile)
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="local-lmstudio",
        name="Local LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["qwen3"],
    )

    registry.register_node(node)
    stats = registry.get_stats()

    assert stats["total_ram_gb"] == 64.0
    assert stats["available_ram_gb"] == 42.5
    assert stats["total_cpu_cores"] == 12
    assert stats["nodes"][0]["gpu_name"] == "Test GPU"


def test_compute_registry_registration_logs_redact_endpoint(caplog):
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="private-live",
        name="Private Live Server",
        host="http://192.0.2.142:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["google/gemma-4-e4b"],
    )

    with caplog.at_level("INFO", logger="app.core.compute_registry"):
        registry.register_node(node)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "192.0.2.142" not in log_text
    assert "http://[redacted-host]:1234" in log_text


def test_lmstudio_resolves_loaded_native_model_before_downloaded_or_stale_config(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_host", "http://localhost:1234")
    monkeypatch.setattr(settings, "lmstudio_model", "qwen")
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        loaded_models=[
            "gemma-4-26b-a4b-it-assistant",
            "google/gemma-4-e4b",
        ],
        model_capabilities={
            "gemma-4-26b-a4b-it-assistant": {
                "is_loaded": False,
                "loadable": True,
                "context_length": 262144,
            },
            "google/gemma-4-e4b": {
                "is_loaded": True,
                "loadable": True,
                "context_length": 8192,
                "loaded_context_length": 8192,
            },
        },
    )

    assert node._resolve_model(None) == "google/gemma-4-e4b"
    assert node._resolve_model("qwen") == "google/gemma-4-e4b"


@pytest.mark.asyncio
async def test_registry_routes_lmstudio_chat_to_loaded_native_model_for_stale_config(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_host", "http://localhost:1234")
    monkeypatch.setattr(settings, "lmstudio_model", "qwen")
    registry = ComputeRegistry()
    client = _SuccessfulChatClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=[
            "gemma-4-26b-a4b-it-assistant",
            "google/gemma-4-e4b",
        ],
        model_capabilities={
            "gemma-4-26b-a4b-it-assistant": {
                "is_loaded": False,
                "loadable": True,
                "context_length": 262144,
            },
            "google/gemma-4-e4b": {
                "is_loaded": True,
                "loadable": True,
                "context_length": 8192,
                "loaded_context_length": 8192,
            },
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat([{"role": "user", "content": "hello"}])

    assert result["message"]["content"] == "fallback answered"
    assert client.payloads[0]["model"] == "google/gemma-4-e4b"


@pytest.mark.asyncio
async def test_registry_forwards_response_format_to_openai_compatible_chat(
    monkeypatch,
):
    registry = ComputeRegistry()
    client = _SuccessfulChatClient()
    node = ComputeNode(
        node_id="openai",
        name="OpenAI compatible",
        host="http://localhost:1234",
        source="network",
        provider_type="openai_compat",
        is_healthy=True,
        loaded_models=["model-a"],
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "out", "schema": {"type": "object"}},
    }

    await registry.chat(
        [{"role": "user", "content": "hello"}],
        response_format=response_format,
    )

    assert client.payloads[0]["response_format"] == response_format


@pytest.mark.asyncio
async def test_registry_translates_response_format_to_ollama_raw_schema(monkeypatch):
    registry = ComputeRegistry()
    client = _OllamaThinkingChatClient()
    client.payloads = []

    async def post(path: str, json: dict):
        client.payloads.append(json)
        return await _OllamaThinkingChatClient().post(path, json)

    client.post = post
    node = ComputeNode(
        node_id="ollama",
        name="Ollama",
        host="http://localhost:11434",
        source="local",
        provider_type="ollama",
        is_healthy=True,
        loaded_models=["model-a"],
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "out", "schema": schema},
    }

    await registry.chat(
        [{"role": "user", "content": "hello"}],
        response_format=response_format,
    )

    assert client.payloads[0]["format"] == schema


@pytest.mark.asyncio
async def test_chat_readiness_uses_positive_cache_for_repeated_status_checks(monkeypatch):
    registry = ComputeRegistry()
    client = _SuccessfulChatClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["qwen3"],
        model_capabilities={
            "qwen3": {
                "is_loaded": True,
                "loadable": True,
                "context_length": 32768,
            }
        },
    )

    async def get_client():
        return client

    async def check_all_health():
        return {"lmstudio": True}

    monkeypatch.setattr(node, "_get_client", get_client)
    monkeypatch.setattr(registry, "check_all_health", check_all_health)
    registry.register_node(node)

    assert await registry.ensure_chat_ready(model="qwen3") is True
    assert await registry.ensure_chat_ready(model="qwen3") is True

    assert client.calls == 1


@pytest.mark.asyncio
async def test_registry_openai_compatible_chat_suppresses_reasoning_content(monkeypatch):
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="qwen",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _ReasoningOnlyChatClient()

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat([{"role": "user", "content": "hello"}])

    assert result["message"]["content"] == ""
    assert "reasoning_content" not in result["message"]


@pytest.mark.asyncio
async def test_openai_compatible_chat_suppresses_reasoning_content(monkeypatch):
    node = ComputeNode(
        node_id="qwen",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _ReasoningOnlyChatClient()

    monkeypatch.setattr(node, "_get_client", get_client)

    result = await node.chat([{"role": "user", "content": "hello"}])

    assert result["message"]["content"] == ""
    assert "reasoning_content" not in result["message"]


@pytest.mark.asyncio
async def test_openai_compatible_chat_strips_inline_thinking(monkeypatch):
    node = ComputeNode(
        node_id="qwen",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _InlineThinkingChatClient()

    monkeypatch.setattr(node, "_get_client", get_client)

    result = await node.chat([{"role": "user", "content": "hello"}])

    assert result["message"]["content"] == "Final answer"


@pytest.mark.asyncio
async def test_openai_compatible_chat_applies_thinking_control_without_payload_field(monkeypatch):
    node = ComputeNode(
        node_id="qwen",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        loaded_models=["qwen3"],
    )
    client = _SuccessfulChatClient()

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)

    result = await node.chat(
        [{"role": "user", "content": "hello"}],
        thinking_mode="off",
    )

    assert result["message"]["content"] == "fallback answered"
    payload = client.payloads[0]
    assert "thinking_mode" not in payload
    assert "Istara thinking mode is OFF" in payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_ollama_chat_removes_reasoning_fields(monkeypatch):
    node = ComputeNode(
        node_id="ollama",
        name="Ollama",
        host="http://localhost:11434",
        source="local",
        provider_type="ollama",
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _OllamaThinkingChatClient()

    monkeypatch.setattr(node, "_get_client", get_client)

    result = await node.chat([{"role": "user", "content": "hello"}])

    assert result["message"] == {"role": "assistant", "content": "Final answer"}


@pytest.mark.asyncio
async def test_openai_compatible_stream_strips_inline_thinking(monkeypatch):
    node = ComputeNode(
        node_id="qwen",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _InlineThinkingStreamClient()

    monkeypatch.setattr(node, "_get_client", get_client)

    chunks = [chunk async for chunk in node.chat_stream([{"role": "user", "content": "hello"}])]

    assert chunks == ["Final streamed"]


@pytest.mark.asyncio
async def test_compute_registry_stream_strips_inline_thinking(monkeypatch):
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="qwen",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _InlineThinkingStreamClient()

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    chunks = [
        chunk
        async for chunk in registry.chat_stream(
            [{"role": "user", "content": "hello"}],
            thinking_mode="on",
        )
    ]

    assert chunks == ["Final streamed"]


def test_context_estimate_includes_tool_and_response_format_schema():
    messages = [{"role": "user", "content": "short prompt"}]
    baseline = ComputeRegistry._estimate_context_tokens(messages, max_tokens=16)
    with_contracts = ComputeRegistry._estimate_context_tokens(
        messages,
        max_tokens=16,
        response_format={"type": "json_schema", "json_schema": {"name": "out"}},
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "long_tool_contract",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "notes": {
                                "type": "string",
                                "description": "detailed retrieval and RAG evidence notes",
                            }
                        },
                    },
                },
            }
        ],
    )

    assert with_contracts > baseline
