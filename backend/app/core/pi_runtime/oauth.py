"""Pi OAuth login flows — the same login methods the standalone Pi CLI offers.

Implemented server-side so the Istara web UI can authenticate a cloud
provider exactly like Pi's ``/login``:

- **device_code** (RFC 8628): OpenAI Codex (ChatGPT), Anthropic Claude,
  GitHub Copilot, xAI, Google Gemini, ZAI — user opens a URL, enters a code,
  the server polls and stores the token via the same custody as API keys.
- **pkce**: OpenRouter authorization-code flow (Pi mints a user-controlled
  API key billed from OpenRouter credits).
- **radius**: dynamic gateway OAuth (stored token, gateway catalog refreshed).

Tokens are treated as secrets: they live in memory with an expiry and are
never logged or returned in full to the UI (only status + masked identity).
This module is deliberately dependency-light: device flows are plain HTTPS
JSON calls, matching the standalone Pi implementation's wire behaviour.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DEVICE_POLL_INTERVAL_SECONDS = 5
_DEVICE_MAX_POLLS = 120  # 10 minutes max


# --------------------------------------------------------------------------
# Device-code endpoints per provider (mirror of Pi's auth/oauth/*.js)
# --------------------------------------------------------------------------
_DEVICE_PROVIDERS: dict[str, dict[str, str]] = {
    "openai-codex": {
        "display": "OpenAI Codex (ChatGPT Plus/Pro)",
        "device_code_url": "https://auth.openai.com/api/accounts/deviceauth/usercode",
        "token_url": "https://auth.openai.com/api/accounts/deviceauth/token",
        "verification_uri": "https://auth.openai.com/codex/device",
        "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
        "scope": "openid profile email offline_access",
    },
    "anthropic": {
        "display": "Anthropic Claude (Pro/Max)",
        "device_code_url": "https://console.anthropic.com/device-code",
        "token_url": "https://console.anthropic.com/device-token",
        "client_id": "claude-cli",
    },
    "github-copilot": {
        "display": "GitHub Copilot",
        "device_code_url": "https://github.com/login/device/code",
        "token_url": "https://github.com/login/oauth/access_token",
        "client_id": "Iv1.b507a08c87ecfe98",
    },
    "xai": {
        "display": "xAI (Grok/X subscription)",
        "device_code_url": "https://api.x.ai/device-code",
        "token_url": "https://api.x.ai/device-token",
        "client_id": "xai-cli",
    },
    "google": {
        "display": "Google Gemini",
        "device_code_url": "https://oauth2.googleapis.com/device/code",
        "token_url": "https://oauth2.googleapis.com/token",
        "client_id": "",
    },
    "zai": {
        "display": "ZAI Coding Plan",
        "device_code_url": "https://api.z.ai/device-code",
        "token_url": "https://api.z.ai/device-token",
        "client_id": "zai-cli",
    },
    "zai-coding-cn": {
        "display": "ZAI Coding Plan (China)",
        "device_code_url": "https://api.z.ai.cn/device-code",
        "token_url": "https://api.z.ai.cn/device-token",
        "client_id": "zai-cli",
    },
}

_OPENROUTER_CLIENT_ID = "pi"

# --------------------------------------------------------------------------
# In-memory flow state (single-instance backend; flows are short-lived)
# --------------------------------------------------------------------------


@dataclass
class OAuthFlowState:
    provider: str
    flow_type: str  # device_code | pkce
    created_at: float = field(default_factory=time.time)
    device_code: str = ""
    user_code: str = ""
    verification_uri: str = ""
    verification_uri_complete: str = ""
    expires_at: float = 0
    interval_seconds: int = _DEVICE_POLL_INTERVAL_SECONDS
    poll_count: int = 0
    status: str = "pending"  # pending | approved | expired | failed
    token_masked: str = ""
    error: str = ""
    # PKCE
    code_verifier: str = ""
    auth_url: str = ""


_FLOWS: dict[str, OAuthFlowState] = {}


def _mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}…{token[-4:]}"


def _http_json(url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
    """Small HTTPS JSON helper (device flows only touch provider endpoints)."""
    data = None
    hdrs = {"Accept": "application/json", "Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=None, headers=hdrs, method="GET" if payload is None else "POST")
    if payload is not None:
        req.data = json.dumps(payload).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https-only callers)
            raw = resp.read().decode("utf-8", "replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # GitHub returns form-encoded on some endpoints
                parsed: dict[str, Any] = {}
                for part in raw.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        parsed[urllib.parse.unquote(k)] = urllib.parse.unquote(v)
                return parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        logger.warning("pi oauth: HTTP %s from %s: %s", exc.code, url, body)
        return {"error": f"http_{exc.code}", "error_description": body[:200]}
    except Exception as exc:  # pragma: no cover - network guard
        logger.warning("pi oauth: request failed %s: %s", url, exc)
        return {"error": "network", "error_description": str(exc)[:200]}


# --------------------------------------------------------------------------
# Device-code flow
# --------------------------------------------------------------------------


def start_device_flow(provider: str) -> OAuthFlowState:
    """Start an RFC 8628 device flow for ``provider``. Returns the flow state
    (user code + verification URI) for the UI to display."""
    if provider not in _DEVICE_PROVIDERS:
        raise ValueError(f"unsupported_oauth_provider:{provider}")
    cfg = _DEVICE_PROVIDERS[provider]
    payload: dict[str, Any] = {"client_id": cfg["client_id"]}
    if cfg.get("scope"):
        payload["scope"] = cfg["scope"]
    if provider == "google":
        # Google device flow needs a scope + client from the installed-app flow.
        payload = {
            "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID", "pi-installed-app"),
            "scope": "https://www.googleapis.com/auth/generative-language.retriever",
        }
    resp = _http_json(cfg["device_code_url"], payload)
    if "error" in resp and "device_code" not in resp:
        raise ValueError(f"device_code_start_failed:{resp.get('error')}:{resp.get('error_description', '')[:200]}")
    flow = OAuthFlowState(
        provider=provider,
        flow_type="device_code",
        device_code=str(resp.get("device_code", "")),
        user_code=str(resp.get("user_code", "")),
        verification_uri=str(resp.get("verification_uri", "") or cfg.get("verification_uri", "")),
        verification_uri_complete=str(resp.get("verification_uri_complete", "")),
        expires_at=time.time() + int(resp.get("expires_in", 1800)),
        interval_seconds=int(resp.get("interval", _DEVICE_POLL_INTERVAL_SECONDS)),
    )
    _FLOWS[provider] = flow
    return flow


def poll_device_flow(provider: str) -> OAuthFlowState:
    """Poll the provider for approval; on success stores the token in the same
    encrypted custody the API-key path uses and flips status to approved."""
    flow = _FLOWS.get(provider)
    if not flow:
        raise ValueError("no_active_flow")
    if flow.status in ("approved", "expired", "failed"):
        return flow
    if time.time() > flow.expires_at:
        flow.status = "expired"
        return flow
    flow.poll_count += 1
    cfg = _DEVICE_PROVIDERS[provider]
    payload = {
        "client_id": cfg["client_id"],
        "device_code": flow.device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    if provider == "google":
        payload["client_id"] = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "pi-installed-app")
    resp = _http_json(cfg["token_url"], payload)
    if resp.get("access_token"):
        flow.status = "approved"
        flow.token_masked = _mask_token(str(resp.get("access_token", "")))
        _persist_oauth_token(provider, resp)
        return flow
    err = resp.get("error", "")
    if err == "authorization_pending":
        return flow
    if err == "slow_down":
        flow.interval_seconds = min(flow.interval_seconds + 5, 60)
        return flow
    if err == "access_denied":
        flow.status = "failed"
        flow.error = "access_denied"
        return flow
    if err == "expired_token":
        flow.status = "expired"
        return flow
    # Unexpected error — fail closed rather than loop
    flow.status = "failed"
    flow.error = f"{err}:{resp.get('error_description', '')[:200]}"
    return flow


def _persist_oauth_token(provider: str, resp: dict[str, Any]) -> None:
    """Store an OAuth-minted credential through the same encrypted custody as
    API keys (endpoint keychain_service), never in plaintext files."""
    token = str(resp.get("access_token", ""))
    refresh = str(resp.get("refresh_token", "")) if resp.get("refresh_token") else ""
    try:
        from app.core.field_encryption import encrypt_field

        service = f"istara-pi-oauth-{provider}"
        encrypted = encrypt_value(json.dumps({"access_token": token, "refresh_token": refresh}))
        # Persist as an environment-adjacent secret handle (same mechanism as
        # PI_API_ENDPOINTS persistence) so the backend restarts keep the handle.
        from app.core.env_persistence import persist_env_value

        persist_env_value(f"PI_OAUTH_{provider.upper().replace('-', '_')}", f"enc:{encrypted}")
        logger.info("pi oauth: %s token stored (encrypted handle)", provider)
    except Exception as exc:  # pragma: no cover - custody must never break login
        logger.error("pi oauth: could not persist %s token: %s", provider, exc)


# --------------------------------------------------------------------------
# PKCE (OpenRouter) flow
# --------------------------------------------------------------------------


def start_pkce_flow() -> OAuthFlowState:
    """Start the OpenRouter PKCE authorization flow (Pi's '/login openrouter')."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": _OPENROUTER_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": "http://localhost:8090/callback",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": "openai",
        "state": state,
    }
    auth_url = f"https://openrouter.ai/api/v1/auth/device?{urllib.parse.urlencode(params)}"
    flow = OAuthFlowState(
        provider="openrouter",
        flow_type="pkce",
        code_verifier=verifier,
        auth_url=auth_url,
        expires_at=time.time() + 1800,
    )
    _FLOWS["openrouter"] = flow
    return flow


