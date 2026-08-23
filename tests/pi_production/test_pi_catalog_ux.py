"""Tests for the Pi catalog-driven model management (DEC-3 owner requirements):

- the settings UI gets a selectable catalog of ALL Pi providers/models
- adding an endpoint via catalog (provider+model) fills base_url/costs/
  capabilities automatically — no manual endpoint typing
- OAuth device-code / PKCE flows exist and expose status via the API
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:9")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import settings as settings_routes


@pytest.fixture()
def client(monkeypatch):
    import app.core.permissions as perms

    monkeypatch.setattr(perms, "require_global_role", lambda request, role: None)
    app = FastAPI()
    app.include_router(settings_routes.router, prefix="/api")
    with TestClient(app) as test_client:
        yield test_client


def test_catalog_exposes_all_pi_providers_and_models(client):
    resp = client.get("/api/settings/pi-catalog")
    assert resp.status_code == 200
    data = resp.json()
    providers = data["providers"]
    # Canonical Pi catalog: 39 providers, >1200 models
    assert len(providers) >= 30
    assert data["total_models"] > 1000
    ids = {p["id"] for p in providers}
    for expected in ("deepseek", "openai", "anthropic", "google", "openai-codex", "openrouter", "github-copilot", "mistral", "groq"):
        assert expected in ids, f"catalog missing provider {expected}"


def test_catalog_provider_auth_hints(client):
    resp = client.get("/api/settings/pi-catalog")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    # API-key provider
    assert "api_key" in providers["deepseek"]["login_methods"]
    assert providers["deepseek"]["env_var"] == "DEEPSEEK_API_KEY"
    # OAuth/subscription provider
    assert "oauth" in providers["openai-codex"]["login_methods"]
    assert providers["openai-codex"]["oauth_flow"] == "openai_codex"
    assert set(providers["openai-codex"]["oauth_methods"]) == {"browser", "device_code"}
    # OpenAI API makes the ChatGPT subscription route explicit for the shared
    # Codex model ids instead of silently defaulting to an API key.
    assert "api_key" in providers["openai"]["login_methods"]
    assert "oauth" in providers["openai"]["login_methods"]
    assert "gpt-5.4" in providers["openai"]["oauth_model_ids"]
    # Google is API-key/ambient-credential only in the installed Pi loaders.
    assert "api_key" in providers["google"]["login_methods"]
    assert "oauth" not in providers["google"]["login_methods"]


def test_add_endpoint_via_catalog_no_manual_url(client):
    """DEC-3: selecting provider+model must fill base_url/costs — no typing."""
    resp = client.post(
        "/api/settings/pi-endpoints",
        json={
            "endpoint_id": "my-deepseek",
            "pi_provider": "deepseek",
            "pi_model": "deepseek-v4-pro",
            "keychain_service": "istara-pi-deepseek",
            "api_key": "sk-test-123",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "added"
    # confirm catalog fields were resolved
    listed = client.get("/api/settings/pi-endpoints").json()["endpoints"]
    ep = next(e for e in listed if e["endpoint_id"] == "my-deepseek")
    assert ep["model"] == "deepseek-v4-pro"
    assert ep["base_url"].startswith("https://")
    assert ep["provider_kind"] in ("openai_compat", "anthropic_compat")
    assert ep["context_window"] > 0
    assert ep["cost_input_per_mtok"] >= 0


def test_add_endpoint_unknown_catalog_model_rejected(client):
    resp = client.post(
        "/api/settings/pi-endpoints",
        json={
            "endpoint_id": "bad-model",
            "pi_provider": "deepseek",
            "pi_model": "does-not-exist-123",
            "keychain_service": "x",
        },
    )
    assert resp.status_code == 400


def test_oauth_flows_endpoints(client):
    resp = client.get("/api/settings/pi-oauth/flows")
    assert resp.status_code == 200
    assert resp.json() == {"flows": []}

    # unknown provider -> 400
    resp = client.post("/api/settings/pi-oauth/start", json={"provider": "nope"})
    assert resp.status_code == 400

    # cancel of an unknown flow -> 404-safe (returns cancelled for missing)
    resp = client.post("/api/settings/pi-oauth/cancel", json={"provider": "github-copilot"})
    assert resp.status_code == 200


def test_oauth_start_github_copilot_device_code(client):
    """GitHub device-code endpoint is public; a real user_code should come back."""
    resp = client.post("/api/settings/pi-oauth/start", json={"provider": "github-copilot"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["flow_type"] == "device_code"
    assert body["user_code"]
    assert "github.com" in (body["verification_uri"] or "")
    # status view shows the pending flow
    flows = client.get("/api/settings/pi-oauth/flows").json()["flows"]
    assert any(f["provider"] == "github-copilot" and f["status"] == "pending" for f in flows)


def test_pkce_openrouter_flow_shape(client):
    """OpenRouter PKCE must expose an auth_url (no device code)."""
    resp = client.post("/api/settings/pi-oauth/start", json={"provider": "openrouter", "method": "browser"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["flow_type"] == "pkce"
    assert "openrouter.ai" in (body["auth_url"] or "")


def test_openai_codex_exposes_browser_and_headless_methods(monkeypatch):
    from app.core.pi_runtime import oauth

    oauth._FLOWS.clear()
    calls = []

    def fake_request(url, payload=None, **kwargs):
        calls.append((url, payload, kwargs))
        if url.endswith("/usercode"):
            return {"device_auth_id": "device-1", "user_code": "ABCD-EFGH", "interval": 2}
        if url.endswith("/deviceauth/token"):
            return {"authorization_code": "auth-code", "code_verifier": "device-verifier"}
        if url.endswith("/oauth/token"):
            return {"access_token": "access.jwt", "refresh_token": "refresh", "expires_in": 3600}
        raise AssertionError(url)

    monkeypatch.setattr(oauth, "_http_request", fake_request)
    browser = oauth.start_openai_browser_flow("https://istara.example/api/settings/pi-oauth/openai/callback")
    assert browser.method == "browser"
    assert browser.flow_id
    assert "auth.openai.com/oauth/authorize" in browser.auth_url
    assert "code_challenge=" in browser.auth_url
    assert browser.redirect_uri.endswith("/openai/callback")

    device = oauth.start_openai_device_flow()
    assert device.method == "device_code"
    assert device.flow_id != browser.flow_id
    assert len(oauth._FLOWS) == 2
    assert device.user_code == "ABCD-EFGH"
    pending = oauth.poll_openai_device_flow(device)
    assert pending.status == "approved"
    assert pending.token_masked
    assert any(url.endswith("/oauth/token") for url, _, _ in calls)
    oauth._FLOWS.clear()


def test_oauth_credential_is_consumed_into_endpoint_custody(client, monkeypatch):
    from app.config import settings
    from app.core.pi_runtime import oauth

    oauth._store_flow(oauth.OAuthFlowState(
        provider="openai-codex",
        oauth_provider="openai-codex",
        flow_type="device_code",
        method="device_code",
        status="approved",
        access_token="access.jwt",
        refresh_token="refresh.jwt",
    ))
    endpoint_id = "codex-oauth-custody-test"
    response = client.post(
        "/api/settings/pi-endpoints",
        json={
            "endpoint_id": endpoint_id,
            "pi_provider": "openai-codex",
            "pi_model": "gpt-5.4",
            "auth_provider": "openai-codex",
            "auth_method": "oauth_device_code",
            "keychain_service": "istara-pi-oauth-openai-codex",
        },
    )
    assert response.status_code == 200, response.text
    listed = client.get("/api/settings/pi-endpoints").json()["endpoints"]
    endpoint = next(item for item in listed if item["endpoint_id"] == endpoint_id)
    assert "oauth_credential_encrypted" not in endpoint
    assert endpoint["auth_method"] == "oauth_device_code"
    settings.pi_api_endpoints = [item for item in settings.pi_api_endpoints if item.endpoint_id != endpoint_id]
    with pytest.raises(ValueError, match="oauth_credential_not_ready"):
        oauth.consume_oauth_credential("openai-codex")
    oauth._FLOWS.clear()


def test_catalog_openai_codex_transport_is_distinct():
    from app.config import PiApiEndpoint

    endpoint = PiApiEndpoint(
        endpoint_id="codex-test",
        provider_kind="openai_codex",
        base_url="https://chatgpt.com/backend-api",
        model="gpt-5.4",
        keychain_service="istara-pi-oauth-openai-codex",
        auth_provider="openai-codex",
        auth_method="oauth_device_code",
    )
    assert endpoint.provider_kind == "openai_codex"
    assert endpoint.auth_method == "oauth_device_code"
