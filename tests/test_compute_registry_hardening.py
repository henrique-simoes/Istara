"""Focused hardening tests for compute registry safety paths."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import settings
from app.core.compute_registry import ComputeNode, ComputeRegistry


@pytest.fixture(autouse=True)
def reset_settings():
    original_lmstudio_host = settings.lmstudio_host
    original_lmstudio_model = settings.lmstudio_model
    original_active_probe = settings.llm_capability_active_probe_enabled
    original_strict_auto_routing = settings.strict_auto_routing
    yield
    settings.lmstudio_host = original_lmstudio_host
    settings.lmstudio_model = original_lmstudio_model
    settings.llm_capability_active_probe_enabled = original_active_probe
    settings.strict_auto_routing = original_strict_auto_routing


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


class _NoLoadedModelsClient:
    async def get(self, path: str, timeout: float | None = None):
        return httpx.Response(
            200,
            request=httpx.Request("GET", f"http://test/{path}"),
            json={"data": []},
        )


@pytest.mark.asyncio
async def test_lmstudio_no_loaded_model_is_reachable_not_ready(monkeypatch):
    node = ComputeNode(
        node_id="lmstudio",
        name="Local LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
    )
    client = _NoLoadedModelsClient()

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)

    healthy = await node.check_health()
    payload = node.to_dict()

    assert healthy is False
    assert node.is_healthy is False
    assert node.health_state == "no_model_loaded"
    assert payload["alive"] is False
    assert payload["is_ready"] is False
    assert payload["is_reachable"] is True
    assert payload["online"] is True
    assert payload["readiness_state"] == "no_model_loaded"


def test_strict_project_model_routing_prefers_authorized_relay_over_local_duplicate():
    registry = ComputeRegistry()
    settings.strict_auto_routing = True
    registry.register_node(
        ComputeNode(
            node_id="local-lmstudio",
            name="Local LM Studio",
            host="http://localhost:1234",
            source="local",
            provider_type="lmstudio",
            priority=1,
            is_healthy=True,
            loaded_models=["gemma-test"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="relay-gemma",
            name="Relay Gemma",
            host="http://relay.local:1234",
            source="relay",
            provider_type="lmstudio",
            priority=20,
            is_healthy=True,
            loaded_models=["gemma-test"],
            allowed_project_ids=["project-a"],
            last_heartbeat=9999999999,
        )
    )

    candidates = registry._select_candidates(
        model="gemma-test",
        strict_model=True,
        project_id="project-a",
    )

    assert [candidate.node_id for candidate in candidates[:2]] == [
        "relay-gemma",
        "local-lmstudio",
    ]


@pytest.mark.asyncio
async def test_cancelled_relay_stream_records_route_failure(monkeypatch):
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="relay-cancelled",
        name="Relay Cancelled",
        host="http://relay.local:1234",
        source="relay",
        provider_type="lmstudio",
        is_healthy=True,
        websocket=object(),
        loaded_models=["gemma-test"],
        allowed_project_ids=["project-a"],
        last_heartbeat=9999999999,
    )

    async def cancelled_chat(*_args, **_kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(node, "chat", cancelled_chat)
    registry.register_node(node)

    with pytest.raises(asyncio.CancelledError):
        async for _ in registry.chat_stream(
            [{"role": "user", "content": "hello"}],
            model="gemma-test",
            project_id="project-a",
        ):
            pass

    assert node.selected_request_count == 1
    assert node.failed_request_count == 1
    assert node.active_requests == 0
    assert "cancelled" in node.last_failure_error.lower()


def test_compute_stats_count_reachable_nodes_separately_from_ready_nodes():
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="lmstudio",
            name="Local LM Studio",
            host="http://localhost:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=False,
            health_state="no_model_loaded",
            model_capabilities={
                "qwen3": {
                    "is_loaded": False,
                    "loadable": True,
                    "supports_tools": True,
                }
            },
        )
    )

    stats = registry.get_stats()

    assert stats["alive_nodes"] == 0
    assert stats["ready_nodes"] == 0
    assert stats["reachable_nodes"] == 1
    assert stats["available_models"] == ["qwen3"]
    assert stats["nodes"][0]["alive"] is False
    assert stats["nodes"][0]["is_reachable"] is True


@pytest.mark.asyncio
async def test_health_check_discovers_lmstudio_capabilities_without_loaded_model(
    monkeypatch,
):
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="lmstudio",
        name="Local LM Studio",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
    )
    client = _NoLoadedModelsClient()

    async def get_client():
        return client

    async def detect_capabilities(
        host, api_key="", provider_type="openai_compat", active_probe=None
    ):
        return {
            "qwen3": SimpleNamespace(
                to_dict=lambda: {
                    "is_loaded": False,
                    "loadable": True,
                    "supports_tools": True,
                }
            )
        }

    monkeypatch.setattr(node, "_get_client", get_client)
    monkeypatch.setattr(
        "app.core.model_capabilities.detect_capabilities_generic",
        detect_capabilities,
    )
    registry.register_node(node)

    results = await registry.check_all_health()

    assert results["lmstudio"] is False
    assert node.is_healthy is False
    assert node.health_state == "no_model_loaded"
    assert node.model_capabilities["qwen3"]["loadable"] is True


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


def test_compute_stats_count_duplicate_local_hardware_once():
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="local-lmstudio",
            name="Local LM Studio",
            host="http://localhost:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=True,
            ram_total_gb=64.0,
            ram_available_gb=40.0,
            cpu_cores=12,
            loaded_models=["qwen3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="local-ollama",
            name="Local Ollama",
            host="http://localhost:11434",
            source="local",
            provider_type="ollama",
            is_healthy=True,
            ram_total_gb=64.0,
            ram_available_gb=39.0,
            cpu_cores=12,
            loaded_models=["nomic-embed-text"],
        )
    )

    stats = registry.get_stats()

    assert stats["total_nodes"] == 2
    assert stats["hardware_node_count"] == 1
    assert stats["total_ram_gb"] == 64.0
    assert stats["available_ram_gb"] == 40.0
    assert stats["total_cpu_cores"] == 12


def test_compute_stats_collapse_local_ip_aliases_before_display_and_ram(monkeypatch):
    import app.core.compute_registry_helpers as compute_registry_helpers

    monkeypatch.setattr(
        compute_registry_helpers,
        "_local_machine_aliases",
        lambda: {"localhost", "127.0.0.1", "192.0.2.142", "192.0.2.215"},
    )
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="network-142",
            name="Mac Studio via .142",
            host="http://192.0.2.142:1234",
            source="network",
            provider_type="lmstudio",
            is_healthy=True,
            ram_total_gb=36.0,
            ram_available_gb=23.4,
            cpu_cores=16,
            loaded_models=["qwen3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="network-215",
            name="Mac Studio via .215",
            host="http://192.0.2.215:1234",
            source="network",
            provider_type="lmstudio",
            is_healthy=True,
            ram_total_gb=36.0,
            ram_available_gb=22.8,
            cpu_cores=16,
            loaded_models=["qwen3"],
        )
    )

    stats = registry.get_stats()

    assert stats["total_nodes"] == 1
    assert stats["hardware_node_count"] == 1
    assert stats["total_ram_gb"] == 36.0
    assert stats["available_ram_gb"] == 23.4
    assert stats["total_cpu_cores"] == 16
    assert [node["node_id"] for node in stats["nodes"]] == ["network-142"]


def test_relay_alias_replaces_network_discovery_for_same_endpoint(monkeypatch):
    import app.core.compute_registry_helpers as compute_registry_helpers

    monkeypatch.setattr(
        compute_registry_helpers,
        "_local_machine_aliases",
        lambda: {"localhost", "127.0.0.1", "192.0.2.142"},
    )
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="network-142",
            name="Network LM Studio",
            host="http://192.0.2.142:1234",
            source="network",
            provider_type="lmstudio",
            is_healthy=True,
            priority=10,
            loaded_models=["qwen3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="relay-142",
            name="Relay Mac Studio",
            host="http://192.0.2.142:1234",
            source="relay",
            provider_type="lmstudio",
            is_relay=True,
            is_healthy=True,
            priority=20,
            loaded_models=["qwen3"],
        )
    )

    stats = registry.get_stats()

    assert list(registry._nodes) == ["relay-142"]
    assert stats["total_nodes"] == 1
    assert stats["nodes"][0]["node_id"] == "relay-142"


def test_project_scoped_relay_stays_visible_beside_local_same_endpoint(monkeypatch):
    import app.core.compute_registry_helpers as compute_registry_helpers

    monkeypatch.setattr(
        compute_registry_helpers,
        "_local_machine_aliases",
        lambda: {"localhost", "127.0.0.1", "192.0.2.142"},
    )
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="local-lmstudio",
            name="Local LM Studio",
            host="http://192.0.2.142:1234",
            source="local",
            provider_type="lmstudio",
            is_healthy=True,
            health_state="ready",
            ram_total_gb=36.0,
            loaded_models=["qwen3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="relay-lmstudio",
            name="Relay Mac Studio",
            host="http://192.0.2.142:1234",
            source="relay",
            provider_type="lmstudio",
            is_relay=True,
            is_healthy=True,
            health_state="ready",
            ram_total_gb=36.0,
            allowed_project_ids=["project-a"],
            loaded_models=["qwen3"],
        )
    )

    stats = registry.get_stats(project_id="project-a")

    assert set(registry._nodes) == {"local-lmstudio", "relay-lmstudio"}
    assert {node["node_id"] for node in stats["nodes"]} == {
        "local-lmstudio",
        "relay-lmstudio",
    }
    assert stats["hardware_node_count"] == 1


def test_project_scoped_relay_stays_distinct_from_unscoped_relay_same_endpoint():
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="relay-unscoped",
            name="Relay Unscoped",
            host="http://host.docker.internal:18112",
            source="relay",
            provider_type="openai_compat",
            is_relay=True,
            is_healthy=True,
            health_state="ready",
            loaded_models=["qwen3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="relay-scoped",
            name="Relay Scoped",
            host="http://host.docker.internal:18112",
            source="relay",
            provider_type="openai_compat",
            is_relay=True,
            is_healthy=True,
            health_state="ready",
            allowed_project_ids=["project-a"],
            loaded_models=["qwen3"],
        )
    )

    stats = registry.get_stats(project_id="project-a")

    assert set(registry._nodes) == {"relay-unscoped", "relay-scoped"}
    assert [node["node_id"] for node in stats["nodes"]] == ["relay-scoped"]


def test_compute_stats_keep_distinct_local_services_but_count_machine_ram_once(
    monkeypatch,
):
    import app.core.compute_registry_helpers as compute_registry_helpers

    monkeypatch.setattr(
        compute_registry_helpers,
        "_local_machine_aliases",
        lambda: {"localhost", "127.0.0.1", "192.0.2.142", "192.0.2.215"},
    )
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="lmstudio",
            name="Local LM Studio",
            host="http://192.0.2.142:1234",
            source="network",
            provider_type="lmstudio",
            is_healthy=True,
            ram_total_gb=36.0,
            ram_available_gb=23.4,
            cpu_cores=16,
            loaded_models=["qwen3"],
        )
    )
    registry.register_node(
        ComputeNode(
            node_id="ollama",
            name="Local Ollama",
            host="http://192.0.2.215:11434",
            source="network",
            provider_type="ollama",
            is_healthy=True,
            ram_total_gb=36.0,
            ram_available_gb=21.0,
            cpu_cores=16,
            loaded_models=["nomic-embed-text"],
        )
    )

    stats = registry.get_stats()

    assert stats["total_nodes"] == 2
    assert stats["hardware_node_count"] == 1
    assert stats["total_ram_gb"] == 36.0
    assert stats["available_ram_gb"] == 23.4
    assert stats["total_cpu_cores"] == 16


def test_compute_stats_include_capability_only_models():
    registry = ComputeRegistry()
    registry.register_node(
        ComputeNode(
            node_id="relay-capabilities",
            name="Relay Capabilities",
            host="http://192.0.2.10:1234",
            source="relay",
            provider_type="lmstudio",
            is_healthy=True,
            model_capabilities={
                "google/gemma-4-e4b": {
                    "supports_tools": True,
                    "supports_vision": False,
                    "context_length": 8192,
                }
            },
        )
    )

    stats = registry.get_stats()

    assert stats["available_models"] == ["google/gemma-4-e4b"]
    assert "google/gemma-4-e4b" in stats["nodes"][0]["model_capabilities"]


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
async def test_chat_readiness_uses_positive_cache_for_repeated_status_checks(
    monkeypatch,
):
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
async def test_registry_openai_compatible_chat_suppresses_reasoning_content(
    monkeypatch,
):
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

    from app.core.compute_registry_invocation import ChatTruncatedEmptyResponse

    with pytest.raises(ChatTruncatedEmptyResponse, match="reasoning exhausted"):
        await registry.chat([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_registry_chat_returns_content_free_route_evidence(monkeypatch):
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="qwen-node",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _SuccessfulChatClient()

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    result = await registry.chat(
        [{"role": "user", "content": "hello"}],
        model="qwen3",
        project_id="project-a",
    )

    route = result["_istara_route"]
    assert route["node_id"] == "qwen-node"
    assert route["node_source"] == "local"
    assert route["provider_type"] == "lmstudio"
    assert route["route_kind"] == "chat"
    assert route["project_id"] == "project-a"
    assert route["model"] == "qwen3"
    assert route["outcome"] == "served"
    assert route["served_request_count"] == 1
    assert "host" not in route


@pytest.mark.asyncio
async def test_registry_chat_emits_content_free_donor_route_telemetry(monkeypatch):
    from app.core import telemetry as telemetry_module

    record_event = AsyncMock()
    monkeypatch.setattr(
        telemetry_module.telemetry_recorder,
        "record_research_validity_event",
        record_event,
    )
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="qwen-node",
        name="Qwen",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["qwen3"],
    )

    async def get_client():
        return _SuccessfulChatClient()

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    await registry.chat(
        [{"role": "user", "content": "hello"}],
        model="qwen3",
        project_id="project-a",
    )
    await asyncio.sleep(0)

    operations = [call.kwargs["operation"] for call in record_event.await_args_list]
    assert operations == ["donor.selected", "donor.served"]
    assert all(
        call.kwargs["project_id"] == "project-a"
        for call in record_event.await_args_list
    )
    assert all(
        call.kwargs["donor_id"] == "qwen-node" for call in record_event.await_args_list
    )
    assert all("host" not in call.kwargs for call in record_event.await_args_list)


@pytest.mark.asyncio
async def test_relay_registration_emits_project_scoped_lifecycle_telemetry(monkeypatch):
    from app.core import telemetry as telemetry_module

    record_event = AsyncMock()
    monkeypatch.setattr(
        telemetry_module.telemetry_recorder,
        "record_research_validity_event",
        record_event,
    )
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="relay-node",
        name="Relay Node",
        host="",
        source="relay",
        provider_type="ollama",
        is_healthy=True,
        health_state="ready",
        loaded_models=["gemma"],
        allowed_project_ids=["project-a"],
    )

    registry.register_node(node)
    await asyncio.sleep(0)

    operations = [call.kwargs["operation"] for call in record_event.await_args_list]
    assert operations == [
        "donor.registered",
        "donor.visible",
        "donor.reachable",
        "donor.ready",
    ]
    assert all(
        call.kwargs["project_id"] == "project-a"
        for call in record_event.await_args_list
    )
    assert all(
        call.kwargs["donor_id"] == "relay-node" for call in record_event.await_args_list
    )


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
async def test_openai_compatible_chat_applies_thinking_control_without_payload_field(
    monkeypatch,
):
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

    chunks = [
        chunk
        async for chunk in node.chat_stream([{"role": "user", "content": "hello"}])
    ]

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
