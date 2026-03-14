"""Local embedding engine using Ollama."""

from dataclasses import dataclass

from app.core.ollama import ollama


@dataclass
class TextChunk:
    """A chunk of text with metadata for embedding."""

    text: str
    source: str
    page: int | None = None
    position: int = 0
    metadata: dict | None = None


@dataclass
class EmbeddedChunk:
    """A text chunk with its embedding vector."""

    chunk: TextChunk
    vector: list[float]


async def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    return await ollama.embed(text)


async def embed_chunks(chunks: list[TextChunk], batch_size: int = 32) -> list[EmbeddedChunk]:
    """Embed multiple text chunks in batches.

    Args:
        chunks: List of text chunks to embed.
        batch_size: Number of texts to embed per API call.

    Returns:
        List of embedded chunks with vectors.
    """
    results: list[EmbeddedChunk] = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.text for c in batch]

        vectors = await ollama.embed_batch(texts)

        for chunk, vector in zip(batch, vectors):
            results.append(EmbeddedChunk(chunk=chunk, vector=vector))

    return results


async def ensure_embed_model() -> None:
    """Ensure the embedding model is available locally."""
    await ollama.ensure_model("nomic-embed-text")
