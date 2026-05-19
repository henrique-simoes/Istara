"""LM Studio model loading and recovery paths for compute registry."""

import httpx
import pytest

from app.config import settings
from app.core.compute_registry import ComputeNode, ComputeRegistry


@pytest.fixture(autouse=True)
def reset_settings():
    original_lmstudio_host = settings.lmstudio_host
    original_lmstudio_model = settings.lmstudio_model
    original_llm_provider = settings.llm_provider
    original_lmstudio_auto_load_enabled = settings.lmstudio_auto_load_enabled
    original_lmstudio_auto_context_reload = settings.lmstudio_auto_context_reload
    original_lmstudio_max_load_attempts = settings.lmstudio_max_load_attempts_per_request
    original_lmstudio_allow_unload = settings.lmstudio_allow_unload_on_reload
    original_strict_auto_routing = settings.strict_auto_routing
    yield
    settings.lmstudio_host = original_lmstudio_host
    settings.lmstudio_model = original_lmstudio_model
    settings.llm_provider = original_llm_provider
    settings.lmstudio_auto_load_enabled = original_lmstudio_auto_load_enabled
    settings.lmstudio_auto_context_reload = original_lmstudio_auto_context_reload
    settings.lmstudio_max_load_attempts_per_request = original_lmstudio_max_load_attempts
    settings.lmstudio_allow_unload_on_reload = original_lmstudio_allow_unload
    settings.strict_auto_routing = original_strict_auto_routing


class _LMLoadThenChatClient:
    def __init__(self):
        self.posts: list[tuple[str, dict]] = []
        self.loaded_models: list[str] = []

    async def post(self, path: str, json: dict, timeout=None):
        self.posts.append((path, json))
        if path == "api/v1/models/load":
            self.loaded_models.append(json["model"])
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test/{path}"),
                json={"loaded": True},
            )
        if path == "v1/chat/completions":
            if json["model"] not in self.loaded_models:
                raise AssertionError("chat called before model load")
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test/{path}"),
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "loaded answer",
                            }
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected post path {path}")


class _NoModelsThenFallbackLoadClient:
    def __init__(self):
        self.chat_models: list[str] = []
        self.load_attempts: list[str] = []

    async def get(self, path: str, timeout: float | None = None):
        if path == "v1/models":
            return httpx.Response(
                200,
                request=httpx.Request("GET", "http://test/v1/models"),
                json={"data": [{"id": "bad-model"}, {"id": "good-model"}]},
            )
        raise AssertionError(f"unexpected get path {path}")

    async def post(self, path: str, json: dict, timeout=None):
        if path == "api/v1/models/load":
            model = json["model"]
            self.load_attempts.append(model)
            if model == "bad-model":
                request = httpx.Request("POST", f"http://test/{path}")
                response = httpx.Response(
                    400,
                    request=request,
                    json={"error": {"message": "No LM Runtime for torchSafetensors"}},
                )
                raise httpx.HTTPStatusError("load failed", request=request, response=response)
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test/{path}"),
                json={"loaded": True},
            )
        if path == "v1/chat/completions":
            model = json["model"]
            self.chat_models.append(model)
            if model == "bad-model":
                request = httpx.Request("POST", f"http://test/{path}")
                response = httpx.Response(
                    400,
                    request=request,
                    json={"error": {"message": "No models loaded. Please load a model."}},
                )
                raise httpx.HTTPStatusError(
                    "No models loaded",
                    request=request,
                    response=response,
                )
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test/{path}"),
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "fallback model answered",
                            }
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected post path {path}")


class _ContextErrorThenReloadClient:
    def __init__(self):
        self.posts: list[tuple[str, dict]] = []
        self.chat_calls = 0
        self.loaded = False

    async def post(self, path: str, json: dict, timeout=None):
        self.posts.append((path, json))
        if path == "api/v1/models/load":
            self.loaded = True
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test/{path}"),
                json={"loaded": True},
            )
        if path == "v1/chat/completions":
            self.chat_calls += 1
            if self.chat_calls == 1:
                request = httpx.Request("POST", f"http://test/{path}")
                response = httpx.Response(
                    400,
                    request=request,
                    json={
                        "error": {
                            "message": "The prompt is greater than the context length."
                        }
                    },
                )
                raise httpx.HTTPStatusError(
                    "context length",
                    request=request,
                    response=response,
                )
            assert self.loaded
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test/{path}"),
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "reloaded answer",
                            }
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected post path {path}")


