"""File processing pipeline — extract text and chunk documents."""

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.core.embeddings import TextChunk


@dataclass
class ProcessedFile:
    """Result of processing a file."""

    source: str
    chunks: list[TextChunk] = field(default_factory=list)
    total_chars: int = 0
    pages: int = 0
    error: str | None = None


def chunk_text(
    text: str,
    source: str,
    page: int | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[TextChunk]:
    """Split text into overlapping chunks.

    Args:
        text: The text to chunk.
        source: Source file identifier.
        page: Page number (for multi-page documents).
        chunk_size: Max characters per chunk.
        chunk_overlap: Character overlap between chunks.

    Returns:
        List of text chunks.
    """
    size = chunk_size or settings.rag_chunk_size
    overlap = chunk_overlap or settings.rag_chunk_overlap

    if not text or not text.strip():
        return []

    # Clean whitespace
    text = text.strip()

    # If text fits in one chunk, return it
    if len(text) <= size:
        return [TextChunk(text=text, source=source, page=page, position=0)]

    chunks: list[TextChunk] = []
    start = 0
    position = 0

    while start < len(text):
        end = start + size

        # Try to break at sentence or paragraph boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start + size // 2, end)
            if para_break > start:
                end = para_break + 2
            else:
                # Look for sentence break
                for sep in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                    sent_break = text.rfind(sep, start + size // 2, end)
                    if sent_break > start:
                        end = sent_break + len(sep)
                        break

        chunk_text_str = text[start:end].strip()
        if chunk_text_str:
            chunks.append(
                TextChunk(
                    text=chunk_text_str,
                    source=source,
                    page=page,
                    position=position,
                )
            )
            position += 1

        start = end - overlap
        if start >= len(text):
            break

    return chunks


def process_txt(file_path: Path) -> ProcessedFile:
    """Process a plain text or markdown file."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_text(text, source=str(file_path))
        return ProcessedFile(
            source=str(file_path),
            chunks=chunks,
            total_chars=len(text),
            pages=1,
        )
    except Exception as e:
        return ProcessedFile(source=str(file_path), error=str(e))


def process_pdf(file_path: Path) -> ProcessedFile:
    """Process a PDF file using pypdf."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        all_chunks: list[TextChunk] = []
        total_chars = 0

        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            total_chars += len(text)
            if text.strip():
                page_chunks = chunk_text(text, source=str(file_path), page=page_num)
                all_chunks.extend(page_chunks)

        return ProcessedFile(
            source=str(file_path),
            chunks=all_chunks,
            total_chars=total_chars,
            pages=len(reader.pages),
        )
    except Exception as e:
        return ProcessedFile(source=str(file_path), error=str(e))


def process_docx(file_path: Path) -> ProcessedFile:
    """Process a DOCX file using python-docx."""
    try:
        from docx import Document

        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)

        chunks = chunk_text(text, source=str(file_path))
        return ProcessedFile(
            source=str(file_path),
            chunks=chunks,
            total_chars=len(text),
            pages=1,
        )
    except Exception as e:
        return ProcessedFile(source=str(file_path), error=str(e))


def process_csv(file_path: Path) -> ProcessedFile:
    """Process a CSV file — convert rows to readable text."""
    try:
        text_parts: list[str] = []
        with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
                text_parts.append(f"Row {row_num}: {row_text}")

        text = "\n".join(text_parts)
        chunks = chunk_text(text, source=str(file_path))
        return ProcessedFile(
            source=str(file_path),
            chunks=chunks,
            total_chars=len(text),
            pages=1,
        )
    except Exception as e:
        return ProcessedFile(source=str(file_path), error=str(e))


# Supported file extensions and their processors
PROCESSORS = {
    ".txt": process_txt,
    ".md": process_txt,
    ".markdown": process_txt,
    ".pdf": process_pdf,
    ".docx": process_docx,
    ".csv": process_csv,
}


def process_file(file_path: Path) -> ProcessedFile:
    """Process a file based on its extension.

    Args:
        file_path: Path to the file to process.

    Returns:
        ProcessedFile with extracted and chunked text.
    """
    suffix = file_path.suffix.lower()
    processor = PROCESSORS.get(suffix)

    if processor is None:
        return ProcessedFile(
            source=str(file_path),
            error=f"Unsupported file type: {suffix}. Supported: {', '.join(PROCESSORS.keys())}",
        )

    return processor(file_path)


def get_supported_extensions() -> list[str]:
    """Return list of supported file extensions."""
    return list(PROCESSORS.keys())
