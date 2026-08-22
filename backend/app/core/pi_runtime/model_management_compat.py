"""Bounded, reversible compatibility planning for legacy LLM servers.

This module deliberately plans a projection; it does not delete or rewrite
``LLMServer`` rows.  That makes dry-runs, retries, and rollback deterministic
and keeps credentials out of migration evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable
from urllib.parse import urlparse

# Providers the Pi catalog projection accepts. This set MUST stay in lockstep
# with PiModelManager._project_llm_server (model_manager.py) — the manager
# imports this constant, and a test asserts plan state == catalog projection
# outcome for every provider. vllm/sglang/llamacpp/mlx are OpenAI-compatible
# server types (model_capabilities.OPENAI_COMPATIBLE_PROVIDER_TYPES, also the
# provider vocabulary of the legacy LLM-server API); anthropic_compat projects
# through the Anthropic-compatible provider kind.
SUPPORTED_PROVIDERS = frozenset({
    "ollama",
    "lmstudio",
    "openai_compat",
    "anthropic",
    "anthropic_compat",
    "vllm",
    "sglang",
    "llamacpp",
    "mlx",
})


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
        for key in ("id", "name", "provider_type", "host", "is_local", "is_relay", "priority", "capabilities")
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def classify_server(row: Any) -> CompatibilityMapping:
    source_id = str(getattr(row, "id", "") or "")
    checksum = _checksum(row)
    if not source_id:
        return CompatibilityMapping("", None, "blocked", "missing_source_id", checksum)
    if bool(getattr(row, "is_relay", False)):
        return CompatibilityMapping(source_id, None, "legacy_only", "relay_not_pi_catalog", checksum)
    provider = str(getattr(row, "provider_type", "") or "").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        return CompatibilityMapping(source_id, None, "blocked", "unsupported_provider", checksum)
    host = str(getattr(row, "host", "") or "").strip()
    parsed = urlparse(host if "://" in host else f"http://{host}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return CompatibilityMapping(source_id, None, "blocked", "invalid_host", checksum)
    return CompatibilityMapping(source_id, f"pi-llm-{source_id}", "projected", None, checksum)


def plan_migration(rows: Iterable[Any]) -> dict[str, Any]:
    """Return an idempotent, secret-free migration plan and audit summary."""
    mappings = [classify_server(row) for row in rows]
    counts = {state: sum(mapping.state == state for mapping in mappings) for state in ("projected", "legacy_only", "blocked")}
    return {
        "mode": "dry_run",
        "canonical_resolver": "PiModelManager",
        "delete_source_rows": False,
        "mappings": [asdict(mapping) for mapping in mappings],
        "counts": counts,
        "rollback": {"available": True, "source_rows_retained": True, "checksums": [m.source_checksum for m in mappings]},
        "removal_criteria": ["all rows projected or explicitly legacy_only", "zero blocked rows", "rollback drill recorded"],
    }
