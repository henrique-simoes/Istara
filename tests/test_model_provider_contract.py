"""Universal model-provider capability contract tests."""

import httpx
import pytest

from app.core.compute_registry import ComputeNode, infer_provider_type
from app.core.model_capabilities import (
    _apply_ollama_show_metadata,
    _capability_from_openai_model,
    detect_capabilities_generic,
    provider_auth_headers,
)


def test_provider_inference_covers_openai_family_and_anthropic():
    assert infer_provider_type("llama.cpp", "http://localhost:8080") == "llamacpp"
    assert infer_provider_type("vllm", "http://localhost:8000") == "vllm"
    assert infer_provider_type("ollama", "https://example.test/v1") == "openai_compat"
    assert infer_provider_type(None, "https://api.anthropic.com") == "anthropic"
    assert (
        infer_provider_type(
            "ollama",
            "https://generativelanguage.googleapis.com/v1beta/openai",
        )
        == "gemini_openai"
    )


def test_provider_auth_headers_use_anthropic_contract():
    assert provider_auth_headers("openai_compat", "sk-test") == {
        "Authorization": "Bearer sk-test"
    }
    assert provider_auth_headers("anthropic", "sk-ant") == {
        "x-api-key": "sk-ant",
        "anthropic-version": "2023-06-01",
    }


def test_openai_compatible_metadata_preserves_modality_and_context():
    cap = _capability_from_openai_model(
        {
            "id": "qwen3.6-35b-a3b",
            "max_model_len": 262144,
            "capabilities": {
                "vision": True,
                "tools": True,
                "json": True,
            },
            "loaded": True,
            "type": "vlm",
        },
        "vllm",
    )

    assert cap is not None
    assert cap.source == "vllm"
    assert cap.context_length == 262144
    assert cap.trained_context_length == 262144
    assert cap.supports_vision is True
    assert cap.supports_tools is True
    assert cap.supports_json is True
    assert cap.is_loaded is True


def test_ollama_show_metadata_distinguishes_trained_and_loaded_context():
    cap = _capability_from_openai_model({"id": "gemma3:4b"}, "ollama")
    assert cap is not None

    _apply_ollama_show_metadata(
        cap,
        {
            "capabilities": ["completion", "vision"],
            "parameters": "temperature 0.7\nnum_ctx 8192",
            "details": {"parameter_size": "4.3B", "quantization_level": "Q4_K_M"},
            "model_info": {"gemma3.context_length": 131072},
        },
    )

    assert cap.supports_vision is True
    assert cap.parameter_count == "4.3B"
    assert cap.quantization == "Q4_K_M"
    assert cap.trained_context_length == 131072
    assert cap.loaded_context_length == 8192
    assert cap.context_length == 8192


class _CapabilityDiscoveryClient:
    def __init__(self):
        self.posts: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str):
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={"data": [{"id": "qwen3:7b", "max_model_len": 32768}]},
        )

    async def post(self, url: str, json: dict):
        self.posts.append((url, json))
        return httpx.Response(200, request=httpx.Request("POST", url), json={})


@pytest.mark.asyncio
async def test_capability_detection_is_passive_unless_active_probe_enabled(monkeypatch):
    client = _CapabilityDiscoveryClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: client)

    caps = await detect_capabilities_generic(
        "http://localhost:1234",
        provider_type="openai_compat",
        active_probe=False,
    )

    assert "qwen3:7b" in caps
    assert client.posts == []


@pytest.mark.asyncio
async def test_capability_detection_active_probe_is_explicit(monkeypatch):
    client = _CapabilityDiscoveryClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: client)

    await detect_capabilities_generic(
        "http://localhost:1234",
        provider_type="openai_compat",
        active_probe=True,
    )

    assert client.posts
    assert client.posts[0][1]["model"] == "qwen3:7b"


class _AnthropicClient:
    def __init__(self):
        self.path = ""
        self.payload = {}

    async def post(self, path: str, json: dict):
        self.path = path
        self.payload = json
        return httpx.Response(
            200,
            request=httpx.Request("POST", f"https://api.anthropic.com/{path}"),
            json={
                "content": [
                    {"type": "thinking", "thinking": "private reasoning"},
                    {"type": "redacted_thinking", "data": "opaque"},
                    {"type": "text", "text": "anthropic ok"},
                ]
            },
        )


@pytest.mark.asyncio
async def test_anthropic_node_uses_messages_api_and_normalizes_response(monkeypatch):
    client = _AnthropicClient()
    node = ComputeNode(
        node_id="anthropic",
        name="Anthropic",
        host="https://api.anthropic.com",
        source="network",
        provider_type="anthropic",
        loaded_models=["claude-sonnet-4-20250514"],
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    result = await node.chat(
        [{"role": "user", "content": "Hi"}],
        model="claude-sonnet-4-20250514",
    )

    assert client.path == "v1/messages"
    assert client.payload["model"] == "claude-sonnet-4-20250514"
    assert client.payload["max_tokens"] == 1024
    assert result == {"message": {"role": "assistant", "content": "anthropic ok"}}
