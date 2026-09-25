"""Local embedding engine with caching (W8: dispatcher-routed).

``embed_text`` / ``embed_chunks`` keep the ``embedding_cache`` in front and
route cache misses through ``agentic.embed`` — legacy engine: the unchanged
``ollama.embed*`` plane; Pi engine: the W8 EmbeddingsGateway. Every downstream
consumer (rag, prompt_rag, agent_memory, skill tools, execution, file
watcher, vector_health) inherits the engine dispatch with zero edits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.embedding_cache import embedding_cache

logger = logging.getLogger(__name__)

# Engine-known embedding dimensions per model, keyed by the canonical model
# identity (the configured embed model name). Learned from validated provider
# responses and seeded by the startup vector-space probes; cache hits are
# validated against it so an entry written under a different embedding
# model/dimension can never flow into retrieval.
_known_embed_dimensions: dict[str, int] = {}

# Serving-model fingerprints per profile namespace (F11). A profile's name and dimension cannot
# tell two models apart: with the default LM Studio profile the identity is the literal
# "default", and a swapped model of the same dimension passed every check. The fingerprint is a
# hash of the vectors a fixed probe produces, so it changes whenever the model serving the
# endpoint changes. The fingerprinted namespace keys the embedding cache, so vectors cached
# from another model are never served, and it binds every vector store manifest.
_known_fingerprints: dict[str, tuple[str, float]] = {}
FINGERPRINT_PROBE_TEXTS = (
    "Istara embedding identity probe: participant quotes about onboarding.",
    "Istara embedding identity probe: invoice reminders arrive late.",
)
FINGERPRINT_TTL_SECONDS = 300.0


def record_known_embed_dimension(model: str, dimension: int) -> None:
    """Record the engine's known embedding dimension for a model."""
    if dimension and dimension > 0:
        _known_embed_dimensions[model] = dimension


def known_embed_dimension(model: str) -> int | None:
    """Return the engine's known embedding dimension for a model, if any."""
    return _known_embed_dimensions.get(model)


def _validate_embedding_vectors(vectors, **kwargs):  # noqa: ANN001, ANN201
    """Lazy wrapper around the gateway validator.

    Imported function-locally so this low-level module does not pull
    ``app.core.pi_runtime`` at module import time — that eager edge closed a
    module-level import cycle (embeddings → pi_runtime.engine → telemetry →
    research_validity → skills.intercoder → skill_factory → file_processor →
    embeddings). Same pattern as the gateway import in ``_dispatch_embed``.
    """
    from app.core.pi_runtime.embeddings_gateway import validate_embedding_vectors

    return validate_embedding_vectors(vectors, **kwargs)


@dataclass
class TextChunk:
    """A chunk of text with metadata for embedding."""

    text: str
    source: str
    page: int | None = None
    position: int = 0
    metadata: dict | None = None
    chunk_type: str = "character"


@dataclass
class EmbeddedChunk:
    """A text chunk with its embedding vector."""

    chunk: TextChunk
    vector: list[float]


def _embed_model_name() -> str:
    """Return the immutable Pi-owned embedding model identity."""
    from app.core.pi_runtime.embedding_profile import get_active_embedding_profile

    return get_active_embedding_profile().model_id


def _embed_cache_namespace() -> str:
    """Return the version-bound cache identity for the active vector space."""
    from app.core.pi_runtime.embedding_profile import get_active_embedding_profile

    return get_active_embedding_profile().cache_namespace


def fingerprint_vectors(vectors: list[list[float]]) -> str:
    """Stable identity of a vector space: the hash of the probe vectors, rounded."""
    import hashlib

    payload = ";".join(",".join(f"{x:.4f}" for x in vector) for vector in vectors)
    return hashlib.sha256(f"{len(vectors[0])}|{payload}".encode()).hexdigest()[:16]


def known_embed_fingerprint(namespace: str | None = None) -> str | None:
    """The fingerprint measured in this process for the active profile, if still fresh."""
    import time

    entry = _known_fingerprints.get(namespace or _embed_cache_namespace())
    if entry and time.monotonic() - entry[1] < FINGERPRINT_TTL_SECONDS:
        return entry[0]
    return None


async def ensure_embed_fingerprint(*, force: bool = False) -> str:
    """Measure (or reuse) the serving model's fingerprint for the active profile.

    One probe batch per profile and TTL window, plus a probe whenever ``force`` is set (health
    checks). The probe also records the dimension for the fingerprinted namespace.
    """
    import time

    base = _embed_cache_namespace()
    if not force:
        fingerprint = known_embed_fingerprint(base)
        if fingerprint:
            return fingerprint
    # One probe text per call: the same request shape as an ordinary single-text embed.
    vectors = [
        _validate_embedding_vectors(await _dispatch_embed([text]), expected_count=1)[0]
        for text in FINGERPRINT_PROBE_TEXTS
    ]
    fingerprint = fingerprint_vectors(vectors)
    _known_fingerprints[base] = (fingerprint, time.monotonic())
    record_known_embed_dimension(f"{base}#{fingerprint}", len(vectors[0]))
    record_known_embed_dimension(base, len(vectors[0]))
    return fingerprint


async def _space_namespace() -> str:
    """Cache namespace of the vector space the serving model actually produces."""
    return f"{_embed_cache_namespace()}#{await ensure_embed_fingerprint()}"


