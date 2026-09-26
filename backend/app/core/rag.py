"""RAG pipeline — retrieve relevant context and augment LLM prompts."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import lancedb

from app.config import settings
from app.core.content_guard import ContentGuard, neutralize_boundary_markup
from app.core.embeddings import EmbeddedChunk, TextChunk, embed_chunks, embed_text
from app.core.keyword_index import KeywordIndex
from app.core.pi_runtime.embedding_profile import get_active_embedding_profile

_guard = ContentGuard()

logger = logging.getLogger(__name__)

RAG_RESEARCH_SPINE_NOTICE = (
    "<promotion_gate>"
    "Hybrid RAG retrieves exact supporting context and source passages. "
    "Retrieved chunks are not accepted Atomic Research artifacts or report "
    "evidence by themselves. Any finding, recommendation, design decision, "
    "task, or report must still pass source evidence-unit extraction, "
    "independent coding, reliability/reconciliation, human-approved Done-task "
    "gating, and report gates."
    "</promotion_gate>"
)


# Source evidence and LLM-derived text live in separate indices. Skill artifacts and agent notes
# are model output: useful to recall explicitly, never source evidence, and never able to confirm a
# claim (F5). Rows written by builds before the split carry these source prefixes in the source
# index and are excluded from evidence retrieval.
SOURCE_TABLE = "chunks"
DERIVED_TABLE = "derived_chunks"
DERIVED_NAMESPACE = "derived"
LEGACY_DERIVED_SOURCE_PREFIXES = ("agent:", "skill:")


def is_derived_source(source: str) -> bool:
    return str(source or "").startswith(LEGACY_DERIVED_SOURCE_PREFIXES)


def _sql_literal(value: str) -> str:
    return str(value).replace("'", "''")


# The fields that define a vector space; a store bound under one never serves another.
_VECTOR_IDENTITY_FIELDS = (
    "profile_id",
    "version",
    "model_id",
    "cache_namespace",
    "dimension",
    "dtype",
    "normalization",
    "prompt_scheme",
)


class VectorProfileMismatchError(RuntimeError):
    """The project index belongs to a different embedding profile version."""


@dataclass
class RetrievalResult:
    """A single retrieval result from the vector store."""

    text: str
    source: str
    page: int | None
    score: float
    agent_id: str = ""
    created_at: float = 0.0
    confidence: float = 1.0
    evidence_unit_id: str = ""
    source_document_id: str = ""
    start_offset: int | None = None
    end_offset: int | None = None
    codebook_version_id: str = ""
    coding_run_id: str = ""
    review_status: str = ""
    reliability_status: str = ""
    retrieval_mode: str = "hybrid"
    provenance_key: str = ""


@dataclass
class RAGContext:
    """Augmented context for an LLM prompt."""

    query: str
    retrieved: list[RetrievalResult]
    context_text: str

    @property
    def has_context(self) -> bool:
        return len(self.retrieved) > 0


class VectorStore:
    """LanceDB-backed vector store for a project."""

    def __init__(
        self, project_id: str, *, table_name: str = SOURCE_TABLE, root: Path | None = None
    ) -> None:
        """``table_name`` selects the source (``chunks``) or derived (``derived_chunks``) index;
        ``root`` points a sandbox store (retrieval evaluation) away from the project's real one."""
        self.project_id = project_id
        db_path = Path(root if root is not None else settings.lance_db_path) / project_id
        db_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(db_path))
        self.table_name = table_name
        self._profile_manifest = db_path / ".embedding-profile.json"
        self.keyword_namespace = DERIVED_NAMESPACE if table_name == DERIVED_TABLE else ""
        self.keyword_root = Path(root) / "keyword_index" if root is not None else None

    def keyword_index(self) -> KeywordIndex:
        """The BM25 index paired with this vector table (same namespace, same sandbox root)."""
        return KeywordIndex(
            self.project_id, namespace=self.keyword_namespace, root=self.keyword_root
        )

    def _active_profile_binding(self) -> dict[str, str | int]:
        profile = get_active_embedding_profile()
        return {
            "profile_id": profile.profile_id,
            "version": profile.version,
            "model_id": profile.model_id,
            "endpoint_id": profile.endpoint_id,
            "cache_namespace": profile.cache_namespace,
            "dimension": profile.dimension,
            "dtype": profile.dtype,
            "normalization": profile.normalization,
            "prompt_scheme": profile.prompt_scheme,
        }

    @staticmethod
    def _identity_differs(bound: dict, active: dict) -> bool:
        """Whether the manifest's vector space differs from the active profile's.

        Manifests written before prompt schemes existed hold vectors of raw text.
        """
        defaults = {"prompt_scheme": "raw"}
        return any(
            bound.get(field, defaults.get(field)) != active[field]
            for field in _VECTOR_IDENTITY_FIELDS
        )

    def _ensure_profile_binding(self, *, bind_fingerprint: bool = False) -> dict[str, str | int]:
        """Bind this project index once and reject silent vector-space drift.

        Existing indexes are safely adopted only into bootstrap version 1,
        whose identity is defined to equal the pre-migration vector space.
        Any later profile activation requires the governed re-index workflow
        to replace this manifest explicitly; ordinary reads/writes fail closed.
        """
        active = self._active_profile_binding()
        if not self._profile_manifest.exists():
            if self._ensure_table() and active["version"] != 1:
                raise VectorProfileMismatchError("unbound_vector_store_requires_v1_migration")
            try:
                with self._profile_manifest.open("x", encoding="utf-8") as handle:
                    json.dump(active, handle, sort_keys=True)
                    handle.write("\n")
            except FileExistsError:
                pass
        try:
            bound = json.loads(self._profile_manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise VectorProfileMismatchError("invalid_vector_profile_manifest") from exc
        if self._identity_differs(bound, active):
            raise VectorProfileMismatchError("vector_profile_mismatch")
        self._check_fingerprint(bound, bind_if_missing=bind_fingerprint)
        return active

    def _check_fingerprint(self, bound: dict, *, bind_if_missing: bool) -> None:
        """Compare the serving model's probe fingerprint with the one this store was built with.

        The profile fields cannot tell two models apart when the name ("default") and dimension
        are equal (F11). A store records the fingerprint of the model that wrote its first
        vectors; any later write or read under another fingerprint fails closed. Stores bound
        before fingerprints existed adopt the current one on their next write.
        """
        from app.core.embeddings import known_embed_fingerprint

        current = known_embed_fingerprint(str(bound.get("cache_namespace") or "") or None)
        recorded = bound.get("fingerprint")
        if recorded:
            if current and current != recorded:
                raise VectorProfileMismatchError("embedding_fingerprint_mismatch")
            return
        if bind_if_missing and current:
            updated = {**bound, "fingerprint": current}
            tmp = self._profile_manifest.with_suffix(".tmp")
            tmp.write_text(json.dumps(updated, sort_keys=True) + "\n", encoding="utf-8")
            tmp.replace(self._profile_manifest)

    def check_profile_binding(self) -> None:
        """Read-only binding check for health reads: never creates a manifest.

        An unbound store (no manifest yet) passes; ``_ensure_profile_binding`` binds it on the
        first real read or write. A bound store with a different identity raises.
        """
        if not self._profile_manifest.exists():
            return
        try:
            bound = json.loads(self._profile_manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise VectorProfileMismatchError("invalid_vector_profile_manifest") from exc
        active = self._active_profile_binding()
        if self._identity_differs(bound, active):
            raise VectorProfileMismatchError("vector_profile_mismatch")
        self._check_fingerprint(bound, bind_if_missing=False)

    def _ensure_table(self) -> bool:
        """Check if the chunks table exists."""
        return self.table_name in self.db.list_tables().tables

    def _table_has_column(self, column: str) -> bool:
        """Check whether the existing table has *column*."""
        if not self._ensure_table():
            return False
        try:
            table = self.db.open_table(self.table_name)
            return column in self._table_columns(table)
        except Exception:
            return False

    def _table_columns(self, table=None) -> set[str]:
        """Return existing table columns, if a table schema can be read."""
        try:
            if table is None:
                if not self._ensure_table():
                    return set()
                table = self.db.open_table(self.table_name)
            return {field.name for field in table.schema}
        except Exception:
            return set()

    def _records_for_existing_schema(self, table, records: list[dict]) -> list[dict]:
        """Drop optional metadata fields unsupported by legacy LanceDB tables."""
        columns = self._table_columns(table)
        if not columns:
            return records

        missing_columns = sorted(set(records[0]) - columns)
        if missing_columns:
            logger.debug(
                "Vector store %s/%s lacks metadata columns %s; writing legacy-compatible rows",
                self.project_id,
                self.table_name,
                ", ".join(missing_columns),
            )

        return [
            {key: value for key, value in record.items() if key in columns} for record in records
        ]

    async def add_chunks(
        self,
        embedded_chunks: list[EmbeddedChunk],
        *,
        agent_id: str = "",
        confidence: float = 1.0,
    ) -> int:
        """Add embedded chunks to the vector store.

        Returns:
            Number of chunks added.
        """
        if not embedded_chunks:
            return 0

        profile = self._ensure_profile_binding(bind_fingerprint=True)
        now = time.time()
        records = []
        for ec in embedded_chunks:
            source = ec.chunk.source
            file_type = Path(source).suffix.lstrip(".") if source else ""
            chunk_type = getattr(ec.chunk, "chunk_type", "character")
            metadata = ec.chunk.metadata or {}
            records.append(
                {
                    "vector": ec.vector,
                    "text": ec.chunk.text,
                    "source": source,
                    "page": ec.chunk.page or 0,
                    "position": ec.chunk.position,
                    "agent_id": agent_id,
                    "file_type": file_type,
                    "chunk_type": chunk_type,
                    "created_at": now,
                    "confidence": confidence,
                    "embedding_profile_id": profile["profile_id"],
                    "embedding_profile_version": profile["version"],
                    "embedding_cache_namespace": profile["cache_namespace"],
                    "evidence_unit_id": str(metadata.get("evidence_unit_id", "")),
                    "source_document_id": str(metadata.get("source_document_id", "")),
                    "start_offset": metadata.get("start_offset")
                    if metadata.get("start_offset") is not None
                    else -1,
                    "end_offset": metadata.get("end_offset")
                    if metadata.get("end_offset") is not None
                    else -1,
                    "codebook_version_id": str(metadata.get("codebook_version_id", "")),
                    "coding_run_id": str(metadata.get("coding_run_id", "")),
                    "review_status": str(metadata.get("review_status", "")),
                    "reliability_status": str(metadata.get("reliability_status", "")),
                    "retrieval_mode": str(metadata.get("retrieval_mode", "hybrid")),
                    "provenance_key": _provenance_key(
                        text=ec.chunk.text,
                        source=source,
                        page=ec.chunk.page or 0,
                        evidence_unit_id=str(metadata.get("evidence_unit_id", "")),
                        start_offset=metadata.get("start_offset")
                        if metadata.get("start_offset") is not None
                        else None,
                        end_offset=metadata.get("end_offset")
                        if metadata.get("end_offset") is not None
                        else None,
                    ),
                }
            )

        if self._ensure_table():
            table = self.db.open_table(self.table_name)
            table.add(self._records_for_existing_schema(table, records))
        else:
            self.db.create_table(self.table_name, records)

        return len(records)

    def _filter_clauses(
        self,
        *,
        source_filter: str | None,
        file_type_filter: str | None,
        agent_id: str | None,
        exclude_source_prefixes: tuple[str, ...],
    ) -> list[str]:
        """LanceDB filter clauses for the given metadata, on columns this table has."""
        clauses: list[str] = []
        if source_filter and self._table_has_column("source"):
            clauses.append(f"source = '{_sql_literal(source_filter)}'")
        if file_type_filter and self._table_has_column("file_type"):
            clauses.append(f"file_type = '{_sql_literal(file_type_filter)}'")
        if agent_id is not None and self._table_has_column("agent_id"):
            clauses.append(f"agent_id = '{_sql_literal(agent_id)}'")
        if exclude_source_prefixes and self._table_has_column("source"):
            clauses.extend(
                f"source NOT LIKE '{_sql_literal(prefix)}%'" for prefix in exclude_source_prefixes
            )
        return clauses

    async def search(
        self,
        query_vector: list[float],
        top_k: int | None = None,
        score_threshold: float | None = None,
        *,
        source_filter: str | None = None,
        file_type_filter: str | None = None,
        agent_id: str | None = None,
        exclude_source_prefixes: tuple[str, ...] = (),
    ) -> list[RetrievalResult]:
        """Search for similar chunks.

        Args:
            query_vector: Query embedding vector.
            top_k: Number of results to return.
            score_threshold: Minimum similarity score.
            source_filter: Only return results from this source path.
            file_type_filter: Only return results with this file type extension.
            agent_id: Only return results produced by this agent.

        Returns:
            List of retrieval results sorted by relevance.
        """
        # ``None`` means "use the setting"; an explicit 0 is a real value (F17: ``or`` treated
        # a 0.0 threshold as unset and silently applied 0.3).
        k = top_k if top_k is not None else settings.rag_top_k
        threshold = score_threshold if score_threshold is not None else settings.rag_score_threshold

        if k <= 0 or not self._ensure_table():
            return []

        self._ensure_profile_binding()
        table = self.db.open_table(self.table_name)

        query_builder = table.search(query_vector).metric("cosine").limit(k)

        filter_clauses = self._filter_clauses(
            source_filter=source_filter,
            file_type_filter=file_type_filter,
            agent_id=agent_id,
            exclude_source_prefixes=exclude_source_prefixes,
        )
        if filter_clauses:
            try:
                # Pre-filter, so excluded rows cannot crowd the k nearest out of the result.
                query_builder = query_builder.where(" AND ".join(filter_clauses), prefilter=True)
            except Exception:
                # Old table schema may not support filter columns — fall back
                logger.debug("Metadata filter failed; falling back to unfiltered search")

        results = query_builder.to_pandas()

        retrieval_results = []
        for _, row in results.iterrows():
            score = 1 - row.get("_distance", 1.0)  # LanceDB returns distance, convert to similarity
            # Skip rows with null/empty text (corrupted or incomplete chunks)
            text_val = row.get("text")
            import pandas as pd

            if (
                text_val is None
                or (isinstance(text_val, float) and pd.isna(text_val))
                or str(text_val).strip() == ""
            ):
                continue
            if score >= threshold:

                def _optional_int(column: str) -> int | None:
                    if column not in row.index:
                        return None
                    value = row.get(column)
                    if value is None or (isinstance(value, float) and pd.isna(value)):
                        return None
                    parsed = int(value)
                    return parsed if parsed >= 0 else None

                retrieval_results.append(
                    RetrievalResult(
                        text=str(row["text"]),
                        source=str(row.get("source", "")),
                        page=int(row["page"]) if row["page"] else None,
                        score=score,
                        agent_id=str(row.get("agent_id", "")) if "agent_id" in row.index else "",
                        created_at=float(row.get("created_at", 0.0))
                        if "created_at" in row.index
                        else 0.0,
                        confidence=float(row.get("confidence", 1.0))
                        if "confidence" in row.index
                        else 1.0,
                        evidence_unit_id=str(row.get("evidence_unit_id", ""))
                        if "evidence_unit_id" in row.index
                        else "",
                        source_document_id=str(row.get("source_document_id", ""))
                        if "source_document_id" in row.index
                        else "",
                        start_offset=_optional_int("start_offset"),
                        end_offset=_optional_int("end_offset"),
                        codebook_version_id=str(row.get("codebook_version_id", ""))
                        if "codebook_version_id" in row.index
                        else "",
                        coding_run_id=str(row.get("coding_run_id", ""))
                        if "coding_run_id" in row.index
                        else "",
                        review_status=str(row.get("review_status", ""))
                        if "review_status" in row.index
                        else "",
                        reliability_status=str(row.get("reliability_status", ""))
                        if "reliability_status" in row.index
                        else "",
                        retrieval_mode=str(row.get("retrieval_mode", "hybrid"))
                        if "retrieval_mode" in row.index
                        else "hybrid",
                        provenance_key=str(row.get("provenance_key", ""))
                        if "provenance_key" in row.index
                        else "",
                    )
                )

        return retrieval_results

    async def delete_file_source(self, file_path: Path | str) -> None:
        """Delete every chunk ingested from ``file_path``, whichever spelling it was stored under.

        ``process_file`` stores ``chunk.source = str(original_path)`` -- the full path -- while the
        upload, reprocess and documents-sync routes deleted by ``file_path.name`` before
        re-ingesting. The exact-match delete never matched, so every reprocess or folder sync
        appended another complete copy of the file to BOTH indices, and the copies (distinct
        provenance keys that differ only by path) also crowded genuinely different evidence out of
        the fused top-k. Deleting both spellings stops the growth and cleans rows written under the
        legacy basename key.
        """
        path = Path(file_path)
        for key in dict.fromkeys((str(path), path.name)):
            await self.delete_by_source(key)

    async def delete_by_source(self, source: str) -> None:
        """Delete all chunks from a specific source file, from BOTH indices.

        The keyword index is independent of the vector table: a project ingested while
        embeddings were offline is keyword-only and has no vector table at all. Returning early
        when the vector table was missing skipped the keyword delete too, so re-ingesting in that
        degraded mode duplicated every chunk however the source key was spelled.
        """
        if self._ensure_table():
            # Quote-escape only: DataFusion string literals take backslashes literally, so doubling
            # them (the old code) made a Windows-style path never match its own rows (F17).
            safe_source = source.replace("'", "''")
            table = self.db.open_table(self.table_name)
            table.delete(f"source = '{safe_source}'")

        # Also remove from the keyword index
        try:
            kw_index = self.keyword_index()
            await kw_index.delete_by_source(source)
        except Exception as e:
            logger.warning(f"Keyword index delete failed during source delete: {e}")

    async def count(self) -> int:
        """Count total chunks in the store."""
        if not self._ensure_table():
            return 0
        table = self.db.open_table(self.table_name)
        return table.count_rows()


# ---------------------------------------------------------------------------
# Hybrid search helpers
# ---------------------------------------------------------------------------


def _provenance_key(
    *,
    text: str,
    source: str,
    page: int | None,
    evidence_unit_id: str = "",
    start_offset: int | None = None,
    end_offset: int | None = None,
) -> str:
    """Return a dedupe key that preserves evidence provenance.

    Two participants may say the same sentence, and those are different
    research evidence units. Dedupe must never collapse provenance down to
    chunk text alone.
    """
    if evidence_unit_id:
        # Two chunks can share a primary evidence unit (a long speaker turn split in two, or the
        # chunk overlap). The span keeps them distinct; the same chunk in both indices still
        # fuses because both rows carry the same span.
        if start_offset is not None or end_offset is not None:
            return f"evidence:{evidence_unit_id}:{start_offset or 0}:{end_offset or 0}"
        return f"evidence:{evidence_unit_id}"
    fingerprint = sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{source}:{page or 0}:{start_offset or ''}:{end_offset or ''}:{fingerprint}"


def retrieval_result_key(result: RetrievalResult) -> str:
    if result.provenance_key:
        return result.provenance_key
    return _provenance_key(
        text=result.text,
        source=result.source,
        page=result.page,
        evidence_unit_id=result.evidence_unit_id,
        start_offset=result.start_offset,
        end_offset=result.end_offset,
    )


def _keyword_retrieval_result(kr, *, score: float = 0.0) -> RetrievalResult:
    """Convert a BM25 hit into a provenance-carrying retrieval result."""

    def _optional_int(value) -> int | None:
        if value in (None, ""):
            return None
        try:
            parsed = int(value)
            return parsed if parsed >= 0 else None
        except (TypeError, ValueError):
            return None

    provenance_key = kr.provenance_key or _provenance_key(
        text=kr.text,
        source=kr.source,
        page=kr.page if kr.page else None,
        evidence_unit_id=kr.evidence_unit_id,
        start_offset=_optional_int(kr.start_offset),
        end_offset=_optional_int(kr.end_offset),
    )
    review_status = kr.review_status or ("non_promotional" if not kr.evidence_unit_id else "")
    reliability_status = kr.reliability_status or (
        "missing_provenance" if not kr.evidence_unit_id else ""
    )
    return RetrievalResult(
        text=kr.text,
        source=kr.source,
        page=kr.page if kr.page else None,
        score=score,
        evidence_unit_id=kr.evidence_unit_id,
        source_document_id=kr.source_document_id,
        start_offset=_optional_int(kr.start_offset),
        end_offset=_optional_int(kr.end_offset),
        codebook_version_id=kr.codebook_version_id,
        coding_run_id=kr.coding_run_id,
        review_status=review_status,
        reliability_status=reliability_status,
        retrieval_mode="keyword",
        provenance_key=provenance_key,
    )


def provenance_share(results: list[RetrievalResult]) -> float | None:
    """Share of retrieved chunks that carry an ``evidence_unit_id`` (measurement 5)."""
    if not results:
        return None
    return sum(1 for result in results if result.evidence_unit_id) / len(results)


async def _record_retrieval_telemetry(
    *,
    project_id: str,
    retrieval_mode: str,
    results: list[RetrievalResult],
    degraded_reason: str | None = None,
) -> None:
    """Record a content-free retrieval event for research-validity audits.

    ``quality_score`` carries the provenance share of the returned chunks: the fraction that can
    be traced to a source evidence unit. It is a count over handles, never content.
    """
    try:
        from app.core.telemetry import telemetry_recorder

        representative = next(
            (
                result
                for result in results
                if result.evidence_unit_id or result.coding_run_id or result.codebook_version_id
            ),
            results[0] if results else None,
        )
        status = "success" if results and not degraded_reason else "degraded"
        await telemetry_recorder.record_research_validity_event(
            operation="retrieval.hybrid",
            project_id=project_id,
            status=status,
            retrieval_mode=retrieval_mode,
            evidence_unit_id=representative.evidence_unit_id if representative else "",
            coding_run_id=representative.coding_run_id if representative else "",
            codebook_version_id=representative.codebook_version_id if representative else "",
            quality_score=provenance_share(results),
            error_type="retrieval_fallback" if degraded_reason else None,
            error_message=degraded_reason[:160] if degraded_reason else None,
        )
    except Exception as e:
        logger.debug("Retrieval telemetry skipped: %s", e)


async def hybrid_search(
    project_id: str,
    query: str,
    query_vector: list[float],
    top_k: int | None = None,
    *,
    source_filter: str | None = None,
    file_type_filter: str | None = None,
    agent_id: str | None = None,
    store: VectorStore | None = None,
    vector_weight: float | None = None,
    keyword_weight: float | None = None,
    rrf_k: int | None = None,
) -> list[RetrievalResult]:
    """Run hybrid search combining vector similarity and BM25 keyword ranking.

    Uses weighted Reciprocal Rank Fusion (RRF, Cormack et al. 2009) to merge the two lists.
    The source store excludes rows derived from model output (see ``is_derived_source``).
    ``store``, the weights and ``rrf_k`` default to the project's source index and settings;
    retrieval evaluation passes a sandbox store and explicit candidate values so a measurement
    never changes the process-wide configuration other projects read.
    """
    k = top_k if top_k is not None else settings.rag_top_k
    fusion_k = rrf_k if rrf_k is not None else settings.rag_rrf_k

    store = store or VectorStore(project_id)
    kw_index = store.keyword_index()
    exclude = LEGACY_DERIVED_SOURCE_PREFIXES if store.table_name == SOURCE_TABLE else ()

    # Run both searches
    vector_results = await store.search(
        query_vector,
        top_k=k * 2,  # fetch more to improve fusion quality
        source_filter=source_filter,
        file_type_filter=file_type_filter,
        agent_id=agent_id,
        exclude_source_prefixes=exclude,
    )
    keyword_results = _filter_keyword_results(
        await kw_index.search(query, top_k=k * 2),
        source_filter=source_filter,
        file_type_filter=file_type_filter,
        exclude_source_prefixes=exclude,
    )
    if agent_id is not None:
        # The keyword index does not currently store agent ownership; avoid
        # mixing unscoped keyword hits into an agent-scoped retrieval.
        keyword_results = []

    vw = settings.rag_hybrid_vector_weight if vector_weight is None else vector_weight
    kw = settings.rag_hybrid_keyword_weight if keyword_weight is None else keyword_weight

    # Build RRF scores keyed by provenance, not text. Qualitative evidence can
    # repeat verbatim across documents/participants and still remain distinct.
    scores: dict[str, dict] = {}

    for rank, r in enumerate(vector_results, 1):
        key = retrieval_result_key(r)
        if key not in scores:
            scores[key] = {"result": r, "score": 0.0}
        scores[key]["score"] += vw * (1.0 / (fusion_k + rank))

    for rank, kr in enumerate(keyword_results, 1):
        keyword_result = _keyword_retrieval_result(kr)
        key = retrieval_result_key(keyword_result)
        if key not in scores:
            scores[key] = {
                "result": keyword_result,
                "score": 0.0,
            }
        scores[key]["score"] += kw * (1.0 / (fusion_k + rank))

    # Sort by fused score descending and take top_k
    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)[:k]

    results = []
    for item in ranked:
        r = item["result"]
        r.score = item["score"]
        results.append(r)

    return results


def _filter_keyword_results(
    keyword_results: list,
    *,
    source_filter: str | None = None,
    file_type_filter: str | None = None,
    exclude_source_prefixes: tuple[str, ...] = (),
) -> list:
    if source_filter:
        keyword_results = [kr for kr in keyword_results if kr.source == source_filter]
    if file_type_filter:
        normalized_file_type = file_type_filter.lstrip(".").lower()
        keyword_results = [
            kr
            for kr in keyword_results
            if Path(kr.source).suffix.lstrip(".").lower() == normalized_file_type
        ]
    if exclude_source_prefixes:
        keyword_results = [
            kr for kr in keyword_results if not str(kr.source).startswith(exclude_source_prefixes)
        ]
    return keyword_results


async def _keyword_only_search(
    project_id: str,
    query: str,
    top_k: int | None = None,
    *,
    source_filter: str | None = None,
    file_type_filter: str | None = None,
    agent_id: str | None = None,
) -> list[RetrievalResult]:
    """Fallback retrieval path for installs where embeddings are unavailable."""
    if agent_id is not None:
        # The keyword index does not currently store agent ownership. Returning
        # empty results keeps agent-scoped retrieval from leaking unscoped hits.
        return []

    k = top_k if top_k is not None else settings.rag_top_k
    keyword_results = _filter_keyword_results(
        await KeywordIndex(project_id).search(query, top_k=k * 2),
        source_filter=source_filter,
        file_type_filter=file_type_filter,
        exclude_source_prefixes=LEGACY_DERIVED_SOURCE_PREFIXES,
    )

    results: list[RetrievalResult] = []
    for rank, kr in enumerate(keyword_results[:k], 1):
        results.append(_keyword_retrieval_result(kr, score=1.0 / rank))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def ingest_chunks(
    project_id: str,
    chunks: list[TextChunk],
    *,
    agent_id: str = "",
) -> int:
    """Embed and store text chunks for a project.

    Args:
        project_id: Project identifier.
        chunks: Text chunks to embed and store.
        agent_id: Optional agent identifier (for agent-generated content).

    Returns:
        Number of chunks ingested.
    """
    if not chunks:
        return 0

    # Always preserve keyword searchability. Vector embeddings depend on local
    # or network compute and should not make document ingestion fail outright.
    try:
        kw_index = KeywordIndex(project_id)
        await kw_index.add_chunks(chunks)
    except Exception as e:
        logger.warning(f"Keyword indexing failed (non-fatal): {e}")

    try:
        embedded = await embed_chunks(chunks)
        confidence = 0.8 if agent_id else 1.0
        store = VectorStore(project_id)
        return await store.add_chunks(embedded, agent_id=agent_id, confidence=confidence)
    except Exception as e:
        logger.warning(
            "Vector ingestion unavailable for project %s; keyword index remains searchable: %s",
            project_id,
            e,
        )
        return 0


async def ingest_derived_chunks(
    project_id: str,
    chunks: list[TextChunk],
    *,
    agent_id: str,
    kind: str,
    replace_source: bool = True,
) -> int:
    """Index LLM-written text (skill artifacts, agent notes) in the DERIVED index only.

    Derived text is model output. It is kept apart from source evidence so it can never confirm
    a claim, never outranks a raw source span, and is only recalled through
    ``retrieve_derived_context``. Rows carry the writing agent in ``agent_id`` so an agent's notes
    are scoped exactly (``a1`` never matches ``a10``). ``replace_source`` deletes earlier rows from
    the same source first, so reruns do not duplicate.
    """
    if not chunks:
        return 0
    for chunk in chunks:
        chunk.metadata = {
            **(chunk.metadata or {}),
            "derived_kind": kind,
            "review_status": "derived_provisional",
            "reliability_status": "not_source_evidence",
        }
    store = VectorStore(project_id, table_name=DERIVED_TABLE)
    if replace_source:
        for source in dict.fromkeys(chunk.source for chunk in chunks):
            await store.delete_by_source(source)
    try:
        await store.keyword_index().add_chunks(chunks)
    except Exception as e:
        logger.warning(f"Derived keyword indexing failed (non-fatal): {e}")
    try:
        embedded = await embed_chunks(chunks)
        return await store.add_chunks(embedded, agent_id=agent_id, confidence=0.5)
    except Exception as e:
        logger.warning("Derived vector ingestion unavailable for project %s: %s", project_id, e)
        return 0


async def retrieve_derived_context(
    project_id: str,
    query: str,
    top_k: int = 5,
    *,
    agent_id: str | None = None,
) -> list[RetrievalResult]:
    """Explicit recall over derived text; results are labelled as model output, not evidence."""
    store = VectorStore(project_id, table_name=DERIVED_TABLE)
    try:
        query_vector = await embed_text(query)
        results = await hybrid_search(
            project_id, query, query_vector, top_k=top_k, agent_id=agent_id, store=store
        )
    except Exception as e:
        logger.debug("Derived retrieval degraded to keyword: %s", e)
        if agent_id is not None:
            return []
        keyword = await store.keyword_index().search(query, top_k=top_k)
        results = [
            _keyword_retrieval_result(kr, score=1.0 / rank)
            for rank, kr in enumerate(keyword[:top_k], 1)
        ]
    for result in results:
        result.review_status = "derived_provisional"
        result.reliability_status = "not_source_evidence"
    return results


async def retrieve_context(
    project_id: str,
    query: str,
    top_k: int | None = None,
    *,
    source_filter: str | None = None,
    file_type_filter: str | None = None,
    agent_id: str | None = None,
) -> RAGContext:
    """Retrieve relevant context for a query.

    Args:
        project_id: Project identifier.
        query: The user's query.
        top_k: Number of results.

    Returns:
        RAGContext with retrieved documents and formatted context.
    """
    degraded_reason: str | None = None
    retrieval_mode = "hybrid"
    try:
        query_vector = await embed_text(query)
        results = await hybrid_search(
            project_id,
            query,
            query_vector,
            top_k=top_k,
            source_filter=source_filter,
            file_type_filter=file_type_filter,
            agent_id=agent_id,
        )
    except Exception as e:
        degraded_reason = str(e)
        retrieval_mode = "keyword"
        logger.warning(
            "Embedding retrieval unavailable for project %s; falling back to keyword search: %s",
            project_id,
            e,
        )
        results = await _keyword_only_search(
            project_id,
            query,
            top_k=top_k,
            source_filter=source_filter,
            file_type_filter=file_type_filter,
            agent_id=agent_id,
        )
    if (
        retrieval_mode == "hybrid"
        and results
        and all(r.retrieval_mode == "keyword" for r in results)
    ):
        # Report the property, not the step: embedding succeeded, but every hit came from BM25
        # (for example a project with no vector table yet).
        retrieval_mode = "keyword"
    await _record_retrieval_telemetry(
        project_id=project_id,
        retrieval_mode=retrieval_mode,
        results=results,
        degraded_reason=degraded_reason,
    )

    # Format context for the LLM — wrap each chunk in untrusted delimiters
    context_parts = [format_context_part(i, r) for i, r in enumerate(results, 1)]

    context_text = "\n\n".join(context_parts) if context_parts else ""

    return RAGContext(
        query=query,
        retrieved=results,
        context_text=context_text,
    )


def format_context_part(index: int, result: RetrievalResult, text: str | None = None) -> str:
    """One retrieved chunk as the model sees it: a source label, then the untrusted wrapper.

    ``index`` is the chunk's rank in the prompt, which follows retrieval order.

    The ONE formatter for retrieved evidence in a prompt. `retrieve_context` and the compressed
    chat/interface path both use it, so a chunk cannot reach the model unlabelled or unwrapped on
    one path while the other path labels and wraps it.
    """
    source_info = f"[Source: {result.source}"
    if result.page:
        source_info += f", page {result.page}"
    # The rank, never the fused RRF value: RRF is ordinal (Cormack et al. 2009) and the best
    # possible chunk fuses to about 0.016, which a model reads as "irrelevant" (F12).
    source_info += f", rank {index}]"
    body = result.text if text is None else text
    wrapped = _guard.wrap_untrusted(body, source=result.source)
    return f"--- Document {index} {source_info} ---\n{wrapped}"


async def build_compressed_rag_context(
    project_id: str,
    rag_result: RAGContext | None,
    query: str,
    max_tokens: int,
    surplus_level: str,
) -> tuple[str, list[RetrievalResult]]:
    """Compress retrieved chunks to the budget, then label and wrap the ones that were kept.

    Returns the prompt text and the results it actually contains, in prompt order. Chat and
    Interfaces used to join raw ``r.text`` with ``---``: no source labels (so the "cite your
    sources" instruction could not be followed), no untrusted-content wrapper, and the UI's
    source list named every retrieved chunk even when the budget cut had dropped it from the prompt.

    The whole returned block, labels and wrappers included, fits ``max_tokens`` (4 characters per
    token). The label and wrapper cost is measured per result rather than assumed.
    """
    from app.core.prompt_compressor import (
        compress_rag_chunks_indexed,
        record_protected_compression_telemetry,
    )

    if not rag_result or not rag_result.retrieved:
        return "", []
    retrieved = [r for r in rag_result.retrieved if r.text]
    # Retrieved text is document content, never a protected methodology block. Neutralising its
    # wrapper/protected-block markup BEFORE compression stops an uploaded file that contains
    # ``<instructions>…</instructions>`` from being pinned ahead of real evidence and exempted from
    # the RAG budget (F14). Blocks the services inject keep their protection.
    chunk_texts = [neutralize_boundary_markup(r.text) for r in retrieved]
    max_chars = max(max_tokens, 0) * 4
    overheads = [len(format_context_part(i, r, "")) + 2 for i, r in enumerate(retrieved, 1)]
    reserve_chars = sum(overheads[: min(len(retrieved), 5)])
    budget_chars = max(max_chars - reserve_chars, max_chars // 2)
    indexed, _ = compress_rag_chunks_indexed(chunk_texts, query, budget_chars // 4, surplus_level)
    await record_protected_compression_telemetry(
        project_id=project_id,
        original_chunks=chunk_texts,
        compressed_chunks=[text for _, text in indexed],
    )
    included: list[RetrievalResult] = []
    parts: list[str] = []
    used = 0
    for index, text in indexed:
        part = format_context_part(len(parts) + 1, retrieved[index], text)
        cost = len(part) + (2 if parts else 0)
        if used + cost > max_chars:
            break
        parts.append(part)
        included.append(retrieved[index])
        used += cost
    return "\n\n".join(parts), included


def build_augmented_prompt(
    query: str,
    rag_context: RAGContext | str,
    project_context: str | None = None,
    company_context: str | None = None,
) -> str:
    """Build the full augmented prompt with context layers.

    Args:
        query: The user's question.
        rag_context: Retrieved context from the vector store, or a pre-compressed
            string (used when budget-aware compression has already been applied).
        project_context: Project-level context (research brief, goals, etc.).
        company_context: Company-level context (product, culture, etc.).

    Returns:
        Formatted system prompt with all context layers.
    """
    parts = [
        "You are Istara, an expert UX Research assistant. "
        "You help researchers organize, analyze, and synthesize research findings. "
        "Always cite your sources when referencing specific documents. "
        "If you're uncertain, say so — never fabricate evidence.",
        RAG_RESEARCH_SPINE_NOTICE,
    ]

    if company_context:
        wrapped_company = _guard.wrap_untrusted(company_context, source="company_context")
        parts.append(f"\n## Company Context\n{wrapped_company}")

    if project_context:
        wrapped_project = _guard.wrap_untrusted(project_context, source="project_context")
        parts.append(f"\n## Project Context\n{wrapped_project}")

    # Support both RAGContext objects and pre-compressed strings
    has_rag = False
    rag_text = ""
    if isinstance(rag_context, str):
        has_rag = bool(rag_context.strip())
        rag_text = rag_context
    elif isinstance(rag_context, RAGContext):
        has_rag = rag_context.has_context
        rag_text = rag_context.context_text

    if has_rag:
        parts.append(
            f"\n## Relevant Documents\n"
            f"The following documents were retrieved from the project knowledge base. "
            f"Use them only as supporting source context; do not present them as "
            f"accepted research unless the evidence chain says they passed the "
            f"Research Spine.\n\n"
            f"{rag_text}"
        )

    return "\n".join(parts)
