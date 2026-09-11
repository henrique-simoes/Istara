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

    mismatches = []
    profile_mismatches = []
    for pid in projects:
        try:
            import lancedb

            from app.core.rag import VectorProfileMismatchError, VectorStore

            db_path = str(data_dir / pid)
            VectorStore(pid)._ensure_profile_binding()
            db = lancedb.connect(db_path)
            if "chunks" not in db.table_names():
                continue
            table = db.open_table("chunks")
            df = table.to_pandas()
            if len(df) == 0:
                continue
            stored_dim = len(df.iloc[0]["vector"])
            if stored_dim != model_dim:
                mismatches.append(
                    {"project_id": pid, "stored_dim": stored_dim, "model_dim": model_dim}
                )
        except VectorProfileMismatchError as e:
            profile_mismatches.append({"project_id": pid, "error": str(e)})
        except Exception as e:
            logger.warning(f"Dimension check failed for project {pid}: {e}")

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
