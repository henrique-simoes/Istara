"""Tests for the CF-SPEC-12 settings endpoints: agentic-engine switch + pi endpoint CRUD."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.pi_runtime.model_manager import PiModelManager
from app.main import app


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
async def test_pi_endpoint_crud(client, monkeypatch):
    monkeypatch.setattr(settings, "team_mode", True)
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
