"""Pure schemas, constants, and payload parsers for the research-validity coding plane."""

from __future__ import annotations

import logging

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
import json
import re


logger = logging.getLogger(__name__)


CoderRunner = Callable[[Any, list[dict], str | None, str], Awaitable[dict]]


ACCEPTED_PROMOTION_STATUSES = {"accepted", "accepted_after_reconciliation"}


RECONCILED_CODE_APPLICATION_STATUSES = {"accepted", "reconciled"}


MAX_CODING_SOURCE_TEXT_CHARS = 700


QWEN_RATE_LIMIT_FALLBACK_CHAINS = {
    "qwen3.7-plus": ("qwen3.7-plus", "qwen3.7-plus-2026-05-26"),
    "qwen3.7-flash": ("qwen3.7-flash", "qwen3.7-flash-2026-07-15"),
}


QWEN_FALLBACK_ONLY_MODELS = tuple(chain[1] for chain in QWEN_RATE_LIMIT_FALLBACK_CHAINS.values())


DASHSCOPE_COMPAT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


CODING_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "applications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "evidence_unit_id": {"type": "string"},
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "primary_code": {"type": "string"},
                    "quote": {"type": "string"},
                    "confidence": {"type": "number"},
                    "rationale": {"type": "string"},
                    "memo": {"type": "string"},
                    "span_start": {"type": "integer"},
                    "span_end": {"type": "integer"},
                    "ambiguity": {"type": "string"},
                    "needs_codebook_revision": {"type": "boolean"},
                },
                "required": [
                    "evidence_unit_id",
                    "codes",
                    "primary_code",
                    "quote",
                    "confidence",
                ],
            },
        }
    },
    "required": ["applications"],
}


CODING_CORE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "applications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "evidence_unit_id": {"type": "string"},
                    "codes": {"type": "array", "items": {"type": "string"}},
                    "primary_code": {"type": "string"},
                    "quote": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "evidence_unit_id",
                    "codes",
                    "primary_code",
                    "quote",
                    "confidence",
                ],
            },
        }
    },
    "required": ["applications"],
}


def _json_list_value(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item or "").strip()]


@dataclass(slots=True)
class CoderSpec:
    node: Any
    coder_id: str
    model_name: str
    # Production Pi selections retain the manager and exact resolved identity
    # so a catalog mutation can be rejected before dispatch.
    pi_manager: Any | None = None
    # Keep the request-scoped execution facade selected alongside the manager.
    # Dispatch can therefore preserve the same authority and usage accounting
    # instead of silently falling back to a process-wide Pi service.
    pi_service: Any | None = None
    pi_endpoint_identity: tuple[str, ...] | None = None


class QwenRateLimitFallbackError(RuntimeError):
    """A rate-limited Qwen slot could not complete with an admitted fallback."""

    def __init__(self, message: str, *, attempts: list[dict[str, str]]) -> None:
        self.attempts = attempts
        super().__init__(message)


def _extract_json_payload(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if isinstance(parsed, list):
        return {"applications": parsed}
    if not isinstance(parsed, dict):
        raise ValueError("Coding response must be a JSON object or list.")
    return parsed


def _application_items(parsed: dict) -> list[dict]:
    """Accept common JSON variants without treating prose as coded evidence."""
    candidate_keys = (
        "applications",
        "code_applications",
        "coding_applications",
        "evidence_units",
        "items",
        "results",
    )
    for key in candidate_keys:
        value = parsed.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if any(
        key in parsed
        for key in (
            "evidence_unit_id",
            "unit_id",
            "id",
            "evidence_unit_stable_id",
            "stable_id",
            "unit_index",
        )
    ):
        return [parsed]
    return []


def _code_list(raw: dict) -> list[str]:
    codes = raw.get("codes")
    if codes is None:
        codes = [raw.get("code_id") or raw.get("primary_code")]
    if not isinstance(codes, list):
        codes = [codes]
    normalized: list[str] = []
    for code in codes:
        if isinstance(code, dict):
            value = code.get("code_id") or code.get("label") or code.get("name")
        else:
            value = code
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.5
    return max(0.0, min(1.0, score))
