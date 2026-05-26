"""BM25 keyword index using SQLite FTS5 for hybrid search."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)


def _fts_terms(query: str) -> list[str]:
    return [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]


def _fts_phrase_query(query: str) -> str:
    terms = _fts_terms(query)
    if not terms:
        return ""
    return '"' + " ".join(term.replace('"', '""') for term in terms) + '"'


def _fts_or_query(query: str) -> str:
    terms = _fts_terms(query)
    return " OR ".join(f'"{term}"' for term in terms)


class KeywordResult:
    """A single keyword search result."""

    def __init__(
        self,
        text: str,
        source: str,
        page: int,
        rank: float,
        *,
        evidence_unit_id: str = "",
        source_document_id: str = "",
        start_offset: int | None = None,
        end_offset: int | None = None,
        codebook_version_id: str = "",
        coding_run_id: str = "",
        review_status: str = "",
        reliability_status: str = "",
        provenance_key: str = "",
    ):
        self.text = text
        self.source = source
        self.page = page
        self.rank = rank
        self.evidence_unit_id = evidence_unit_id
        self.source_document_id = source_document_id
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.codebook_version_id = codebook_version_id
        self.coding_run_id = coding_run_id
        self.review_status = review_status
        self.reliability_status = reliability_status
        self.provenance_key = provenance_key


class KeywordIndex:
    """SQLite FTS5 keyword index for a project."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        db_dir = Path(settings.data_dir) / "keyword_index"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_dir / f"{project_id}.db")

    async def _get_db(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.db_path)
        await self._migrate_legacy_contentless_table(db)
        await db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5("
            "text, source UNINDEXED, page UNINDEXED, "
            "evidence_unit_id UNINDEXED, source_document_id UNINDEXED, "
            "start_offset UNINDEXED, end_offset UNINDEXED, "
            "codebook_version_id UNINDEXED, coding_run_id UNINDEXED, "
            "review_status UNINDEXED, reliability_status UNINDEXED, "
            "provenance_key UNINDEXED, tokenize='porter unicode61')"
        )
        await db.commit()
        return db

    async def _migrate_legacy_contentless_table(self, db: aiosqlite.Connection) -> None:
        """Replace legacy contentless FTS tables that cannot return stored fields."""
        async with db.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'chunks_fts'"
        ) as cur:
            row = await cur.fetchone()

        create_sql = str(row[0]).lower().replace(" ", "") if row and row[0] else ""
        needs_rebuild = (
            "content=''" in create_sql
            or 'content=""' in create_sql
            or "evidence_unit_id" not in create_sql
        )
        if not needs_rebuild:
            return

        logger.warning(
            "Migrating legacy keyword index for project %s; "
            "files may need reprocessing to restore keyword hits.",
            self.project_id,
        )
        await db.execute("DROP TABLE IF EXISTS chunks_fts")
        await db.commit()

    async def add_chunks(self, chunks: list) -> int:
        """Add chunks to the keyword index. chunks should have .text, .source, .page attrs."""
        if not chunks:
            return 0
        db = await self._get_db()
        try:
            rows = []
            for c in chunks:
                metadata = c.metadata or {}
                rows.append(
                    (
                        c.text,
                        c.source,
                        c.page or 0,
                        str(metadata.get("evidence_unit_id", "")),
                        str(metadata.get("source_document_id", "")),
                        metadata.get("start_offset"),
                        metadata.get("end_offset"),
                        str(metadata.get("codebook_version_id", "")),
                        str(metadata.get("coding_run_id", "")),
                        str(metadata.get("review_status", "")),
                        str(metadata.get("reliability_status", "")),
                        str(metadata.get("provenance_key", "")),
                    )
                )
            await db.executemany(
                "INSERT INTO chunks_fts ("
                "text, source, page, evidence_unit_id, source_document_id, "
                "start_offset, end_offset, codebook_version_id, coding_run_id, "
                "review_status, reliability_status, provenance_key"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            await db.commit()
            return len(rows)
        finally:
            await db.close()

    async def search(self, query: str, top_k: int = 10) -> list[KeywordResult]:
        """Search using BM25 ranking."""
        if not query.strip():
            return []
        phrase_query = _fts_phrase_query(query)
        if not phrase_query:
            return []
        db = await self._get_db()
        try:
            sql = (
                "SELECT text, source, page, evidence_unit_id, source_document_id, "
                "start_offset, end_offset, codebook_version_id, coding_run_id, "
                "review_status, reliability_status, provenance_key, rank "
                "FROM chunks_fts "
                "WHERE chunks_fts MATCH ? "
                "ORDER BY rank "
                "LIMIT ?"
            )

            def _result_from_row(row) -> KeywordResult:
                return KeywordResult(
                    text=row[0],
                    source=row[1],
                    page=row[2],
                    rank=row[12],
                    evidence_unit_id=row[3] or "",
                    source_document_id=row[4] or "",
                    start_offset=row[5],
                    end_offset=row[6],
                    codebook_version_id=row[7] or "",
                    coding_run_id=row[8] or "",
                    review_status=row[9] or "",
                    reliability_status=row[10] or "",
                    provenance_key=row[11] or "",
                )

            async with db.execute(sql, (phrase_query, top_k)) as cur:
                results = []
                async for row in cur:
                    results.append(_result_from_row(row))
            # If exact phrase match returns nothing, try individual terms
            if not results:
                terms = _fts_or_query(query)
                if terms:
                    async with db.execute(sql, (terms, top_k)) as cur:
                        async for row in cur:
                            results.append(_result_from_row(row))
            return results
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []
        finally:
            await db.close()

    async def delete_by_source(self, source: str) -> None:
        """Delete all entries from a source file."""
        db = await self._get_db()
        try:
            await db.execute("DELETE FROM chunks_fts WHERE source = ?", (source,))
            await db.commit()
        except Exception as e:
            logger.warning(f"Keyword index delete failed for {source}: {e}")
        finally:
            await db.close()

    async def count(self) -> int:
        db = await self._get_db()
        try:
            async with db.execute("SELECT COUNT(*) FROM chunks_fts") as cur:
                row = await cur.fetchone()
                return row[0] if row else 0
        except Exception:
            return 0
        finally:
            await db.close()

    async def rebuild(self) -> None:
        """Rebuild the FTS index."""
        db = await self._get_db()
        try:
            await db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
            await db.commit()
        except Exception as e:
            logger.warning(f"Keyword index rebuild failed: {e}")
        finally:
            await db.close()
