"""Pi embeddings gateway (W8 — master plan §8 W8, §9 anchor).

pi-ai cannot execute embeddings, so the gateway is Python-direct HTTP under
Pi identity management: the endpoint is resolved through the
``PiModelManager`` catalog (``kind=local`` Ollama native ``/api/embed``, or
any ``/v1/embeddings``-compatible entry) and called with ``httpx``. Pi traffic
stays identity-pinned — never ComputeRegistry capacity and never donated
compute.

Accounting stays with the dispatcher's one-row-per-dispatch contract (§5.5):
``AgenticDispatcher.embed`` records the single ``purpose="embed"`` ledger row
for each dispatch (success and failure alike), so the gateway itself never
writes ledger rows and a dispatch can never be double-counted.

Vector-space invariant: BOTH engines embed with the SAME model
(``default_embed_model``). An engine switch must never silently change the
embedding space — every stored vector and cache entry would be invalidated.
``assert_vector_space_invariant`` runs at startup next to the
``vector_health`` dimension probe.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.core.embedding_validation import (
    validate_embedding_vectors as _validate_embedding_vectors,
)
from app.core.token_counter import count_tokens

from .endpoints import ResolvedPiEndpoint
from .model_manager import PiModelManager

logger = logging.getLogger(__name__)


class PiEmbeddingError(RuntimeError):
    """Typed gateway failure (HTTP status, malformed or short response)."""


class VectorSpaceInvariantError(RuntimeError):
    """The two engines cannot be proven to share one safe vector space."""


def default_embed_model() -> str:
    """The ONE embedding model for both engines (vector-space invariant).

    Mirrors ``app.core.embeddings._embed_model_name`` exactly; keep the two
    rules in lockstep (``assert_vector_space_invariant`` guards the drift).
    """
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_embed_model
    return settings.ollama_embed_model


def validate_embedding_vectors(vectors: Any, **kwargs: Any) -> list[list[float]]:
    """Validate provider vectors with the gateway's typed error contract."""
    return _validate_embedding_vectors(vectors, error_type=PiEmbeddingError, **kwargs)


async def assert_vector_space_invariant(*, dimension_probe: Any) -> str:
    """Probe both engines and require one model/dimension vector space.

    The configured model name is passed to both real engine paths, but the
    dimensions are established from independent provider responses through
    ``vector_health``. The caller supplies that probe so this gateway remains
    independent from the legacy embedding wrapper and cannot form an import
    cycle. A mismatch or failed probe raises instead of allowing startup to
    continue with unsafe engine switching.
    """
    model = default_embed_model()
    legacy = await dimension_probe(
        engine="legacy", model=model, check_stored=False
    )
    pi = await dimension_probe(engine="pi", model=model, check_stored=False)
    for engine, result in (("legacy", legacy), ("pi", pi)):
        if result.get("status") != "ok":
            raise VectorSpaceInvariantError(
                f"vector_space_invariant_probe_failed: {engine}: {result.get('message', 'unknown')}"
            )
    if legacy.get("model") != pi.get("model") or legacy.get("model_dim") != pi.get("model_dim"):
        raise VectorSpaceInvariantError(
            "vector_space_invariant_violation: "
            f"legacy model/dim={legacy.get('model')!r}/{legacy.get('model_dim')!r}, "
            f"pi model/dim={pi.get('model')!r}/{pi.get('model_dim')!r}"
        )
    return model


