"""Contracts for the Pi-owned, versioned embedding-profile authority."""

from __future__ import annotations

import inspect

import httpx
import pytest
from sqlalchemy import delete, func, select

from app.config import settings
from app.core.pi_runtime.embedding_profile import (
    ActiveEmbeddingProfile,
    EmbeddingProfileError,
    bootstrap_embedding_profile,
    get_active_embedding_profile,
    public_embedding_profile,
    reset_embedding_profile_cache,
)
from app.core.pi_runtime.embeddings_gateway import (
    EmbeddingsGateway,
    default_embed_model,
)
from app.core.pi_runtime.endpoints import PiEndpointResolutionError, ResolvedPiEndpoint
from app.core.pi_runtime.model_manager import PiModelManager
from app.core.embeddings import EmbeddedChunk, TextChunk
from app.core.rag import VectorProfileMismatchError, VectorStore
from app.models.database import async_session, init_db
from app.models.embedding_profile import EmbeddingProfile


def _endpoint(endpoint_id: str, model: str) -> ResolvedPiEndpoint:
    return ResolvedPiEndpoint(
        endpoint_id=endpoint_id,
        provider_kind="openai_compat",
        base_url=f"http://{endpoint_id}.invalid/v1",
        model=model,
        api_key="",
        timeout_ms=30_000,
        max_retries=0,
        kind="remote",
    )


def _profile(endpoint_id: str, model: str) -> ActiveEmbeddingProfile:
    return ActiveEmbeddingProfile(
        profile_id="default",
        version=1,
        model_id=model,
        endpoint_id=endpoint_id,
        transport="pi_http",
        dimension=0,
        dtype="float",
        normalization="provider_native",
        cache_namespace=model,
        health_status="unknown",
        migration_source="test",
    )


@pytest.mark.asyncio
async def test_profile_bootstraps_once_and_classical_provider_cannot_mutate_it(
    monkeypatch,
):
    await init_db()
    async with async_session() as db:
        await db.execute(delete(EmbeddingProfile))
        await db.commit()

        reset_embedding_profile_cache()
        monkeypatch.setattr(settings, "llm_provider", "ollama")
        monkeypatch.setattr(settings, "ollama_embed_model", "bootstrap-embed")
        first = await bootstrap_embedding_profile(db)

        assert first.version == 1
        assert first.model_id == "bootstrap-embed"
        assert first.endpoint_id == "pi-local-ollama"
        assert first.cache_namespace == "bootstrap-embed"
        assert first.migration_source == "legacy:ollama"

        monkeypatch.setattr(settings, "llm_provider", "lmstudio")
        monkeypatch.setattr(settings, "lmstudio_embed_model", "must-not-take-over")
        second = await bootstrap_embedding_profile(db)

        assert second == first
        assert get_active_embedding_profile() == first
        count = await db.scalar(select(func.count()).select_from(EmbeddingProfile))
        assert count == 1

        await db.execute(delete(EmbeddingProfile))
        await db.commit()
        reset_embedding_profile_cache()


@pytest.mark.asyncio
async def test_profile_reloads_persisted_identity_instead_of_current_classical_setting(
    monkeypatch,
):
    await init_db()
    async with async_session() as db:
        await db.execute(delete(EmbeddingProfile))
        await db.commit()

        reset_embedding_profile_cache()
        monkeypatch.setattr(settings, "llm_provider", "lmstudio")
        monkeypatch.setattr(settings, "lmstudio_embed_model", "persisted-embed")
        persisted = await bootstrap_embedding_profile(db)

        reset_embedding_profile_cache()
        monkeypatch.setattr(settings, "llm_provider", "ollama")
        monkeypatch.setattr(settings, "ollama_embed_model", "wrong-after-restart")
        reloaded = await bootstrap_embedding_profile(db)

        assert reloaded == persisted
        assert reloaded.model_id == "persisted-embed"
        assert reloaded.endpoint_id == "pi-local-lmstudio"

        await db.execute(delete(EmbeddingProfile))
        await db.commit()
        reset_embedding_profile_cache()


def test_embedding_resolution_pins_endpoint_identity_not_only_model_name():
    manager = PiModelManager(
        endpoints=[
            _endpoint("embed-primary", "shared-embed"),
            _endpoint("embed-shadow", "shared-embed"),
        ],
        include_local=False,
    )

    resolved = manager.resolve_embed("shared-embed", endpoint_id="embed-shadow")

    assert resolved.endpoint_id == "embed-shadow"


def test_missing_pinned_embedding_endpoint_fails_closed_even_when_model_matches():
    manager = PiModelManager(
        endpoints=[_endpoint("embed-primary", "shared-embed")],
        include_local=False,
    )

    with pytest.raises(PiEndpointResolutionError, match="unknown_pi_embed_endpoint"):
        manager.resolve_embed("shared-embed", endpoint_id="removed-endpoint")


