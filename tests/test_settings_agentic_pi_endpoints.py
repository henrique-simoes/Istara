"""Tests for the CF-SPEC-12 settings endpoints: agentic-engine switch + pi endpoint CRUD."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.pi_runtime.model_manager import PiModelManager
from app.main import app


def test_pi_default_omits_builtin_without_a_ready_credential(monkeypatch):
    """An identity catalog entry alone is not an available global chat default."""
    from app.api.routes import settings as settings_routes

    monkeypatch.setattr(settings, "pi_api_endpoints", [])
    monkeypatch.setattr(settings, "pi_default_endpoint_id", "", raising=False)
    monkeypatch.setattr(
        settings_routes,
        "pi_endpoint_credential_status",
        lambda _endpoint: "missing",
    )

    assert settings_routes._pi_default_info(
        [
            {
                "endpoint_id": "pi-deepseek-default",
                "model": "deepseek-v4-pro",
                "kind": "remote",
            }
        ]
    ) == (None, None)


@pytest_asyncio.fixture
async def client(admin_auth_headers):
    """Exercise both authentication middleware and route-level admin checks."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=admin_auth_headers,
    ) as authenticated_client:
        yield authenticated_client


@pytest.mark.asyncio
async def test_agentic_engine_switch_pi_and_istara(client, monkeypatch):
    monkeypatch.setattr(settings, "team_mode", True)
    original = settings.agentic_engine_default
    try:
        resp = await client.post("/api/settings/agentic-engine", json={"engine": "pi"})
        assert resp.status_code == 200
        assert resp.json()["agentic_engine_default"] == "pi"
        assert settings.agentic_engine_default == "pi"

        resp = await client.post("/api/settings/agentic-engine", json={"engine": "istara"})
        assert resp.status_code == 200
        assert resp.json()["agentic_engine_default"] == "legacy"
        assert settings.agentic_engine_default == "legacy"

        resp = await client.post("/api/settings/agentic-engine", json={"engine": "bogus"})
        assert resp.status_code == 400
    finally:
        settings.agentic_engine_default = original


@pytest.mark.asyncio
async def test_agentic_engine_reports_read_only_persistence(client, monkeypatch):
    """A read-only runtime must not claim the global engine was persisted."""
    from app.api.routes import settings as settings_routes

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings_routes, "_persist_env", lambda *_args: False)
    original = settings.agentic_engine_default
    try:
        response = await client.post(
            "/api/settings/agentic-engine", json={"engine": "legacy"}
        )

        assert response.status_code == 200, response.text
        assert response.json()["persisted"] is False
        assert response.json()["agentic_engine_default"] == "legacy"
    finally:
        settings.agentic_engine_default = original


@pytest.mark.asyncio
async def test_strict_routing_reports_read_only_persistence(client, monkeypatch):
    """A read-only runtime must not claim strict routing was persisted."""
    from app.api.routes import settings as settings_routes

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings_routes, "_persist_env", lambda *_args: False)
    original = settings.strict_auto_routing
    try:
        response = await client.post(
            "/api/settings/strict-routing", json={"enabled": not original}
        )

        assert response.status_code == 200, response.text
        assert response.json()["persisted"] is False
        assert response.json()["strict_auto_routing"] is (not original)
    finally:
        settings.strict_auto_routing = original


