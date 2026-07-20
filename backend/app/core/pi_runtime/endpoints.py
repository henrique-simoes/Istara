"""Identity-pinned Pi endpoint resolution.

This is deliberately separate from ``LLMServer`` and ``llm_router``.  Those
objects advertise capacity to the ordinary Istara/Petals scheduler; adding a
Pi API endpoint there would allow a same-model donor collision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import PiApiEndpoint, _read_macos_keychain_secret, settings


DEFAULT_ENDPOINT_ID = "pi-deepseek-default"


class PiEndpointResolutionError(ValueError):
    """A selected Pi request has no usable, exact endpoint binding."""


@dataclass(frozen=True)
class ResolvedPiEndpoint:
    endpoint_id: str
    provider_kind: str
    base_url: str
    model: str
    api_key: str
    timeout_ms: int
    max_retries: int
    # Test-only: when ``provider_kind == "faux"`` the worker uses these scripted
    # deterministic completions instead of a network provider. The production
    # resolver never sets this — only tests construct a faux endpoint — so the
    # real provider HTTP stack is exercised in production paths.
    faux_responses: tuple[Any, ...] | None = None

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
            )

    def resolve(self, endpoint_id: str, *, model: str | None = None) -> ResolvedPiEndpoint:
        endpoint = self._endpoints.get((endpoint_id or "").strip())
        if endpoint is None:
            raise PiEndpointResolutionError("unknown_pi_endpoint")
        if model is not None and model != endpoint.model:
            raise PiEndpointResolutionError("pi_endpoint_model_mismatch")
        api_key = _read_macos_keychain_secret(endpoint.keychain_service, endpoint.keychain_account)
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
        )

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
