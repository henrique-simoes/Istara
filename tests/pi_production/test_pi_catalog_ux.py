"""Tests for the Pi catalog-driven model management (DEC-3 owner requirements):

- the settings UI gets a selectable catalog of ALL Pi providers/models
- adding an endpoint via catalog (provider+model) fills base_url/costs/
  capabilities automatically — no manual endpoint typing
- OAuth device-code / PKCE flows exist and expose status via the API
"""

from __future__ import annotations

import base64
import json
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


_DASHSCOPE_SINGAPORE_MODEL_IDS = {
    "qwen3.8-max",
    "qwen3.7-max",
    "qwen3.7-max-2026-06-08",
    "qwen3.7-max-2026-05-20",
    "qwen3-max",
    "qwen3-max-2026-01-23",
    "qwen3.7-plus",
    "qwen3.7-plus-2026-05-26",
    "qwen3.7-flash",
    "qwen3.7-flash-2026-07-15",
    "qwen3.6-plus",
    "qwen3.6-plus-2026-04-02",
    "qwen3.5-plus",
    "qwen3.5-plus-2026-04-20",
    "qwen3.5-plus-2026-02-15",
    "qwen3.6-flash",
    "qwen3.6-flash-2026-04-16",
    "qwen3.5-flash",
    "qwen3.5-flash-2026-02-23",
    "qwen-plus",
    "qwen-flash",
    "qwen3-coder-plus",
    "qwen3-coder-flash",
    "qwen3.6-35b-a3b",
    "qwen3.5-397b-a17b",
    "qwen3.5-122b-a10b",
    "qwen3.5-27b",
    "qwen3.5-35b-a3b",
    "qwen-plus-character",
    "qwen-flash-character",
    "qwen3-vl-plus",
    "qwen3-vl-flash",
    "qwen-vl-max",
    "qwen-vl-plus",
    "qwen3.5-omni-plus",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "glm-5.1",
    "glm-5.2",
    "ZHIPU/GLM-5.2",
}

# The live Docker provider proof may move through these exact model identities
# only when DashScope reports a provider rate limit. The same
# ``DASHSCOPE_API_KEY`` is valid for each attempt; a fallback must never be
# selected for auth, model-admission, transport, or application errors.
_DASHSCOPE_QWEN_RATE_LIMIT_FALLBACK = (
    "qwen3.7-plus",
    "qwen3.7-plus-2026-05-26",
    "qwen3.7-flash-2026-07-15",
)


def _fake_codex_access_token(account_id: str = "test-account") -> str:
    """Create a structurally valid (unsigned) Codex JWT for contract tests."""
    def encode(value: object) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()
    return ".".join(
        (
            encode({"alg": "none", "typ": "JWT"}),
            encode({"https://api.openai.com/auth": {"chatgpt_account_id": account_id}}),
            "signature",
        )
    )


@pytest.fixture()
def client(monkeypatch):
    from app import config as app_config
    from app.config import settings

    original_endpoints = list(settings.pi_api_endpoints)
    monkeypatch.setattr(settings_routes, "require_global_role", lambda request, role: None)
    monkeypatch.setattr(settings_routes, "_persist_pi_endpoints", lambda: None)
    monkeypatch.setattr(app_config, "_write_macos_keychain_secret", lambda *args, **kwargs: True)
    app = FastAPI()
    app.include_router(settings_routes.router, prefix="/api")
    with TestClient(app) as test_client:
        yield test_client
    settings.pi_api_endpoints = original_endpoints


def test_catalog_exposes_all_pi_providers_and_models(client):
    resp = client.get("/api/settings/pi-catalog")
    assert resp.status_code == 200
    data = resp.json()
    providers = data["providers"]
    # Canonical Pi catalog: 39 providers, >1200 models
    assert len(providers) >= 30
    assert data["total_models"] > 1000
    ids = {p["id"] for p in providers}
    for expected in ("deepseek", "dashscope", "openai", "anthropic", "google", "openai-codex", "openrouter", "github-copilot", "mistral", "groq"):
        assert expected in ids, f"catalog missing provider {expected}"


