"""Pi-compatible OAuth flows for the web model-management surface.

The standalone Pi CLI owns the provider protocols.  The web adapter mirrors the
same user-facing methods without ever returning credentials to the browser:

* OpenAI Codex: browser PKCE callback **or** headless device code.
* OpenRouter: browser PKCE authorization.
* GitHub Copilot, xAI, and Kimi Code: device-code login.
* Other providers are advertised only when their Pi loader exposes a supported
  method.  An unsupported method is rejected instead of being guessed.

Short-lived flow state is kept in memory.  Completed access/refresh credentials
are encrypted at rest and the access token is placed in the same Keychain/env
custody path used by Pi endpoint resolution.  Status responses contain only
masked identity and never token material.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DEVICE_POLL_INTERVAL_SECONDS = 5
_DEVICE_MAX_POLLS = 180
_OPENAI_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
_OPENAI_AUTH_BASE = "https://auth.openai.com"
_OPENAI_DEVICE_USER_CODE_URL = f"{_OPENAI_AUTH_BASE}/api/accounts/deviceauth/usercode"
_OPENAI_DEVICE_TOKEN_URL = f"{_OPENAI_AUTH_BASE}/api/accounts/deviceauth/token"
_OPENAI_DEVICE_VERIFICATION_URI = f"{_OPENAI_AUTH_BASE}/codex/device"
_OPENAI_DEVICE_REDIRECT_URI = f"{_OPENAI_AUTH_BASE}/deviceauth/callback"
_OPENAI_AUTHORIZE_URL = f"{_OPENAI_AUTH_BASE}/oauth/authorize"
_OPENAI_TOKEN_URL = f"{_OPENAI_AUTH_BASE}/oauth/token"
_OPENAI_SCOPE = "openid profile email offline_access"
_OPENROUTER_CLIENT_ID = "pi"
_ANTHROPIC_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
_ANTHROPIC_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
_ANTHROPIC_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_ANTHROPIC_SCOPE = "org:create_api_key user:profile user:inference user:sessions:claude_code user:mcp_servers user:file_upload"

# The generic entries match the current pi-ai loaders.  OpenAI and OpenRouter
# have dedicated implementations below because their callback/token shapes are
# not RFC-8628-compatible.
_DEVICE_PROVIDERS: dict[str, dict[str, Any]] = {
    "github-copilot": {
        "device_code_url": "https://github.com/login/device/code",
        "token_url": "https://github.com/login/oauth/access_token",
        "verification_uri": "https://github.com/login/device",
        "client_id": "Iv1.b507a08c87ecfe98",
        "form": False,
    },
    "xai": {
        "device_code_url": "https://auth.x.ai/oauth2/device/code",
        "token_url": "https://auth.x.ai/oauth2/token",
        "client_id": "b1a00492-073a-47ea-816f-4c329264a828",
        "scope": "openid profile email offline_access grok-cli:access api:access",
        "form": True,
    },
    "kimi-coding": {
        "device_code_url": "https://auth.kimi.com/api/oauth/device_authorization",
        "token_url": "https://auth.kimi.com/api/oauth/token",
        "client_id": "17e5f671-d194-4dfb-9706-5516cb48c098",
        "form": True,
    },
}


@dataclass
class OAuthFlowState:
    provider: str
    flow_type: str  # device_code | pkce
    method: str = "device_code"
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
    code_verifier: str = ""
    state: str = ""
    auth_url: str = ""
    redirect_uri: str = ""
    oauth_provider: str = ""
    access_token: str = ""
    refresh_token: str = ""


_FLOWS: dict[str, OAuthFlowState] = {}


def _mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}…{token[-4:]}"


def _parse_response(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        parsed: dict[str, Any] = {}
        for part in raw.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                parsed[urllib.parse.unquote_plus(key)] = urllib.parse.unquote_plus(value)
        return parsed


def _http_request(
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    form: bool = False,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    body: bytes | None = None
    request_headers = {"Accept": "application/json"}
    if payload is not None:
        if form:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = urllib.parse.urlencode(payload).encode("utf-8")
        else:
            request_headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (allowlisted provider URLs)
            return _parse_response(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        # Do not log response bodies: OAuth errors can contain provider data or
        # reflected authorization input.  The UI receives a bounded generic code.
        return {"error": f"http_{exc.code}"}
    except Exception as exc:  # pragma: no cover - network guard
        logger.warning("pi oauth request failed for %s: %s", urllib.parse.urlsplit(url).netloc, type(exc).__name__)
        return {"error": "network"}


def _http_json(url: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return _http_request(url, payload, **kwargs)


def _oauth_env_key(provider: str) -> str:
    return f"PI_OAUTH_{provider.upper().replace('-', '_')}"


def _oauth_keychain_service(provider: str) -> str:
    return f"istara-pi-oauth-{provider}"


def _complete_flow(flow: OAuthFlowState, response: dict[str, Any]) -> OAuthFlowState:
    access = str(response.get("access_token") or response.get("access") or "")
    if not access:
        flow.status = "failed"
        flow.error = "oauth_token_missing_access"
        return flow
    flow.status = "approved"
    flow.token_masked = _mask_token(access)
    flow.access_token = access
    flow.refresh_token = str(response.get("refresh_token") or response.get("refresh") or "")
    return flow


# ---------------------------------------------------------------------------
# OpenAI Codex — exact Pi browser + headless methods
# ---------------------------------------------------------------------------


def _parse_authorization_input(value: str) -> tuple[str, str | None]:
    """Parse Pi's manual browser fallback: code, URL, or code#state."""
    raw = value.strip()
    if not raw:
        raise ValueError("oauth_code_required")
    try:
        parsed = urllib.parse.urlsplit(raw)
        if parsed.scheme and parsed.query:
            params = urllib.parse.parse_qs(parsed.query)
            code = (params.get("code") or [""])[0]
            state = (params.get("state") or [None])[0]
            if code:
                return code, state
    except ValueError:
        pass
    if "#" in raw:
        code, state = raw.split("#", 1)
        return code, state
    if "code=" in raw:
        params = urllib.parse.parse_qs(raw)
        return (params.get("code") or [""])[0], (params.get("state") or [None])[0]
    return raw, None


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def start_openai_browser_flow(callback_url: str) -> OAuthFlowState:
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": _OPENAI_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": _OPENAI_SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "pi",
    }
    flow = OAuthFlowState(
        provider="openai-codex",
        oauth_provider="openai-codex",
        flow_type="pkce",
        method="browser",
        code_verifier=verifier,
        state=state,
        redirect_uri=callback_url,
        auth_url=f"{_OPENAI_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}",
        expires_at=time.time() + 1800,
    )
    _FLOWS["openai-codex"] = flow
    return flow


