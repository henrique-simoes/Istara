"""The identity of a vector space, as each vector store's manifest records it.

A store is bound to the embedding profile that wrote its first vectors, and never serves another:
different model, cache namespace, dimension or prompt scheme means a different space. Manifests
written before prompt schemes existed hold vectors of raw text.
"""

from __future__ import annotations

import json
from pathlib import Path

VECTOR_IDENTITY_FIELDS = (
    "profile_id",
    "version",
    "model_id",
    "cache_namespace",
    "dimension",
    "dtype",
    "normalization",
    "prompt_scheme",
)
_DEFAULTS = {"prompt_scheme": "raw"}


def identity_differs(bound: dict, active: dict) -> bool:
    """Whether a manifest's vector space differs from the active profile's."""
    return any(
        bound.get(field, _DEFAULTS.get(field)) != active[field] for field in VECTOR_IDENTITY_FIELDS
    )


def write_manifest(path: Path, binding: dict, fingerprint: str | None) -> None:
    """Atomically bind a store's manifest to ``binding`` (the embedding migration's last step)."""
    record = dict(binding)
    if fingerprint:
        record["fingerprint"] = fingerprint
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
