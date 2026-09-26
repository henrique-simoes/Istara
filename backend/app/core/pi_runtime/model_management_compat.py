"""Bounded, reversible compatibility planning for legacy LLM servers.

This module deliberately plans a projection; it does not delete or rewrite
``LLMServer`` rows.  That makes dry-runs, retries, and rollback deterministic
and keeps credentials out of migration evidence.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from app.config import settings

# Providers the Pi catalog projection accepts. This set MUST stay in lockstep
# with PiModelManager._project_llm_server (model_manager.py) — the manager
# imports this constant, and a test asserts plan state == catalog projection
# outcome for every provider. vllm/sglang/llamacpp/mlx are OpenAI-compatible
# server types (model_capabilities.OPENAI_COMPATIBLE_PROVIDER_TYPES, also the
# provider vocabulary of the legacy LLM-server API); anthropic_compat projects
# through the Anthropic-compatible provider kind.
SUPPORTED_PROVIDERS = frozenset(
    {
        "ollama",
        "lmstudio",
        "openai_compat",
        "anthropic",
        "anthropic_compat",
        "vllm",
        "sglang",
        "llamacpp",
        "mlx",
    }
)


@dataclass(frozen=True)
class CompatibilityMapping:
    source_id: str
    canonical_endpoint_id: str | None
    state: str  # projected | legacy_only | blocked
    reason: str | None
    source_checksum: str


def _checksum(row: Any) -> str:
    """Hash non-secret source identity/configuration for recovery evidence."""
    payload = {
        key: getattr(row, key, None)
        for key in (
            "id",
            "name",
            "provider_type",
            "host",
            "is_local",
            "is_relay",
            "priority",
            "capabilities",
        )
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def host_is_plannable(host: str) -> bool:
    """Whether a legacy server host may be projected into the Pi catalog.

    Mirrors the platform's endpoint policy for user-configured service URLs
    (``EndpointPolicy.allow_userinfo=False``, ``allow_query=False``) and
    tightens it one step further: the scheme must be written out explicitly.
    ``PiModelManager._project_llm_server`` uses the stored host verbatim as
    the catalog ``base_url``, so a schemeless host would project a URL that is
    dead on arrival (httpx raises ``UnsupportedProtocol``) while the plan's
    removal criteria would still bless the row for deletion — the same
    silent-config-loss class as unsupported providers. The plan classifier and
    the catalog projection both call this helper so their outcomes stay
    identical.
    """
    value = (host or "").strip()
    if "://" not in value:
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
        and not (parsed.username or parsed.password)
        and not parsed.query
    )


def classify_server(row: Any) -> CompatibilityMapping:
    source_id = str(getattr(row, "id", "") or "")
    checksum = _checksum(row)
    if not source_id:
        return CompatibilityMapping("", None, "blocked", "missing_source_id", checksum)
    if bool(getattr(row, "is_relay", False)):
        return CompatibilityMapping(
            source_id, None, "legacy_only", "relay_not_pi_catalog", checksum
        )
    provider = str(getattr(row, "provider_type", "") or "").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        return CompatibilityMapping(source_id, None, "blocked", "unsupported_provider", checksum)
    host = str(getattr(row, "host", "") or "").strip()
    if not host_is_plannable(host):
        return CompatibilityMapping(source_id, None, "blocked", "invalid_host", checksum)
    return CompatibilityMapping(source_id, f"pi-llm-{source_id}", "projected", None, checksum)


def plan_migration(rows: Iterable[Any]) -> dict[str, Any]:
    """Return an idempotent, secret-free migration plan and audit summary."""
    mappings = [classify_server(row) for row in rows]
    counts = {
        state: sum(mapping.state == state for mapping in mappings)
        for state in ("projected", "legacy_only", "blocked")
    }
    return {
        "mode": "dry_run",
        "canonical_resolver": "PiModelManager",
        "delete_source_rows": False,
        "mappings": [asdict(mapping) for mapping in mappings],
        "counts": counts,
        "rollback": {
            "available": True,
            "source_rows_retained": True,
            "checksums": [m.source_checksum for m in mappings],
        },
        "removal_criteria": [
            "all rows projected or explicitly legacy_only",
            "zero blocked rows",
            "rollback drill recorded",
        ],
    }


logger = logging.getLogger(__name__)

# LLMServer rows projected onto Pi catalog entries (base URL, key, models, capabilities).
LOCAL_SERVER_TYPES = {"ollama", "lmstudio"}


def server_capabilities(row: object) -> dict:
    """An LLMServer row's capabilities JSON, or {} when it is missing or not an object."""
    try:
        capabilities = json.loads(getattr(row, "capabilities", "") or "{}")
    except (TypeError, ValueError):
        return {}
    return capabilities if isinstance(capabilities, dict) else {}


def server_base_url(provider_type: str, row: object) -> str | None:
    """The row's OpenAI-style base URL, or None when its host cannot be planned."""
    host = (getattr(row, "host", "") or "").rstrip("/")
    if not host_is_plannable(host):
        return None
    if provider_type in LOCAL_SERVER_TYPES and not host.endswith("/v1"):
        return f"{host}/v1"
    return host


def server_api_key(provider_type: str, row: object) -> str | None:
    """The row's key (decrypted), a local server's placeholder, or None when decryption fails."""
    encrypted_key = getattr(row, "api_key", "") or ""
    if encrypted_key:
        try:
            from app.core.field_encryption import decrypt_field

            return decrypt_field(encrypted_key)
        except Exception:
            logger.debug(
                "pi model manager: LLMServer key projection failed for %s",
                getattr(row, "id", "?"),
            )
            return None
    if provider_type == "ollama":
        return "ollama"
    if provider_type == "lmstudio":
        return settings.lmstudio_api_key or "lm-studio"
    return ""


def server_model(provider_type: str, row: object, capabilities: dict) -> str:
    """The row's first advertised model, else the provider's configured default."""
    models = capabilities.get("models")
    if isinstance(models, list) and models and models[0]:
        return models[0]
    if provider_type == "ollama":
        return settings.ollama_model
    if provider_type == "lmstudio":
        return settings.lmstudio_model
    return getattr(row, "name", "") or "default"


def server_embedding_model(provider_type: str) -> str:
    """The provider's configured embedding model for an LLMServer row."""
    if provider_type == "lmstudio":
        return settings.lmstudio_embed_model
    if provider_type == "ollama":
        return settings.ollama_embed_model
    return ""


def llm_server_row_fields(provider_type: str, row: object) -> dict | None:
    """Catalog fields for an LLMServer row, or None for an unsupported type or an unservable row."""
    if provider_type not in SUPPORTED_PROVIDERS:
        return None
    host = server_base_url(provider_type, row)
    api_key = server_api_key(provider_type, row) if host is not None else None
    if host is None or api_key is None:
        return None
    capabilities = server_capabilities(row)
    return {
        "base_url": host,
        "api_key": api_key,
        "capabilities": capabilities,
        "is_local": bool(getattr(row, "is_local", False)) or provider_type in LOCAL_SERVER_TYPES,
        "model": server_model(provider_type, row, capabilities),
        "embedding_model": server_embedding_model(provider_type),
    }