def _exchange_openai_code(code: str, verifier: str, redirect_uri: str) -> dict[str, Any]:
    return _http_request(
        _OPENAI_TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": _OPENAI_CLIENT_ID,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
        },
        form=True,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def finish_openai_browser_flow(code: str, state: str) -> OAuthFlowState:
    flow = _FLOWS.get("openai-codex")
    if not flow or flow.method != "browser":
        raise ValueError("no_active_openai_browser_flow")
    if time.time() > flow.expires_at:
        flow.status = "expired"
        return flow
    if not state or not secrets.compare_digest(state, flow.state):
        flow.status = "failed"
        flow.error = "oauth_state_mismatch"
        raise ValueError("oauth_state_mismatch")
    response = _exchange_openai_code(code, flow.code_verifier, flow.redirect_uri)
    if response.get("error"):
        flow.status = "failed"
        flow.error = str(response.get("error"))[:120]
        raise ValueError("openai_token_exchange_failed")
    return _complete_flow(flow, response)


def start_openai_device_flow() -> OAuthFlowState:
    response = _http_json(_OPENAI_DEVICE_USER_CODE_URL, {"client_id": _OPENAI_CLIENT_ID})
    if response.get("error"):
        raise ValueError(f"device_code_start_failed:{response['error']}")
    device_auth_id = str(response.get("device_auth_id") or "")
    user_code = str(response.get("user_code") or "")
    interval = response.get("interval", _DEVICE_POLL_INTERVAL_SECONDS)
    if not device_auth_id or not user_code:
        raise ValueError("invalid_openai_device_code_response")
    flow = OAuthFlowState(
        provider="openai-codex",
        oauth_provider="openai-codex",
        flow_type="device_code",
        method="device_code",
        device_code=device_auth_id,
        user_code=user_code,
        verification_uri=_OPENAI_DEVICE_VERIFICATION_URI,
        expires_at=time.time() + 15 * 60,
        interval_seconds=max(1, int(interval)),
    )
    _FLOWS["openai-codex"] = flow
    return flow


