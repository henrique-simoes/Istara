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

import httpx

from app.config import settings

from .endpoints import ResolvedPiEndpoint
from .model_manager import PiModelManager

logger = logging.getLogger(__name__)


class PiEmbeddingError(RuntimeError):
    """Typed gateway failure (HTTP status, malformed or short response)."""


class VectorSpaceInvariantError(RuntimeError):
    """The two engines would embed with different models — never allowed."""


def default_embed_model() -> str:
    """The ONE embedding model for both engines (vector-space invariant).

    Mirrors ``app.core.embeddings._embed_model_name`` exactly; keep the two
    rules in lockstep (``assert_vector_space_invariant`` guards the drift).
    """
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_embed_model
    return settings.ollama_embed_model


def assert_vector_space_invariant() -> str:
    """Assert the Pi gateway and the legacy plane embed with the same model.

    Returns the shared model name. Raises ``VectorSpaceInvariantError`` on any
    divergence so an engine switch can never silently change the embedding
    space (which would invalidate every stored vector).
    """
    if settings.llm_provider == "lmstudio":
        legacy = settings.lmstudio_embed_model
    else:
        legacy = settings.ollama_embed_model
    pi = default_embed_model()
    if pi != legacy:
        raise VectorSpaceInvariantError(
            "vector_space_invariant_violation: "
            f"pi embed model {pi!r} != legacy embed model {legacy!r}"
        )
    return pi


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

    async def _call_native_ollama(self, endpoint: ResolvedPiEndpoint, model: str,
                                  texts: list[str]) -> list[list[float]]:
        base = endpoint.base_url.rstrip("/")
        host = base[:-3] if base.endswith("/v1") else base
        client = await self._get_client(endpoint.timeout_ms)
        resp = await client.post(f"{host}/api/embed", json={"model": model, "input": texts})
        resp.raise_for_status()
        embeddings = resp.json().get("embeddings") or []
        return [list(vector) for vector in embeddings]

    async def _call_openai_compatible(self, endpoint: ResolvedPiEndpoint, model: str,
                                      texts: list[str]) -> list[list[float]]:
        base = endpoint.base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {endpoint.api_key}"} if endpoint.api_key else {}
        client = await self._get_client(endpoint.timeout_ms)
        resp = await client.post(f"{base}/embeddings", json={"model": model, "input": texts},
                                 headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data") or []
        ordered = sorted(data, key=lambda item: item.get("index", 0))
        return [list(item.get("embedding") or []) for item in ordered]

    async def embed(self, texts: list[str], *, model: str | None = None) -> dict:
        """Embed ``texts`` through the Pi-managed endpoint; fail closed.

        Returns the dispatcher outcome shape (``embeddings`` plus endpoint /
        model identity and exact-zero usage) — the dispatcher records the one
        ledger row for the dispatch. Resolution and HTTP failures raise
        (``PiEndpointResolutionError``, ``httpx`` errors, ``PiEmbeddingError``)
        so the dispatch can never leak onto the legacy plane or donors.
        """
        texts = list(texts)
        model = model or default_embed_model()
        manager = self.manager()
        await manager.ensure_db_projection()
        endpoint = manager.resolve_embed()
        if self._is_native_ollama(endpoint):
            vectors = await self._call_native_ollama(endpoint, model, texts)
        else:
            vectors = await self._call_openai_compatible(endpoint, model, texts)
        if len(vectors) != len(texts):
            raise PiEmbeddingError(
                f"embed_response_cardinality: {len(vectors)} vectors for {len(texts)} texts"
            )
        return {
            "embeddings": vectors,
            "endpoint_id": endpoint.endpoint_id,
            "model": model,
            # Embeddings consume no billable tokens; exact-zero accounting.
            "usage": {"estimate": False},
            "status": "success",
        }
