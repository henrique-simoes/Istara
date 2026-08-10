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

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema.validators import Draft202012Validator

# tests/pi_benchmark/schema.py -> parents[2] is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = _REPO_ROOT / "comparison-Istara-pi" / "metrics-schema.json"
SCHEMA_VERSION = "1.1.0"


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


# Shared record/provenance helpers live with the schema contract so the runner and live
# driver both depend on this leaf module; neither execution path imports the other.
def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=str(_REPO_ROOT), stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:  # pragma: no cover - git absent / not a repo
        return ""


def git_provenance() -> tuple[str, bool]:
    """Return ``(git_sha, git_dirty)``; use a padded stub if git is absent."""
    sha = _git("rev-parse", "HEAD") or "0000000"
    dirty = bool(_git("status", "--porcelain"))
    return sha[: max(7, len(sha))] if len(sha) >= 7 else (sha + "0000000")[:7], dirty


def input_sha256(scenario_id: str, seed: int) -> str:
    """Return the deterministic input hash shared by both engine arms."""
    payload = json.dumps({"scenario": scenario_id, "seed": seed}, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _order_for_pair(pair_index: int) -> str:
    """Alternate which arm ran first, exposing and controlling order bias."""
    return "legacy_first" if pair_index % 2 == 0 else "pi_first"


def build_record(
    *,
    config: Any,
    scenario: Any,
    engine: str,
    seed: int,
    repeat: int,
    pair_index: int,
    git_sha: str,
    git_dirty: bool,
    ts: str,
    status: str,
    not_runnable_reason: str | None = None,
    metrics: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble and validate one schema-conformant run record."""
    record_id = f"{config.phase}-{config.tier}-{scenario.pack}-{scenario.id}-seed{seed}-r{repeat}-{engine}"
    pair_id = f"{config.phase}-{config.tier}-{scenario.pack}-{scenario.id}-seed{seed}-r{repeat}"
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "pair_id": pair_id,
        "phase": config.phase,
        "tier": config.tier,
        "engine": engine,
        "pack": scenario.pack,
        "scenario": {
            "id": scenario.id,
            "title": scenario.title,
            "seed": seed,
            "order": _order_for_pair(pair_index),
        },
        "provenance": {
            "git_sha": git_sha,
            "git_dirty": git_dirty,
            "input_sha256": input_sha256(scenario.id, seed),
            "model_id": None,
            "endpoint_fingerprint": "offline-contract",
            "ts": ts,
        },
        "status": status,
        "usage": usage if usage is not None else {
            "input_tokens": 0, "output_tokens": 0, "cache_tokens": 0,
            "total_tokens": 0, "cost_usd": 0, "estimate": False, "estimator": None,
        },
    }
    if not_runnable_reason is not None:
        record["not_runnable_reason"] = not_runnable_reason
    if metrics is not None:
        record["metrics"] = metrics
    if extensions is not None:
        record["extensions"] = extensions
    validate_record(record)
    return record


def write_record_atomic(records_dir: Path, unit_id: str, record: dict[str, Any]) -> Path:
    """Write one record with a temporary file and atomic replacement."""
    records_dir = Path(records_dir)
    records_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = records_dir / f"{unit_id}.json.tmp"
    final_path = records_dir / f"{unit_id}.json"
    tmp_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_path, final_path)
    return final_path
