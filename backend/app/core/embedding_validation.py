"""Pure validation for provider embedding vectors."""

from __future__ import annotations

import math
from typing import Any


class EmbeddingVectorError(ValueError):
    """An embedding response cannot safely enter a cache or vector index."""


def validate_embedding_vectors(
    vectors: Any,
    *,
    expected_count: int | None = None,
    expected_dimension: int | None = None,
    error_type: type[Exception] = EmbeddingVectorError,
) -> list[list[float]]:
    """Reject empty, ragged, non-numeric, and non-finite provider vectors."""

    def fail(message: str) -> None:
        raise error_type(message)

    if not isinstance(vectors, (list, tuple)):
        fail("embed_response_invalid_vectors: expected a list")
    if expected_count is not None and len(vectors) != expected_count:
        fail(f"embed_response_cardinality: {len(vectors)} vectors for {expected_count} texts")

    normalized: list[list[float]] = []
    dimension = expected_dimension
    for index, vector in enumerate(vectors):
        if not isinstance(vector, (list, tuple)) or not vector:
            fail(f"embed_response_invalid_vector: index={index}")
        if dimension is None:
            dimension = len(vector)
        if len(vector) != dimension:
            fail(
                "embed_response_dimension: "
                f"index={index} has {len(vector)} values; expected {dimension}"
            )
        checked: list[float] = []
        for value_index, value in enumerate(vector):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                fail(f"embed_response_non_numeric: index={index} value={value_index}")
            if not math.isfinite(float(value)):
                fail(f"embed_response_non_finite: index={index} value={value_index}")
            checked.append(value)
        normalized.append(checked)
    return normalized