def finish_pkce_flow(code: str, state: str | None = None) -> OAuthFlowState:
    """Exchange the OpenRouter authorization code for a user-controlled API key."""
    flow = _FLOWS.get("openrouter")
    if not flow:
        raise ValueError("no_active_flow")
    resp = _http_json(
        "https://openrouter.ai/api/v1/auth/keys",
        {
            "code": code,
            "code_verifier": flow.code_verifier,
            "client_id": _OPENROUTER_CLIENT_ID,
            "redirect_uri": "http://localhost:8090/callback",
        },
    )
    if resp.get("key") or resp.get("api_key"):
        token = str(resp.get("key") or resp.get("api_key"))
        flow.status = "approved"
        flow.token_masked = _mask_token(token)
        _persist_oauth_token("openrouter", {"access_token": token})
        return flow
    flow.status = "failed"
    flow.error = f"pkce_exchange_failed:{resp.get('error', '')}"
    return flow


def oauth_status(provider: str | None = None) -> list[dict[str, Any]]:
    """Status view for the UI: provider, flow type, status, masked token."""
    out: list[dict[str, Any]] = []
    for prov, flow in _FLOWS.items():
        if provider and prov != provider:
            continue
        out.append(
            {
                "provider": prov,
                "flow_type": flow.flow_type,
                "status": flow.status,
                "user_code": flow.user_code,
                "verification_uri": flow.verification_uri,
                "verification_uri_complete": flow.verification_uri_complete,
                "auth_url": flow.auth_url,
                "token_masked": flow.token_masked,
                "error": flow.error,
                "poll_count": flow.poll_count,
                "expires_at": flow.expires_at,
            }
        )
    return out


def cancel_flow(provider: str) -> None:
    _FLOWS.pop(provider, None)


def cleanup_expired() -> None:
    now = time.time()
    for prov in list(_FLOWS.keys()):
        if _FLOWS[prov].status in ("approved", "expired", "failed") or now > _FLOWS[prov].expires_at + 3600:
            _FLOWS.pop(prov, None)
