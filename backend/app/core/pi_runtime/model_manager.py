"""Pi-only endpoint catalog and exact/capability based selection.

This module intentionally has no ComputeRegistry imports.  Pi traffic is
identity-pinned and must never become schedulable donated compute; selection is
exact-identity or capability-filtered over the catalog — never donor-style
capacity scoring.

Catalog sources, all projected to exact-identity entries:

1. Static settings endpoints — ``settings.pi_api_endpoints`` plus the built-in
   ``pi-deepseek-default`` (secret materialization stays with the resolver).
2. Persisted ``LLMServer`` rows — projected read-only at refresh time as
   ``pi-llm-<id>`` entries; relay/browser donor rows are NEVER projected.
3. Local serving — Ollama / LM Studio OpenAI-compatible ``/v1`` endpoints from
   settings hosts, marked ``kind="local"``.
4. The sanctioned Petals bridge — healthy, explicitly consented, project-scoped
   relay/browser nodes projected by ``app.core.petals_bridge`` as identity-pinned
   loopback endpoints.  This module still never imports ``ComputeRegistry`` and
   never performs donor-capacity scoring.
"""

from __future__ import annotations

import json
import logging
import weakref
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256

from app.config import PiApiEndpoint, settings

from .endpoints import (
    DEFAULT_ENDPOINT_ID,
    PiEndpointResolutionError,
    PiEndpointResolver,
    ResolvedPiEndpoint,
)
from .model_management_compat import SUPPORTED_PROVIDERS, host_is_plannable

logger = logging.getLogger(__name__)

# Petals bridge identities are generated from donor node ids.  This namespace
# is reserved so a user-configured Pi endpoint cannot shadow a consented donor
# projection and make a request resolve to a different provider than its route
# identity claims.
PETALS_ENDPOINT_PREFIX = "pi-petals-"


def is_reserved_petals_endpoint_id(endpoint_id: str) -> bool:
    return str(endpoint_id or "").strip().startswith(PETALS_ENDPOINT_PREFIX)


def _is_petals_entry(entry: _CatalogEntry) -> bool:
    """Recognize both dynamic projections and explicit Petals test catalogs."""
    return entry.source == "petals" or entry.kind == "petals"


def _is_contract_stub_chat_entry(entry: _CatalogEntry) -> bool:
    """Return whether an entry is the deterministic QA plane, not a model.

    The contract provider is intentionally useful for startup/embedding wire
    checks, but it must never be admitted as a chat, ensemble, or Research
    Spine rater.  Keeping the predicate on the catalog entry lets embedding
    resolution continue to use the stub while every chat selection path shares
    the same fail-closed boundary.
    """
    return bool(settings.llm_provider_contract_stub and entry.kind == "local")


# Live managers, so LLMServer CRUD / network discovery can invalidate the
# DB projection on every in-process manager (W8 UX parity) without changing
# how managers are constructed or shared.
_LIVE_MANAGERS: weakref.WeakSet[PiModelManager] = weakref.WeakSet()


@dataclass(frozen=True)
class PiEndpointInfo:
    endpoint_id: str
    model: str
    provider_kind: str
    context_window: int = 0
    max_tokens: int = 0
    supports_tools: bool = True
    supports_vision: bool = False
    supports_reasoning: bool | None = None
    kind: str = "remote"
    pi_provider: str = ""
    auth_method: str = "api_key"


@dataclass(frozen=True)
class _CatalogEntry:
    """One exact-identity catalog row from any source."""

    endpoint_id: str
    provider_kind: str
    base_url: str
    model: str
    source: str  # "settings" | "local" | "llm_server" | "petals"
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
    supports_reasoning: bool | None = None
    kind: str = "remote"
    pi_provider: str = ""
    auth_method: str = "api_key"
    # Donated Petals identities are project-scoped by the registry.  Keep the
    # authorization projection alongside the catalog row so selection can
    # exclude an otherwise healthy donor before it consumes an ensemble slot.
    allowed_project_ids: tuple[str, ...] = ()
    # Settings-source entries keep their secrets in the resolver/Keychain.
    resolved: ResolvedPiEndpoint | None = None