@pytest.mark.asyncio
async def test_configured_unknown_lmstudio_model_does_not_load_first_downloaded_model(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_host", "http://localhost:1234")
    monkeypatch.setattr(settings, "lmstudio_model", "qwen")
    registry = ComputeRegistry()
    client = _LMLoadThenChatClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=[],
        allowed_project_ids=["project-a"],
        model_capabilities={
            "gemma-4-26b-a4b-it-assistant": {
                "is_loaded": False,
                "loadable": True,
                "context_length": 262144,
            },
            "google/gemma-4-e4b": {
                "is_loaded": False,
                "loadable": True,
                "context_length": 8192,
            },
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    assert node._resolve_model("qwen") == "qwen"
    result = await registry.chat([{"role": "user", "content": "hello"}], model="qwen")

    assert result["message"]["content"] == "loaded answer"
    assert client.posts[0][0] == "api/v1/models/load"
    assert client.posts[0][1]["model"] == "qwen"


@pytest.mark.asyncio
async def test_registry_loads_lmstudio_model_marked_not_loaded_before_chat(monkeypatch):
    registry = ComputeRegistry()
    client = _LMLoadThenChatClient()
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
                "is_loaded": False,
                "loadable": True,
                "context_length": 32768,
            }
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat([{"role": "user", "content": "hello"}], model="qwen3")

    assert result["message"]["content"] == "loaded answer"
    assert client.posts[0][0] == "api/v1/models/load"
    assert client.posts[0][1]["model"] == "qwen3"
    assert client.posts[0][1]["context_length"] >= 4096
    assert client.posts[1][0] == "v1/chat/completions"
    assert node.model_capabilities["qwen3"]["is_loaded"] is True


@pytest.mark.asyncio
async def test_registry_reloads_lmstudio_model_with_larger_context_before_chat(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_auto_context_reload", True)
    registry = ComputeRegistry()
    client = _LMLoadThenChatClient()
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
                "context_length": 2048,
                "loaded_context_length": 2048,
                "trained_context_length": 32768,
            }
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat(
        [{"role": "user", "content": "hello"}],
        model="qwen3",
        min_context=5000,
    )

    assert result["message"]["content"] == "loaded answer"
    load_payload = client.posts[0][1]
    assert client.posts[0][0] == "api/v1/models/load"
    assert load_payload["model"] == "qwen3"
    assert load_payload["context_length"] >= 5000
    assert client.posts[1][0] == "v1/chat/completions"
    assert node.model_capabilities["qwen3"]["loaded_context_length"] >= 5000


@pytest.mark.asyncio
async def test_registry_does_not_auto_reload_lmstudio_context_by_default(
    monkeypatch,
):
    registry = ComputeRegistry()
    client = _LMLoadThenChatClient()
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
                "context_length": 2048,
                "loaded_context_length": 2048,
                "trained_context_length": 32768,
            }
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    with pytest.raises(RuntimeError, match="No compute nodes available for chat"):
        await registry.chat(
            [{"role": "user", "content": "hello"}],
            model="qwen3",
            min_context=5000,
        )

    assert client.posts == []


@pytest.mark.asyncio
async def test_registry_recovers_context_error_by_reloading_lmstudio_model(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_auto_context_reload", True)
    registry = ComputeRegistry()
    client = _ContextErrorThenReloadClient()
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
                "loaded_context_length": 32768,
                "trained_context_length": 32768,
            }
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat(
        [{"role": "user", "content": "hello"}],
        model="qwen3",
        min_context=5000,
    )

    assert result["message"]["content"] == "reloaded answer"
    assert [path for path, _ in client.posts] == [
        "v1/chat/completions",
        "api/v1/models/load",
        "v1/chat/completions",
    ]
    assert client.posts[1][1]["context_length"] >= 5000