class EmbeddingsGateway:
    """Resolve an embed endpoint from the PiModelManager and call it directly."""

    def __init__(self, manager: PiModelManager | None = None,
                 *, client: httpx.AsyncClient | None = None) -> None:
        self._manager = manager
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None

    def manager(self) -> PiModelManager:
        if self._manager is None:
            self._manager = PiModelManager()
        return self._manager

    async def _get_client(self, timeout_ms: int) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(timeout=max(timeout_ms, 1000) / 1000)
        return self._owned_client

    @staticmethod
    def _is_native_ollama(endpoint: ResolvedPiEndpoint) -> bool:
        # The well-known local Ollama entry speaks the native /api/embed
        # contract; every other entry is treated as /v1/embeddings-compatible
        # (Ollama also serves the OpenAI-compatible shape under /v1).
        return endpoint.endpoint_id == "pi-local-ollama"

    @staticmethod
    def _normalize_usage(
        raw_usage: Any, endpoint: ResolvedPiEndpoint, texts: list[str]
    ) -> dict[str, Any]:
        """Normalize provider usage, explicitly estimating when it is absent."""
        usage = raw_usage if isinstance(raw_usage, dict) and raw_usage else None
        if usage is None:
            input_tokens = count_tokens("\n".join(texts))
            estimate = True
        else:
            input_tokens = int(usage.get(
                "input_tokens", usage.get("prompt_tokens", usage.get("input", 0))
            ) or 0)
            estimate = bool(usage.get("estimate", False))
        output_tokens = int((usage or {}).get(
            "output_tokens", (usage or {}).get("completion_tokens", (usage or {}).get("output", 0))
        ) or 0)
        cache_read = int((usage or {}).get("cache_read", (usage or {}).get("cacheRead", 0)) or 0)
        cache_write = int((usage or {}).get("cache_write", (usage or {}).get("cacheWrite", 0)) or 0)
        total_tokens = int((usage or {}).get(
            "total_tokens", (usage or {}).get(
                "total", input_tokens + output_tokens + cache_read + cache_write
            )
        ) or 0)

        cost_raw = (usage or {}).get("cost")
        if isinstance(cost_raw, dict):
            cost_usd = float(cost_raw.get("total", 0) or 0)
        elif cost_raw is not None:
            cost_usd = float(cost_raw or 0)
        elif "cost_usd" in (usage or {}):
            cost_usd = float((usage or {}).get("cost_usd") or 0)
        else:
            cost_usd = (
                input_tokens * endpoint.cost_input_per_mtok
                + output_tokens * endpoint.cost_output_per_mtok
                + cache_read * endpoint.cost_cache_read_per_mtok
                + cache_write * endpoint.cost_cache_write_per_mtok
            ) / 1_000_000
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "estimate": estimate,
        }

    async def _call_native_ollama(self, endpoint: ResolvedPiEndpoint, model: str,
                                  texts: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        base = endpoint.base_url.rstrip("/")
        host = base[:-3] if base.endswith("/v1") else base
        client = await self._get_client(endpoint.timeout_ms)
        resp = await client.post(f"{host}/api/embed", json={"model": model, "input": texts})
        resp.raise_for_status()
        payload = resp.json()
        embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        return list(embeddings or []), self._normalize_usage(
            payload.get("usage") if isinstance(payload, dict) else None,
            endpoint,
            texts,
        )

    async def _call_openai_compatible(self, endpoint: ResolvedPiEndpoint, model: str,
                                      texts: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        base = endpoint.base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {endpoint.api_key}"} if endpoint.api_key else {}
        client = await self._get_client(endpoint.timeout_ms)
        resp = await client.post(f"{base}/embeddings", json={"model": model, "input": texts},
                                 headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            data = []
        ordered = sorted(
            data,
            key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0,
        )
        vectors = [item.get("embedding") if isinstance(item, dict) else item for item in ordered]
        return vectors, self._normalize_usage(
            payload.get("usage") if isinstance(payload, dict) else None,
            endpoint,
            texts,
        )

    async def embed(self, texts: list[str], *, model: str | None = None) -> dict:
        """Embed ``texts`` through the Pi-managed endpoint; fail closed.

        Returns the dispatcher outcome shape (``embeddings`` plus endpoint /
        model identity and normalized usage) — the dispatcher records the one
        ledger row for the dispatch. Resolution and HTTP failures raise
        (``PiEndpointResolutionError``, ``httpx`` errors, ``PiEmbeddingError``)
        so the dispatch can never leak onto the legacy plane or donors.
        """
        texts = list(texts)
        model = model or default_embed_model()
        manager = self.manager()
        await manager.ensure_db_projection()
        endpoint = manager.resolve_embed(model)
        if self._is_native_ollama(endpoint):
            vectors, usage = await self._call_native_ollama(endpoint, model, texts)
        else:
            vectors, usage = await self._call_openai_compatible(endpoint, model, texts)
        vectors = validate_embedding_vectors(vectors, expected_count=len(texts))
        return {
            "embeddings": vectors,
            "endpoint_id": endpoint.endpoint_id,
            "model": model,
            "usage": usage,
            "status": "success",
        }
