"""Role-aware embedding prompts: each model family's query and document formats (model cards).

Retrieval embedders are trained with instructions, and a raw string loses that training.
EmbeddingGemma expects ``task: search result | query: ...`` for queries and ``title: none | text:
...`` for documents; Qwen3-Embedding an ``Instruct: ...\\nQuery:`` prefix on queries only;
nomic-embed-text ``search_query: `` and ``search_document: ``. Ollama's /api/embed applies no
template, so Istara applies the scheme itself, the same one at index time and at query time.

The scheme is part of the vector-space identity (the embedding profile): vectors written under one
scheme are never compared with queries embedded under another. Profiles and indexes from before
schemes existed are ``raw``.
"""

from __future__ import annotations

from typing import Literal

EmbedRole = Literal["query", "document"]

RAW = "raw"

SCHEMES: dict[str, dict[str, str]] = {
    RAW: {"query": "{text}", "document": "{text}"},
    # https://ai.google.dev/gemma/docs/embeddinggemma/model_card (retrieval query / document)
    "embeddinggemma": {
        "query": "task: search result | query: {text}",
        "document": "title: none | text: {text}",
    },
    # Qwen3-Embedding model card: the instruction goes on queries only.
    "qwen3-embedding": {
        "query": (
            "Instruct: Given a web search query, retrieve relevant passages that answer the query"
            "\nQuery:{text}"
        ),
        "document": "{text}",
    },
    # nomic-embed-text model card: task prefixes on both sides.
    "nomic": {"query": "search_query: {text}", "document": "search_document: {text}"},
}

# Substrings of a model name (Ollama tag or LM Studio id) that identify its family.
_FAMILIES = (
    ("embeddinggemma", "embeddinggemma"),
    ("qwen3-embedding", "qwen3-embedding"),
    ("nomic-embed-text", "nomic"),
)


def scheme_for_model(model_id: str) -> str:
    """The model card's scheme for a model name; unknown models (and BGE-M3) take raw text."""
    name = str(model_id or "").strip().lower()
    for needle, scheme in _FAMILIES:
        if needle in name:
            return scheme
    return RAW


def resolve_scheme(setting: str | None, model_id: str) -> str:
    """``auto`` picks the model card's scheme; any other value must name a known scheme."""
    value = str(setting or "auto").strip().lower()
    if value == "auto":
        return scheme_for_model(model_id)
    if value not in SCHEMES:
        raise ValueError(f"unknown embedding prompt scheme: {setting!r}")
    return value


def apply_scheme(scheme: str, role: EmbedRole, text: str) -> str:
    """The exact string the embedder receives for ``text`` in ``role`` under ``scheme``."""
    template = SCHEMES.get(scheme, SCHEMES[RAW])[role]
    # Not str.format: research text contains braces.
    return template.replace("{text}", text)


def namespace_for(model_id: str, scheme: str) -> str:
    """Cache namespace of a vector space; raw keeps the model name so existing caches stay valid."""
    return model_id if scheme == RAW else f"{model_id}|prompts:{scheme}"