async def _dispatch_embed(texts: list[str], *, project_id: str | None = None) -> list[list[float]]:
    """Route cache-miss embeddings through the AgenticDispatcher (W8)."""
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    return await agentic.embed(
        texts=texts, project_id=project_id, params=TurnParams(model=_embed_model_name())
    )


async def embed_text(text: str) -> list[float]:
    """Embed a single text string, checking the cache first."""
    model = _embed_model_name()
    cache_namespace = await _space_namespace()

    cached = await embedding_cache.get(cache_namespace, text)
    if cached is not None:
        known = known_embed_dimension(cache_namespace)
        if known is not None:
            try:
                # Validate the cached vector against the engine's known
                # dimension for this model (not the dimension the entry happens
                # to carry): a numeric entry written under a different
                # embedding model/dimension must be treated as a miss and
                # re-embedded.
                return _validate_embedding_vectors(
                    [cached], expected_count=1, expected_dimension=known
                )[0]
            except Exception:
                logger.warning(
                    "Ignoring malformed or stale-dimension embedding cache entry for model %s",
                    model,
                )
        else:
            # The engine's dimension for this model has not been established
            # yet in this process — fail closed and re-embed rather than trust
            # an entry whose vector space cannot be verified.
            logger.debug(
                "Embedding cache entry for model %s not trusted (dimension unknown)", model
            )

    vectors = _validate_embedding_vectors(await _dispatch_embed([text]), expected_count=1)
    record_known_embed_dimension(cache_namespace, len(vectors[0]))
    record_known_embed_dimension(_embed_cache_namespace(), len(vectors[0]))
    vector = vectors[0]
    await embedding_cache.put(cache_namespace, text, vector)
    return vector


async def embed_chunks(chunks: list[TextChunk], batch_size: int = 32) -> list[EmbeddedChunk]:
    """Embed multiple text chunks in batches with per-chunk caching.

    Args:
        chunks: List of text chunks to embed.
        batch_size: Number of texts to embed per API call.

    Returns:
        List of embedded chunks with vectors.
    """
    if not chunks:
        return []
    model = _embed_model_name()
    cache_namespace = await _space_namespace()
    results: list[EmbeddedChunk] = [None] * len(chunks)  # type: ignore[list-item]

    # First pass: check cache for each chunk
    uncached_indices: list[int] = []
    for idx, chunk in enumerate(chunks):
        cached = await embedding_cache.get(cache_namespace, chunk.text)
        if cached is not None:
            known = known_embed_dimension(cache_namespace)
            if known is not None:
                try:
                    # Cache entries are part of the shared vector space too.  Do
                    # not let a stale/corrupt value bypass the same cardinality,
                    # numeric, and dimensional validation used for provider data —
                    # dimension is checked against the engine's known dimension
                    # for this model, never inferred from the entry itself.
                    results[idx] = EmbeddedChunk(
                        chunk=chunk,
                        vector=_validate_embedding_vectors(
                            [cached], expected_count=1, expected_dimension=known
                        )[0],
                    )
                    continue
                except Exception:
                    logger.warning(
                        "Ignoring malformed or stale-dimension embedding cache entry for model %s",
                        model,
                    )
            else:
                logger.debug(
                    "Embedding cache entry for model %s not trusted (dimension unknown)", model
                )
        uncached_indices.append(idx)

    if uncached_indices:
        logger.debug(
            "Embedding cache: %d hits, %d misses",
            len(chunks) - len(uncached_indices),
            len(uncached_indices),
        )

    # Second pass: batch-embed uncached chunks
    for batch_start in range(0, len(uncached_indices), batch_size):
        batch_indices = uncached_indices[batch_start : batch_start + batch_size]
        batch_chunks = [chunks[i] for i in batch_indices]
        texts = [c.text for c in batch_chunks]

        vectors = _validate_embedding_vectors(
            await _dispatch_embed(texts), expected_count=len(texts)
        )
        record_known_embed_dimension(cache_namespace, len(vectors[0]))
        record_known_embed_dimension(_embed_cache_namespace(), len(vectors[0]))

        for i, (chunk, vector) in enumerate(zip(batch_chunks, vectors)):
            original_idx = batch_indices[i]
            results[original_idx] = EmbeddedChunk(chunk=chunk, vector=vector)
            await embedding_cache.put(cache_namespace, chunk.text, vector)

    return results


async def ensure_embed_model() -> None:
    """Provision the active profile through Pi authority for every engine."""
    from app.core.pi_runtime.embedding_profile import get_active_embedding_profile
    from app.core.pi_runtime.embeddings_gateway import EmbeddingsGateway
    from app.core.pi_runtime.model_manager_provisioning import ensure_endpoint_model

    profile = get_active_embedding_profile()
    gateway = EmbeddingsGateway(profile=profile)
    manager = gateway.manager()
    await manager.ensure_db_projection()
    endpoint = manager.resolve_embed(profile.model_id, endpoint_id=profile.endpoint_id)
    provisioned = await ensure_endpoint_model(endpoint, profile.model_id)
    if endpoint.kind == "local" and not provisioned:
        from app.core.pi_runtime.endpoints import PiEndpointResolutionError

        raise PiEndpointResolutionError(f"embedding_model_provision_failed:{endpoint.endpoint_id}")
