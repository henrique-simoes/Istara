"""Shared task contract helpers for API and LLM-callable task surfaces."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

TASK_PRIORITIES = {"urgent", "high", "medium", "low"}


def dedupe_text_list(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            cleaned.append(item)
            seen.add(item)
    return cleaned


def normalize_task_priority(value: Any) -> str:
    priority = str(value or "medium").strip().lower()
    if priority == "critical":
        priority = "urgent"
    return priority if priority in TASK_PRIORITIES else "medium"


async def ensure_project_documents(
    db: AsyncSession,
    project_id: str,
    document_ids: list[Any],
) -> tuple[list[str], str | None]:
    ids = dedupe_text_list(document_ids)
    if not ids:
        return [], None
    rows = (
        await db.execute(select(Document.id, Document.project_id).where(Document.id.in_(ids)))
    ).all()
    project_by_id = {row[0]: row[1] for row in rows}
    invalid = [
        doc_id
        for doc_id in ids
        if doc_id not in project_by_id or project_by_id.get(doc_id) != project_id
    ]
    if invalid:
        return [], "Cannot create task: input_document_ids contains unknown documents for this project."
    return ids, None