@pytest.mark.asyncio
async def test_gateway_uses_profile_model_and_exact_endpoint(monkeypatch):
    manager = PiModelManager(
        endpoints=[
            _endpoint("embed-primary", "shared-embed"),
            _endpoint("embed-shadow", "shared-embed"),
        ],
        include_local=False,
    )
    profile = _profile("embed-shadow", "shared-embed")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            request=request,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
        )

    monkeypatch.setattr(
        "app.core.pi_runtime.embeddings_gateway.get_active_embedding_profile",
        lambda: profile,
        raising=False,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await EmbeddingsGateway(manager=manager, client=client).embed(
            ["evidence"]
        )

    assert result["model"] == "shared-embed"
    assert result["endpoint_id"] == "embed-shadow"
    assert requests[0].url.host == "embed-shadow.invalid"


def test_default_embed_model_is_profile_owned_not_classical_provider(monkeypatch):
    profile = _profile("profile-endpoint", "profile-model")
    monkeypatch.setattr(
        "app.core.pi_runtime.embeddings_gateway.get_active_embedding_profile",
        lambda: profile,
        raising=False,
    )
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_embed_model", "classical-model")

    assert default_embed_model() == "profile-model"


@pytest.mark.asyncio
async def test_gateway_rejects_model_override_outside_active_profile(monkeypatch):
    profile = _profile("profile-endpoint", "profile-model")
    monkeypatch.setattr(
        "app.core.pi_runtime.embeddings_gateway.get_active_embedding_profile",
        lambda: profile,
        raising=False,
    )

    with pytest.raises(EmbeddingProfileError, match="embedding_profile_model_mismatch"):
        await EmbeddingsGateway(
            manager=PiModelManager(endpoints=[], include_local=False)
        ).embed(["evidence"], model="classical-model")


def test_startup_bootstraps_profile_before_vector_checks():
    from app.main import lifespan

    source = inspect.getsource(lifespan)
    bootstrap = source.index("bootstrap_embedding_profile")
    invariant = source.index("assert_vector_space_invariant")
    vector_health = source.index("check_embedding_dimensions")

    assert bootstrap < invariant
    assert bootstrap < vector_health


def test_public_metadata_surfaces_report_profile_not_classical_provider(monkeypatch):
    from app.api.routes import projects as project_routes
    from app.api.routes import settings as settings_routes
    from app.core.pi_runtime import embedding_profile as profile_module

    profile = _profile("profile-endpoint", "profile-model")
    monkeypatch.setattr(profile_module, "_active_profile", profile)
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    monkeypatch.setattr(settings, "lmstudio_embed_model", "classical-model")

    assert settings_routes._embed_model() == "profile-model"
    assert project_routes._embed_model() == "profile-model"
    assert public_embedding_profile() == {
        "profile_id": "default",
        "version": 1,
        "model_id": "profile-model",
        "endpoint_id": "profile-endpoint",
        "dimension": 0,
        "dtype": "float",
        "normalization": "provider_native",
        "health_status": "unknown",
    }


@pytest.mark.asyncio
async def test_vector_store_binds_v1_profile_and_rejects_silent_profile_change(
    monkeypatch, tmp_path
):
    from app.core.pi_runtime import embedding_profile as profile_module

    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path))
    monkeypatch.setattr(
        profile_module, "_active_profile", _profile("profile-endpoint", "profile-model")
    )
    store = VectorStore("project-profile-bound")
    await store.add_chunks(
        [
            EmbeddedChunk(
                chunk=TextChunk(text="exact source span", source="source.md"),
                vector=[0.1, 0.2],
            )
        ]
    )

    manifest = store._profile_manifest.read_text(encoding="utf-8")
    assert '"model_id": "profile-model"' in manifest
    assert '"version": 1' in manifest

    monkeypatch.setattr(
        profile_module,
        "_active_profile",
        ActiveEmbeddingProfile(
            **{**_profile("next-endpoint", "next-model").__dict__, "version": 2}
        ),
    )
    with pytest.raises(VectorProfileMismatchError, match="vector_profile_mismatch"):
        await store.search([0.1, 0.2])
    with pytest.raises(VectorProfileMismatchError, match="vector_profile_mismatch"):
        await store.add_chunks(
            [
                EmbeddedChunk(
                    chunk=TextChunk(text="must not mix", source="source.md"),
                    vector=[0.3, 0.4],
                )
            ]
        )

    from app.core import embeddings as embeddings_module
    from app.core.vector_health import check_embedding_dimensions

    async def probe(_text: str) -> list[float]:
        return [0.3, 0.4]

    monkeypatch.setattr(embeddings_module, "embed_text", probe)
    health = await check_embedding_dimensions(project_id="project-profile-bound")
    assert health["status"] == "profile_mismatch"
    assert health["profile_mismatches"] == [
        {"project_id": "project-profile-bound", "error": "vector_profile_mismatch"}
    ]
