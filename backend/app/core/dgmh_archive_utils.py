"""Shared helpers for DGM-H archive evolution."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

ARCHIVE_STATUS = {
    "candidate": "candidate",
    "approved": "approved",
    "active": "active",
    "confirmed": "confirmed",
    "archived": "archived",
    "failed": "failed",
    "reverted": "reverted",
    "quarantined": "quarantined",
}

SELECTABLE_STATUSES = {
    ARCHIVE_STATUS["candidate"],
    ARCHIVE_STATUS["approved"],
    ARCHIVE_STATUS["active"],
    ARCHIVE_STATUS["confirmed"],
}

_SECRET_PATTERNS = [
    re.compile(
        r"(?i)['\"]?\b(password|passwd|api[_-]?key|secret|token|access[_-]?token|refresh[_-]?token)\b['\"]?\s*[:=]\s*['\"]?[^'\"\s,;}]+"
    ),
    re.compile(r"://[^:/\s]+:[^@\s]+@"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\b[A-Za-z0-9_=-]{48,}\b"),
]


def utcnow() -> datetime:
    return datetime.now(UTC)


def clean_string(value: Any, *, max_chars: int = 4000) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\x00", " ").strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:max_chars]


def clean_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = clean_string(key, max_chars=120)
            if re.search(r"(?i)(password|passwd|api[_-]?key|secret|token)", safe_key):
                cleaned[safe_key] = "[REDACTED]"
            else:
                cleaned[safe_key] = clean_payload(item, depth=depth + 1)
        return cleaned
    if isinstance(value, list):
        return [clean_payload(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, tuple):
        return [clean_payload(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, (str, bytes)):
        return clean_string(value.decode("utf-8", "ignore") if isinstance(value, bytes) else value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return clean_string(value)


def normalize_token(value: str, fallback: str = "evaluation") -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", str(value or "").lower()).strip("_")
    return normalized or fallback


def score_from_metrics(
    *,
    score: float | None = None,
    metrics_before: dict | None = None,
    metrics_after: dict | None = None,
) -> float | None:
    if score is not None:
        return float(score)
    before = metrics_before or {}
    after = metrics_after or {}
    for key in ("score", "quality", "accuracy", "success_rate", "consensus_score"):
        if isinstance(before.get(key), (int, float)) and isinstance(after.get(key), (int, float)):
            return float(after[key]) - float(before[key])
    if isinstance(after.get("delta"), (int, float)):
        return float(after["delta"])
    return None


def ucb_score(
    *,
    score: float | None,
    confidence: float,
    evaluation_count: int,
    total_variants: int,
    exploration: float = 1.414,
) -> float:
    exploitation = float(score if score is not None else 0.0)
    bounded_confidence = max(0.0, min(1.0, float(confidence)))
    evidence_n = max(1, int(evaluation_count))
    total_n = max(2, int(total_variants))
    exploration_bonus = exploration * math.sqrt(math.log(total_n) / evidence_n)
    return round(exploitation * bounded_confidence + exploration_bonus, 6)


def artifact_kind(surfaces: list[str], source_system: str, proposed_change: dict) -> str:
    surface_set = set(surfaces)
    if source_system == "hyperagent" or surface_set & {"configs", "compute"}:
        return "parameter_variant"
    if surface_set & {"prompts"}:
        return "prompt_variant"
    if surface_set & {"skills"}:
        return "skill_variant"
    if surface_set & {"agents"}:
        return "agent_variant"
    if surface_set & {"ui"}:
        return "ui_variant"
    if surface_set & {"backend_code"}:
        return "backend_variant"
    if surface_set & {"integrations", "mcp", "channels", "connection_strings"}:
        return "integration_variant"
    if surface_set & {"documents", "transcription", "interviews"}:
        return "document_pipeline_variant"
    if proposed_change.get("evidence_only"):
        return "evidence_trace"
    return "proposal_variant"


def mutation_kind(source_system: str, proposed_change: dict) -> str:
    if proposed_change.get("evidence_only"):
        return "producer_evidence"
    mapping = {
        "autoresearch": "autoresearch_candidate",
        "hyperagent": "parameter_tuning",
        "reasoning_bank": "reasoning_memory",
        "memento": "agent_skill_design",
        "agent_factory": "agent_skill_design",
        "skill_evolution": "skill_design",
        "self_evolution": "persona_promotion",
    }
    return mapping.get(
        source_system, normalize_token(proposed_change.get("mutation_kind", "proposal"))
    )


def status_from_governance(status: str) -> str:
    mapping = {
        "draft": ARCHIVE_STATUS["candidate"],
        "proposed": ARCHIVE_STATUS["candidate"],
        "approved": ARCHIVE_STATUS["approved"],
        "applied": ARCHIVE_STATUS["active"],
        "rejected": ARCHIVE_STATUS["archived"],
        "reverted": ARCHIVE_STATUS["reverted"],
        "quarantined": ARCHIVE_STATUS["quarantined"],
    }
    return mapping.get(status, ARCHIVE_STATUS["candidate"])
