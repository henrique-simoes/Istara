"""Vector store health checks -- dimension validation and diagnostics."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import settings
from app.core.embedding_validation import validate_embedding_vectors

logger = logging.getLogger(__name__)


async def check_embedding_dimensions(
    project_id: str | None = None,
    *,
    engine: str | None = None,
    model: str | None = None,
    check_stored: bool = True,
) -> dict:
    """Verify stored vector dimensions match current embedding model output."""
    if engine is None:
        from app.core.embeddings import embed_text

        async def embed_probe():
            return [await embed_text("dimension validation check")]
    else:
        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        async def embed_probe():
            vectors = await agentic.embed(
                texts=["dimension validation check"],
                params=TurnParams(model=model),
                engine=engine,
                agent_id="istara-startup",
                spine_phase="startup.vector_health",
            )
            return validate_embedding_vectors(vectors, expected_count=1)

    try:
        test_vectors = validate_embedding_vectors(await embed_probe(), expected_count=1)
        model_dim = len(test_vectors[0])
        if engine is None:
            await _refresh_fingerprint()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Cannot get model dimensions: {e}",
            "stored_dim": 0,
            "model_dim": 0,
        }

    # Seed the engine's known embedding dimension for the probed model so
    # cache hits are validated against a probe-established vector space (the
    # engine's dimension), never inferred from the cache entry itself.
    if model:
        try:
            from app.core.embeddings import record_known_embed_dimension

            record_known_embed_dimension(model, model_dim)
        except Exception:
            logger.debug("Could not record known embedding dimension", exc_info=True)

    result = {
        "status": "ok",
        "message": "Embedding probe dimensions are valid",
        "stored_dim": 0,
        "model_dim": model_dim,
        "model": model,
        "engine": engine,
    }
    if not check_stored:
        return result

    # Check a specific project or scan all
    data_dir = Path(settings.lance_db_path)
    if not data_dir.exists():
        return {
            "status": "empty",
            "message": "No vector stores found",
            "stored_dim": 0,
            "model_dim": model_dim,
        }

    projects = [project_id] if project_id else [d.name for d in data_dir.iterdir() if d.is_dir()]

    found: dict[str, list[dict]] = {"dimension": [], "profile": [], "fingerprint": []}
    for pid in projects:
        kind, row = _project_vector_state(data_dir, pid, model_dim)
        if kind in found:
            found[kind].append(row)
    mismatches = found["dimension"]
    profile_mismatches = found["profile"]
    fingerprint_mismatches = found["fingerprint"]

    if fingerprint_mismatches:
        return {
            "status": "fingerprint_mismatch",
            "message": (
                f"The embedding model serving now is not the one that built "
                f"{len(fingerprint_mismatches)} project index(es), although the dimension "
                "matches. A governed re-index is required."
            ),
            "fingerprint_mismatches": fingerprint_mismatches,
            "model_dim": model_dim,
            "stored_dim": 0,
        }

    if profile_mismatches:
        return {
            "status": "profile_mismatch",
            "message": (
                f"Embedding profile mismatch in {len(profile_mismatches)} project(s). "
                "A governed re-index is required."
            ),
            "profile_mismatches": profile_mismatches,
            "model_dim": model_dim,
            "stored_dim": 0,
        }

    if mismatches:
        return {
            "status": "mismatch",
            "message": (
                f"Dimension mismatch in {len(mismatches)} project(s). Reprocess files to fix."
            ),
            "mismatches": mismatches,
            "model_dim": model_dim,
            "stored_dim": mismatches[0]["stored_dim"] if mismatches else 0,
        }

    return {
        "status": "ok",
        "message": "All vector dimensions match",
        "stored_dim": model_dim,
        "model_dim": model_dim,
        "model": model,
        "engine": engine,
    }


async def _refresh_fingerprint() -> None:
    """Re-measure the serving model's identity (best effort).

    A same-dimension swap changes the fingerprint, not the dimension (F11). Without a fresh
    fingerprint the stores are still checked by profile and dimension.
    """
    from app.core.embeddings import ensure_embed_fingerprint

    try:
        await ensure_embed_fingerprint(force=True)
    except Exception as exc:
        logger.warning("Embedding fingerprint probe failed: %s", exc)


def _project_vector_state(data_dir: Path, pid: str, model_dim: int) -> tuple[str, dict | None]:
    """Classify one project's store: ``ok``, ``skip``, ``dimension``, ``profile``, ``fingerprint``.

    A health READ: it checks the binding without writing a manifest for an unbound store (F16),
    and reads the stored dimension from the schema instead of loading the table.
    """
    from app.core.rag import VectorProfileMismatchError, VectorStore

    try:
        import lancedb

        VectorStore(pid).check_profile_binding()
        db = lancedb.connect(str(data_dir / pid))
        if "chunks" not in db.table_names():
            return "skip", None
        table = db.open_table("chunks")
        if table.count_rows() == 0:
            return "skip", None
        stored_dim = int(getattr(table.schema.field("vector").type, "list_size", 0) or 0)
    except VectorProfileMismatchError as e:
        kind = "fingerprint" if str(e) == "embedding_fingerprint_mismatch" else "profile"
        return kind, {"project_id": pid, "error": str(e)}
    except Exception as e:
        logger.warning(f"Dimension check failed for project {pid}: {e}")
        return "skip", None
    if stored_dim != model_dim:
        return "dimension", {"project_id": pid, "stored_dim": stored_dim, "model_dim": model_dim}
    return "ok", None