def test_catalog_provider_auth_hints(client):
    resp = client.get("/api/settings/pi-catalog")
    providers = {p["id"]: p for p in resp.json()["providers"]}
    # API-key provider
    assert "api_key" in providers["deepseek"]["login_methods"]
    assert providers["deepseek"]["env_var"] == "DEEPSEEK_API_KEY"
    assert "api_key" in providers["dashscope"]["login_methods"]
    assert providers["dashscope"]["env_var"] == "DASHSCOPE_API_KEY"
    assert providers["dashscope"]["base_url"] == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    assert {m["id"] for m in providers["dashscope"]["models"]} >= {"qwen3.7-plus", "qwen3.7-flash"}
    dashscope_model_ids = {m["id"] for m in providers["dashscope"]["models"]}
    assert all(model_id in dashscope_model_ids for model_id in _DASHSCOPE_QWEN_RATE_LIMIT_FALLBACK)
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


def test_regular_dashscope_catalog_matches_pi_singapore_contract(client):
    """Every model in the current Pi DashScope contract must be selectable.

    This is intentionally an exact set check: silently shipping only the two
    models used by one smoke test would make the settings catalog diverge from
    the user-owned Pi provider configuration.
    """
    resp = client.get("/api/settings/pi-catalog")
    assert resp.status_code == 200
    provider = next(item for item in resp.json()["providers"] if item["id"] == "dashscope")
    models = {item["id"]: item for item in provider["models"]}
    assert set(models) == _DASHSCOPE_SINGAPORE_MODEL_IDS
    assert all(item["api"] == "openai-completions" for item in models.values())
    assert all(item["baseUrl"] == provider["base_url"] for item in models.values())
    assert all(
        item["cost"][key] == 0
        for item in models.values()
        for key in ("input", "output", "cacheRead", "cacheWrite")
    )


def test_every_dashscope_model_is_resolvable_by_pi_model_management(client):
    """The expanded Pi list must be usable by the Settings resolver, not only listed."""
    for index, model_id in enumerate(sorted(_DASHSCOPE_SINGAPORE_MODEL_IDS)):
        resp = client.post(
            "/api/settings/pi-endpoints",
            json={
                "endpoint_id": f"dashscope-catalog-{index}",
                "pi_provider": "dashscope",
                "pi_model": model_id,
                "keychain_service": "istara-pi-dashscope",
                "api_key": "sk-test-dashscope",
            },
        )
        assert resp.status_code == 200, f"{model_id}: {resp.text}"
    endpoints = {
        item["model"]: item
        for item in client.get("/api/settings/pi-endpoints").json()["endpoints"]
        if item.get("pi_provider") == "dashscope"
    }
    assert endpoints["qwen3.7-plus"]["supports_reasoning"] is True
    assert endpoints["qwen3.7-plus"]["supports_vision"] is True
    assert endpoints["qwen-plus"]["supports_reasoning"] is False
    assert endpoints["qwen-plus"]["supports_vision"] is False


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


@pytest.mark.parametrize("model_id", [
    "qwen3.7-plus",
    "qwen3.7-plus-2026-05-26",
    "qwen3.7-flash",
    "qwen3.7-flash-2026-07-15",
])
def test_add_regular_dashscope_qwen_endpoint_via_catalog(client, model_id):
    """The supplied Pi custom-provider contract must be resolvable by the manager."""
    resp = client.post(
        "/api/settings/pi-endpoints",
        json={
            "endpoint_id": f"dashscope-{model_id}",
            "pi_provider": "dashscope",
            "pi_model": model_id,
            "keychain_service": "istara-pi-dashscope",
            "api_key": "sk-test-dashscope",
        },
    )
    assert resp.status_code == 200, resp.text
    endpoint = next(
        item for item in client.get("/api/settings/pi-endpoints").json()["endpoints"]
        if item["endpoint_id"] == f"dashscope-{model_id}"
    )
    assert endpoint["pi_provider"] == "dashscope"
    assert endpoint["model"] == model_id
    assert endpoint["provider_kind"] == "openai_compat"
    assert endpoint["base_url"] == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    assert endpoint["context_window"] == 1_000_000
    assert endpoint["max_tokens"] == 65_536


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


