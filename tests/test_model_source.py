"""CF-SPEC-1 Phase 6: unified model-source resolution and the execution-only
pi bridge. Locks DEC-10 precedence: explicit selection > local direct >
pi-managed fallback (stub-marked planes only) ; donations untouched; the
bridge never advertises capacity."""

import json

import httpx
import pytest

from app.config import settings


class _FakeEndpointInfo:
    def __init__(self, endpoint_id: str, model: str):
        self.endpoint_id = endpoint_id
        self.model = model


class _FakeManager:
    def __init__(self, endpoints: list[tuple[str, str]], secret: str = "sk-test"):
        self._endpoints = endpoints
        self._secret = secret

    def catalog(self):
        return [_FakeEndpointInfo(eid, model) for eid, model in self._endpoints]

    def resolve(self, *, endpoint_id=None, model=None, **_kw):
        target = None
        for eid, m in self._endpoints:
            if endpoint_id and eid == endpoint_id:
                target = (eid, m)
                break
            if model and m == model:
                target = (eid, m)
                break
        if not target:
            from app.core.pi_runtime.endpoints import PiEndpointResolutionError

            raise PiEndpointResolutionError("no_matching_pi_endpoint")
        from app.core.pi_runtime.endpoints import ResolvedPiEndpoint

        return ResolvedPiEndpoint(
            endpoint_id=target[0],
            provider_kind="openai_compat",
            base_url="https://provider.test/v1",
            model=target[1],
            api_key=self._secret,
            timeout_ms=30000,
            max_retries=2,
        )


@pytest.fixture(autouse=True)
def _restore_settings():
    yield
    settings.llm_provider_contract_stub = False


@pytest.mark.asyncio
async def test_explicit_model_resolves_to_pi_managed(monkeypatch):
    from app.core.agentic import model_source as ms

    monkeypatch.setattr(ms, "_pi_manager", lambda: _FakeManager([("ep1", "deepseek-v4-pro")]))
    source = await ms.resolve_model_source("deepseek-v4-pro")
    assert source is not None and source.plane == "pi-managed"
    assert source.endpoint_id == "ep1" and source.api_key  # executable secret present


@pytest.mark.asyncio
async def test_explicit_local_model_prefers_local_plane(monkeypatch):
    from app.core.agentic import model_source as ms

    monkeypatch.setattr(ms, "_pi_manager", lambda: _FakeManager([]))
    monkeypatch.setattr(settings, "ollama_model", "qwen3:latest", raising=False)
    source = await ms.resolve_model_source("qwen3:latest")
    assert source is not None and source.plane == "local-direct"


@pytest.mark.asyncio
async def test_stub_plane_is_invisible_when_marked(monkeypatch):
    from app.core.agentic import model_source as ms

    monkeypatch.setattr(ms, "_pi_manager", lambda: _FakeManager([]))
    monkeypatch.setattr(settings, "ollama_model", "qwen3:latest", raising=False)
    settings.llm_provider_contract_stub = True
    assert await ms.resolve_model_source("qwen3:latest") is None
    assert await ms.resolve_model_source(None) is None
    assert await ms.has_non_stub_source() is False


@pytest.mark.asyncio
async def test_stub_marked_stack_falls_back_to_pi_managed_default(monkeypatch):
    """DEC-10: Istara on a stub plane uses the configured pi endpoint instead."""
    from app.core.agentic import model_source as ms

    monkeypatch.setattr(
        ms, "_pi_manager", lambda: _FakeManager([("ep-deepseek", "deepseek-v4-pro")])
    )
    settings.llm_provider_contract_stub = True
    source = await ms.resolve_model_source(None)
    assert source is not None and source.plane == "pi-managed"


@pytest.mark.asyncio
async def test_unknown_explicit_model_leaves_donation_path_untouched(monkeypatch):
    from app.core.agentic import model_source as ms

    monkeypatch.setattr(ms, "_pi_manager", lambda: _FakeManager([("ep1", "deepseek-v4-pro")]))
    assert await ms.resolve_model_source("some-donated-model") is None


def _sse_bytes(chunks: list[dict]) -> bytes:
    lines = [b"data: " + json.dumps(c).encode() for c in chunks]
    return b"\n\n".join(lines) + b"\n\ndata: [DONE]\n\n"


@pytest.mark.asyncio
async def test_bridge_streams_content_tools_and_exact_usage():
    from app.core.agentic.model_source import ModelSource
    from app.core.agentic.pi_bridge import stream_openai_chat

    sse = _sse_bytes(
        [
            {"choices": [{"delta": {"role": "assistant", "content": "PO"}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": "NG"}, "finish_reason": None}]},
            {
                "choices": [
                    {
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13},
            },
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path.endswith("/v1/chat/completions")
        assert request.headers["Authorization"] == "Bearer sk-live"
        assert body["model"] == "deepseek-v4-pro"
        assert body["stream"] is True
        assert body["messages"][0]["role"] == "system"
        return httpx.Response(200, content=sse, headers={"Content-Type": "text/event-stream"})

    source = ModelSource(
        plane="pi-managed",
        endpoint_id="ep1",
        base_url="https://provider.test",
        api_key="sk-live",
        model="deepseek-v4-pro",
    )
    forwarded: list[str] = []
    message = await stream_openai_chat(
        source=source,
        history=[{"role": "user", "content": "hi"}],
        system="sys",
        stream_cb=lambda event: forwarded.append(event.get("text", "")),
        transport=httpx.MockTransport(handler),
    )
    assert message["role"] == "assistant"
    assert message["content"] == "PONG"
    meta = message["_bridge_meta"]
    assert meta["usage"]["total_tokens"] == 13 and meta["usage"]["estimate"] is False
    assert meta["endpoint_id"] == "ep1" and meta["plane"] == "pi-managed"
    assert "".join(forwarded) == "PONG"


@pytest.mark.asyncio
async def test_bridge_surfaces_tool_calls():
    from app.core.agentic.model_source import ModelSource
    from app.core.agentic.pi_bridge import stream_openai_chat

    sse = _sse_bytes(
        [
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_1",
                                    "function": {"name": "search", "arguments": '{"query":'},
                                }
                            ]
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [{"index": 0, "function": {"arguments": '"cats"}'}}]
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            },
        ]
    )
    source = ModelSource(
        plane="pi-managed", endpoint_id="ep1", base_url="https://p.test", api_key="k",
        model="m",
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse, headers={"Content-Type": "text/event-stream"})

    message = await stream_openai_chat(
        source=source, history=[{"role": "user", "content": "q"}],
        transport=httpx.MockTransport(handler),
    )
    calls = message["tool_calls"]
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "search"
    assert json.loads(calls[0]["function"]["arguments"]) == {"query": "cats"}
