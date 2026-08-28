"""W8 contract coverage — embeddings gateway + model-management UX parity.

Master plan §8 W8: embeddings migrate under Pi identity management through
``backend/app/core/pi_runtime/embeddings_gateway.py`` (pi-ai cannot execute
embeddings, so the gateway is Python-direct HTTP against a PiModelManager-
resolved endpoint). ``agentic.embed`` dispatches both loop modes through the
same Pi-governed embeddings gateway; the wrappers (``embeddings.py`` ``embed_text`` /
``embed_chunks`` / ``ensure_embed_model``, ``validation.py:_get_embeddings``)
route through the dispatcher so the 14 downstream consumers inherit the
change with zero edits. The vector-space invariant pins BOTH engines to the
same embed model. UX parity: LLMServer CRUD + network discovery re-project
into the Pi catalog, settings model pickers merge the Pi catalog, and the
projects API exposes the per-project ``agentic_engine`` selector.

All verification here is stubbed/static — MockTransport HTTP, spies, and AST
checks; no live model activity and no external traffic.
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.config import settings
from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.pi_runtime.embeddings_gateway import (
    EmbeddingsGateway,
    PiEmbeddingError,
    VectorSpaceInvariantError,
    assert_vector_space_invariant,
    default_embed_model,
    validate_embedding_vectors,
)
from app.core.pi_runtime.embedding_profile import (
    ActiveEmbeddingProfile,
    reset_embedding_profile_cache,
)
from app.core.pi_runtime.endpoints import PiEndpointResolutionError, ResolvedPiEndpoint
from app.core.pi_runtime.model_manager import PiModelManager, reset_live_db_projections
from app.core.pi_runtime.model_manager_provisioning import ensure_endpoint_model
from app.core.embeddings import TextChunk
from app.models.agentic_usage import AgenticUsageRow
from app.models.database import async_session, init_db

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _embedding_provider_baseline(monkeypatch):
    """Keep synthetic local endpoints aligned with their Ollama identity."""
    reset_embedding_profile_cache()
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    yield
    reset_embedding_profile_cache()


# ── helpers ─────────────────────────────────────────────────────────────


def _endpoint(**overrides) -> ResolvedPiEndpoint:
    base = dict(
        endpoint_id="pi-local-ollama",
        provider_kind="openai_compat",
        base_url="http://127.0.0.1:11434/v1",
        model=default_embed_model(),
        api_key="ollama",
        timeout_ms=30000,
        max_retries=0,
        kind="local",
    )
    base.update(overrides)
    return ResolvedPiEndpoint(**base)


def _profile(endpoint_id: str, model: str | None = None) -> ActiveEmbeddingProfile:
    selected_model = model or default_embed_model()
    return ActiveEmbeddingProfile(
        profile_id="w8-test",
        version=1,
        model_id=selected_model,
        endpoint_id=endpoint_id,
        transport="pi_http",
        dimension=0,
        dtype="float",
        normalization="provider_native",
        cache_namespace=selected_model,
        health_status="unknown",
        migration_source="test",
    )


def _isolated(manager: PiModelManager) -> PiModelManager:
    """Pin the catalog to its explicit entries (skip the DB projection)."""
    manager._db_projected = True
    return manager


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _function_source(path: Path, function_name: str) -> str:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ):
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {path}")


@pytest.mark.asyncio
async def test_cached_batch_vectors_use_the_same_validation_boundary(monkeypatch):
    """Malformed cached vectors must be treated as misses, not trusted data."""
    from app.core import embeddings

    chunks = [TextChunk(text="cached", source="test")]
    monkeypatch.setattr(
        embeddings.embedding_cache, "get", lambda *_: _async_value(["bad"])
    )
    monkeypatch.setattr(
        embeddings, "_dispatch_embed", lambda *_args, **_kwargs: _async_value([[0.25]])
    )
    stored = []
    monkeypatch.setattr(
        embeddings.embedding_cache, "put", lambda *args: _async_record(stored, args)
    )

    result = await embeddings.embed_chunks(chunks)

    assert result[0].vector == [0.25]
    assert stored


@pytest.mark.asyncio
async def test_cache_hit_dimension_is_checked_against_engine_known_dimension(
    monkeypatch,
):
    """F-2: a numeric cache entry written under a different embedding
    model/dimension must be treated as a miss and re-embedded — the cached
    vector's dimension is validated against the engine's KNOWN dimension for
    the model, never inferred from the entry itself."""
    from app.core import embeddings

    model = embeddings._embed_model_name()
    # The engine knows this model embeds at dimension 2 (startup probe / a
    # prior provider response recorded it).
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {model: 2})
    # The cache holds a numeric-but-stale 3-dim entry.
    monkeypatch.setattr(
        embeddings.embedding_cache, "get", lambda *_: _async_value([0.1, 0.2, 0.3])
    )
    dispatched = []

    async def fake_dispatch(*_a, **_k):
        dispatched.append(True)
        return [[0.4, 0.5]]

    monkeypatch.setattr(embeddings, "_dispatch_embed", fake_dispatch)
    stored = []
    monkeypatch.setattr(
        embeddings.embedding_cache, "put", lambda *args: _async_record(stored, args)
    )

    result = await embeddings.embed_text("stale-dim")

    # Re-embedded through the provider; the stale entry never reached retrieval.
    assert result == [0.4, 0.5]
    assert dispatched
    assert stored


@pytest.mark.asyncio
async def test_cache_hit_matching_known_dimension_is_served(monkeypatch):
    """A cache entry whose dimension matches the engine's known dimension is
    served without touching the provider."""
    from app.core import embeddings

    model = embeddings._embed_model_name()
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {model: 2})
    monkeypatch.setattr(
        embeddings.embedding_cache, "get", lambda *_: _async_value([0.5, 0.6])
    )
    dispatched = []
    monkeypatch.setattr(
        embeddings,
        "_dispatch_embed",
        lambda *_a, **_k: _async_record(dispatched, [[0.7, 0.8]]),
    )
    stored = []
    monkeypatch.setattr(
        embeddings.embedding_cache, "put", lambda *args: _async_record(stored, args)
    )

    result = await embeddings.embed_text("matching-dim")

    assert result == [0.5, 0.6]
    assert not dispatched
    assert not stored


@pytest.mark.asyncio
async def test_cache_hit_with_unknown_engine_dimension_fails_closed(monkeypatch):
    """Before the engine's dimension is established (no probe/provider
    response in this process), a cached entry must NOT be trusted — fail
    closed and re-embed rather than serve an unverifiable vector space."""
    from app.core import embeddings

    model = embeddings._embed_model_name()
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {})
    monkeypatch.setattr(
        embeddings.embedding_cache, "get", lambda *_: _async_value([1.0, 2.0, 3.0])
    )
    dispatched = []

    async def fake_dispatch(*_a, **_k):
        dispatched.append(True)
        return [[0.1, 0.2]]

    monkeypatch.setattr(embeddings, "_dispatch_embed", fake_dispatch)
    stored = []
    monkeypatch.setattr(
        embeddings.embedding_cache, "put", lambda *args: _async_record(stored, args)
    )

    result = await embeddings.embed_text("unknown-dim")

    assert result == [0.1, 0.2]
    assert dispatched
    assert stored
    assert embeddings.known_embed_dimension(model) == 2


@pytest.mark.asyncio
async def test_embed_chunks_stale_dimension_entry_is_reembedded(monkeypatch):
    """Batch path: a stale-dimension cached chunk is re-embedded and the
    provider dimension is recorded for later hits."""
    from app.core import embeddings

    model = embeddings._embed_model_name()
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {model: 2})
    chunks = [
        TextChunk(text="stale-a", source="s"),
        TextChunk(text="stale-b", source="s"),
    ]

    async def fake_get(_model, text):
        return [0.1, 0.2, 0.3] if text == "stale-a" else None

    monkeypatch.setattr(embeddings.embedding_cache, "get", fake_get)
    dispatched = []

    async def fake_dispatch(texts, **_k):
        dispatched.append(True)
        return [[0.4, 0.5] for _ in texts]

    monkeypatch.setattr(embeddings, "_dispatch_embed", fake_dispatch)
    stored = []
    monkeypatch.setattr(
        embeddings.embedding_cache, "put", lambda *args: _async_record(stored, args)
    )

    results = await embeddings.embed_chunks(chunks)

    assert [r.vector for r in results] == [[0.4, 0.5], [0.4, 0.5]]
    # Both chunks went through the provider: the stale hit was re-embedded.
    assert dispatched
    assert len(stored) == 2


@pytest.mark.asyncio
async def test_record_known_dimension_persists_for_later_hits(monkeypatch):
    """Provider responses record the engine's dimension; matching cache hits
    after a restart-style unknown state are then trusted."""
    from app.core import embeddings

    model = embeddings._embed_model_name()
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {})
    monkeypatch.setattr(
        embeddings.embedding_cache, "get", lambda *_: _async_value(None)
    )
    monkeypatch.setattr(
        embeddings, "_dispatch_embed", lambda *_a, **_k: _async_value([[0.5, 0.6]])
    )
    stored = []
    monkeypatch.setattr(
        embeddings.embedding_cache, "put", lambda *args: _async_record(stored, args)
    )

    await embeddings.embed_text("probe")

    assert embeddings.known_embed_dimension(model) == 2
    assert stored


async def _async_value(value):
    return value


async def _async_record(target, value):
    target.append(value)


# ── gateway: native Ollama + /v1/embeddings ─────────────────────────────


async def test_gateway_native_ollama_api_embed(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    manager = _isolated(PiModelManager(endpoints=[_endpoint()]))
    gateway = EmbeddingsGateway(
        manager=manager,
        client=_mock_client(handler),
        profile=_profile("pi-local-ollama"),
    )
    outcome = await gateway.embed(["alpha", "beta"])
    assert outcome["embeddings"] == [[0.1, 0.2], [0.3, 0.4]]
    assert outcome["endpoint_id"] == "pi-local-ollama"
    assert outcome["model"] == settings.ollama_embed_model
    assert outcome["status"] == "success"
    (request,) = requests
    # The native Ollama contract is /api/embed on the raw host (no /v1).
    assert str(request.url) == "http://127.0.0.1:11434/api/embed"
    import json

    body = json.loads(request.content)
    assert body == {"model": settings.ollama_embed_model, "input": ["alpha", "beta"]}


async def test_gateway_openai_compatible_v1_embeddings():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.9]},
                    {"index": 0, "embedding": [0.8]},
                ]
            },
        )

    manager = _isolated(
        PiModelManager(
            endpoints=[
                _endpoint(
                    endpoint_id="pi-llm-7",
                    base_url="http://gpu.local:8000/v1",
                    api_key="sekret",
                    kind="remote",
                    model=settings.ollama_embed_model,
                ),
            ]
        )
    )
    gateway = EmbeddingsGateway(
        manager=manager,
        client=_mock_client(handler),
        profile=_profile("pi-llm-7", "nomic-embed-text"),
    )
    outcome = await gateway.embed(["a", "b"], model="nomic-embed-text")
    # Response items are ordered by index, not by payload order.
    assert outcome["embeddings"] == [[0.8], [0.9]]
    assert outcome["endpoint_id"] == "pi-llm-7"
    (request,) = requests
    assert str(request.url) == "http://gpu.local:8000/v1/embeddings"
    assert request.headers["Authorization"] == "Bearer sekret"


async def test_gateway_openai_usage_reaches_accounting_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"index": 0, "embedding": [0.8]}],
                "usage": {"prompt_tokens": 123, "total_tokens": 123},
            },
        )

    manager = _isolated(
        PiModelManager(
            endpoints=[
                _endpoint(
                    endpoint_id="pi-llm-priced",
                    base_url="http://gpu.local:8000/v1",
                    api_key="sekret",
                    kind="remote",
                    cost_input_per_mtok=2.0,
                )
            ]
        )
    )
    gateway = EmbeddingsGateway(
        manager=manager,
        client=_mock_client(handler),
        profile=_profile("pi-llm-priced"),
    )

    outcome = await gateway.embed(["a"])

    assert outcome["usage"] == {
        "input_tokens": 123,
        "output_tokens": 0,
        "cache_read": 0,
        "cache_write": 0,
        "total_tokens": 123,
        "cost_usd": pytest.approx(0.000246),
        "estimate": False,
    }


async def test_gateway_local_missing_usage_is_explicitly_estimated():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.8]]})

    manager = _isolated(PiModelManager(endpoints=[_endpoint(cost_input_per_mtok=1.0)]))
    gateway = EmbeddingsGateway(manager=manager, client=_mock_client(handler))

    outcome = await gateway.embed(["local text"])

    assert outcome["usage"]["estimate"] is True
    assert outcome["usage"]["input_tokens"] > 0
    assert outcome["usage"]["total_tokens"] == outcome["usage"]["input_tokens"]
    assert outcome["usage"]["cost_usd"] > 0


async def test_remote_embedding_usage_is_persisted_exactly_in_ledger():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"index": 0, "embedding": [0.8]}],
                "usage": {"prompt_tokens": 123, "total_tokens": 123},
            },
        )

    await init_db()
    project_id = f"w8-remote-{uuid.uuid4().hex[:12]}"
    manager = _isolated(
        PiModelManager(
            endpoints=[
                _endpoint(
                    endpoint_id="pi-llm-priced",
                    base_url="http://gpu.local:8000/v1",
                    api_key="sekret",
                    kind="remote",
                    cost_input_per_mtok=2.0,
                )
            ]
        )
    )
    dispatcher = AgenticDispatcher(
        embeddings_gateway=EmbeddingsGateway(
            manager=manager,
            client=_mock_client(handler),
            profile=_profile("pi-llm-priced"),
        )
    )

    await dispatcher.embed(texts=["a"], project_id=project_id, engine="pi")

    async with async_session() as session:
        row = await session.scalar(
            select(AgenticUsageRow).where(
                AgenticUsageRow.project_id == project_id,
                AgenticUsageRow.purpose == "embed",
            )
        )
    assert row is not None
    assert row.input_tokens == 123
    assert row.total_tokens == 123
    assert row.cost_usd == pytest.approx(0.000246)
    assert row.estimate == 0


async def test_local_missing_embedding_usage_is_flagged_in_ledger():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.8]]})

    await init_db()
    project_id = f"w8-local-{uuid.uuid4().hex[:12]}"
    manager = _isolated(PiModelManager(endpoints=[_endpoint(cost_input_per_mtok=1.0)]))
    dispatcher = AgenticDispatcher(
        embeddings_gateway=EmbeddingsGateway(
            manager=manager, client=_mock_client(handler)
        )
    )

    await dispatcher.embed(texts=["local text"], project_id=project_id, engine="pi")

    async with async_session() as session:
        row = await session.scalar(
            select(AgenticUsageRow).where(
                AgenticUsageRow.project_id == project_id,
                AgenticUsageRow.purpose == "embed",
            )
        )
    assert row is not None
    assert row.estimate == 1
    assert row.input_tokens > 0
    assert row.total_tokens == row.input_tokens
    assert row.cost_usd > 0


async def test_gateway_response_cardinality_fails_typed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1]]})

    manager = _isolated(PiModelManager(endpoints=[_endpoint()]))
    gateway = EmbeddingsGateway(manager=manager, client=_mock_client(handler))
    with pytest.raises(PiEmbeddingError, match="embed_response_cardinality"):
        await gateway.embed(["one", "two"])


async def test_gateway_http_error_propagates():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    manager = _isolated(PiModelManager(endpoints=[_endpoint()]))
    gateway = EmbeddingsGateway(manager=manager, client=_mock_client(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await gateway.embed(["x"])


# ── catalog: embed endpoint resolution ──────────────────────────────────


def test_unpinned_resolver_is_not_a_runtime_authority(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    manager = PiModelManager(
        endpoints=[
            _endpoint(
                endpoint_id="pi-llm-remote", kind="remote", base_url="http://r:8000/v1"
            ),
            _endpoint(
                endpoint_id="pi-local-lmstudio", base_url="http://127.0.0.1:1234/v1"
            ),
            _endpoint(),
        ]
    )
    assert manager.resolve_embed().endpoint_id == "pi-local-ollama"

    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    no_ollama = PiModelManager(
        endpoints=[
            _endpoint(
                endpoint_id="pi-llm-remote", kind="remote", base_url="http://r:8000/v1"
            ),
            _endpoint(
                endpoint_id="pi-local-lmstudio", base_url="http://127.0.0.1:1234/v1"
            ),
        ]
    )
    assert no_ollama.resolve_embed().endpoint_id == "pi-local-lmstudio"

    remote_only = PiModelManager(
        endpoints=[
            _endpoint(
                endpoint_id="pi-llm-remote", kind="remote", base_url="http://r:8000/v1"
            ),
        ]
    )
    with pytest.raises(PiEndpointResolutionError, match="no_matching_pi_embed_endpoint_model"):
        remote_only.resolve_embed()


def test_production_manager_routes_requested_remote_embedding_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_embed_model", "local-embed")
    remote = _endpoint(
        endpoint_id="pi-llm-remote-embed",
        kind="remote",
        base_url="http://gpu.local:8000/v1",
        model="remote-embed",
        api_key="sekret",
    )
    manager = PiModelManager(endpoints=[remote, _endpoint()])

    assert manager.resolve_embed("remote-embed").endpoint_id == "pi-llm-remote-embed"


def test_production_manager_routes_lmstudio_embedding_configuration(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(settings, "lmstudio_embed_model", "lmstudio-embed")
    monkeypatch.setattr(settings, "ollama_embed_model", "ollama-embed")

    endpoint = PiModelManager().resolve_embed("lmstudio-embed")

    assert endpoint.endpoint_id == "pi-local-lmstudio"


def test_resolve_embed_fail_closed_without_compatible_entries():
    # Anthropic has no embeddings API; an anthropic-only catalog fails typed.
    manager = PiModelManager(
        endpoints=[
            _endpoint(
                endpoint_id="pi-claude",
                provider_kind="anthropic_compat",
                base_url="https://api.anthropic.invalid",
                kind="remote",
            ),
        ]
    )
    with pytest.raises(
        PiEndpointResolutionError, match="no_matching_pi_embed_endpoint"
    ):
        manager.resolve_embed()


def test_live_pi_manager_refreshes_after_settings_endpoint_mutation(monkeypatch):
    from app.config import PiApiEndpoint
    from app.core.pi_runtime.model_manager import reset_live_settings_catalogs

    monkeypatch.setattr(settings, "pi_api_endpoints", [])
    manager = PiModelManager(include_local=False)
    assert "pi-live-added" not in {item.endpoint_id for item in manager.catalog()}
    settings.pi_api_endpoints.append(
        PiApiEndpoint(
            endpoint_id="pi-live-added",
            provider_kind="openai_compat",
            base_url="https://provider.invalid/v1",
            model="live-model",
            keychain_service="test-only",
        )
    )
    reset_live_settings_catalogs()
    assert "pi-live-added" in {item.endpoint_id for item in manager.catalog()}


# ── vector-space invariant ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_vector_space_invariant_probes_both_engines(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    calls = []

    async def probe(*, engine, model, check_stored):
        calls.append((engine, model, check_stored))
        return {"status": "ok", "model": model, "model_dim": 2}

    assert (
        await assert_vector_space_invariant(dimension_probe=probe)
        == settings.ollama_embed_model
    )
    assert calls == [
        ("legacy", settings.ollama_embed_model, False),
        ("pi", settings.ollama_embed_model, False),
    ]


@pytest.mark.asyncio
async def test_vector_space_invariant_raises_on_dimension_divergence(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")

    async def probe(*, engine, model, check_stored):
        return {
            "status": "ok",
            "model": model,
            "model_dim": 2 if engine == "legacy" else 3,
        }

    with pytest.raises(
        VectorSpaceInvariantError, match="vector_space_invariant_violation"
    ):
        await assert_vector_space_invariant(dimension_probe=probe)


@pytest.mark.asyncio
async def test_vector_space_invariant_probe_failure_is_typed(monkeypatch):
    async def probe(*, engine, model, check_stored):
        return {"status": "error", "message": f"{engine} unavailable"}

    with pytest.raises(
        VectorSpaceInvariantError, match="vector_space_invariant_probe_failed"
    ):
        await assert_vector_space_invariant(dimension_probe=probe)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"embeddings": [[]]},
        {"embeddings": [["not-a-number"]]},
        {"embeddings": [[None]]},
    ],
)
async def test_gateway_malformed_vector_fails_before_success(payload):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    manager = _isolated(PiModelManager(endpoints=[_endpoint()]))
    gateway = EmbeddingsGateway(manager=manager, client=_mock_client(handler))
    with pytest.raises(PiEmbeddingError, match="embed_response_"):
        await gateway.embed(["one"])


def test_embedding_vector_validation_rejects_non_finite_values():
    with pytest.raises(PiEmbeddingError, match="embed_response_non_finite"):
        validate_embedding_vectors([[float("nan")]], expected_count=1)


def test_default_embed_model_matches_pi_owned_wrapper_rule(monkeypatch):
    from app.core.embeddings import _embed_model_name

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    assert default_embed_model() == _embed_model_name()
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    assert default_embed_model() == _embed_model_name()


# ── wrappers: cache in front, dispatcher behind ─────────────────────────


class _FakeCache:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], list[float]] = {}
        self.gets = 0
        self.puts = 0

    async def get(self, model: str, text: str):
        self.gets += 1
        return self.store.get((model, text))

    async def put(self, model: str, text: str, vector) -> None:
        self.puts += 1
        self.store[(model, text)] = vector


class _EmbedSpy:
    def __init__(self, vectors=None) -> None:
        self.calls: list[dict] = []
        self._vectors = vectors

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        texts = kwargs.get("texts") or []
        if self._vectors is not None:
            return self._vectors
        return [[float(i)] for i, _ in enumerate(texts)]


async def test_embed_text_routes_through_agentic_embed_with_cache_in_front(monkeypatch):
    from app.core import embeddings as embeddings_module
    from app.core.agentic import agentic

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    cache = _FakeCache()
    spy = _EmbedSpy(vectors=[[0.5, 0.6]])
    monkeypatch.setattr(embeddings_module, "embedding_cache", cache)
    monkeypatch.setattr(agentic, "embed", spy)

    vector = await embeddings_module.embed_text("hello")
    assert vector == [0.5, 0.6]
    assert len(spy.calls) == 1
    assert spy.calls[0]["texts"] == ["hello"]
    assert spy.calls[0]["params"].model == settings.ollama_embed_model

    # Second call hits the cache — the dispatcher is not touched again.
    cached = await embeddings_module.embed_text("hello")
    assert cached == [0.5, 0.6]
    assert len(spy.calls) == 1


@pytest.mark.asyncio
async def test_embed_text_malformed_dispatch_result_never_reaches_cache(monkeypatch):
    from app.core import embeddings as embeddings_module
    from app.core.agentic import agentic

    cache = _FakeCache()
    monkeypatch.setattr(embeddings_module, "embedding_cache", cache)
    monkeypatch.setattr(agentic, "embed", _EmbedSpy(vectors=[[]]))

    with pytest.raises(PiEmbeddingError, match="embed_response_invalid_vector"):
        await embeddings_module.embed_text("malformed")
    assert cache.puts == 0


async def test_embed_chunks_batches_through_agentic_embed(monkeypatch):
    from app.core import embeddings as embeddings_module
    from app.core.agentic import agentic

    cache = _FakeCache()
    spy = _EmbedSpy()
    monkeypatch.setattr(embeddings_module, "embedding_cache", cache)
    monkeypatch.setattr(agentic, "embed", spy)

    chunks = [embeddings_module.TextChunk(text=f"c{i}", source="s") for i in range(5)]
    results = await embeddings_module.embed_chunks(chunks, batch_size=2)
    # 5 uncached chunks, batch_size=2 -> 3 dispatcher calls, order preserved.
    assert [len(call["texts"]) for call in spy.calls] == [2, 2, 1]
    assert [r.chunk.text for r in results] == [f"c{i}" for i in range(5)]
    assert cache.puts == 5


async def test_validation_get_embeddings_dispatches_project_scoped(monkeypatch):
    from app.core import validation as validation_module
    from app.core.agentic import agentic

    spy = _EmbedSpy(vectors=[[0.1], [0.2]])
    monkeypatch.setattr(agentic, "embed", spy)
    vectors = await validation_module._get_embeddings(["r1", "r2"], project_id="proj-9")
    assert vectors == [[0.1], [0.2]]
    assert spy.calls[0]["project_id"] == "proj-9"

    async def failing(**kwargs):
        raise RuntimeError("embed unavailable")

    monkeypatch.setattr(agentic, "embed", failing)
    assert await validation_module._get_embeddings(["r1"], project_id="proj-9") == []


# ── bootstrap: provisioner ──────────────────────────────────────────────


async def test_ensure_embed_model_legacy_engine_still_uses_pi_authority(monkeypatch):
    from app.core import embeddings as embeddings_module

    monkeypatch.setattr(settings, "agentic_engine_default", "legacy")
    endpoint = _endpoint()
    provisioned = []

    async def ensure_db_projection(self):
        return None

    def resolve_embed(self, model=None, endpoint_id=None):
        assert endpoint_id == "pi-local-ollama"
        return endpoint

    async def ensure(ep, model_name):
        provisioned.append((ep, model_name))
        return True

    monkeypatch.setattr(PiModelManager, "ensure_db_projection", ensure_db_projection)
    monkeypatch.setattr(PiModelManager, "resolve_embed", resolve_embed)
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager_provisioning.ensure_endpoint_model", ensure
    )
    await embeddings_module.ensure_embed_model()
    assert provisioned == [(endpoint, default_embed_model())]


async def test_ensure_embed_model_pi_uses_the_provisioner(monkeypatch):
    from app.core import embeddings as embeddings_module

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "agentic_engine_default", "pi")
    endpoint = _endpoint()
    provisioned = []

    async def ensure_db_projection(self):
        return None

    def resolve_embed(self, model=None, endpoint_id=None):
        assert endpoint_id == "pi-local-ollama"
        return endpoint

    async def ensure_model(ep, model):
        provisioned.append((ep, model))
        return True

    monkeypatch.setattr(PiModelManager, "ensure_db_projection", ensure_db_projection)
    monkeypatch.setattr(PiModelManager, "resolve_embed", resolve_embed)
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager_provisioning.ensure_endpoint_model",
        ensure_model,
    )

    await embeddings_module.ensure_embed_model()
    assert provisioned == [(endpoint, settings.ollama_embed_model)]


@pytest.mark.asyncio
async def test_ensure_embed_model_rejects_local_provisioning_failure(monkeypatch):
    from app.core import embeddings as embeddings_module

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "agentic_engine_default", "pi")
    endpoint = _endpoint()

    async def ensure_db_projection(self):
        return None

    def resolve_embed(self, model=None, endpoint_id=None):
        assert endpoint_id == "pi-local-ollama"
        return endpoint

    async def ensure_model(ep, model):
        return False

    monkeypatch.setattr(PiModelManager, "ensure_db_projection", ensure_db_projection)
    monkeypatch.setattr(PiModelManager, "resolve_embed", resolve_embed)
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager_provisioning.ensure_endpoint_model",
        ensure_model,
    )

    with pytest.raises(
        PiEndpointResolutionError, match="embedding_model_provision_failed"
    ):
        await embeddings_module.ensure_embed_model()


async def test_provisioner_remote_is_noop_and_local_ollama_ensures(monkeypatch):
    remote = _endpoint(
        endpoint_id="pi-llm-9", kind="remote", base_url="http://r:8000/v1"
    )
    assert await ensure_endpoint_model(remote, "m") is False

    ensured = []

    class _FakeOllamaClient:
        def __init__(self, base_url=None):
            self.base_url = base_url

        async def ensure_model(self, model_name):
            ensured.append((self.base_url, model_name))
            return True

    monkeypatch.setattr("app.core.ollama.OllamaClient", _FakeOllamaClient)
    local = _endpoint()
    assert await ensure_endpoint_model(local, "nomic-embed-text") is True
    # The /v1 suffix is stripped back to the native Ollama host.
    assert ensured == [("http://127.0.0.1:11434", "nomic-embed-text")]


@pytest.mark.asyncio
async def test_provisioner_lmstudio_uses_compute_node_load_helper(monkeypatch):
    monkeypatch.setattr(settings, "lmstudio_auto_load_enabled", True)
    calls = []

    class _FakeComputeNode:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        async def load_model(self, model, *, force):
            calls.append(("load", model, force))
            return True

    monkeypatch.setattr("app.core.compute_node.ComputeNode", _FakeComputeNode)
    endpoint = _endpoint(
        endpoint_id="pi-local-lmstudio",
        base_url="http://127.0.0.1:1234/v1",
        kind="local",
    )

    assert await ensure_endpoint_model(endpoint, "lmstudio-embed") is True
    assert calls[0][1]["provider_type"] == "lmstudio"
    assert calls[0][1]["host"] == "http://127.0.0.1:1234"
    assert calls[1] == ("load", "lmstudio-embed", False)


@pytest.mark.asyncio
async def test_provisioner_lmstudio_load_false_fails_typed(monkeypatch):
    monkeypatch.setattr(settings, "lmstudio_auto_load_enabled", True)

    class _UnavailableComputeNode:
        def __init__(self, **kwargs):
            pass

        async def load_model(self, model, *, force):
            return False

    monkeypatch.setattr("app.core.compute_node.ComputeNode", _UnavailableComputeNode)
    endpoint = _endpoint(
        endpoint_id="pi-local-lmstudio",
        base_url="http://127.0.0.1:1234/v1",
        kind="local",
    )

    with pytest.raises(PiEndpointResolutionError, match="provision_lmstudio_failed"):
        await ensure_endpoint_model(endpoint, "lmstudio-embed")


async def test_provisioner_unknown_local_plane_fails_typed():
    unknown = _endpoint(
        endpoint_id="pi-llm-3", kind="local", base_url="http://10.0.0.8:9000/v1"
    )
    with pytest.raises(
        PiEndpointResolutionError, match="provision_unsupported_local_endpoint"
    ):
        await ensure_endpoint_model(unknown, "m")


# ── UX parity: projection reset, merged catalog, engine field ───────────


def test_reset_db_projection_drops_only_llm_server_entries():
    manager = PiModelManager(endpoints=[_endpoint()])
    projected = manager._project_llm_server(
        type(
            "Row",
            (),
            {
                "id": "srv-1",
                "is_relay": False,
                "provider_type": "openai_compat",
                "capabilities": "{}",
                "host": "http://gpu.local:8000",
                "is_local": False,
                "api_key": "",
                "name": "gpu",
            },
        )()
    )
    assert projected is not None
    manager._entries[projected.endpoint_id] = projected
    manager._db_projected = True

    manager.reset_db_projection()
    assert manager._db_projected is False
    assert "pi-llm-srv-1" not in manager._entries
    # Static/local entries are authoritative and survive the reset.
    assert "pi-local-ollama" in manager._entries


def test_reset_live_db_projections_hits_live_managers():
    manager = PiModelManager(endpoints=[_endpoint()])
    projected = manager._project_llm_server(
        type(
            "Row",
            (),
            {
                "id": "srv-live",
                "is_relay": False,
                "provider_type": "openai_compat",
                "capabilities": "{}",
                "host": "http://gpu.local:8000",
                "is_local": False,
                "api_key": "",
                "name": "gpu",
            },
        )()
    )
    manager._entries[projected.endpoint_id] = projected
    manager._db_projected = True
    reset_live_db_projections()
    assert manager._db_projected is False
    assert "pi-llm-srv-live" not in manager._entries


async def test_settings_pi_catalog_info_merges_identity_view(monkeypatch):
    from app.api.routes import settings as settings_routes
    from app.core.pi_runtime.model_manager import PiEndpointInfo

    class _StubManager:
        def __init__(self, *args, **kwargs):
            pass

        async def ensure_db_projection(self):
            return None

        def catalog(self):
            return [
                PiEndpointInfo(
                    "pi-local-ollama", "stub-model", "openai_compat", kind="local"
                ),
                PiEndpointInfo("pi-llm-7", "gpu-model", "openai_compat", kind="remote"),
            ]

    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager.PiModelManager", _StubManager
    )
    entries = await settings_routes._pi_catalog_info()
    assert [e["endpoint_id"] for e in entries] == ["pi-local-ollama", "pi-llm-7"]
    # Identity/capability view only — never URLs or keys.
    for entry in entries:
        assert set(entry) <= {
            "endpoint_id",
            "model",
            "provider_kind",
            "context_window",
            "max_tokens",
            "supports_tools",
            "supports_vision",
            "kind",
            "pi_provider",
            "auth_method",
        }


@pytest.mark.asyncio
async def test_settings_pi_catalog_info_fails_closed_when_projection_is_unavailable(
    monkeypatch,
):
    """The compatibility model inventory must not hide Pi authority failures."""
    from fastapi import HTTPException
    from app.api.routes import settings as settings_routes

    class _BrokenManager:
        async def ensure_db_projection(self):
            raise RuntimeError("projection unavailable")

    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager.PiModelManager", _BrokenManager
    )

    with pytest.raises(HTTPException) as exc_info:
        await settings_routes._pi_catalog_info()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "error": "pi_catalog_unavailable",
        "message": "Pi model catalog is unavailable.",
    }


def test_projects_update_validates_agentic_engine():
    from pydantic import ValidationError

    from app.api.routes.projects import ProjectUpdate

    assert ProjectUpdate(agentic_engine="PI").agentic_engine == "pi"
    assert ProjectUpdate(agentic_engine="legacy").agentic_engine == "legacy"
    assert ProjectUpdate(agentic_engine="").agentic_engine is None
    with pytest.raises(ValidationError):
        ProjectUpdate(agentic_engine="bogus-engine")


# ── dispatcher: Pi embed through the gateway, fail-closed ───────────────


async def test_dispatcher_pi_embed_success_and_failure_accounting(monkeypatch):
    from app.core.agentic.dispatcher import AgenticDispatcher

    recorded = []

    async def capture(**kwargs):
        recorded.append(kwargs)

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", capture)
    legacy_calls = []

    async def legacy_spy(verb, **kwargs):
        legacy_calls.append(verb)
        return {"embeddings": [[9.9]]}

    class _StubGateway:
        def __init__(self, outcome=None, exc=None):
            self._outcome = outcome
            self._exc = exc

        async def embed(self, texts, *, model=None):
            if self._exc is not None:
                raise self._exc
            return self._outcome

    ok_gateway = _StubGateway(
        outcome={
            "embeddings": [[0.7]],
            "endpoint_id": "pi-local-ollama",
            "usage": {"estimate": False},
            "status": "success",
        }
    )
    dispatcher = AgenticDispatcher(
        legacy_executor=legacy_spy, embeddings_gateway=ok_gateway
    )
    vectors = await dispatcher.embed(texts=["x"], project_id="p1", engine="pi")
    assert vectors == [[0.7]]
    assert legacy_calls == []
    assert len(recorded) == 1
    assert recorded[0]["engine"] == "pi" and recorded[0]["purpose"] == "embed"
    assert recorded[0]["outcome"]["endpoint_id"] == "pi-local-ollama"

    # A gateway failure raises typed, records its one error row, and never
    # leaks onto the legacy plane.
    recorded.clear()
    failing = AgenticDispatcher(
        legacy_executor=legacy_spy,
        embeddings_gateway=_StubGateway(
            exc=PiEndpointResolutionError("no_matching_pi_embed_endpoint")
        ),
    )
    with pytest.raises(
        PiEndpointResolutionError, match="no_matching_pi_embed_endpoint"
    ):
        await failing.embed(texts=["x"], project_id="p1", engine="pi")
    assert legacy_calls == []
    assert len(recorded) == 1
    assert recorded[0]["engine"] == "pi"
    assert recorded[0]["outcome"]["status"] == "error"
    assert recorded[0]["error_type"] == "PiEndpointResolutionError"


# ── static: the migration is wired where the plan says ──────────────────


def test_static_wrappers_dispatch_and_drop_direct_legacy_calls():
    source = (REPO_ROOT / "backend/app/core/embeddings.py").read_text(encoding="utf-8")
    assert "ollama.embed(" not in source and "ollama.embed_batch(" not in source
    assert "agentic.embed" in source
    validation = _function_source(
        REPO_ROOT / "backend/app/core/validation.py", "_get_embeddings"
    )
    assert "agentic.embed" in validation
    assert "llm_router.embed_batch" not in validation


def test_static_dispatcher_embed_dispatches_pi_to_gateway():
    source = _function_source(
        REPO_ROOT / "backend/app/core/agentic/dispatcher.py", "embed"
    )
    assert "_embed_gateway" in source
    assert "pi_embed_gateway_unavailable" not in source


def test_static_ux_parity_hooks():
    # Classical LLM-server CRUD is retired; Pi endpoint mutations refresh the
    # live Pi authority directly.
    assert not (REPO_ROOT / "backend/app/api/routes/llm_servers.py").exists()
    settings_source = (REPO_ROOT / "backend/app/api/routes/settings.py").read_text(
        encoding="utf-8"
    )
    assert settings_source.count("reset_live_settings_catalogs()") >= 3
    discovery = (REPO_ROOT / "backend/app/core/network_discovery.py").read_text(
        encoding="utf-8"
    )
    assert "reset_live_db_projections" in discovery
    assert settings_source.count('"pi_catalog": await _pi_catalog_info()') == 2
    projects = (REPO_ROOT / "backend/app/api/routes/projects.py").read_text(
        encoding="utf-8"
    )
    assert "agentic_engine" in projects
    main = (REPO_ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert "assert_vector_space_invariant" in main
    assert "shared_embed_model = await assert_vector_space_invariant(" in main
    assert "dimension_probe=check_embedding_dimensions" in main
    assert 'raise RuntimeError("vector_space_invariant_violation")' in main


def test_static_legacy_embed_executor_uses_pi_model_authority():
    source = _function_source(
        REPO_ROOT / "backend/app/core/agentic/legacy.py", "_embed"
    )
    assert "EmbeddingsGateway" in source
    assert "ollama" not in source