@pytest.mark.skipif(
    __import__("sys").platform != "darwin",
    reason="macOS Keychain custody contract; Linux custody is env-persist by design",
)
def test_update_endpoint_reuses_catalog_and_keychain_custody(client, monkeypatch):
    """PUT must preserve the canonical Pi catalog and secret-custody rules."""
    from app import config as app_config

    writes = []
    monkeypatch.setattr(
        app_config,
        "_write_macos_keychain_secret",
        lambda service, account, secret: writes.append((service, account, secret)) or True,
    )
    endpoint_id = "update-deepseek"
    created = client.post(
        "/api/settings/pi-endpoints",
        json={
            "endpoint_id": endpoint_id,
            "pi_provider": "deepseek",
            "pi_model": "deepseek-v4-pro",
            "keychain_service": "istara-pi-deepseek",
            "api_key": "sk-old",
        },
    )
    assert created.status_code == 200, created.text
    writes.clear()

    # A catalog update may omit derived fields; the route must resolve them and
    # keep the existing Keychain service while custodying the replacement key.
    updated = client.put(
        f"/api/settings/pi-endpoints/{endpoint_id}",
        json={
            "endpoint_id": endpoint_id,
            "pi_provider": "deepseek",
            "pi_model": "deepseek-v4-flash",
            "api_key": "sk-new",
        },
    )
    assert updated.status_code == 200, updated.text
    endpoint = next(
        item for item in client.get("/api/settings/pi-endpoints").json()["endpoints"]
        if item["endpoint_id"] == endpoint_id
    )
    assert endpoint["model"] == "deepseek-v4-flash"
    assert endpoint["base_url"].startswith("https://")
    assert endpoint["context_window"] > 0
    assert endpoint["keychain_service"] == "istara-pi-deepseek"
    assert writes == [("istara-pi-deepseek", "default", "sk-new")]

    # Explicit non-catalog updates retain the same validation contract as POST;
    # a failed update must not replace the previously valid endpoint.
    rejected = client.put(
        f"/api/settings/pi-endpoints/{endpoint_id}",
        json={
            "endpoint_id": endpoint_id,
            "base_url": "http://insecure.example.com",
            "model": "uncatalogued",
            "keychain_service": "istara-pi-deepseek",
        },
    )
    assert rejected.status_code == 400
    after_rejection = next(
        item for item in client.get("/api/settings/pi-endpoints").json()["endpoints"]
        if item["endpoint_id"] == endpoint_id
    )
    assert after_rejection["model"] == "deepseek-v4-flash"


@pytest.mark.parametrize("endpoint_id", ["pi-petals-legacy", "pi-deepseek-default"])
def test_endpoint_mutations_cannot_claim_reserved_or_builtin_identity(client, endpoint_id):
    """PUT/DELETE must preserve the same identity boundary as POST.

    The fixture injects rows directly to model a stale or malformed persisted
    settings payload; normal POST creation already rejects both identities.
    """
    from app.config import PiApiEndpoint, settings

    settings.pi_api_endpoints.append(
        PiApiEndpoint(
            endpoint_id=endpoint_id,
            base_url="https://example.invalid/v1",
            model="test-model",
            keychain_service="istara-test",
        )
    )

    updated = client.put(
        f"/api/settings/pi-endpoints/{endpoint_id}",
        json={"endpoint_id": endpoint_id, "model": "replacement-model"},
    )
    assert updated.status_code == 400

    deleted = client.delete(f"/api/settings/pi-endpoints/{endpoint_id}")
    assert deleted.status_code == 400
    assert any(item.endpoint_id == endpoint_id for item in settings.pi_api_endpoints)


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