def poll_openai_device_flow(flow: OAuthFlowState) -> OAuthFlowState:
    if flow.status in ("approved", "expired", "failed"):
        return flow
    if time.time() > flow.expires_at or flow.poll_count >= _DEVICE_MAX_POLLS:
        flow.status = "expired"
        return flow
    flow.poll_count += 1
    response = _http_json(
        _OPENAI_DEVICE_TOKEN_URL,
        {"device_auth_id": flow.device_code, "user_code": flow.user_code},
    )
    if response.get("authorization_code") and response.get("code_verifier"):
        exchanged = _exchange_openai_code(
            str(response["authorization_code"]),
            str(response["code_verifier"]),
            _OPENAI_DEVICE_REDIRECT_URI,
        )
        if exchanged.get("error"):
            flow.status = "failed"
            flow.error = "openai_token_exchange_failed"
            return flow
        return _complete_flow(flow, exchanged)
    error = str(response.get("error") or "")
    if error in {"authorization_pending", "deviceauth_authorization_pending", "http_403", "http_404"}:
        return flow
    if error == "slow_down":
        flow.interval_seconds = min(flow.interval_seconds + 5, 60)
        return flow
    if error in {"access_denied", "authorization_denied"}:
        flow.status = "failed"
        flow.error = "access_denied"
        return flow
    flow.status = "failed"
    flow.error = error or "openai_device_poll_failed"
    return flow


# ---------------------------------------------------------------------------
# Other Pi loaders: RFC-8628 device code and OpenRouter PKCE
# ---------------------------------------------------------------------------


def consume_oauth_credential(provider: str) -> dict[str, str]:
    """Return the just-approved credential to the authenticated endpoint add.

    The caller immediately encrypts this value into the endpoint's persisted
    secret field. It is never serialized into OAuth status or sent to the UI.
    """
    flow = _FLOWS.get(provider)
    if not flow or flow.status != "approved" or not flow.access_token:
        raise ValueError("oauth_credential_not_ready")
    return {"access_token": flow.access_token, "refresh_token": flow.refresh_token}


def start_device_flow(provider: str) -> OAuthFlowState:
    if provider == "openai-codex":
        return start_openai_device_flow()
    cfg = _DEVICE_PROVIDERS.get(provider)
    if not cfg:
        raise ValueError(f"unsupported_oauth_provider:{provider}")
    payload: dict[str, Any] = {"client_id": cfg["client_id"]}
    if cfg.get("scope"):
        payload["scope"] = cfg["scope"]
    response = _http_json(
        cfg["device_code_url"],
        payload,
        form=bool(cfg.get("form")),
        headers={"Accept": "application/json"},
    )
    if response.get("error"):
        raise ValueError(f"device_code_start_failed:{response['error']}")
    device_code = str(response.get("device_code") or "")
    user_code = str(response.get("user_code") or "")
    if not device_code or not user_code:
        raise ValueError("invalid_device_code_response")
    flow = OAuthFlowState(
        provider=provider,
        oauth_provider=provider,
        flow_type="device_code",
        method="device_code",
        device_code=device_code,
        user_code=user_code,
        verification_uri=str(response.get("verification_uri") or cfg.get("verification_uri") or ""),
        verification_uri_complete=str(response.get("verification_uri_complete") or ""),
        expires_at=time.time() + int(response.get("expires_in") or 900),
        interval_seconds=max(1, int(response.get("interval") or _DEVICE_POLL_INTERVAL_SECONDS)),
    )
    _FLOWS[provider] = flow
    return flow


def poll_device_flow(provider: str) -> OAuthFlowState:
    flow = _FLOWS.get(provider)
    if not flow:
        raise ValueError("no_active_flow")
    if flow.provider == "openai-codex":
        return poll_openai_device_flow(flow)
    if flow.status in ("approved", "expired", "failed"):
        return flow
    if time.time() > flow.expires_at or flow.poll_count >= _DEVICE_MAX_POLLS:
        flow.status = "expired"
        return flow
    flow.poll_count += 1
    cfg = _DEVICE_PROVIDERS.get(provider, {})
    payload: dict[str, Any] = {
        "client_id": cfg.get("client_id", ""),
        "device_code": flow.device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    response = _http_json(cfg.get("token_url", ""), payload, form=bool(cfg.get("form")))
    if response.get("access_token"):
        return _complete_flow(flow, response)
    error = str(response.get("error") or "")
    if error in {"authorization_pending", "deviceauth_authorization_pending", "http_403", "http_404"}:
        return flow
    if error == "slow_down":
        flow.interval_seconds = min(flow.interval_seconds + 5, 60)
        return flow
    if error in {"access_denied", "authorization_denied"}:
        flow.status = "failed"
        flow.error = "access_denied"
        return flow
    if error in {"expired_token", "invalid_grant"}:
        flow.status = "expired"
        return flow
    flow.status = "failed"
    flow.error = error or "device_poll_failed"
    return flow


def start_pkce_flow(redirect_uri: str = "http://localhost:8090/callback") -> OAuthFlowState:
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": _OPENROUTER_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": "openai",
        "state": state,
    }
    flow = OAuthFlowState(
        provider="openrouter",
        oauth_provider="openrouter",
        flow_type="pkce",
        method="browser",
        code_verifier=verifier,
        state=state,
        redirect_uri=redirect_uri,
        auth_url=f"https://openrouter.ai/api/v1/auth/device?{urllib.parse.urlencode(params)}",
        expires_at=time.time() + 1800,
    )
    _FLOWS["openrouter"] = flow
    return flow


