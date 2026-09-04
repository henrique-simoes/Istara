"""Provider-specific adapters for Istara structured LLM contracts.

Istara keeps one canonical structured-output shape internally, then translates
that shape to the request fields each serving endpoint expects. The canonical
shape follows OpenAI-compatible ``response_format`` because that is what LM
Studio and most OpenAI-compatible local servers expose.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


ANTHROPIC_STRUCTURED_TOOL_NAME = "istara_emit_structured_response"
NORMALIZED_SKILL_OUTPUT_FIELDS = (
    "summary",
    "nuggets",
    "facts",
    "insights",
    "recommendations",
    "suggestions",
)
THINKING_BLOCK_PATTERNS = (
    r"<think>.*?</think>",
    r"<thinking>.*?</thinking>",
    r"<thought>.*?</thought>",
    r"\[thinking\].*?\[/thinking\]",
    r"\[thought\].*?\[/thought\]",
)


@dataclass(frozen=True)
class SchemaBudgetResult:
    """Decision record for a schema passed to an LLM request."""

    schema_name: str
    schema_tokens: int
    max_schema_tokens: int
    used_fallback: bool
    reason: str
    preserved_fields: tuple[str, ...] = NORMALIZED_SKILL_OUTPUT_FIELDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_name": self.schema_name,
            "schema_tokens": self.schema_tokens,
            "max_schema_tokens": self.max_schema_tokens,
            "used_fallback": self.used_fallback,
            "reason": self.reason,
            "preserved_fields": list(self.preserved_fields),
        }


def openai_json_schema_response_format(
    *,
    name: str,
    schema: dict[str, Any],
    strict: bool = True,
) -> dict[str, Any]:
    """Build Istara's canonical OpenAI-compatible JSON Schema wrapper."""

    safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")[:64] or "istara_output"
    return {
        "type": "json_schema",
        "json_schema": {
            "name": safe_name,
            "schema": schema,
            "strict": bool(strict),
        },
    }


def extract_json_schema(response_format: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the raw JSON Schema object from a canonical response format."""

    if not isinstance(response_format, dict):
        return None
    if response_format.get("type") == "json_schema":
        wrapped = response_format.get("json_schema")
        if isinstance(wrapped, dict):
            schema = wrapped.get("schema")
            if isinstance(schema, dict):
                return schema
            if wrapped.get("type"):
                return wrapped
    if response_format.get("type") == "object":
        return response_format
    return None


def response_format_name(
    response_format: dict[str, Any] | None, default: str = "istara_output"
) -> str:
    if isinstance(response_format, dict):
        wrapped = response_format.get("json_schema")
        if isinstance(wrapped, dict) and isinstance(wrapped.get("name"), str):
            return wrapped["name"]
    return default


def ollama_format_from_response_format(response_format: dict[str, Any]) -> Any:
    """Translate canonical response_format into Ollama's ``format`` value."""

    if response_format.get("type") == "json_object":
        return "json"
    schema = extract_json_schema(response_format)
    return schema if schema is not None else response_format


def provider_response_format_fields(
    provider_type: str | None,
    response_format: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return provider-specific request fields for structured final output."""

    if not response_format:
        return {}
    provider = (provider_type or "openai_compat").strip().lower()
    if provider == "ollama":
        return {"format": ollama_format_from_response_format(response_format)}
    if provider in {"gemini", "google_gemini", "gemini_native"}:
        schema = extract_json_schema(response_format)
        if schema:
            return {
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": schema,
                }
            }
    if provider in {"anthropic", "anthropic_compat"}:
        return {}
    return {"response_format": response_format}


def anthropic_structured_output_tool(
    response_format: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Represent final structured output as a forced Anthropic tool."""

    schema = extract_json_schema(response_format)
    if not schema:
        return None
    name = response_format_name(response_format, ANTHROPIC_STRUCTURED_TOOL_NAME)
    return {
        "name": ANTHROPIC_STRUCTURED_TOOL_NAME,
        "description": (
            "Return Istara's final structured JSON response. Use this tool only "
            f"when the requested output schema is {name}."
        ),
        "input_schema": schema,
    }


def normalize_anthropic_structured_tool_block(block: dict[str, Any]) -> str | None:
    """Return JSON content when Anthropic used the forced structured-output tool."""

    if block.get("type") != "tool_use" or block.get("name") != ANTHROPIC_STRUCTURED_TOOL_NAME:
        return None
    payload = block.get("input")
    if not isinstance(payload, dict):
        payload = {}
    return json.dumps(payload, ensure_ascii=False)


def strip_thinking_markers(text: str) -> str:
    """Remove common visible reasoning blocks before parsing final JSON."""

    cleaned = text or ""
    for pattern in THINKING_BLOCK_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Parse an object from a model response with markdown/prose tolerance."""

    raw = strip_thinking_markers(text)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", raw):
        try:
            parsed, _ = decoder.raw_decode(raw[match.start() :])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            continue
    return None