def test_oauth_start_github_copilot_device_code(client, monkeypatch):
    """Admin-authorized GitHub device-code setup returns the expected shape."""
    from app.core.pi_runtime import oauth

    monkeypatch.setattr(
        oauth,
        "start_device_flow",
        lambda provider: oauth._store_flow(oauth.OAuthFlowState(
            provider=provider,
            flow_type="device_code",
            status="pending",
            user_code="ABCD-EFGH",
            verification_uri="https://github.com/login/device",
        )),
    )
    resp = client.post("/api/settings/pi-oauth/start", json={"provider": "github-copilot"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["flow_type"] == "device_code"
    assert body["user_code"]
    assert "github.com" in (body["verification_uri"] or "")
    # status view shows the pending flow
    flows = client.get("/api/settings/pi-oauth/flows").json()["flows"]
    assert any(f["provider"] == "github-copilot" and f["status"] == "pending" for f in flows)


def test_pkce_openrouter_flow_shape(client, monkeypatch):
    """OpenRouter PKCE must expose an auth_url (no device code)."""
    from app.core.pi_runtime import oauth

    monkeypatch.setattr(
        oauth,
        "start_pkce_flow",
        lambda redirect_uri: oauth._store_flow(oauth.OAuthFlowState(
            provider="openrouter",
            flow_type="pkce",
            method="browser",
            status="pending",
            auth_url="https://openrouter.ai/auth?state=test",
        )),
    )
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
            return {
                "access_token": _fake_codex_access_token(),
                "refresh_token": "refresh",
                "expires_in": 3600,
            }
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


def test_openai_codex_rejects_incomplete_or_unbound_token(monkeypatch):
    """Match Pi 0.84.3: Codex OAuth must be a complete account-bound JWT."""
    from app.core.pi_runtime import oauth

    assert oauth._codex_account_id("a.WzFd.c") is None
    oauth._FLOWS.clear()
    monkeypatch.setattr(
        oauth,
        "_http_request",
        lambda url, payload=None, **kwargs: {
            "access_token": "not-a-jwt",
            "refresh_token": "refresh",
            "expires_in": 3600,
        }
        if url.endswith("/oauth/token")
        else {},
    )
    flow = oauth.start_openai_browser_flow("https://istara.example/callback")
    with pytest.raises(ValueError, match="openai_token_response_invalid"):
        oauth.finish_openai_browser_flow("code", flow.state, flow.flow_id)
    assert flow.status == "failed"
    assert flow.error == "openai_token_response_invalid"
    oauth._FLOWS.clear()


def test_add_openai_codex_luna_via_catalog_uses_oauth_transport(client):
    """The requested Luna OAuth path must resolve through Pi Model Management."""
    from app.config import settings
    from app.core.pi_runtime import oauth

    flow = oauth._store_flow(oauth.OAuthFlowState(
        provider="openai-codex",
        oauth_provider="openai-codex",
        flow_type="device_code",
        method="device_code",
        status="approved",
        access_token=_fake_codex_access_token("luna-account"),
        refresh_token="refresh.jwt",
        credential_expires_at=9_999_999_999,
    ))
    endpoint_id = "openai-codex-gpt-5-6-luna-oauth-device-code"
    response = client.post(
        "/api/settings/pi-endpoints",
        json={
            "endpoint_id": endpoint_id,
            "pi_provider": "openai-codex",
            "pi_model": "gpt-5.6-luna",
            "auth_provider": "openai-codex",
            "auth_method": "oauth_device_code",
            "oauth_flow_id": flow.flow_id,
            "keychain_service": "istara-pi-oauth-openai-codex",
        },
    )
    assert response.status_code == 200, response.text
    endpoint = next(item for item in settings.pi_api_endpoints if item.endpoint_id == endpoint_id)
    assert endpoint.provider_kind == "openai_codex"
    assert endpoint.base_url == "https://chatgpt.com/backend-api"
    assert endpoint.model == "gpt-5.6-luna"
    assert endpoint.context_window == 272_000
    assert endpoint.max_tokens == 128_000
    assert endpoint.supports_vision is True
    assert endpoint.supports_reasoning is True
    settings.pi_api_endpoints = [item for item in settings.pi_api_endpoints if item.endpoint_id != endpoint_id]
    oauth._FLOWS.clear()


def test_oauth_credential_is_consumed_into_endpoint_custody(client, monkeypatch):
    from app.config import settings
    from app.core.pi_runtime import oauth

    flow = oauth._store_flow(oauth.OAuthFlowState(
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
            "oauth_flow_id": flow.flow_id,
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


def test_oauth_endpoint_sparse_update_preserves_existing_custody(client):
    """A metadata-only edit must not require re-authentication or drop OAuth."""
    from app.config import settings
    from app.core.pi_runtime import oauth

    flow = oauth._store_flow(oauth.OAuthFlowState(
        provider="openai-codex",
        oauth_provider="openai-codex",
        flow_type="device_code",
        method="device_code",
        status="approved",
        access_token="access.jwt",
        refresh_token="refresh.jwt",
    ))
    endpoint_id = "codex-oauth-sparse-update"
    created = client.post(
        "/api/settings/pi-endpoints",
        json={
            "endpoint_id": endpoint_id,
            "pi_provider": "openai-codex",
            "pi_model": "gpt-5.4",
            "auth_provider": "openai-codex",
            "auth_method": "oauth_device_code",
            "oauth_flow_id": flow.flow_id,
            "keychain_service": "istara-pi-oauth-openai-codex",
        },
    )
    assert created.status_code == 200, created.text
    original_ciphertext = next(
        item.oauth_credential_encrypted
        for item in settings.pi_api_endpoints
        if item.endpoint_id == endpoint_id
    )

    updated = client.put(
        f"/api/settings/pi-endpoints/{endpoint_id}",
        json={"endpoint_id": endpoint_id, "pi_provider": "openai-codex", "pi_model": "gpt-5.4"},
    )
    assert updated.status_code == 200, updated.text
    replacement = next(
        item for item in settings.pi_api_endpoints if item.endpoint_id == endpoint_id
    )
    assert replacement.oauth_credential_encrypted == original_ciphertext
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
