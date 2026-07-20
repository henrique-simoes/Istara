"""Pi-only endpoint catalog and exact/capability based selection.

This module intentionally has no ComputeRegistry imports.  Pi traffic is
identity-pinned and must never become schedulable donated compute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .endpoints import PiEndpointResolutionError, PiEndpointResolver, ResolvedPiEndpoint


@dataclass(frozen=True)
class PiEndpointInfo:
    endpoint_id: str
    model: str
    provider_kind: str
    context_window: int = 0
    max_tokens: int = 0
    supports_tools: bool = True
    supports_vision: bool = False


class PiModelManager:
    """Select from the fixed Pi catalog, never by donor capacity/scoring."""

    def __init__(self, resolver: PiEndpointResolver | None = None, endpoints: Iterable[ResolvedPiEndpoint] = ()) -> None:
        self._resolver = resolver or PiEndpointResolver()
        self._endpoints = {endpoint.endpoint_id: endpoint for endpoint in endpoints}

    def _all(self) -> list[ResolvedPiEndpoint]:
        return list(self._endpoints.values())

    def resolve(self, *, endpoint_id: str | None = None, model: str | None = None,
                require_vision: bool = False, min_context: int = 0) -> ResolvedPiEndpoint:
        if endpoint_id:
            endpoint = self._endpoints.get(endpoint_id) or self._resolver.resolve(endpoint_id, model=model)
            if model and endpoint.model != model:
                raise PiEndpointResolutionError("pi_endpoint_model_mismatch")
            return endpoint
        candidates = self._all()
        if not candidates:
            # Existing configured endpoints retain the resolver as the source of truth.
            from .endpoints import DEFAULT_ENDPOINT_ID
            return self._resolver.resolve(DEFAULT_ENDPOINT_ID, model=model)
        for endpoint in candidates:
            if model is None or endpoint.model == model:
                return endpoint
        raise PiEndpointResolutionError("no_matching_pi_endpoint")

    def resolve_distinct(self, n: int, *, model: str | None = None, exclude: Iterable[str] = ()) -> list[ResolvedPiEndpoint]:
        excluded = set(exclude)
        matches = [item for item in self._all() if item.endpoint_id not in excluded and (model is None or item.model == model)]
        if len(matches) < n:
            raise PiEndpointResolutionError("insufficient_distinct_pi_endpoints")
        return matches[:n]

    def catalog(self) -> list[PiEndpointInfo]:
        return [PiEndpointInfo(item.endpoint_id, item.model, item.provider_kind) for item in self._all()]
