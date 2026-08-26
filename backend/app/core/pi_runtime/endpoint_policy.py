"""Shared policy for Pi endpoint creation and sparse updates.

POST and PUT are one authority boundary: catalog-derived transport fields,
endpoint validation, and credential custody must not drift between them.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException

from app.config import PiApiEndpoint

logger = logging.getLogger(__name__)


def _apply_catalog_fields(payload: dict[str, Any]) -> None:
    provider = str(payload.get("pi_provider") or "").strip().lower()
    model_id = str(payload.get("pi_model") or "").strip()
    if not provider or not model_id:
        return

    from app.core.pi_runtime.catalog import load_catalog

    provider_models = load_catalog().get(provider)
    if not provider_models:
        raise HTTPException(status_code=400, detail=f"unknown pi provider: {provider}")
    match = next((model for model in provider_models if model["id"] == model_id), None)
    if not match:
        raise HTTPException(status_code=400, detail=f"unknown pi model: {model_id}")

    api = str(match.get("api", "")).lower()
    payload["provider_kind"] = (
        "openai_codex"
        if api == "openai-codex-responses"
        else "anthropic_compat" if "anthropic" in api else "openai_compat"
    )
    payload["base_url"] = match.get("baseUrl") or payload.get("base_url")
    payload["model"] = match["id"]
    payload["context_window"] = int(match.get("contextWindow") or 0)
    payload["max_tokens"] = int(match.get("maxTokens") or 0)
    cost = match.get("cost") or {}
    payload["cost_input_per_mtok"] = float(cost.get("input") or 0.0)
    payload["cost_output_per_mtok"] = float(cost.get("output") or 0.0)
    payload["cost_cache_read_per_mtok"] = float(cost.get("cacheRead") or 0.0)
    payload["cost_cache_write_per_mtok"] = float(cost.get("cacheWrite") or 0.0)
    payload["pi_provider"] = provider
    payload["auth_provider"] = str(payload.get("auth_provider") or provider).strip()
    payload["auth_method"] = str(payload.get("auth_method") or "api_key").strip()
    if not str(payload.get("keychain_service") or "").strip():
        payload["keychain_service"] = (
            f"istara-pi-oauth-{payload['auth_provider']}"
            if payload["auth_method"].startswith("oauth")
            else f"istara-pi-{provider}"
        )


def _validate_endpoint_fields(payload: dict[str, Any]) -> None:
    payload["base_url"] = str(payload.get("base_url") or "").strip()
    payload["model"] = str(payload.get("model") or "").strip()
    payload["keychain_service"] = str(payload.get("keychain_service") or "").strip()
    if not payload["base_url"] or not payload["model"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "base_url and model are required — select a Pi provider+model "
                "from the catalog or provide them explicitly"
            ),
        )
    if not payload["base_url"].startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise HTTPException(status_code=400, detail="base_url must be https (or loopback)")
    if not payload["keychain_service"]:
        raise HTTPException(
            status_code=400,
            detail="keychain_service is required (Pi endpoints resolve secrets via Keychain)",
        )


def prepare_pi_endpoint_payload(data: Any, existing: PiApiEndpoint | None = None) -> dict[str, Any]:
    """Resolve catalog fields and validate a POST or sparse PUT payload."""
    payload = data.model_dump()
    if existing is not None:
        provided_fields = set(getattr(data, "model_fields_set", set()))
        for field, value in existing.model_dump().items():
            if field not in provided_fields:
                payload[field] = value
        payload["endpoint_id"] = existing.endpoint_id
    _apply_catalog_fields(payload)
    _validate_endpoint_fields(payload)
    return payload


def _custody_api_key(data: Any, payload: dict[str, Any]) -> None:
    api_key = str(data.api_key or "").strip()
    if not api_key:
        return
    try:
        from app.config import _write_macos_keychain_secret

        _write_macos_keychain_secret(
            payload["keychain_service"],
            payload.get("keychain_account") or "default",
            api_key,
        )
    except Exception as exc:  # pragma: no cover - custody failure is non-fatal to config
        logger.warning(
            "pi endpoint: keychain write failed for %s: %s",
            payload.get("endpoint_id", "<unknown>"),
            exc,
        )


def _custody_oauth(data: Any, payload: dict[str, Any], existing: PiApiEndpoint | None) -> None:
    from app.core.field_encryption import encrypt_field
    from app.core.pi_runtime.oauth import consume_oauth_credential

    flow_id = str(data.oauth_flow_id or "").strip()
    if not flow_id:
        if existing is not None and payload.get("oauth_credential_encrypted"):
            return
        raise HTTPException(status_code=400, detail="oauth_flow_id is required after Pi login")
    try:
        credential = consume_oauth_credential(
            str(payload.get("auth_provider") or payload.get("pi_provider") or ""),
            flow_id,
        )
        payload["oauth_credential_encrypted"] = encrypt_field(
            json.dumps(credential, separators=(",", ":"))
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - provider custody guard
        raise HTTPException(status_code=503, detail="oauth_credential_custody_failed") from exc


def custody_pi_endpoint_credentials(
    data: Any, payload: dict[str, Any], existing: PiApiEndpoint | None = None
) -> None:
    """Custody a new credential and preserve an existing OAuth credential."""
    auth_method = str(payload.get("auth_method") or "api_key").strip().lower()
    if auth_method.startswith("oauth"):
        _custody_oauth(data, payload, existing)
    else:
        _custody_api_key(data, payload)
        payload.pop("oauth_credential_encrypted", None)