class PiModelManager:
    """Select from the Pi catalog, never by donor capacity/scoring."""

    def __init__(
        self,
        resolver: PiEndpointResolver | None = None,
        endpoints: Iterable[ResolvedPiEndpoint] | None = None,
        *,
        include_local: bool = True,
    ) -> None:
        self._resolver = resolver or PiEndpointResolver()
        self._explicit_catalog = endpoints is not None
        self._include_local = include_local
        if endpoints is None:
            # Duck-typed resolvers (test doubles) may not expose configured();
            # they stay resolvable by id through resolver.resolve.
            configured = getattr(self._resolver, "configured", None)
            entries = (
                [self._from_settings(endpoint) for endpoint in configured()]
                if callable(configured)
                else []
            )
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
            pi_provider=getattr(endpoint, "auth_provider", "")
            or getattr(endpoint, "pi_provider", ""),
            auth_method=getattr(endpoint, "auth_method", "api_key"),
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
            supports_reasoning=endpoint.supports_reasoning,
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
            supports_reasoning=endpoint.supports_reasoning,
            kind=endpoint.kind,
            # ``ResolvedPiEndpoint`` is the already-admitted boundary used by
            # explicit test/faux catalogs and does not carry a donor allowlist.
            # Dynamic Petals projections below populate the real allowlist;
            # an explicit Petals endpoint is therefore treated as an
            # intentionally wildcard-admitted fixture rather than as a
            # restricted donor with an accidentally empty scope.
            allowed_project_ids=("*",) if endpoint.kind == "petals" else (),
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
            self._refresh_petals_projection()
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
            rows = []
        for row in (row for row in rows if getattr(row, "is_healthy", None) is not False):
            entry = self._project_llm_server(row)
            if entry is not None:
                self._entries.setdefault(entry.endpoint_id, entry)
        self._refresh_petals_projection()

    def _refresh_petals_projection(self) -> None:
        """Replace dynamic donor entries from current consent/health state."""
        stale = [key for key, entry in self._entries.items() if entry.source == "petals"]
        for key in stale:
            del self._entries[key]
        self._project_petals()

    def _project_petals(self) -> None:
        """One-directional projection of consented donors through the petals bridge.

        The bridge module (``app.core.petals_bridge``, outside pi_runtime) is the
        only sanctioned boundary to donated compute — this manager never imports
        the registry itself, never mutates anything, and a disabled bridge or any
        bridge failure simply leaves the static catalog authoritative.
        """
        try:
            from app.core import petals_bridge

            entries = petals_bridge.catalog_entries()
        except Exception:  # pragma: no cover - bridge unavailable/disabled
            logger.debug("pi model manager: petals projection skipped")
            return
        for entry_dict in entries:
            endpoint_id = str(entry_dict["endpoint_id"])
            existing = self._entries.get(endpoint_id)
            if existing is not None:
                if not _is_petals_entry(existing):
                    logger.error(
                        "pi model manager: reserved %s identity is already configured by %s; "
                        "donor projection is withheld",
                        endpoint_id,
                        existing.source,
                    )
                continue
            self._entries[endpoint_id] = _CatalogEntry(
                endpoint_id=endpoint_id,
                provider_kind=str(entry_dict.get("provider_kind", "openai_compat")),
                base_url=str(entry_dict["base_url"]).rstrip("/"),
                model=str(entry_dict.get("model") or "default"),
                source="petals",
                api_key=str(entry_dict.get("api_key") or ""),
                kind="petals",
                allowed_project_ids=tuple(
                    str(project_id).strip()
                    for project_id in (entry_dict.get("allowed_project_ids") or ())
                    if str(project_id).strip()
                ),
            )

    @staticmethod
    def _project_llm_server(row: object) -> _CatalogEntry | None:
        # Relay/browser donors are never Pi endpoints (isolation invariant).
        if getattr(row, "is_relay", False):
            return None
        provider_type = (getattr(row, "provider_type", "") or "").strip().lower()
        # Single source of truth with the compatibility plan: rows the plan
        # marks `projected` MUST reach the catalog, and rows it marks `blocked`
        # MUST be dropped here (silent config loss at the migration gate
        # otherwise). vllm/sglang/llamacpp/mlx are OpenAI-compatible server
        # types and project through the openai_compat provider kind.
        if provider_type not in SUPPORTED_PROVIDERS:
            return None
        try:
            capabilities = json.loads(getattr(row, "capabilities", "") or "{}")
        except (TypeError, ValueError):
            capabilities = {}
        host = (getattr(row, "host", "") or "").rstrip("/")
        if not host_is_plannable(host):
            return None
        is_local = bool(getattr(row, "is_local", False)) or provider_type in {"ollama", "lmstudio"}
        if provider_type in {"ollama", "lmstudio"} and not host.endswith("/v1"):
            host = f"{host}/v1"
        provider_kind = (
            "anthropic_compat" if provider_type.startswith("anthropic") else "openai_compat"
        )
        encrypted_key = getattr(row, "api_key", "") or ""
        api_key = ""
        if encrypted_key:
            try:
                from app.core.field_encryption import decrypt_field

                api_key = decrypt_field(encrypted_key)
            except Exception:
                logger.debug(
                    "pi model manager: LLMServer key projection failed for %s",
                    getattr(row, "id", "?"),
                )
                return None
        elif provider_type == "ollama":
            api_key = "ollama"
        elif provider_type == "lmstudio":
            api_key = settings.lmstudio_api_key or "lm-studio"
        models = capabilities.get("models") if isinstance(capabilities, dict) else None
        model = (models[0] if isinstance(models, list) and models else "") or (
            settings.ollama_model
            if provider_type == "ollama"
            else settings.lmstudio_model
            if provider_type == "lmstudio"
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
            context_window=(
                int(capabilities.get("context_window", 0) or 0)
                if isinstance(capabilities, dict)
                else 0
            ),
            supports_vision=(
                bool(capabilities.get("vision", False)) if isinstance(capabilities, dict) else False
            ),
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
        stale = [
            key for key, entry in self._entries.items() if entry.source in {"llm_server", "petals"}
        ]
        for key in stale:
            del self._entries[key]

    def refresh_settings_catalog(self) -> None:
        """Refresh mutable Pi settings/local entries on a live manager.

        Explicit test/benchmark catalogs remain immutable. Production managers
        rebuild their resolver too, so endpoint add/update/delete affects the
        next turn without a backend restart.
        """
        if self._explicit_catalog:
            return
        self._resolver = PiEndpointResolver()
        stale = [
            key for key, entry in self._entries.items() if entry.source in {"settings", "local"}
        ]
        for key in stale:
            del self._entries[key]
        configured = getattr(self._resolver, "configured", None)
        if callable(configured):
            for endpoint in configured():
                entry = self._from_settings(endpoint)
                self._entries[entry.endpoint_id] = entry
        if self._include_local:
            for entry in self._local_entries():
                self._entries[entry.endpoint_id] = entry

    # ── selection (exact identity or capability-filtered, never scored) ──
    @staticmethod
    def _matches(
        entry: _CatalogEntry,
        *,
        model: str | None,
        require_vision: bool,
        min_context: int,
        project_id: str | None = None,
    ) -> bool:
        # ``pi-petals-*`` is a projection namespace, never a user-configurable
        # endpoint namespace.  A malformed persisted/static entry must not
        # participate in generic selection (including distinct ensembles).
        if is_reserved_petals_endpoint_id(entry.endpoint_id) and not _is_petals_entry(entry):
            return False
        if _is_petals_entry(entry):
            allowed = set(entry.allowed_project_ids)
            if project_id is None:
                # A restricted donor must never be selected by a projectless
                # call.  Wildcard donors remain available to global/admin
                # catalog callers and to legacy non-research probes.
                if "*" not in allowed:
                    return False
            else:
                requested_project = str(project_id).strip()
                if not requested_project or (
                    "*" not in allowed and requested_project not in allowed
                ):
                    return False
        if model is not None and entry.model != model:
            return False
        if require_vision and not entry.supports_vision:
            return False
        if min_context > 0 and entry.context_window < min_context:
            return False
        return True

    @staticmethod
    def _admit(
        model: str | None,
        require_vision: bool,
        min_context: int,
        *,
        entry_model: str,
        supports_vision: bool,
        context_window: int,
    ) -> None:
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
            pi_provider=entry.pi_provider,
            provider_account_handle=(
                sha256(
                    f"{entry.source}\0{entry.pi_provider or entry.provider_kind}".encode()
                ).hexdigest()[:16]
            ),
            cost_input_per_mtok=entry.cost_input_per_mtok,
            cost_output_per_mtok=entry.cost_output_per_mtok,
            cost_cache_read_per_mtok=entry.cost_cache_read_per_mtok,
            cost_cache_write_per_mtok=entry.cost_cache_write_per_mtok,
            context_window=entry.context_window,
            max_tokens=entry.max_tokens,
            supports_tools=entry.supports_tools,
            supports_vision=entry.supports_vision,
            supports_reasoning=entry.supports_reasoning,
            kind=entry.kind,
        )

    def default_endpoint_id(self, *, project_id: str | None = None) -> str:
        """Return the global chat default without changing capability selection."""
        requested = str(getattr(settings, "pi_default_endpoint_id", "") or "").strip()
        if requested:
            entry = self._entries.get(requested)
            if (
                entry is not None
                and not _is_contract_stub_chat_entry(entry)
                and self._matches(
                    entry,
                    model=None,
                    require_vision=False,
                    min_context=0,
                    project_id=project_id,
                )
            ):
                return requested

        for entry in self._entries.values():
            if (
                entry.source == "settings"
                and entry.endpoint_id != DEFAULT_ENDPOINT_ID
                and not _is_contract_stub_chat_entry(entry)
                and self._matches(
                    entry,
                    model=None,
                    require_vision=False,
                    min_context=0,
                    project_id=project_id,
                )
            ):
                return entry.endpoint_id

        # Explicit catalogs (the injected authority used by deterministic
        # harnesses and isolated callers) do not have a settings-sourced
        # default or a resolver-backed built-in.  Selecting the resolver's
        # global default here would silently discard the injected catalog and
        # route an unqualified self-MoA turn to an unrelated endpoint.  Keep
        # insertion order as the catalog's deliberate priority and apply the
        # same project/capability admission checks used by normal resolution.
        if self._explicit_catalog:
            for entry in self._entries.values():
                if not _is_contract_stub_chat_entry(entry) and self._matches(
                    entry,
                    model=None,
                    require_vision=False,
                    min_context=0,
                    project_id=project_id,
                ):
                    return entry.endpoint_id

        built_in = self._entries.get(DEFAULT_ENDPOINT_ID)
        if built_in is not None and not _is_contract_stub_chat_entry(built_in):
            return built_in.endpoint_id
        return DEFAULT_ENDPOINT_ID

    def resolve(
        self,
        *,
        endpoint_id: str | None = None,
        model: str | None = None,
        require_vision: bool = False,
        min_context: int = 0,
        project_id: str | None = None,
    ) -> ResolvedPiEndpoint:
        if endpoint_id is None and model is None and not require_vision and min_context <= 0:
            endpoint_id = self.default_endpoint_id(project_id=project_id)
        if endpoint_id:
            if is_reserved_petals_endpoint_id(endpoint_id):
                configured = self._entries.get(endpoint_id)
                if configured is None or not _is_petals_entry(configured):
                    raise PiEndpointResolutionError("petals_endpoint_namespace_conflict")
            entry = self._entries.get(endpoint_id)
            if entry is None:
                # Settings-configured endpoints remain exactly resolvable.
                endpoint = self._resolver.resolve(endpoint_id, model=model)
                self._admit(
                    None,
                    require_vision,
                    min_context,
                    entry_model=endpoint.model,
                    supports_vision=endpoint.supports_vision,
                    context_window=endpoint.context_window,
                )
                return endpoint
            if _is_contract_stub_chat_entry(entry):
                raise PiEndpointResolutionError("contract_stub_pi_endpoint")
            if _is_petals_entry(entry):
                allowed = set(entry.allowed_project_ids)
                if project_id is None and "*" not in allowed:
                    raise PiEndpointResolutionError("petals_project_id_required")
                if project_id is not None:
                    requested_project = str(project_id).strip()
                    if not requested_project or (
                        "*" not in allowed and requested_project not in allowed
                    ):
                        raise PiEndpointResolutionError("petals_project_not_authorized")
            self._admit(
                model,
                require_vision,
                min_context,
                entry_model=entry.model,
                supports_vision=entry.supports_vision,
                context_window=entry.context_window,
            )
            return self._materialize(entry)
        candidates = [
            entry
            for entry in self._entries.values()
            if not _is_contract_stub_chat_entry(entry)
            and self._matches(
                entry,
                model=model,
                require_vision=require_vision,
                min_context=min_context,
                project_id=project_id,
            )
        ]
        if candidates:
            return self._materialize(candidates[0])
        if not self._entries:
            # Explicitly empty catalogs retain the resolver as the source of truth.
            endpoint = self._resolver.resolve(DEFAULT_ENDPOINT_ID, model=model)
            self._admit(
                None,
                require_vision,
                min_context,
                entry_model=endpoint.model,
                supports_vision=endpoint.supports_vision,
                context_window=endpoint.context_window,
            )
            return endpoint
        raise PiEndpointResolutionError("no_matching_pi_endpoint")

    def resolve_distinct(
        self,
        n: int,
        *,
        model: str | None = None,
        exclude: Iterable[str] = (),
        exclude_models: Iterable[str] = (),
        require_vision: bool = False,
        min_context: int = 0,
        project_id: str | None = None,
    ) -> list[ResolvedPiEndpoint]:
        """Resolve N endpoints backed by N distinct model identities.

        Endpoint identity is still preserved for exact routing and provenance,
        but replicas serving the same model do not provide independent model
        judgments and therefore cannot satisfy an ensemble-diversity request.
        """
        excluded = set(exclude)
        excluded_models = {
            str(item or "").strip().casefold() for item in exclude_models if str(item or "").strip()
        }
        matches: list[_CatalogEntry] = []
        seen_models: set[str] = set()
        for entry in self._entries.values():
            if (
                entry.endpoint_id in excluded
                or entry.model.strip().casefold() in excluded_models
                or _is_contract_stub_chat_entry(entry)
                or not self._matches(
                    entry,
                    model=model,
                    require_vision=require_vision,
                    min_context=min_context,
                    project_id=project_id,
                )
            ):
                continue
            model_identity = entry.model.strip().casefold()
            if not model_identity or model_identity in seen_models:
                continue
            seen_models.add(model_identity)
            matches.append(entry)
            if len(matches) >= n:
                break
        if len(matches) < n:
            raise PiEndpointResolutionError("insufficient_distinct_pi_models")
        return [self._materialize(entry) for entry in matches]

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
        self,
        model: str | None = None,
        *,
        provider: str | None = None,
        endpoint_id: str | None = None,
    ) -> ResolvedPiEndpoint:
        """Resolve the identity-pinned endpoint for one embedding model.

        Only OpenAI-compatible entries qualify. A concrete requested model is
        an exact capability requirement, so a configured remote endpoint with
        that model beats unrelated local entries. When the model is omitted or
        ``default``, the active local provider anchors the vector space.
        """
        if endpoint_id and is_reserved_petals_endpoint_id(endpoint_id):
            configured = self._entries.get(endpoint_id)
            if configured is None or not _is_petals_entry(configured):
                raise PiEndpointResolutionError("petals_endpoint_namespace_conflict")
        candidates = [
            entry
            for entry in self._entries.values()
            if entry.provider_kind == "openai_compat"
            and not (
                is_reserved_petals_endpoint_id(entry.endpoint_id) and not _is_petals_entry(entry)
            )
        ]
        if not candidates:
            raise PiEndpointResolutionError("no_matching_pi_embed_endpoint")
        active_provider = (provider or settings.llm_provider or "ollama").strip().lower()
        requested_model = (model or self._active_embed_model(active_provider) or "").strip()

        if endpoint_id:
            pinned = self._entries.get(endpoint_id)
            if pinned is None or pinned.provider_kind != "openai_compat":
                raise PiEndpointResolutionError("unknown_pi_embed_endpoint")
            if requested_model and requested_model != "default":
                if self._embedding_model(pinned) != requested_model:
                    raise PiEndpointResolutionError("pi_embed_endpoint_model_mismatch")
            return self._materialize(pinned)

        if requested_model and requested_model != "default":
            exact = [
                entry for entry in candidates if self._embedding_model(entry) == requested_model
            ]
            if exact:
                active_local = [
                    entry for entry in exact if self._is_active_local(entry, active_provider)
                ]
                return self._materialize((active_local or exact)[0])
            raise PiEndpointResolutionError("no_matching_pi_embed_endpoint_model")

        active_local = [
            entry for entry in candidates if self._is_active_local(entry, active_provider)
        ]
        if active_local:
            return self._materialize(active_local[0])
        default_model = [entry for entry in candidates if self._embedding_model(entry) == "default"]
        if default_model:
            return self._materialize(default_model[0])
        if len(candidates) == 1:
            # ``default`` is intentionally provider-neutral. An explicit
            # single endpoint is therefore the only safe identity to use.
            return self._materialize(candidates[0])
        raise PiEndpointResolutionError("no_matching_pi_embed_endpoint")

    def catalog(self, *, project_id: str | None = None) -> list[PiEndpointInfo]:
        """Identity/capability view with optional project-scoped admission.

        Settings and benchmark callers intentionally omit ``project_id`` and
        receive the global identity catalog. Project-readable surfaces pass
        their project so an unadmitted Petals identity is not advertised as
        selectable before the resolver rejects it.
        """
        return [
            PiEndpointInfo(
                entry.endpoint_id,
                entry.model,
                entry.provider_kind,
                pi_provider=entry.pi_provider,
                auth_method=entry.auth_method,
                context_window=entry.context_window,
                max_tokens=entry.max_tokens,
                supports_tools=entry.supports_tools,
                supports_vision=entry.supports_vision,
                supports_reasoning=entry.supports_reasoning,
                kind=entry.kind,
            )
            for entry in self._entries.values()
            if (
                self._matches(
                    entry,
                    model=None,
                    require_vision=False,
                    min_context=0,
                    project_id=project_id,
                )
                or (project_id is None and _is_petals_entry(entry))
            )
        ]

    def available_model_identities(self, *, project_id: str | None = None) -> tuple[str, ...]:
        """Return distinct, project-admitted model identities without resolving secrets.

        Adaptive validation needs to decide whether a multi-model method is
        appropriate before dispatch.  It must inspect the same Pi catalog as
        the dispatcher, but that decision must not materialize settings
        credentials or make a provider request.  Petals authorization and
        reserved-namespace checks therefore run through the same admission
        predicate used by ``resolve_distinct``.
        """
        identities: list[str] = []
        seen: set[str] = set()
        for entry in self._entries.values():
            if _is_contract_stub_chat_entry(entry):
                continue
            if not self._matches(
                entry,
                model=None,
                require_vision=False,
                min_context=0,
                project_id=project_id,
            ):
                continue
            identity = entry.model.strip().casefold()
            if identity and identity not in seen:
                seen.add(identity)
                identities.append(identity)
        return tuple(identities)


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


def reset_live_settings_catalogs() -> None:
    """Refresh mutable configured endpoints on every live production manager."""
    for manager in list(_LIVE_MANAGERS):
        try:
            manager.refresh_settings_catalog()
        except Exception:  # pragma: no cover - defensive; CRUD remains durable
            logger.debug("pi model manager: settings catalog refresh skipped")
