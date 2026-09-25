"""Chunking parameters mean what they say (F17 residue, found by measurement 2).

The re-indexing ablation (M2) measured ``chunk_overlap=0`` and the default 180 as the same
sandbox, span for span. ``chunk_text`` read ``chunk_overlap or settings.rag_chunk_overlap``, so
an explicit 0 became 180: the zero-as-unset defect class F17 fixed elsewhere. The same loop set
``start = end - overlap`` without checking progress. When the overlap reaches the distance to
the chosen break, which can be half the chunk size, the start stops advancing and the loop never
ends. The tuning ranges allow that pairing (chunk size 400, overlap 400).
"""

from __future__ import annotations

import multiprocessing

import pytest

from app.config import settings
from app.core.file_processor import chunk_by_heading, chunk_text

PARAGRAPHS = "\n\n".join(
    f"Paragraph {i}. Owners chase late invoices by phone every Friday afternoon, and receipts "
    f"fade on thermal paper before the quarter closes, so the accountant asks twice."
    for i in range(40)
)


def _spans(chunks, text):
    spans, cursor = [], 0
    for chunk in chunks:
        start = text.find(chunk.text, cursor)
        assert start >= 0
        spans.append((start, start + len(chunk.text)))
        cursor = start + 1
    return spans


def test_an_explicit_zero_overlap_is_zero(monkeypatch):
    monkeypatch.setattr(settings, "rag_chunk_overlap", 180)
    chunks = chunk_text(PARAGRAPHS, source="p.md", chunk_size=600, chunk_overlap=0)
    spans = _spans(chunks, PARAGRAPHS)
    overlaps = [
        prev_end - start for (_, prev_end), (start, _) in zip(spans, spans[1:], strict=False)
    ]
    assert len(chunks) > 3
    assert max(overlaps) <= 0, f"chunks overlap by {max(overlaps)} characters with overlap=0"


def test_heading_sections_honour_an_explicit_zero_overlap(monkeypatch):
    monkeypatch.setattr(settings, "rag_chunk_overlap", 180)
    text = "## Long section\n\n" + PARAGRAPHS
    chunks = chunk_by_heading(text, source="h.md", max_size=600, overlap=0)
    spans = _spans(chunks, text)
    assert (
        max(prev_end - start for (_, prev_end), (start, _) in zip(spans, spans[1:], strict=False))
        <= 0
    )


def _chunk_in_child(size, overlap, queue):
    queue.put(len(chunk_text(PARAGRAPHS, source="p.md", chunk_size=size, chunk_overlap=overlap)))


@pytest.mark.parametrize("size,overlap", [(400, 400), (400, 399), (300, 1000)])
def test_an_overlap_as_large_as_the_chunk_still_terminates(size, overlap):
    ctx = multiprocessing.get_context("fork")
    queue = ctx.Queue()
    child = ctx.Process(target=_chunk_in_child, args=(size, overlap, queue))
    child.start()
    child.join(5)
    hung = child.is_alive()
    if hung:
        child.kill()
        child.join()
    assert not hung, f"chunk_text(size={size}, overlap={overlap}) did not finish in 5 s"
    assert queue.get(timeout=1) > 1


def test_a_non_positive_chunk_size_is_refused():
    with pytest.raises(ValueError):
        chunk_text(PARAGRAPHS, source="p.md", chunk_size=0, chunk_overlap=0)
