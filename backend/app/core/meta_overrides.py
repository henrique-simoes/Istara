"""Read-only project-scoped Meta-Hyperagent override helpers.

Runtime systems can consult approved project variants without importing the
Meta-Hyperagent orchestration module and forming dependency cycles.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
VARIANTS_FILE = DATA_DIR / "_meta_variants.json"
OVERRIDES_FILE = DATA_DIR / "_meta_overrides.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Meta override file unavailable at %s: %s", path, exc)
        return default


def get_project_parameter_overrides(project_id: str | None) -> dict[str, Any]:
    """Return active/confirmed parameter overrides for one project."""
    scoped_project_id = str(project_id or "").strip()
    if not scoped_project_id:
        return {}

    result: dict[str, Any] = {}
    persisted = (_load_json(OVERRIDES_FILE, {}).get("projects") or {}).get(scoped_project_id, {})
    for parameter_path, entry in persisted.items():
        result[str(parameter_path)] = entry.get("value") if isinstance(entry, dict) else entry

    variants = _load_json(VARIANTS_FILE, [])
    if isinstance(variants, list):
        for variant in variants:
            if str(variant.get("project_id") or "") != scoped_project_id:
                continue
            if variant.get("status") not in {"active", "confirmed"}:
                continue
            if variant.get("reverted_at"):
                continue
            parameter_path = str(variant.get("parameter_path") or "").strip()
            if parameter_path:
                result[parameter_path] = variant.get("new_value")

    return {key: value for key, value in result.items() if key}


def get_parameter_override(
    parameter_path: str,
    *,
    project_id: str | None,
    default: Any = None,
) -> Any:
    """Return a single project-scoped override or ``default``."""
    return get_project_parameter_overrides(project_id).get(parameter_path, default)


def get_self_evolution_threshold_overrides(project_id: str | None) -> dict[str, Any]:
    """Return project-scoped self-evolution threshold overrides."""
    prefix = "self_evolution.PROMOTION_THRESHOLDS."
    result: dict[str, Any] = {}
    for path, value in get_project_parameter_overrides(project_id).items():
        if path.startswith(prefix):
            key = path[len(prefix) :]
            if key:
                result[key] = value
    return result
