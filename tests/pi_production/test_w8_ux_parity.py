"""Executable W8 regressions for merged model and engine-indicator contracts."""

import pytest

from app.api.routes import projects as project_routes
from app.api.routes import settings as settings_routes
from app.config import settings


@pytest.mark.asyncio
async def test_settings_models_exposes_pi_catalog_and_normalized_global_engine(
    monkeypatch,
):
    class StubOllama:
        async def health(self):
            return True

    class StubRegistry:
        _nodes = {}

        async def list_models(self):
            return [{"name": "legacy-model", "model": "legacy-model"}]

    async def catalog_info():
        return [{"endpoint_id": "pi-1", "model": "pi-model", "kind": "remote"}]

    monkeypatch.setattr(settings_routes, "require_global_role", lambda *_a, **_k: None)
    monkeypatch.setattr(settings_routes, "ollama", StubOllama())
    monkeypatch.setattr("app.core.compute_registry.compute_registry", StubRegistry())
    monkeypatch.setattr(settings_routes, "_pi_catalog_info", catalog_info)
    monkeypatch.setattr(settings, "agentic_engine_default", "PI", raising=False)

    body = await settings_routes.get_models(object())

    assert body["agentic_engine_default"] == "pi"
    assert body["models"][0]["name"] == "legacy-model"
    assert body["pi_catalog"][0]["endpoint_id"] == "pi-1"


@pytest.mark.asyncio
async def test_project_response_exposes_normalized_global_engine(monkeypatch):
    project = type(
        "ProjectStub",
        (),
        dict(
            id="project-1",
            name="Project",
            description="",
            phase="discover",
            company_context="",
            project_context="",
            guardrails="",
            is_paused=False,
            owner_id="owner",
            watch_folder_path=None,
            agentic_engine=None,
            created_at=None,
            updated_at=None,
        ),
    )()
    monkeypatch.setattr(
        settings, "agentic_engine_default", "pi-replacement", raising=False
    )
    monkeypatch.setattr(
        project_routes, "get_subject", lambda _r: type("S", (), {"id": "u"})()
    )
    monkeypatch.setattr(project_routes, "is_global_admin", lambda _s: True)

    response = await project_routes._project_response(project, object(), object())

    assert response["global_agentic_engine"] == "pi"


@pytest.mark.asyncio
async def test_project_response_exposes_embed_model_as_safe_metadata(monkeypatch):
    """W3: the canonical embedding identity is visible in safe metadata — the
    model NAME only, never an endpoint URL or key."""
    project = type(
        "ProjectStub",
        (),
        dict(
            id="project-1",
            name="Project",
            description="",
            phase="discover",
            company_context="",
            project_context="",
            guardrails="",
            is_paused=False,
            owner_id="owner",
            watch_folder_path=None,
            agentic_engine=None,
            created_at=None,
            updated_at=None,
        ),
    )()
    from app.core.pi_runtime import embedding_profile as profile_module
    from app.core.pi_runtime.embedding_profile import ActiveEmbeddingProfile

    monkeypatch.setattr(
        profile_module,
        "_active_profile",
        ActiveEmbeddingProfile(
            profile_id="default",
            version=1,
            model_id="nomic-embed-text",
            endpoint_id="pi-local-ollama",
            transport="pi_http",
            dimension=0,
            dtype="float",
            normalization="provider_native",
            cache_namespace="nomic-embed-text",
            health_status="unknown",
            migration_source="test",
        ),
    )
    monkeypatch.setattr(
        project_routes, "get_subject", lambda _r: type("S", (), {"id": "u"})()
    )
    monkeypatch.setattr(project_routes, "is_global_admin", lambda _s: True)

    response = await project_routes._project_response(project, object(), object())

    assert response["embed_model"] == "nomic-embed-text"
    # Safe metadata: a bare model name — no scheme, host, port, or key material.
    assert "://" not in response["embed_model"]
    assert " " not in response["embed_model"]