def start_anthropic_browser_flow(callback_url: str) -> OAuthFlowState:
    verifier, challenge = _pkce_pair()
    # Pi's Anthropic loader uses the verifier itself as the OAuth state.
    state = verifier
    params = {
        "code": "true",
        "client_id": _ANTHROPIC_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": callback_url,
        "scope": _ANTHROPIC_SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    flow = OAuthFlowState(
        provider="anthropic",
        oauth_provider="anthropic",
        flow_type="pkce",
        method="browser",
        code_verifier=verifier,
        state=state,
        redirect_uri=callback_url,
        auth_url=f"{_ANTHROPIC_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}",
        expires_at=time.time() + 1800,
    )
    _FLOWS["anthropic"] = flow
    return flow


def finish_anthropic_browser_flow(code: str, state: str) -> OAuthFlowState:
    flow = _FLOWS.get("anthropic")
    if not flow or flow.method != "browser":
        raise ValueError("no_active_anthropic_browser_flow")
    if not state or not secrets.compare_digest(state, flow.state):
        flow.status = "failed"
        flow.error = "oauth_state_mismatch"
        raise ValueError("oauth_state_mismatch")
    response = _http_json(
        _ANTHROPIC_TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": _ANTHROPIC_CLIENT_ID,
            "code": code,
            "state": state,
            "redirect_uri": flow.redirect_uri,
            "code_verifier": flow.code_verifier,
        },
    )
    if response.get("error"):
        flow.status = "failed"
        flow.error = "anthropic_token_exchange_failed"
        raise ValueError("anthropic_token_exchange_failed")
    return _complete_flow(flow, response)


def finish_pkce_flow(code: str, state: str | None = None) -> OAuthFlowState:
    flow = _FLOWS.get("openrouter")
    if not flow:
        raise ValueError("no_active_flow")
    if state and flow.state and not secrets.compare_digest(state, flow.state):
        raise ValueError("oauth_state_mismatch")
    response = _http_json(
        "https://openrouter.ai/api/v1/auth/keys",
        {
            "code": code,
            "code_verifier": flow.code_verifier,
            "client_id": _OPENROUTER_CLIENT_ID,
            "redirect_uri": flow.redirect_uri,
        },
    )
    token = str(response.get("key") or response.get("api_key") or "")
    if not token:
        flow.status = "failed"
        flow.error = "pkce_exchange_failed"
        raise ValueError("pkce_exchange_failed")
    return _complete_flow(flow, {"access_token": token})


def finish_browser_flow(provider: str, code: str, state: str) -> OAuthFlowState:
    if provider == "openai-codex":
        return finish_openai_browser_flow(code, state)
    if provider == "anthropic":
        return finish_anthropic_browser_flow(code, state)
    if provider == "openrouter":
        return finish_pkce_flow(code, state)
    raise ValueError("unsupported_browser_oauth_provider")


def complete_browser_flow(provider: str, authorization_input: str) -> OAuthFlowState:
    code, state = _parse_authorization_input(authorization_input)
    flow = _FLOWS.get(provider)
    if not flow or flow.method != "browser":
        raise ValueError("no_active_browser_flow")
    return finish_browser_flow(provider, code, state or flow.state)


def oauth_status(provider: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prov, flow in _FLOWS.items():
        if provider and prov != provider:
            continue
        out.append(
            {
                "provider": prov,
                "flow_type": flow.flow_type,
                "method": flow.method,
                "oauth_provider": flow.oauth_provider or flow.provider,
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


def browser_callback_page(success: bool, message: str) -> str:
    safe = html.escape(message)
    tone = "#166534" if success else "#b91c1c"
    return f"""<!doctype html><meta charset='utf-8'><title>Istara sign-in</title>
<body style='font:16px system-ui;max-width:36rem;margin:15vh auto;padding:2rem;color:{tone}'>
<h1>{'Authentication complete' if success else 'Authentication failed'}</h1><p>{safe}</p>
<p>You can close this window and return to Istara.</p></body>"""


def cancel_flow(provider: str) -> None:
    _FLOWS.pop(provider, None)


def cleanup_expired() -> None:
    now = time.time()
    for provider in list(_FLOWS):
        flow = _FLOWS[provider]
        if flow.status in ("approved", "expired", "failed") or now > flow.expires_at + 3600:
            _FLOWS.pop(provider, None)