@pytest.mark.asyncio
async def test_pi_endpoint_crud(client, monkeypatch):
    from app.api.routes import settings as settings_routes

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings_routes, "_persist_env", lambda *_args: None)
    monkeypatch.setattr(
        settings_routes, "custody_pi_endpoint_credentials", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(settings_routes, "pi_endpoint_credential_status", lambda _ep: "ready")
    original = list(settings.pi_api_endpoints)
    try:
        settings.pi_api_endpoints = []
        # Keep the same production-style manager alive across every route
        # mutation.  The endpoint routes must refresh this manager because it
        # is the catalog used by Pi dispatchers, not merely mutate settings.
        manager = PiModelManager(include_local=False)
        assert {info.endpoint_id for info in manager.catalog()} == {"pi-deepseek-default"}
        payload = {
            "endpoint_id": "pi-test-endpoint",
            "provider_kind": "openai_compat",
            "base_url": "https://api.example.com",
            "model": "test-model-1",
            "keychain_service": "istara-test-key",
        }
        resp = await client.post("/api/settings/pi-endpoints", json=payload)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "added"
        added = {info.endpoint_id: info for info in manager.catalog()}
        assert added["pi-test-endpoint"].model == "test-model-1"
        assert added["pi-test-endpoint"].provider_kind == "openai_compat"

        reserved = await client.post(
            "/api/settings/pi-endpoints",
            json={**payload, "endpoint_id": "pi-petals-donor-1"},
        )
        assert reserved.status_code == 400
        assert "reserved" in reserved.json()["detail"]

        resp = await client.get("/api/settings/pi-endpoints")
        assert resp.status_code == 200
        ids = [e["endpoint_id"] for e in resp.json()["endpoints"]]
        assert ids == ["pi-test-endpoint"]
        assert "retirement_note" in resp.json()

        # duplicate rejected
        resp = await client.post("/api/settings/pi-endpoints", json=payload)
        assert resp.status_code == 409

        # https required
        resp = await client.post("/api/settings/pi-endpoints", json={
            **payload, "endpoint_id": "pi-bad", "base_url": "http://insecure.example.com",
        })
        assert resp.status_code == 400

        # keychain_service required
        resp = await client.post("/api/settings/pi-endpoints", json={
            **payload, "endpoint_id": "pi-bad2", "keychain_service": "",
        })
        assert resp.status_code == 400

        # update
        resp = await client.put("/api/settings/pi-endpoints/pi-test-endpoint",
                                json={**payload, "model": "test-model-2"})
        assert resp.status_code == 200
        assert settings.pi_api_endpoints[0].model == "test-model-2"
        updated = {info.endpoint_id: info for info in manager.catalog()}
        assert updated["pi-test-endpoint"].model == "test-model-2"

        # delete
        resp = await client.delete("/api/settings/pi-endpoints/pi-test-endpoint")
        assert resp.status_code == 200
        assert settings.pi_api_endpoints == []
        assert "pi-test-endpoint" not in {info.endpoint_id for info in manager.catalog()}
        resp = await client.delete("/api/settings/pi-endpoints/pi-test-endpoint")
        assert resp.status_code == 404
    finally:
        settings.pi_api_endpoints = original


@pytest.mark.asyncio
async def test_api_key_endpoint_rejects_missing_credential(client, monkeypatch):
    """A connection is never advertised when neither a new nor stored key exists."""
    from app.api.routes import settings as settings_routes
    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings_routes, "_persist_env", lambda *_args: None)
    original_endpoints = list(settings.pi_api_endpoints)
    try:
        settings.pi_api_endpoints = []
        response = await client.post(
            "/api/settings/pi-endpoints",
            json={
                "endpoint_id": "pi-missing-key",
                "provider_kind": "openai_compat",
                "base_url": "https://api.example.com",
                "model": "model-without-key",
                "keychain_service": "istara-missing-key",
                "auth_method": "api_key",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "pi_api_key_required"
        assert settings.pi_api_endpoints == []
    finally:
        settings.pi_api_endpoints = original_endpoints


@pytest.mark.asyncio
async def test_api_key_endpoint_reports_ready_without_returning_secret(client, monkeypatch):
    from app import config as app_config
    from app.api.routes import settings as settings_routes
    from app.core.pi_runtime import endpoint_policy

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings_routes, "_persist_env", lambda *_args: None)
    monkeypatch.setattr(endpoint_policy.sys, "platform", "darwin")
    monkeypatch.setattr(app_config, "_write_macos_keychain_secret", lambda *_args: True)
    monkeypatch.setattr(
        endpoint_policy, "_read_pi_endpoint_secret", lambda *_args, **_kwargs: "stored"
    )
    original_endpoints = list(settings.pi_api_endpoints)
    try:
        settings.pi_api_endpoints = []
        response = await client.post(
            "/api/settings/pi-endpoints",
            json={
                "endpoint_id": "pi-ready-key",
                "provider_kind": "openai_compat",
                "base_url": "https://api.example.com",
                "model": "model-with-key",
                "keychain_service": "istara-ready-key",
                "auth_method": "api_key",
                "api_key": "test-only-secret",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["credential_status"] == "ready"
        listed = await client.get("/api/settings/pi-endpoints")
        endpoint = listed.json()["endpoints"][0]
        assert endpoint["credential_status"] == "ready"
        assert "api_key" not in endpoint
        assert "test-only-secret" not in listed.text
    finally:
        settings.pi_api_endpoints = original_endpoints


@pytest.mark.asyncio
async def test_research_ensemble_preferences_are_ordered_and_distinct(client, monkeypatch):
    from app.api.routes import settings as settings_routes
    from app.config import PiApiEndpoint

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings_routes, "_persist_env", lambda *_args: None)
    monkeypatch.setattr(settings_routes, "pi_endpoint_credential_status", lambda _ep: "ready")
    original_endpoints = list(settings.pi_api_endpoints)
    original_preferences = list(settings.pi_research_endpoint_ids)
    try:
        settings.pi_api_endpoints = [
            PiApiEndpoint(
                endpoint_id="ep-a",
                base_url="https://a.example.com",
                model="model-a",
                keychain_service="key-a",
            ),
            PiApiEndpoint(
                endpoint_id="ep-b",
                base_url="https://b.example.com",
                model="model-b",
                keychain_service="key-b",
            ),
            PiApiEndpoint(
                endpoint_id="ep-a-replica",
                base_url="https://a-replica.example.com",
                model="model-a",
                keychain_service="key-a-replica",
            ),
        ]
        settings.pi_research_endpoint_ids = []

        saved = await client.put(
            "/api/settings/pi-research-ensemble",
            json={"endpoint_ids": ["ep-b", "ep-a"]},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["endpoint_ids"] == ["ep-b", "ep-a"]
        assert settings.pi_research_endpoint_ids == ["ep-b", "ep-a"]

        duplicate_identity = await client.put(
            "/api/settings/pi-research-ensemble",
            json={"endpoint_ids": ["ep-a", "ep-a-replica"]},
        )
        assert duplicate_identity.status_code == 400
        assert duplicate_identity.json()["detail"] == "duplicate_research_model_identity"
        assert settings.pi_research_endpoint_ids == ["ep-b", "ep-a"]

        listed = await client.get("/api/settings/pi-endpoints")
        assert listed.json()["research_endpoint_ids"] == ["ep-b", "ep-a"]

        deleted = await client.delete("/api/settings/pi-endpoints/ep-b")
        assert deleted.status_code == 200
        assert settings.pi_research_endpoint_ids == ["ep-a"]
    finally:
        settings.pi_api_endpoints = original_endpoints
        settings.pi_research_endpoint_ids = original_preferences


@pytest.mark.asyncio
async def test_pi_endpoint_default_is_auto_selected_and_switchable(client, monkeypatch):
    """The first connected provider is the global chat default until changed."""
    from app.api.routes import settings as settings_routes

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings_routes, "_persist_env", lambda *_args: None)
    monkeypatch.setattr(
        settings_routes, "custody_pi_endpoint_credentials", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(settings_routes, "pi_endpoint_credential_status", lambda _ep: "ready")
    original_endpoints = list(settings.pi_api_endpoints)
    original_default = getattr(settings, "pi_default_endpoint_id", "")
    payload = {
        "provider_kind": "openai_compat",
        "base_url": "https://api.example.com",
        "keychain_service": "istara-test-key",
    }
    try:
        settings.pi_api_endpoints = []
        monkeypatch.setattr(settings, "pi_default_endpoint_id", "", raising=False)

        first = await client.post(
            "/api/settings/pi-endpoints",
            json={**payload, "endpoint_id": "pi-first", "model": "model-first"},
        )
        assert first.status_code == 200
        assert first.json()["default_endpoint_id"] == "pi-first"

        second = await client.post(
            "/api/settings/pi-endpoints",
            json={**payload, "endpoint_id": "pi-second", "model": "model-second"},
        )
        assert second.status_code == 200
        assert second.json()["default_endpoint_id"] == "pi-first"

        listed = await client.get("/api/settings/pi-endpoints")
        assert listed.json()["default_endpoint_id"] == "pi-first"
        assert listed.json()["default_model"] == "model-first"

        switched = await client.post(
            "/api/settings/pi-default", json={"endpoint_id": "pi-second"}
        )
        assert switched.status_code == 200
        assert switched.json()["default_endpoint_id"] == "pi-second"
        assert settings.pi_default_endpoint_id == "pi-second"

        deleted = await client.delete("/api/settings/pi-endpoints/pi-second")
        assert deleted.status_code == 200
        assert deleted.json()["default_endpoint_id"] == "pi-first"
        assert settings.pi_default_endpoint_id == "pi-first"
    finally:
        settings.pi_api_endpoints = original_endpoints
        settings.pi_default_endpoint_id = original_default
