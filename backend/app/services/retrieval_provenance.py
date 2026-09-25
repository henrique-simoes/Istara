"""Retrieval provenance: every source chunk carries the evidence unit it was cut from.

Hybrid RAG is the spine's exact-evidence retriever (research-validity contract, "Retrieval
Contract"): a hit must be traceable to its source span and evidence unit. Evidence units are
segmented from the document text at ingestion; retrieval chunks are cut from the same text by a
different splitter. Before this module nothing joined the two. No production path set
``evidence_unit_id`` on a chunk, ``retrieval_metadata_for_unit`` had no callers, and every
keyword hit came back ``missing_provenance`` (measurement 5: 0% coverage).

``annotate_chunks_with_evidence_units`` locates each chunk in the document text the units were
segmented from, and stamps it with the unit it overlaps most, the chunk's own span, and the
source document. ``index_document_source_chunks`` is the one ingestion entry point that does this
and then writes both indices. ``provenance_coverage`` is the health invariant.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import TextChunk
from app.core.research_validity import retrieval_metadata_for_unit

logger = logging.getLogger(__name__)


def _unit_dict(unit: Any) -> dict:
    if isinstance(unit, dict):
        return unit
    return {
        "id": getattr(unit, "id", None),
        "stable_id": getattr(unit, "stable_id", None),
        "source_location": getattr(unit, "source_location", None),
        "start_offset": getattr(unit, "start_offset", None),
        "end_offset": getattr(unit, "end_offset", None),
        "method": getattr(unit, "method", "") or "",
        "phase": getattr(unit, "phase", "") or "",
        "source_text": getattr(unit, "source_text", "") or "",
    }


def annotate_chunks_with_evidence_units(
    chunks: list[TextChunk],
    units: list[Any],
    *,
    document_id: str,
    document_text: str,
) -> int:
    """Stamp each chunk with the evidence unit it overlaps most. Returns how many were stamped.

    ``document_text`` must be the text the units were segmented from, after the same ``strip()``
    that ``persist_document_source_evidence_units`` applies. Unit offsets index into it. Chunks are
    located in order with ``str.find`` from the previous chunk's start, which is exact for every
    Istara splitter (chunks are contiguous slices, possibly overlapping). A chunk that cannot be
    located still gets its ``source_document_id`` but no unit: it is never guessed.
    """
    unit_rows = [
        u
        for u in (_unit_dict(unit) for unit in units)
        if u.get("id") is not None
        and u.get("start_offset") is not None
        and u.get("end_offset") is not None
    ]
    text = (document_text or "").strip()
    cursor = 0
    stamped = 0
    for chunk in chunks:
        metadata = {**(chunk.metadata or {}), "source_document_id": document_id}
        position = text.find(chunk.text, cursor) if chunk.text else -1
        if position < 0 and chunk.text:
            position = text.find(chunk.text)
        if position >= 0:
            cursor = position + 1
            start, end = position, position + len(chunk.text)
            best, best_overlap = None, 0
            for unit in unit_rows:
                overlap = min(end, int(unit["end_offset"])) - max(start, int(unit["start_offset"]))
                if overlap > best_overlap:
                    best, best_overlap = unit, overlap
            metadata["start_offset"] = start
            metadata["end_offset"] = end
            if best is not None:
                handles = retrieval_metadata_for_unit(best)
                metadata.update(
                    {
                        "evidence_unit_id": str(handles["evidence_unit_id"]),
                        "evidence_unit_stable_id": handles.get("stable_id") or "",
                        "retrieval_role": handles["retrieval_role"],
                    }
                )
                stamped += 1
        chunk.metadata = metadata
    return stamped


async def load_document_evidence_units(
    db: AsyncSession, *, project_id: str, document_id: str
) -> list[Any]:
    from app.models.research_validity import EvidenceUnit

    rows = await db.execute(
        select(EvidenceUnit)
        .where(
            EvidenceUnit.project_id == project_id,
            EvidenceUnit.source_document_id == document_id,
            EvidenceUnit.unit_type == "source_span",
        )
        .order_by(EvidenceUnit.unit_index)
    )
    return list(rows.scalars().all())


def document_source_text(document: Any) -> str:
    """The text a document's evidence units were segmented from (decrypted, stripped)."""
    from app.core.file_encryption import reveal_document_text

    return reveal_document_text(
        getattr(document, "content_text", None) or getattr(document, "content_preview", None) or ""
    ).strip()


async def index_document_source_chunks(
    project_id: str,
    chunks: list[TextChunk],
    *,
    document_id: str | None,
    units: list[Any] | None = None,
    document_text: str = "",
    db: AsyncSession | None = None,
) -> int:
    """Annotate chunks with evidence-unit provenance, then write BOTH indices.

    ``units`` may be passed (just persisted) or loaded from ``db`` for an existing document. With
    no document, the chunks are indexed without provenance, and the coverage invariant reports them.
    """
    from app.core.rag import ingest_chunks

    if document_id:
        if units is None and db is not None:
            units = await load_document_evidence_units(
                db, project_id=project_id, document_id=document_id
            )
        stamped = annotate_chunks_with_evidence_units(
            chunks, units or [], document_id=document_id, document_text=document_text
        )
        if chunks and stamped < len(chunks):
            logger.info(
                "Provenance: %d of %d chunks for document %s map to an evidence unit",
                stamped,
                len(chunks),
                document_id,
            )
    return await ingest_chunks(project_id, chunks)


async def provenance_coverage(project_id: str) -> dict:
    """Health invariant: the share of SOURCE chunks that carry an ``evidence_unit_id``.

    Counts rows with a filter in the query, never loading the table. Derived text is not source
    evidence, and rows a build before the split wrote into the source table are excluded from
    the denominator and reported separately.
    """
    from app.core.rag import VectorStore

    store = VectorStore(project_id)
    result = {
        "source_chunks": 0,
        "with_evidence_unit": 0,
        "coverage": None,
        "legacy_derived_rows": 0,
        "status": "empty",
    }
    try:
        if not store._ensure_table():
            return result
        table = store.db.open_table(store.table_name)
        derived_filter = "(source LIKE 'agent:%' OR source LIKE 'skill:%')"
        total = table.count_rows()
        legacy = table.count_rows(derived_filter)
        source_total = total - legacy
        with_unit = 0
        if "evidence_unit_id" in table.schema.names and source_total:
            with_unit = table.count_rows(f"evidence_unit_id != '' AND NOT {derived_filter}")
    except Exception as e:
        logger.warning("Provenance coverage unavailable for %s: %s", project_id, e)
        result["status"] = "unavailable"
        return result
    coverage = (with_unit / source_total) if source_total else None
    result.update(
        {
            "source_chunks": source_total,
            "with_evidence_unit": with_unit,
            "coverage": round(coverage, 4) if coverage is not None else None,
            "legacy_derived_rows": legacy,
            "status": "empty"
            if not source_total
            else ("ok" if with_unit == source_total else "degraded"),
        }
    )
    return result
