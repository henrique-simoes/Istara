"""Pi-only endpoint catalog and exact/capability based selection.

This module intentionally has no ComputeRegistry imports.  Pi traffic is
identity-pinned and must never become schedulable donated compute; selection is
exact-identity or capability-filtered over the catalog — never donor-style
capacity scoring.

Catalog sources (master plan §5.2), all projected to exact-identity entries:

1. Static settings endpoints — ``settings.pi_api_endpoints`` plus the built-in
   ``pi-deepseek-default`` (secret materialization stays with the resolver).
2. Persisted ``LLMServer`` rows — projected read-only at refresh time as
   ``pi-llm-<id>`` entries; relay/browser donor rows are NEVER projected.
3. Local serving — Ollama / LM Studio OpenAI-compatible ``/v1`` endpoints from
   settings hosts, marked ``kind="local"``.
"""

from __future__ import annotations

import json
import logging
import weakref
from dataclasses import dataclass
from typing import Iterable

from app.config import PiApiEndpoint, settings

from .endpoints import (
    DEFAULT_ENDPOINT_ID,
    PiEndpointResolutionError,
    PiEndpointResolver,
    ResolvedPiEndpoint,
)

logger = logging.getLogger(__name__)

# Live managers, so LLMServer CRUD / network discovery can invalidate the
# DB projection on every in-process manager (W8 UX parity) without changing
# how managers are constructed or shared.
_LIVE_MANAGERS: "weakref.WeakSet[PiModelManager]" = weakref.WeakSet()


@dataclass(frozen=True)
class PiEndpointInfo:
    endpoint_id: str
    model: str
    provider_kind: str
    context_window: int = 0
    max_tokens: int = 0
    supports_tools: bool = True
    supports_vision: bool = False
    kind: str = "remote"


@dataclass(frozen=True)
class _CatalogEntry:
    """One exact-identity catalog row from any source."""

    endpoint_id: str
    provider_kind: str
    base_url: str
    model: str
    source: str  # "settings" | "local" | "llm_server"
    embedding_model: str = ""
    api_key: str = ""
    timeout_ms: int = 30_000
    max_retries: int = 0
    cost_input_per_mtok: float = 0.0
    cost_output_per_mtok: float = 0.0
    cost_cache_read_per_mtok: float = 0.0
    cost_cache_write_per_mtok: float = 0.0
    context_window: int = 0
    max_tokens: int = 0
    supports_tools: bool = True
    supports_vision: bool = False
    kind: str = "remote"
    # Settings-source entries keep their secrets in the resolver/Keychain.
    resolved: ResolvedPiEndpoint | None = None