@pytest.mark.asyncio
async def test_registry_recovers_lmstudio_no_models_loaded_with_discovered_fallback(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_host", "http://localhost:1234")
    monkeypatch.setattr(settings, "lmstudio_model", "bad-model")
    monkeypatch.setattr(settings, "lmstudio_max_load_attempts_per_request", 2)
    registry = ComputeRegistry()
    client = _NoModelsThenFallbackLoadClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["bad-model", "good-model"],
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat([{"role": "user", "content": "hello"}], project_id="project-a")

    assert result["message"]["content"] == "fallback model answered"
    assert client.chat_models == ["bad-model", "good-model"]
    assert client.load_attempts == ["bad-model", "good-model"]
    assert node.loaded_models == ["bad-model", "good-model"]
    assert node.is_healthy is True


@pytest.mark.asyncio
async def test_strict_routing_uses_configured_lmstudio_model_when_request_omits_model(
    monkeypatch,
):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(settings, "lmstudio_model", "google/gemma-4-e4b")
    monkeypatch.setattr(settings, "strict_auto_routing", True)
    registry = ComputeRegistry()
    client = _LMLoadThenChatClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://relay.example",
        source="relay",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=[],
        allowed_project_ids=["project-a"],
        model_capabilities={
            "gemma-4-26b-a4b-it-assistant": {
                "is_loaded": False,
                "loadable": True,
                "context_length": 262144,
            },
            "google/gemma-4-e4b": {
                "is_loaded": False,
                "loadable": True,
                "context_length": 8192,
            },
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat([{"role": "user", "content": "hello"}], project_id="project-a")

    assert result["message"]["content"] == "loaded answer"
    assert client.posts[0][0] == "api/v1/models/load"
    assert client.posts[0][1]["model"] == "google/gemma-4-e4b"
    assert client.posts[1][1]["model"] == "google/gemma-4-e4b"


@pytest.mark.asyncio
async def test_strict_routing_does_not_recover_context_with_different_lmstudio_model(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_auto_context_reload", True)
    monkeypatch.setattr(settings, "strict_auto_routing", True)
    registry = ComputeRegistry()
    client = _LMLoadThenChatClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["google/gemma-4-e4b", "gemma-4-26b-a4b-it-assistant"],
        model_capabilities={
            "google/gemma-4-e4b": {
                "is_loaded": True,
                "loadable": True,
                "context_length": 2048,
                "loaded_context_length": 2048,
                "trained_context_length": 8192,
            },
            "gemma-4-26b-a4b-it-assistant": {
                "is_loaded": False,
                "loadable": True,
                "context_length": 262144,
                "trained_context_length": 262144,
            },
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    with pytest.raises(RuntimeError, match="No compute nodes available for chat"):
        await registry.chat(
            [{"role": "user", "content": "hello"}],
            model="google/gemma-4-e4b",
            min_context=9000,
        )

    assert client.posts == []


@pytest.mark.asyncio
async def test_registry_limits_lmstudio_no_model_recovery_to_one_load_by_default(
    monkeypatch,
):
    monkeypatch.setattr(settings, "lmstudio_host", "http://localhost:1234")
    monkeypatch.setattr(settings, "lmstudio_model", "bad-model")
    registry = ComputeRegistry()
    client = _NoModelsThenFallbackLoadClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["bad-model", "good-model"],
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    with pytest.raises(RuntimeError, match="No compute nodes available for chat"):
        await registry.chat([{"role": "user", "content": "hello"}])

    assert client.chat_models == ["bad-model"]
    assert client.load_attempts == ["bad-model"]


@pytest.mark.asyncio
async def test_registry_respects_lmstudio_auto_load_disabled(monkeypatch):
    monkeypatch.setattr(settings, "lmstudio_host", "http://localhost:1234")
    monkeypatch.setattr(settings, "lmstudio_model", "bad-model")
    monkeypatch.setattr(settings, "lmstudio_auto_load_enabled", False)
    registry = ComputeRegistry()
    client = _NoModelsThenFallbackLoadClient()
    node = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["bad-model", "good-model"],
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    with pytest.raises(RuntimeError, match="No compute nodes available for chat"):
        await registry.chat([{"role": "user", "content": "hello"}])

    assert client.chat_models == ["bad-model"]
    assert client.load_attempts == []
