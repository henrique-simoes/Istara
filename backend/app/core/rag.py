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
from app.core.content_guard import ContentGuard
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

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        db_path = Path(settings.lance_db_path) / project_id
        db_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(db_path))
        self.table_name = "chunks"
        self._profile_manifest = db_path / ".embedding-profile.json"

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
        }

    def _ensure_profile_binding(self) -> dict[str, str | int]:
        """Bind this project index once and reject silent vector-space drift.

        Existing indexes are safely adopted only into bootstrap version 1,
        whose identity is defined to equal the pre-migration vector space.
        Any later profile activation requires the governed re-index workflow
        to replace this manifest explicitly; ordinary reads/writes fail closed.
        """
        active = self._active_profile_binding()
        if not self._profile_manifest.exists():
            if self._ensure_table() and active["version"] != 1:
                raise VectorProfileMismatchError(
                    "unbound_vector_store_requires_v1_migration"
                )
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
        identity_fields = (
            "profile_id",
            "version",
            "model_id",
            "cache_namespace",
            "dimension",
            "dtype",
            "normalization",
        )
        if any(bound.get(field) != active[field] for field in identity_fields):
            raise VectorProfileMismatchError("vector_profile_mismatch")
        return active

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
            {key: value for key, value in record.items() if key in columns}
            for record in records
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

        profile = self._ensure_profile_binding()
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

    async def search(
        self,
        query_vector: list[float],
        top_k: int | None = None,
        score_threshold: float | None = None,
        *,
        source_filter: str | None = None,
        file_type_filter: str | None = None,
        agent_id: str | None = None,
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
        k = top_k or settings.rag_top_k
        threshold = score_threshold or settings.rag_score_threshold

        if not self._ensure_table():
            return []

        self._ensure_profile_binding()
        table = self.db.open_table(self.table_name)

        query_builder = table.search(query_vector).metric("cosine").limit(k)

        # Build optional LanceDB filter from provided params
        filter_clauses: list[str] = []
        if source_filter and self._table_has_column("source"):
            safe = source_filter.replace("'", "''")
            filter_clauses.append(f"source = '{safe}'")
        if file_type_filter and self._table_has_column("file_type"):
            safe = file_type_filter.replace("'", "''")
            filter_clauses.append(f"file_type = '{safe}'")
        if agent_id is not None and self._table_has_column("agent_id"):
            safe = agent_id.replace("'", "''")
            filter_clauses.append(f"agent_id = '{safe}'")

        if filter_clauses:
            try:
                query_builder = query_builder.where(" AND ".join(filter_clauses))
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

    async def delete_by_source(self, source: str) -> None:
        """Delete all chunks from a specific source file."""
        if not self._ensure_table():
            return
        # Sanitize input to prevent injection
        safe_source = source.replace("'", "''").replace("\\", "\\\\")
        table = self.db.open_table(self.table_name)
        table.delete(f"source = '{safe_source}'")

        # Also remove from the keyword index
        try:
            kw_index = KeywordIndex(self.project_id)
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
    review_status = kr.review_status or (
        "non_promotional" if not kr.evidence_unit_id else ""
    )
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


async def _record_retrieval_telemetry(
    *,
    project_id: str,
    retrieval_mode: str,
    results: list[RetrievalResult],
    degraded_reason: str | None = None,
) -> None:
    """Record a content-free retrieval event for research-validity audits."""
    try:
        from app.core.telemetry import telemetry_recorder

        representative = next(
            (
                result
                for result in results
                if result.evidence_unit_id
                or result.coding_run_id
                or result.codebook_version_id
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
) -> list[RetrievalResult]:
    """Run hybrid search combining vector similarity and BM25 keyword ranking.

    Uses Reciprocal Rank Fusion (RRF) to merge the two result lists.
    """
    k = top_k or settings.rag_top_k
    rrf_k = 60  # RRF constant

    store = VectorStore(project_id)
    kw_index = KeywordIndex(project_id)

    # Run both searches
    vector_results = await store.search(
        query_vector,
        top_k=k * 2,  # fetch more to improve fusion quality
        source_filter=source_filter,
        file_type_filter=file_type_filter,
        agent_id=agent_id,
    )
    keyword_results = await kw_index.search(query, top_k=k * 2)
    if source_filter:
        keyword_results = [kr for kr in keyword_results if kr.source == source_filter]
    if file_type_filter:
        normalized_file_type = file_type_filter.lstrip(".").lower()
        keyword_results = [
            kr
            for kr in keyword_results
            if Path(kr.source).suffix.lstrip(".").lower() == normalized_file_type
        ]
    if agent_id is not None:
        # The keyword index does not currently store agent ownership; avoid
        # mixing unscoped keyword hits into an agent-scoped retrieval.
        keyword_results = []

    vw = settings.rag_hybrid_vector_weight
    kw = settings.rag_hybrid_keyword_weight

    # Build RRF scores keyed by provenance, not text. Qualitative evidence can
    # repeat verbatim across documents/participants and still remain distinct.
    scores: dict[str, dict] = {}

    for rank, r in enumerate(vector_results, 1):
        key = retrieval_result_key(r)
        if key not in scores:
            scores[key] = {"result": r, "score": 0.0}
        scores[key]["score"] += vw * (1.0 / (rrf_k + rank))

    for rank, kr in enumerate(keyword_results, 1):
        keyword_result = _keyword_retrieval_result(kr)
        key = retrieval_result_key(keyword_result)
        if key not in scores:
            scores[key] = {
                "result": keyword_result,
                "score": 0.0,
            }
        scores[key]["score"] += kw * (1.0 / (rrf_k + rank))

    # Sort by fused score descending and take top_k
    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)[:k]

    results = []
    for item in ranked:
        r = item["result"]
        r.score = item["score"]
        results.append(r)

    return results


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

    k = top_k or settings.rag_top_k
    keyword_results = await KeywordIndex(project_id).search(query, top_k=k * 2)

    if source_filter:
        keyword_results = [kr for kr in keyword_results if kr.source == source_filter]
    if file_type_filter:
        normalized_file_type = file_type_filter.lstrip(".").lower()
        keyword_results = [
            kr
            for kr in keyword_results
            if Path(kr.source).suffix.lstrip(".").lower() == normalized_file_type
        ]

    results: list[RetrievalResult] = []
    for rank, kr in enumerate(keyword_results[:k], 1):
        results.append(
            _keyword_retrieval_result(kr, score=1.0 / rank)
        )
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
    await _record_retrieval_telemetry(
        project_id=project_id,
        retrieval_mode=retrieval_mode,
        results=results,
        degraded_reason=degraded_reason,
    )

    # Format context for the LLM — wrap each chunk in untrusted delimiters
    context_parts = []
    for i, r in enumerate(results, 1):
        source_info = f"[Source: {r.source}"
        if r.page:
            source_info += f", page {r.page}"
        source_info += f", relevance: {r.score:.2f}]"
        wrapped = _guard.wrap_untrusted(r.text, source=r.source)
        context_parts.append(f"--- Document {i} {source_info} ---\n{wrapped}")

    context_text = "\n\n".join(context_parts) if context_parts else ""

    return RAGContext(
        query=query,
        retrieved=results,
        context_text=context_text,
    )


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
