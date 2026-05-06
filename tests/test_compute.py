"""Tests for Compute API routes — nodes, stats."""

import asyncio

import httpx
import pytest
from app.api.routes.compute import _infer_relay_provider_type, relay_websocket
from app.api.routes import settings as settings_routes
from app.config import settings
from app.core.auth import create_token
from app.core.compute_registry import ComputeNode, ComputeRegistry, compute_registry
from app.core.lmstudio import LMStudioClient, configured_lmstudio_model_is_authoritative
from app.main import app, _build_configured_local_llm_node
from app.models.database import init_db
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_provider = settings.llm_provider
    original_lmstudio_host = settings.lmstudio_host
    original_lmstudio_model = settings.lmstudio_model
    original_lmstudio_api_key = settings.lmstudio_api_key
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.llm_provider = original_provider
    settings.lmstudio_host = original_lmstudio_host
    settings.lmstudio_model = original_lmstudio_model
    settings.lmstudio_api_key = original_lmstudio_api_key


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


def test_configured_local_lmstudio_node_preserves_api_key_and_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(
        settings,
        "lmstudio_host",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    monkeypatch.setattr(settings, "lmstudio_api_key", "test-key")

    node = _build_configured_local_llm_node()

    assert node._openai_endpoint("chat/completions") == "chat/completions"
    assert node.api_key == "test-key"
    assert node.loaded_models == ["gemini-3.1-flash-lite-preview"]


def test_configured_lmstudio_model_is_authoritative(monkeypatch):
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    assert configured_lmstudio_model_is_authoritative()
    assert not configured_lmstudio_model_is_authoritative("default")


@pytest.mark.asyncio
async def test_lmstudio_model_probe_uses_configured_openai_model(monkeypatch):
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")

    class FakeClient:
        def __init__(self):
            self.payload = None

        async def post(self, path, *, json, timeout):
            self.payload = json
            return httpx.Response(
                200,
                request=httpx.Request("POST", f"http://test{path}"),
                json={"model": json["model"], "choices": []},
            )

    fake = FakeClient()
    client = LMStudioClient("https://generativelanguage.googleapis.com/v1beta/openai/")

    async def get_client():
        return fake

    monkeypatch.setattr(client, "_get_client", get_client)

    assert await client.detect_loaded_model(force=True) == "gemini-3.1-flash-lite-preview"
    assert fake.payload["model"] == "gemini-3.1-flash-lite-preview"


@pytest.mark.asyncio
async def test_settings_models_preserves_configured_lmstudio_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")

    class MismatchedProbeClient(LMStudioClient):
        def __init__(self):
            super().__init__("https://generativelanguage.googleapis.com/v1beta/openai/")
            self.detect_calls = 0

        async def health(self):
            return True

        async def list_models(self):
            return [{"name": "models/gemini-2.5-flash"}]

        async def detect_loaded_model(self, force: bool = False):
            self.detect_calls += 1
            return "models/gemini-2.5-flash"

    fake_client = MismatchedProbeClient()

    async def no_registry_models():
        return []

    def fail_persist(*_args, **_kwargs):
        raise AssertionError("Configured LM Studio model should not be auto-persisted")

    monkeypatch.setattr(settings_routes, "ollama", fake_client)
    monkeypatch.setattr(compute_registry, "list_models", no_registry_models)
    monkeypatch.setattr(settings_routes, "_persist_env", fail_persist)

    response = await settings_routes.get_models()

    assert response["active_model"] == "gemini-3.1-flash-lite-preview"
    assert settings.lmstudio_model == "gemini-3.1-flash-lite-preview"
    assert fake_client.detect_calls == 0


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


def test_relay_provider_inference_preserves_openai_compatible_contracts():
    assert _infer_relay_provider_type("http://10.0.10.142:1234", None) == "lmstudio"
    assert _infer_relay_provider_type("http://10.0.10.142:1234", "ollama") == "lmstudio"
    assert _infer_relay_provider_type("http://example.test:9999/v1", "ollama") == ("openai_compat")
    assert _infer_relay_provider_type("http://10.0.10.142:11434", None) == "ollama"
    assert (
        _infer_relay_provider_type(
            "https://generativelanguage.googleapis.com/v1beta/openai/",
            "ollama",
        )
        == "gemini_openai"
    )


def test_register_node_skips_lower_priority_duplicate_provider_mismatch():
    registry = ComputeRegistry()
    lmstudio = ComputeNode(
        node_id="lmstudio",
        name="LM Studio",
        host="http://10.0.10.142:1234",
        source="network",
        provider_type="openai_compat",
        is_healthy=True,
        priority=1,
    )
    mistaken_ollama = ComputeNode(
        node_id="ollama-duplicate",
        name="Mistaken Ollama",
        host="http://10.0.10.142:1234/v1",
        source="network",
        provider_type="ollama",
        is_healthy=True,
        priority=5,
    )

    registry.register_node(lmstudio)
    registry.register_node(mistaken_ollama)

    assert list(registry._nodes) == ["lmstudio"]
    assert registry._nodes["lmstudio"].provider_type == "openai_compat"


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


def test_resolve_model_prefers_explicit_capability_over_advertised_fallback():
    node = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="network",
        provider_type="gemini_openai",
        loaded_models=["models/gemini-2.5-flash"],
        model_capabilities={
            "gemini-3.1-flash-lite-preview": {
                "supports_tools": True,
                "context_length": 32768,
            }
        },
    )

    assert node._resolve_model("gemini-3.1-flash-lite-preview") == ("gemini-3.1-flash-lite-preview")


def test_configured_openai_primary_uses_pinned_model_when_models_list_is_broader(monkeypatch):
    monkeypatch.setattr(
        settings,
        "lmstudio_host",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    node = ComputeNode(
        node_id="gemini",
        name="Gemini",
        host="https://generativelanguage.googleapis.com/v1beta/openai",
        source="local",
        provider_type="lmstudio",
        loaded_models=["models/gemini-2.5-flash", "models/gemini-2.5-pro"],
    )

    assert node._resolve_model(None) == "gemini-3.1-flash-lite-preview"
    assert node._resolve_model("gemini-3.1-flash-lite-preview") == "gemini-3.1-flash-lite-preview"


def test_network_openai_fallback_keeps_own_advertised_model(monkeypatch):
    monkeypatch.setattr(
        settings,
        "lmstudio_host",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(settings, "lmstudio_model", "gemini-3.1-flash-lite-preview")
    node = ComputeNode(
        node_id="secondary",
        name="Secondary",
        host="http://10.0.10.142:1234",
        source="network",
        provider_type="openai_compat",
        loaded_models=["qwen3.6-35b-a3b@q5_k_xl"],
    )

    assert node._resolve_model(None) == "qwen3.6-35b-a3b@q5_k_xl"


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
        raise httpx.HTTPStatusError("stream provider overloaded", request=request, response=response)

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


@pytest.mark.asyncio
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
        host="http://10.0.10.142:1234",
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
        host="http://10.0.10.142:1234",
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


@pytest.mark.asyncio
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
        host="http://10.0.10.142:1234",
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

    chunks = [chunk async for chunk in registry.chat_stream([{"role": "user", "content": "hello"}])]

    assert chunks == ["fallback streamed"]
    assert primary_client.calls == 5
    assert primary.cb_state == "open"
    assert fallback_client.calls == 1
    assert fallback_client.paths == ["v1/chat/completions"]
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
        host="http://10.0.10.142:1234",
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
