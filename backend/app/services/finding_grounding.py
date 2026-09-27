"""Ground a skill's nugget in the raw source document it quotes (D-12, DEC-5).

A skill returns nuggets as quotes plus the name of the file they came from, but no document id,
so until now every skill nugget was stored as a model-written ``candidate_atom``: no exact-span
evidence unit, no governed coding run, and a report gate that could never pass.

Grounding is deliberately narrow. A nugget is grounded only when its quote occurs as one contiguous
span of a raw source document's text (user uploads, project files, external sources; never agent or
task output). Runs of whitespace may differ (transcripts wrap lines, models do not); every other
character must match. No fuzzy matching and no model judgement: an ungrounded nugget stays a
candidate. When the quote occurs in several documents, the document the skill named wins; if none is
named, the nugget stays ungrounded, because a quote shared by several participants cannot be
attributed to one of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

RAW_SOURCE_KINDS = frozenset({"user_upload", "project_file", "external"})
MIN_QUOTE_CHARS = 12
_QUOTE_MARKS = "\"'“”‘’«»"


@dataclass(frozen=True)
class Grounding:
    document_id: str
    start: int
    end: int
    text: str
    location: str


def _clean_quote(value: str) -> str:
    quote = str(value or "").strip()
    while len(quote) > 1 and quote[0] in _QUOTE_MARKS and quote[-1] in _QUOTE_MARKS:
        quote = quote[1:-1].strip()
    return quote


def locate_quote(quote: str, text: str) -> tuple[int, int] | None:
    """Return the (start, end) of ``quote`` in ``text``, whitespace-insensitive, else None."""
    quote = _clean_quote(quote)
    if len(quote) < MIN_QUOTE_CHARS or not text:
        return None
    exact = text.find(quote)
    if exact >= 0:
        return exact, exact + len(quote)
    words = quote.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    match = re.search(pattern, text)
    return (match.start(), match.end()) if match else None


def _names_document(source: str, document) -> bool:
    name = str(source or "").strip()
    if not name:
        return False
    candidates = {
        document.file_name or "",
        document.title or "",
        Path(document.file_path or "").name,
    }
    return name in candidates or Path(name).name in candidates


async def load_raw_source_texts(
    db: AsyncSession, project_id: str, *, limit: int = 200
) -> list[tuple[object, str]]:
    """Raw source documents of a project with their revealed text, newest first."""
    from app.core.file_encryption import reveal_document_text
    from app.models.document import Document

    rows = (
        (
            await db.execute(
                select(Document)
                .where(Document.project_id == project_id)
                .order_by(Document.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    loaded = []
    for document in rows:
        kind = getattr(document.source, "value", document.source)
        if str(kind) not in RAW_SOURCE_KINDS:
            continue
        try:
            text = reveal_document_text(document.content_text or "")
        except Exception:
            continue
        if text:
            loaded.append((document, text))
    return loaded


def ground_quote(
    quote: str,
    source_name: str,
    documents: list[tuple[object, str]],
    *,
    preferred_ids: list[str] | None = None,
) -> Grounding | None:
    """Find the one raw source document that contains ``quote``.

    Preference order: the document the skill named, then the task's own input documents, then a
    unique match anywhere in the project. Several unnamed matches leave the quote ungrounded.
    """
    hits = []
    for document, text in documents:
        span = locate_quote(quote, text)
        if span is not None:
            hits.append((document, text, span))
    if not hits:
        return None
    named = [hit for hit in hits if _names_document(source_name, hit[0])]
    preferred = [hit for hit in hits if hit[0].id in set(preferred_ids or [])]
    chosen = named or preferred or (hits if len(hits) == 1 else [])
    if len(chosen) != 1:
        return None
    document, text, (start, end) = chosen[0]
    return Grounding(
        document_id=document.id,
        start=start,
        end=end,
        text=text[start:end],
        location=f"{document.file_name or document.title}#chars={start}-{end}",
    )
