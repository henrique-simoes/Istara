"""Identity-pinned Pi endpoint resolution.

This is deliberately separate from ``LLMServer`` and ``llm_router``.  Those
objects advertise capacity to the ordinary Istara/Petals scheduler; adding a
Pi API endpoint there would allow a same-model donor collision.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from app.config import (
    PiApiEndpoint,
    _read_macos_keychain_secret,
    _read_pi_endpoint_secret,
    settings,
)


DEFAULT_ENDPOINT_ID = "pi-deepseek-default"

# Per-endpoint secret TTL: Keychain subprocess reads are expensive and must not
# run on every turn (H-4).
SECRET_CACHE_TTL_SECONDS = 60.0


def _read_endpoint_secret(endpoint: PiApiEndpoint) -> str:
    """Resolve an endpoint secret (env fallback handled in ``app.config``).

    The Keychain read is delegated through this module's
    ``_read_macos_keychain_secret`` global so the existing test seam keeps
    working; the secret value is never logged.
    """
    return _read_pi_endpoint_secret(
        endpoint.endpoint_id,
        endpoint.keychain_service,
        endpoint.keychain_account,
        keychain_reader=_read_macos_keychain_secret,
    )


class PiEndpointResolutionError(ValueError):
    """A selected Pi request has no usable, exact endpoint binding."""


class PiRuntimeTurnError(RuntimeError):
    """A governed Pi turn reached a non-success terminal (``error``/``aborted``).

    Governed seams fail closed on this instead of returning a proposal, reply,
    or delegation result built from a failed or partially-streamed turn — a
    worker failure must never surface as a false-success artifact or reply.
    """

    def __init__(self, status: str, error: str | None = None) -> None:
        self.status = status
        self.error = error
        super().__init__(f"pi_runtime_turn_{status}:{error or 'unknown'}")


@dataclass(frozen=True)
class ResolvedPiEndpoint:
    endpoint_id: str
    provider_kind: str
    base_url: str
    model: str
    api_key: str
    timeout_ms: int
    max_retries: int
    # Trustworthy per-endpoint pricing (USD per 1M tokens). Forwarded to the
    # worker so pi-ai prices real usage and the per-run cost ceiling can fail
    # closed; a real endpoint left at 0.0 cannot enforce a cost budget.
    cost_input_per_mtok: float = 0.0
    cost_output_per_mtok: float = 0.0
    cost_cache_read_per_mtok: float = 0.0
    cost_cache_write_per_mtok: float = 0.0
    # Test-only: when ``provider_kind == "faux"`` the worker uses these scripted
    # deterministic completions instead of a network provider. The production
    # resolver never sets this — only tests construct a faux endpoint — so the
    # real provider HTTP stack is exercised in production paths.
    faux_responses: tuple[Any, ...] | None = None
    faux_forced_tool_calls: tuple[Any, ...] | None = None
    # Static capability advertisement used by PiModelManager admission. 0/False
    # means "unknown" and fails closed only when a caller explicitly requires
    # the capability (min_context / require_vision).
    context_window: int = 0
    max_tokens: int = 0
    supports_tools: bool = True
    supports_vision: bool = False
    kind: str = "remote"

    def telemetry_identity(self) -> dict[str, str]:
        """Safe fields permitted in telemetry; never return URL/key material."""
        return {
            "endpoint_id": self.endpoint_id,
            "provider_kind": self.provider_kind,
            "model": self.model,
        }


class PiEndpointResolver:
    """Resolve Pi endpoints exactly, without any compute-registry fallback."""

    def __init__(self, endpoints: list[PiApiEndpoint] | None = None) -> None:
        configured = endpoints if endpoints is not None else settings.pi_api_endpoints
        self._endpoints = {endpoint.endpoint_id: endpoint for endpoint in configured}
        if DEFAULT_ENDPOINT_ID not in self._endpoints:
            self._endpoints[DEFAULT_ENDPOINT_ID] = PiApiEndpoint(
                endpoint_id=DEFAULT_ENDPOINT_ID,
                provider_kind="openai_compat",
                base_url=settings.pi_replacement_deepseek_base_url,
                model=settings.pi_replacement_deepseek_model,
                keychain_service=settings.pi_replacement_deepseek_keychain_service,
                keychain_account=settings.pi_replacement_deepseek_keychain_account,
                # Priced by default so the built-in endpoint's cost ceiling fails
                # closed; operators override with their negotiated contract rate.
                # Every category the endpoint can spend must be priced — pi-ai
                # prices input, output, and cache-read (DeepSeek cache hits)
                # independently, so a cache-read turn on an input/output-only
                # endpoint would otherwise fail closed as unpriced.
                cost_input_per_mtok=settings.pi_replacement_deepseek_cost_input_per_mtok,
                cost_output_per_mtok=settings.pi_replacement_deepseek_cost_output_per_mtok,
                cost_cache_read_per_mtok=settings.pi_replacement_deepseek_cost_cache_read_per_mtok,
            )
        # endpoint_id -> (monotonic read time, secret); only non-empty secrets.
        self._secret_cache: dict[str, tuple[float, str]] = {}

    def _endpoint(self, endpoint_id: str, model: str | None) -> PiApiEndpoint:
        endpoint = self._endpoints.get((endpoint_id or "").strip())
        if endpoint is None:
            raise PiEndpointResolutionError("unknown_pi_endpoint")
        if model is not None and model != endpoint.model:
            raise PiEndpointResolutionError("pi_endpoint_model_mismatch")
        return endpoint

    def _cached_secret(self, endpoint_id: str) -> str | None:
        entry = self._secret_cache.get(endpoint_id)
        if entry is None:
            return None
        read_at, secret = entry
        if time.monotonic() - read_at >= SECRET_CACHE_TTL_SECONDS:
            self._secret_cache.pop(endpoint_id, None)
            return None
        return secret

    def _store_secret(self, endpoint_id: str, secret: str) -> str:
        if secret:
            self._secret_cache[endpoint_id] = (time.monotonic(), secret)
        return secret

    def _read_secret(self, endpoint: PiApiEndpoint) -> str:
        """Blocking secret read (sync callers only); TTL-cached per endpoint."""
        cached = self._cached_secret(endpoint.endpoint_id)
        if cached is not None:
            return cached
        secret = _read_endpoint_secret(endpoint)
        return self._store_secret(endpoint.endpoint_id, secret)

    async def _read_secret_async(self, endpoint: PiApiEndpoint) -> str:
        """Secret read off the event loop (``asyncio.to_thread``); TTL-cached."""
        cached = self._cached_secret(endpoint.endpoint_id)
        if cached is not None:
            return cached
        secret = await asyncio.to_thread(_read_endpoint_secret, endpoint)
        return self._store_secret(endpoint.endpoint_id, secret)

    def _build(self, endpoint: PiApiEndpoint, api_key: str) -> ResolvedPiEndpoint:
        if not api_key:
            raise PiEndpointResolutionError("missing_keychain_secret")
        return ResolvedPiEndpoint(
            endpoint_id=endpoint.endpoint_id,
            provider_kind=endpoint.provider_kind,
            base_url=endpoint.base_url.rstrip("/"),
            model=endpoint.model,
            api_key=api_key,
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

    def configured(self) -> list[PiApiEndpoint]:
        """Identity-only view of every configured endpoint (never secrets)."""
        return list(self._endpoints.values())

    def resolve(self, endpoint_id: str, *, model: str | None = None) -> ResolvedPiEndpoint:
        endpoint = self._endpoint(endpoint_id, model)
        return self._build(endpoint, self._read_secret(endpoint))

    async def aresolve(
        self, endpoint_id: str, *, model: str | None = None
    ) -> ResolvedPiEndpoint:
        """Async resolution: Keychain reads never stall the event loop (H-4)."""
        endpoint = self._endpoint(endpoint_id, model)
        return self._build(endpoint, await self._read_secret_async(endpoint))

    def describe(self, endpoint_id: str) -> dict[str, str]:
        """Return identity-only metadata for validation and telemetry setup."""
        endpoint = self._endpoints.get((endpoint_id or "").strip())
        if endpoint is None:
            raise PiEndpointResolutionError("unknown_pi_endpoint")
        return {
            "endpoint_id": endpoint.endpoint_id,
            "provider_kind": endpoint.provider_kind,
            "model": endpoint.model,
        }
