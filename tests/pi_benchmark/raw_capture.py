"""Raw LLM prompt/output capture (CF-321).

Implements comparison-Istara-pi/raw-llm-output-capture-requirements.md: every live
LLM call used in benchmark runs retains its prompt and output as gzipped JSONL under
``<run>/raw-llm-calls/{prompts,outputs}.jsonl.gz``, one record per call with a stable
``call_id``. Aggregate metrics are never enough — the owner inspects raw behavior.

Rules enforced here (from the requirements doc):

- Never store API keys or auth headers. Credentials appear only as presence booleans
  (``deepseek_key_present``). Any injected secret value is redacted wherever it
  appears, and every redaction is listed.
- Do NOT redact normal prompt text, assistant output, tool names/arguments, or
  scenario content — those are the comparison evidence.
- Prefer full text; cap only oversized payloads, recording full length, retained
  length, cap reason, and the sha256 of the full text.
- Import-safe at T0: stdlib only, no backend imports.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REDACTED = "[REDACTED]"
CAP_CHARS = 64_000

# Generic secret shapes (key-shaped tokens). The actual provider key value, when
# known, is redacted separately by exact match.
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[A-Za-z0-9._-]{12,}"),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cap_text(text: str) -> tuple[str, dict[str, Any] | None]:
    """Cap oversized text, returning (retained, capping-record-or-None)."""
    if len(text) <= CAP_CHARS:
        return text, None
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return text[:CAP_CHARS], {
        "full_length": len(text),
        "retained_length": CAP_CHARS,
        "cap_reason": "exceeds_cap_chars",
        "full_sha256": digest,
    }


def redact_secrets(
    value: Any, *, secret_values: tuple[str, ...] = ()
) -> tuple[Any, list[str]]:
    """Recursively redact secrets from a JSON-able value.

    Returns (redacted_value, redaction_descriptions). Redacts (a) exact matches of
    known secret values (e.g. the runtime API key), (b) key-shaped patterns, and
    (c) dict keys that name credentials outright.
    """
    redactions: list[str] = []

    def _scrub_text(text: str) -> str:
        out = text
        for secret in secret_values:
            if secret and secret in out:
                out = out.replace(secret, REDACTED)
                if "provider_api_key_value" not in redactions:
                    redactions.append("provider_api_key_value")
        for pattern in _SECRET_PATTERNS:
            if pattern.search(out):
                out = pattern.sub(
                    lambda m: (m.group(1) + REDACTED) if m.groups() else REDACTED, out
                )
                label = f"pattern:{pattern.pattern[:24]}"
                if label not in redactions:
                    redactions.append(label)
        return out

    def _walk(node: Any, path: str) -> Any:
        if isinstance(node, str):
            return _scrub_text(node)
        if isinstance(node, dict):
            scrubbed = {}
            for key, val in node.items():
                key_str = str(key)
                if key_str.lower() in {
                    "api_key",
                    "authorization",
                    "auth_header",
                    "token",
                    "secret",
                    "password",
                }:
                    scrubbed[key_str] = REDACTED
                    redactions.append(f"credential_field:{path}/{key_str}")
                    continue
                scrubbed[key_str] = _walk(val, f"{path}/{key_str}")
            return scrubbed
        if isinstance(node, (list, tuple)):
            return [_walk(item, f"{path}[{index}]") for index, item in enumerate(node)]
        return node

    return _walk(value, "$"), redactions


class RawCaptureWriter:
    """Crash-safe appender for prompts.jsonl.gz / outputs.jsonl.gz.

    Each append opens, writes one JSON line, and closes — a killed process loses at
    most the in-flight record, never earlier ones (multi-member gzip stays readable).
    """

    def __init__(self, raw_dir: Path | str) -> None:
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _append(self, name: str, record: dict[str, Any]) -> None:
        path = self.raw_dir / name
        with gzip.open(path, "at", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def record_prompt(
        self,
        *,
        call_id: str,
        scenario_id: str,
        engine_path: str,
        provider: str,
        model: str,
        adapter_mode: str,
        settings: dict[str, Any],
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]] | None = None,
        secret_values: tuple[str, ...] = (),
    ) -> None:
        payload = {
            "call_id": call_id,
            "scenario_id": scenario_id,
            "engine_path": engine_path,
            "provider": provider,
            "model": model,
            "timestamp": utc_now_iso(),
            "adapter_mode": adapter_mode,
            "settings": settings,
            "messages": messages,
            "tool_schemas": tool_schemas or [],
        }
        redacted, redactions = redact_secrets(payload, secret_values=secret_values)
        redacted["redactions"] = redactions
        self._append("prompts.jsonl.gz", redacted)

    def record_output(
        self,
        *,
        call_id: str,
        scenario_id: str,
        engine_path: str,
        provider: str,
        model: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        stop_reason: str | None = None,
        error: str | None = None,
        latency_s: float | None = None,
        usage: dict[str, Any] | None = None,
        cost_usd: float | None = None,
        secret_values: tuple[str, ...] = (),
    ) -> None:
        retained, capping = cap_text(content or "")
        payload = {
            "call_id": call_id,
            "scenario_id": scenario_id,
            "engine_path": engine_path,
            "provider": provider,
            "model": model,
            "timestamp": utc_now_iso(),
            "content": retained,
            "tool_calls": tool_calls or [],
            "stop_reason": stop_reason,
            "error": error,
            "latency_s": latency_s,
            "usage": usage,
            "cost_usd": cost_usd,
            "capping": capping,
        }
        redacted, redactions = redact_secrets(payload, secret_values=secret_values)
        redacted["redactions"] = redactions
        self._append("outputs.jsonl.gz", redacted)


def read_records(path: Path | str) -> list[dict[str, Any]]:
    """Read back a gzipped JSONL capture file (verification/tests)."""
    records = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records