class PiModelManager:
    """Select from the Pi catalog, never by donor capacity/scoring."""

    def __init__(self, resolver: PiEndpointResolver | None = None,
                 endpoints: Iterable[ResolvedPiEndpoint] | None = None,
                 *, include_local: bool = True) -> None:
        self._resolver = resolver or PiEndpointResolver()
        if endpoints is None:
            # Duck-typed resolvers (test doubles) may not expose configured();
            # they stay resolvable by id through resolver.resolve.
            configured = getattr(self._resolver, "configured", None)
            entries = [self._from_settings(endpoint) for endpoint in configured()] if callable(configured) else []
            if include_local:
                entries.extend(self._local_entries())
        else:
            # Explicit catalog (tests/benchmarks): use exactly these endpoints.
            entries = [self._coerce(endpoint) for endpoint in endpoints]
        self._entries = {entry.endpoint_id: entry for entry in entries}
        self._db_projected = False
        _LIVE_MANAGERS.add(self)

    # ── catalog sources ──────────────────────────────────────────────────
    @staticmethod
    def _from_settings(endpoint: PiApiEndpoint) -> _CatalogEntry:
        return _CatalogEntry(
            endpoint_id=endpoint.endpoint_id,
            provider_kind=endpoint.provider_kind,
            base_url=endpoint.base_url.rstrip("/"),
            model=endpoint.model,
            source="settings",
            timeout_ms=endpoint.timeout_ms,
            max_retries=endpoint.max_retries,
            cost_input_per_mtok=endpoint.cost_input_per_mtok,
            cost_output_per_mtok=endpoint.cost_output_per_mtok,
            cost_cache_read_per_mtok=endpoint.cost_cache_read_per_mtok,
            cost_cache_write_per_mtok=endpoint.cost_cache_write_per_mtok,
            context_window=endpoint.context_window,
            max_tokens=endpoint.max_tokens,
            supports_tools=endpoint.supports_tools,
            supports_vision=endpoint.supports_vision,
        )

    @staticmethod
    def _coerce(endpoint: ResolvedPiEndpoint) -> _CatalogEntry:
        return _CatalogEntry(
            endpoint_id=endpoint.endpoint_id,
            provider_kind=endpoint.provider_kind,
            base_url=endpoint.base_url,
            model=endpoint.model,
            embedding_model=endpoint.model,
            source="local" if endpoint.kind == "local" else "explicit",
            api_key=endpoint.api_key,
            timeout_ms=endpoint.timeout_ms,
            max_retries=endpoint.max_retries,
            cost_input_per_mtok=endpoint.cost_input_per_mtok,
            cost_output_per_mtok=endpoint.cost_output_per_mtok,
            cost_cache_read_per_mtok=endpoint.cost_cache_read_per_mtok,
            cost_cache_write_per_mtok=endpoint.cost_cache_write_per_mtok,
            context_window=endpoint.context_window,
            max_tokens=endpoint.max_tokens,
            supports_tools=endpoint.supports_tools,
            supports_vision=endpoint.supports_vision,
            kind=endpoint.kind,
            resolved=endpoint,
        )

    @staticmethod
    def _local_entries() -> list[_CatalogEntry]:
        """Local serving as OpenAI-compatible /v1 endpoints (kind=local)."""
        return [
            _CatalogEntry(
                endpoint_id="pi-local-ollama",
                provider_kind="openai_compat",
                base_url=settings.ollama_host.rstrip("/") + "/v1",
                model=settings.ollama_model,
                embedding_model=settings.ollama_embed_model,
                source="local",
                api_key="ollama",
                kind="local",
            ),
            _CatalogEntry(
                endpoint_id="pi-local-lmstudio",
                provider_kind="openai_compat",
                base_url=settings.lmstudio_host.rstrip("/") + "/v1",
                model=settings.lmstudio_model,
                embedding_model=settings.lmstudio_embed_model,
                source="local",
                api_key=settings.lmstudio_api_key or "lm-studio",
                kind="local",
            ),
        ]

    async def ensure_db_projection(self) -> None:
        """Project persisted LLMServer rows into the catalog (read-only, once).

        One-directional (DB row -> Pi catalog entry); nothing Pi-side writes
        back or registers into the live registry. Projection/storage failures
        leave the static catalog authoritative; resolving a missing projected
        endpoint then fails closed as ``unknown_pi_endpoint``.
        """
        if self._db_projected:
            return
        self._db_projected = True
        try:
            from sqlalchemy import select

            from app.models.database import async_session
            from app.models.llm_server import LLMServer

            async with async_session() as db:
                rows = list((await db.execute(select(LLMServer))).scalars().all())
        except Exception:  # pragma: no cover - storage unavailable
            logger.debug("pi model manager: LLMServer projection skipped (storage unavailable)")
            return
        for row in rows:
            entry = self._project_llm_server(row)
            if entry is not None:
                self._entries.setdefault(entry.endpoint_id, entry)

    @staticmethod
    def _project_llm_server(row: object) -> _CatalogEntry | None:
        # Relay/browser donors are never Pi endpoints (isolation invariant).
        if getattr(row, "is_relay", False):
            return None
        provider_type = (getattr(row, "provider_type", "") or "").strip().lower()
        if provider_type not in {"ollama", "lmstudio", "openai_compat", "anthropic_compat", "anthropic"}:
            return None
        try:
            capabilities = json.loads(getattr(row, "capabilities", "") or "{}")
        except (TypeError, ValueError):
            capabilities = {}
        host = (getattr(row, "host", "") or "").rstrip("/")
        if not host:
            return None
        is_local = bool(getattr(row, "is_local", False)) or provider_type in {"ollama", "lmstudio"}
        if provider_type in {"ollama", "lmstudio"} and not host.endswith("/v1"):
            host = f"{host}/v1"
        provider_kind = "anthropic_compat" if provider_type.startswith("anthropic") else "openai_compat"
        encrypted_key = getattr(row, "api_key", "") or ""
        api_key = ""
        if encrypted_key:
            try:
                from app.core.field_encryption import decrypt_field

                api_key = decrypt_field(encrypted_key)
            except Exception:
                logger.debug("pi model manager: LLMServer key projection failed for %s", getattr(row, "id", "?"))
                return None
        elif provider_type == "ollama":
            api_key = "ollama"
        elif provider_type == "lmstudio":
            api_key = settings.lmstudio_api_key or "lm-studio"
        models = capabilities.get("models") if isinstance(capabilities, dict) else None
        model = (models[0] if isinstance(models, list) and models else "") or (
            settings.ollama_model if provider_type == "ollama"
            else settings.lmstudio_model if provider_type == "lmstudio"
            else (getattr(row, "name", "") or "default")
        )
        return _CatalogEntry(
            endpoint_id=f"pi-llm-{getattr(row, 'id', '')}",
            provider_kind=provider_kind,
            base_url=host,
            model=model,
            embedding_model=(
                settings.lmstudio_embed_model
                if provider_type == "lmstudio"
                else settings.ollama_embed_model
                if provider_type == "ollama"
                else ""
            ),
            source="llm_server",
            api_key=api_key,
            context_window=int(capabilities.get("context_window", 0) or 0) if isinstance(capabilities, dict) else 0,
            supports_vision=bool(capabilities.get("vision", False)) if isinstance(capabilities, dict) else False,
            kind="local" if is_local else "remote",
        )

    def reset_db_projection(self) -> None:
        """Drop projected LLMServer rows so the next projection re-reads the DB.

        Called when the legacy model-management plane mutates ``LLMServer``
        rows (CRUD or network discovery, W8 UX parity): the static settings /
        local catalog is authoritative and untouched, only ``llm_server``-
        sourced entries are invalidated. The projection stays one-directional
        and lazy — it re-materializes on the next ``ensure_db_projection``.
        """
        self._db_projected = False
        stale = [key for key, entry in self._entries.items() if entry.source == "llm_server"]
        for key in stale:
            del self._entries[key]

    # ── selection (exact identity or capability-filtered, never scored) ──
    @staticmethod
    def _matches(entry: _CatalogEntry, *, model: str | None, require_vision: bool, min_context: int) -> bool:
        if model is not None and entry.model != model:
            return False
        if require_vision and not entry.supports_vision:
            return False
        if min_context > 0 and entry.context_window < min_context:
            return False
        return True

    @staticmethod
    def _admit(model: str | None, require_vision: bool, min_context: int,
               *, entry_model: str, supports_vision: bool, context_window: int) -> None:
        if model is not None and entry_model != model:
            raise PiEndpointResolutionError("pi_endpoint_model_mismatch")
        if require_vision and not supports_vision:
            raise PiEndpointResolutionError("pi_endpoint_capability_missing:vision")
        if min_context > 0 and context_window < min_context:
            raise PiEndpointResolutionError("pi_endpoint_capability_missing:context")

    def _materialize(self, entry: _CatalogEntry) -> ResolvedPiEndpoint:
        if entry.resolved is not None:
            return entry.resolved
        if entry.source == "settings":
            # Secret materialization stays with the resolver (Keychain/env, TTL-cached).
            return self._resolver.resolve(entry.endpoint_id, model=entry.model)
        return ResolvedPiEndpoint(
            endpoint_id=entry.endpoint_id,
            provider_kind=entry.provider_kind,
            base_url=entry.base_url,
            model=entry.model,
            api_key=entry.api_key,
            timeout_ms=entry.timeout_ms,
            max_retries=entry.max_retries,
            cost_input_per_mtok=entry.cost_input_per_mtok,
            cost_output_per_mtok=entry.cost_output_per_mtok,
            cost_cache_read_per_mtok=entry.cost_cache_read_per_mtok,
            cost_cache_write_per_mtok=entry.cost_cache_write_per_mtok,
            context_window=entry.context_window,
            max_tokens=entry.max_tokens,
            supports_tools=entry.supports_tools,
            supports_vision=entry.supports_vision,
            kind=entry.kind,
        )

    def resolve(self, *, endpoint_id: str | None = None, model: str | None = None,
                require_vision: bool = False, min_context: int = 0) -> ResolvedPiEndpoint:
        if endpoint_id:
            entry = self._entries.get(endpoint_id)
            if entry is None:
                # Settings-configured endpoints remain exactly resolvable.
                endpoint = self._resolver.resolve(endpoint_id, model=model)
                self._admit(None, require_vision, min_context, entry_model=endpoint.model,
                            supports_vision=endpoint.supports_vision, context_window=endpoint.context_window)
                return endpoint
            self._admit(model, require_vision, min_context, entry_model=entry.model,
                        supports_vision=entry.supports_vision, context_window=entry.context_window)
            return self._materialize(entry)
        candidates = [
            entry for entry in self._entries.values()
            if self._matches(entry, model=model, require_vision=require_vision, min_context=min_context)
        ]
        if candidates:
            return self._materialize(candidates[0])
        if not self._entries:
            # Explicitly empty catalogs retain the resolver as the source of truth.
            endpoint = self._resolver.resolve(DEFAULT_ENDPOINT_ID, model=model)
            self._admit(None, require_vision, min_context, entry_model=endpoint.model,
                        supports_vision=endpoint.supports_vision, context_window=endpoint.context_window)
            return endpoint
        raise PiEndpointResolutionError("no_matching_pi_endpoint")

    def resolve_distinct(self, n: int, *, model: str | None = None, exclude: Iterable[str] = (),
                         require_vision: bool = False, min_context: int = 0) -> list[ResolvedPiEndpoint]:
        """N endpoints with distinct identity; fail-closed if fewer than n exist."""
        excluded = set(exclude)
        matches = [
            entry for entry in self._entries.values()
            if entry.endpoint_id not in excluded
            and self._matches(entry, model=model, require_vision=require_vision, min_context=min_context)
        ]
        if len(matches) < n:
            raise PiEndpointResolutionError("insufficient_distinct_pi_endpoints")
        return [self._materialize(entry) for entry in matches[:n]]

    @staticmethod
    def _active_embed_model(provider: str | None = None) -> str:
        active_provider = (provider or settings.llm_provider or "").strip().lower()
        if active_provider == "lmstudio":
            return settings.lmstudio_embed_model
        return settings.ollama_embed_model

    @staticmethod
    def _embedding_model(entry: _CatalogEntry) -> str:
        """Return the model used for this entry's embedding request."""
        if entry.endpoint_id == "pi-local-ollama":
            return settings.ollama_embed_model
        if entry.endpoint_id == "pi-local-lmstudio":
            return settings.lmstudio_embed_model
        if entry.embedding_model:
            return entry.embedding_model
        return entry.model

    @staticmethod
    def _is_active_local(entry: _CatalogEntry, provider: str) -> bool:
        if entry.kind != "local":
            return False
        active_provider = provider.strip().lower()
        if active_provider == "lmstudio":
            return entry.endpoint_id == "pi-local-lmstudio" or (
                entry.base_url.rstrip("/").removesuffix("/v1")
                == settings.lmstudio_host.rstrip("/").removesuffix("/v1")
            )
        return entry.endpoint_id == "pi-local-ollama" or (
            entry.base_url.rstrip("/").removesuffix("/v1")
            == settings.ollama_host.rstrip("/").removesuffix("/v1")
        )

    def resolve_embed(
        self, model: str | None = None, *, provider: str | None = None
    ) -> ResolvedPiEndpoint:
        """Resolve the identity-pinned endpoint for one embedding model.

        Only OpenAI-compatible entries qualify. A concrete requested model is
        an exact capability requirement, so a configured remote endpoint with
        that model beats unrelated local entries. When the model is omitted or
        ``default``, the active local provider anchors the vector space.
        """
        candidates = [
            entry for entry in self._entries.values()
            if entry.provider_kind == "openai_compat"
        ]
        if not candidates:
            raise PiEndpointResolutionError("no_matching_pi_embed_endpoint")
        active_provider = (provider or settings.llm_provider or "ollama").strip().lower()
        requested_model = (model or self._active_embed_model(active_provider) or "").strip()

        if requested_model and requested_model != "default":
            exact = [
                entry for entry in candidates
                if self._embedding_model(entry) == requested_model
            ]
            if exact:
                active_local = [
                    entry for entry in exact
                    if self._is_active_local(entry, active_provider)
                ]
                return self._materialize((active_local or exact)[0])
            raise PiEndpointResolutionError("no_matching_pi_embed_endpoint_model")

        active_local = [
            entry for entry in candidates
            if self._is_active_local(entry, active_provider)
        ]
        if active_local:
            return self._materialize(active_local[0])
        default_model = [
            entry for entry in candidates
            if self._embedding_model(entry) == "default"
        ]
        if default_model:
            return self._materialize(default_model[0])
        if len(candidates) == 1:
            # ``default`` is intentionally provider-neutral. An explicit
            # single endpoint is therefore the only safe identity to use.
            return self._materialize(candidates[0])
        raise PiEndpointResolutionError("no_matching_pi_embed_endpoint")

    def catalog(self) -> list[PiEndpointInfo]:
        """Identity/capability view for the settings UI and benchmarks."""
        return [
            PiEndpointInfo(
                entry.endpoint_id, entry.model, entry.provider_kind,
                context_window=entry.context_window, max_tokens=entry.max_tokens,
                supports_tools=entry.supports_tools, supports_vision=entry.supports_vision,
                kind=entry.kind,
            )
            for entry in self._entries.values()
        ]


def reset_live_db_projections() -> None:
    """Invalidate the LLMServer projection on every live manager (W8).

    Called by the legacy model-management plane (``llm_servers`` CRUD,
    network discovery) after it commits row changes, so the next Pi-side
    resolution re-projects the updated rows. Never raises: projection
    invalidation must not break the legacy plane that triggered it.
    """
    for manager in list(_LIVE_MANAGERS):
        try:
            manager.reset_db_projection()
        except Exception:  # pragma: no cover - defensive; never break the caller
            logger.debug("pi model manager: projection reset skipped for one manager")
