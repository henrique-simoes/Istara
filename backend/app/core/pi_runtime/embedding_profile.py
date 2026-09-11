"""Versioned, persisted embedding identity owned by Pi Model Management."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.embedding_profile import EmbeddingProfile


class EmbeddingProfileError(RuntimeError):
    """The persisted embedding authority is missing or internally inconsistent."""


@dataclass(frozen=True)
class ActiveEmbeddingProfile:
    """Immutable runtime projection of the one active profile version."""

    profile_id: str
    version: int
    model_id: str
    endpoint_id: str
    transport: str
    dimension: int
    dtype: str
    normalization: str
    cache_namespace: str
    health_status: str
    migration_source: str


_active_profile: ActiveEmbeddingProfile | None = None


def _legacy_bootstrap_snapshot() -> ActiveEmbeddingProfile:
    """Capture the effective pre-migration vector identity exactly once."""
    provider = str(settings.llm_provider or "ollama").strip().lower()
    if provider == "lmstudio":
        model_id = settings.lmstudio_embed_model
        endpoint_id = "pi-local-lmstudio"
    else:
        provider = "ollama"
        model_id = settings.ollama_embed_model
        endpoint_id = "pi-local-ollama"
    return ActiveEmbeddingProfile(
        profile_id="default",
        version=1,
        model_id=model_id,
        endpoint_id=endpoint_id,
        transport="pi_http",
        dimension=0,
        dtype="float",
        normalization="provider_native",
        # Preserve the existing cache keys during the additive bootstrap.
        cache_namespace=model_id,
        health_status="unknown",
        migration_source=f"legacy:{provider}",
    )


def _snapshot(row: EmbeddingProfile) -> ActiveEmbeddingProfile:
    return ActiveEmbeddingProfile(
        profile_id=row.profile_id,
        version=row.version,
        model_id=row.model_id,
        endpoint_id=row.endpoint_id,
        transport=row.transport,
        dimension=row.dimension,
        dtype=row.dtype,
        normalization=row.normalization,
        cache_namespace=row.cache_namespace,
        health_status=row.health_status,
        migration_source=row.migration_source,
    )


async def bootstrap_embedding_profile(db: AsyncSession) -> ActiveEmbeddingProfile:
    """Load the sole active profile, or persist the legacy identity as v1.

    This is an additive migration: it never changes the effective model,
    endpoint, cache namespace, or stored vectors. After the first row exists,
    classical provider settings are migration provenance only and cannot
    influence subsequent process starts.
    """
    global _active_profile

    rows = list(
        (
            await db.execute(
                select(EmbeddingProfile)
                .where(EmbeddingProfile.is_active.is_(True))
                .order_by(EmbeddingProfile.version.desc())
            )
        )
        .scalars()
        .all()
    )
    if len(rows) > 1:
        raise EmbeddingProfileError("multiple_active_embedding_profiles")
    if rows:
        _active_profile = _snapshot(rows[0])
        return _active_profile

    candidate = _active_profile or _legacy_bootstrap_snapshot()
    row = EmbeddingProfile(
        id=str(uuid.uuid4()),
        profile_id=candidate.profile_id,
        version=candidate.version,
        is_active=True,
        model_id=candidate.model_id,
        endpoint_id=candidate.endpoint_id,
        transport=candidate.transport,
        dimension=candidate.dimension,
        dtype=candidate.dtype,
        normalization=candidate.normalization,
        cache_namespace=candidate.cache_namespace,
        health_status=candidate.health_status,
        migration_source=candidate.migration_source,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        # Multiple application workers may bootstrap the same fresh database.
        # The partial unique index elects one active row; every loser reloads
        # that winner rather than manufacturing a second authority.
        await db.rollback()
        winner = await db.scalar(
            select(EmbeddingProfile).where(EmbeddingProfile.is_active.is_(True))
        )
        if winner is None:
            raise
        _active_profile = _snapshot(winner)
        return _active_profile
    await db.refresh(row)
    _active_profile = _snapshot(row)
    return _active_profile


def get_active_embedding_profile() -> ActiveEmbeddingProfile:
    """Return the process-pinned profile.

    Proper application startup persists/loads the row before any model work.
    The compatibility snapshot keeps isolated library/test callers stable and
    freezes on first access rather than following later classical setting
    mutations.
    """
    global _active_profile
    if _active_profile is None:
        _active_profile = _legacy_bootstrap_snapshot()
    return _active_profile


def public_embedding_profile() -> dict[str, str | int]:
    """Return non-secret identity metadata safe for API and UI disclosure."""
    profile = get_active_embedding_profile()
    return {
        "profile_id": profile.profile_id,
        "version": profile.version,
        "model_id": profile.model_id,
        "endpoint_id": profile.endpoint_id,
        "dimension": profile.dimension,
        "dtype": profile.dtype,
        "normalization": profile.normalization,
        "health_status": profile.health_status,
    }


def reset_embedding_profile_cache() -> None:
    """Clear only the in-process projection (tests and explicit restart simulation)."""
    global _active_profile
    _active_profile = None
