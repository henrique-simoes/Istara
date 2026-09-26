"""Knowledge Sync Service — indexes project documents into LanceDB and BM25."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_processor import TextChunk, chunk_text, process_file
from app.core.keyword_index import KeywordIndex
from app.core.rag import VectorStore
from app.models.document import Document
from app.services.retrieval_provenance import (
    document_source_text,
    index_document_source_chunks,
)

logger = logging.getLogger(__name__)


class KnowledgeSyncService:
    """Synchronizes and indexes all project documents into LanceDB and BM25."""

    async def sync_project(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Index or re-index all documents belonging to a project.

        Extracts text from files on disk or document content stored in DB,
        chunks appropriately, and updates both the BM25 keyword index and
        LanceDB vector store.
        """
        result = await db.execute(select(Document).where(Document.project_id == project_id))
        documents = result.scalars().all()

        store = VectorStore(project_id)
        kw_index = KeywordIndex(project_id)

        indexed_docs = 0
        total_chunks = 0
        sources_indexed: list[str] = []

        for doc in documents:
            source_key = doc.file_path or doc.file_name or doc.title or doc.id
            chunks: list[TextChunk] = []

            # 1. Try file on disk
            file_path_obj = Path(doc.file_path) if doc.file_path else None
            if file_path_obj and file_path_obj.exists():
                try:
                    proc_res = process_file(file_path_obj)
                    if proc_res.chunks:
                        chunks = proc_res.chunks
                except Exception as e:
                    logger.warning(
                        "File processing failed for %s (%s): %s",
                        doc.id,
                        doc.file_path,
                        e,
                    )

            # 2. Fall back to database-persisted text / preview. It is stored through
            # ``protect_document_text``, so with FILE_ENCRYPTION_ENABLED it is ciphertext until
            # revealed; indexing it raw put ciphertext into both indices (F15).
            if not chunks:
                content = document_source_text(doc)
                if content:
                    chunks = chunk_text(
                        content,
                        source=source_key,
                    )

            if not chunks:
                continue

            # Tag chunks with source document metadata
            for c in chunks:
                if not c.source:
                    c.source = source_key
                c.metadata = {
                    **(c.metadata or {}),
                    "source_document_id": doc.id,
                    "document_id": doc.id,
                    "title": doc.title,
                }

            # Delete old chunks for this source to ensure idempotency
            try:
                if doc.file_path:
                    await store.delete_file_source(doc.file_path)
                else:
                    await store.delete_by_source(source_key)
            except Exception as e:
                logger.debug("Failed deleting old vector chunks for %s: %s", source_key, e)

            try:
                await kw_index.delete_by_source(source_key)
            except Exception as e:
                logger.debug("Failed deleting old keyword chunks for %s: %s", source_key, e)

            # Ingest chunks into both indices, each stamped with its evidence unit
            try:
                await index_document_source_chunks(
                    project_id,
                    chunks,
                    document_id=doc.id,
                    document_text=document_source_text(doc),
                    db=db,
                )
                indexed_docs += 1
                total_chunks += len(chunks)
                sources_indexed.append(source_key)
            except Exception as e:
                logger.error("Failed ingesting chunks for %s: %s", doc.id, e)

        logger.info(
            "Knowledge sync completed for project %s: %d docs, %d chunks",
            project_id,
            indexed_docs,
            total_chunks,
        )

        return {
            "status": "ok",
            "project_id": project_id,
            "documents_indexed": indexed_docs,
            "chunks_indexed": total_chunks,
            "sources": sources_indexed,
        }
