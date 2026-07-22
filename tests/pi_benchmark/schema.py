"""Load and validate Pi-vs-Legacy benchmark run records.

This module is the single point of truth for reading and validating records against
``comparison-Istara-pi/metrics-schema.json`` (benchmark task B0-1). Downstream assets
— the paired runner, feature-criteria compiler, JudgeLayer, and the report generator —
import :func:`validate_record` so that "conforms to the schema" means exactly one thing.

Deliberately dependency-light: only the stdlib plus ``jsonschema`` (already a project
dependency). Importing this module never touches the backend, the database, a network
endpoint, or a model — it is safe at determinism tier T0.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema.validators import Draft202012Validator

# tests/pi_benchmark/schema.py -> parents[2] is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = _REPO_ROOT / "comparison-Istara-pi" / "metrics-schema.json"


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Return the parsed metrics schema.

    Raises FileNotFoundError if the schema is missing and json.JSONDecodeError if it is
    not valid JSON — both are hard failures for the whole benchmark, so they surface
    rather than being swallowed.
    """
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = load_schema()
    # check_schema raises jsonschema.SchemaError if the schema itself is malformed —
    # cheap insurance that B0-1 never ships an unusable contract.
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def iter_errors(record: dict[str, Any]):
    """Yield every schema violation for ``record`` (empty iterator == valid)."""
    yield from _validator().iter_errors(record)


def is_valid(record: dict[str, Any]) -> bool:
    """Return True iff ``record`` conforms to the metrics schema."""
    return next(iter_errors(record), None) is None


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate ``record`` in place and return it.

    Raises ``jsonschema.ValidationError`` on the first violation. Callers that want to
    collect every problem should use :func:`iter_errors` instead.
    """
    _validator().validate(record)
    return record
