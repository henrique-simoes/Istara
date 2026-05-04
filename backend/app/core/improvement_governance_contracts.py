"""Shared contracts for Istara improvement governance."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

STATUS = {
    "draft": "draft",
    "proposed": "proposed",
    "approved": "approved",
    "applied": "applied",
    "rejected": "rejected",
    "reverted": "reverted",
    "quarantined": "quarantined",
}

POLICY = {
    "auto": "auto_apply",
    "approval": "approval_required",
    "admin": "admin_required",
}

RISK = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}

SURFACES = {
    "auto": {"memory", "telemetry", "evaluation", "documentation"},
    "admin": {"backend_code", "integrations", "mcp", "compute", "security", "connection_strings"},
    "behavior": {
        "prompts",
        "configs",
        "skills",
        "agents",
        "ui",
        "backend_code",
        "integrations",
        "mcp",
        "compute",
        "security",
        "orchestration",
        "connection_strings",
    },
}

FEATURE_CONTRACT_MATRIX = [
    {
        "feature": "interviews_audio_upload_transcription_tagging_documents",
        "surfaces": ["interviews", "transcription", "documents", "skills"],
        "required_evidence": [
            "audio dependency health",
            "language detection result",
            "transcription confidence or provider error",
            "tagging and document creation trace",
            "rollback for generated document/tag changes",
        ],
    },
    {
        "feature": "memento_skills_and_agent_creation",
        "surfaces": ["skills", "agents", "prompts", "reasoning"],
        "required_evidence": [
            "capability gap",
            "source memories",
            "approval decision",
            "promotion metrics",
            "rollback path",
        ],
    },
    {
        "feature": "hyperagent_meta_tuning",
        "surfaces": ["configs", "orchestration", "skills", "agents"],
        "required_evidence": [
            "observation snapshot",
            "parameter bounds",
            "approval decision",
            "variant metrics before and after",
            "revert or confirm action",
        ],
    },
    {
        "feature": "dgmh_archive_evolution",
        "surfaces": ["orchestration", "configs", "skills", "agents", "telemetry"],
        "required_evidence": [
            "archive parent selection score",
            "lineage and generation",
            "proposal and approval link",
            "evaluation runs with uncertainty",
            "ReasoningBank success or failure trace",
            "rollback or quarantine action",
        ],
    },
    {
        "feature": "karpathy_autoresearch",
        "surfaces": ["configs", "skills", "prompts", "ui", "compute"],
        "required_evidence": [
            "baseline score",
            "candidate mutation",
            "sampled measurements",
            "uncertainty guard",
            "keep/revert decision",
            "governance promotion proposal",
        ],
    },
    {
        "feature": "reasoning_bank",
        "surfaces": ["memory", "reasoning", "telemetry"],
        "required_evidence": [
            "source trace",
            "redacted memory",
            "retrieval usage",
            "quarantine/edit history",
            "impact on future task outcomes",
        ],
    },
    {
        "feature": "mcp_integrations_and_aura_research",
        "surfaces": ["mcp", "integrations", "security", "telemetry"],
        "required_evidence": [
            "access policy",
            "secret redaction",
            "audit entry",
            "tool health",
            "rollback or disable path",
        ],
    },
    {
        "feature": "whatsapp_telegram_channel_integrations",
        "surfaces": ["channels", "integrations", "security"],
        "required_evidence": [
            "webhook validation",
            "credential storage policy",
            "message processing trace",
            "rate/error telemetry",
            "disable path",
        ],
    },
    {
        "feature": "ensemble_model_and_llm_orchestration",
        "surfaces": ["compute", "orchestration", "telemetry"],
        "required_evidence": [
            "model eligibility",
            "statistical comparison",
            "fallback route",
            "latency and error percentiles",
            "hardware utilization signal",
        ],
    },
    {
        "feature": "pooled_compute_connection_strings",
        "surfaces": ["connection_strings", "compute", "security"],
        "required_evidence": [
            "hashed token storage",
            "redemption audit",
            "network guard result",
            "pool health",
            "revocation path",
        ],
    },
    {
        "feature": "desktop_tray_installation",
        "surfaces": ["ui", "integrations", "compute"],
        "required_evidence": [
            "dependency install check",
            "server lifecycle trace",
            "tray action result",
            "error recovery state",
            "platform-specific rollback",
        ],
    },
    {
        "feature": "all_menus_and_submenus",
        "surfaces": ["ui", "backend_code", "telemetry"],
        "required_evidence": [
            "frontend route coverage",
            "API contract coverage",
            "empty/loading/error states",
            "accessibility and mobile checks",
            "visual change telemetry",
        ],
    },
]

_SECRET_PATTERNS = [
    re.compile(
        r"(?i)['\"]?\b(password|passwd|api[_-]?key|secret|token|access[_-]?token|refresh[_-]?token)\b['\"]?\s*[:=]\s*['\"]?[^'\"\s,;}]+"
    ),
    re.compile(r"://[^:/\s]+:[^@\s]+@"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\b[A-Za-z0-9_=-]{48,}\b"),
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


def normalize_surface(surface: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", surface.strip().lower()).strip("_")
    aliases = {
        "backend": "backend_code",
        "code": "backend_code",
        "integration": "integrations",
        "llm": "compute",
        "llms": "compute",
        "reasoning_bank": "reasoning",
        "transcripts": "transcription",
        "audio": "transcription",
        "whatsapp": "channels",
        "telegram": "channels",
        "aura": "integrations",
    }
    return aliases.get(normalized, normalized)


def normalize_surfaces(surfaces: list[str] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for surface in surfaces or []:
        normalized = normalize_surface(str(surface))
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out or ["evaluation"]
