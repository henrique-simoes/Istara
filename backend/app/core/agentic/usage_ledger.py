"""Content-free usage telemetry for one dispatcher invocation."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.core.telemetry import telemetry_recorder


async def record_agentic_usage(
    *, engine: str, purpose: str, project_id: str, agent_id: str,
    outcome: dict[str, Any], model: str | None = None, started_at: float | None = None,
) -> None:
    """Persist a safe usage row through telemetry; never include endpoint URLs/keys."""
    usage = outcome.get("usage") or {}
    input_tokens = usage.get("input_tokens", usage.get("input", 0))
    output_tokens = usage.get("output_tokens", usage.get("output", 0))
    cache_read = usage.get("cache_read", usage.get("cacheRead", 0))
    cache_write = usage.get("cache_write", usage.get("cacheWrite", 0))
    total = usage.get("total_tokens", usage.get("totalTokens", input_tokens + output_tokens + cache_read + cache_write))
    cost = usage.get("cost_usd", usage.get("cost", {}).get("total", 0)) if isinstance(usage.get("cost"), dict) else usage.get("cost_usd", 0)
    metadata = {
        "engine": engine, "purpose": purpose, "endpoint_id": outcome.get("endpoint_id"),
        "input_tokens": input_tokens, "output_tokens": output_tokens, "cache_read": cache_read,
        "cache_write": cache_write, "total_tokens": total, "cost_usd": cost,
        "tool_calls": len(outcome.get("tool_calls") or []), "turns": usage.get("turn_count", 1),
        "stop_reason": outcome.get("stop_reason"), "outcome": outcome.get("status", "success"),
        "estimate": bool(usage.get("estimate", engine == "legacy")),
    }
    await telemetry_recorder.record_span(
        trace_id=f"agentic-{uuid.uuid4().hex}", operation=purpose, model_name=model or "",
        agent_id=agent_id, project_id=project_id, duration_ms=(time.perf_counter() - started_at) * 1000 if started_at else 0,
        status="success" if metadata["outcome"] == "success" else "error", event_kind="agentic_usage",
        route_id=json.dumps(metadata, sort_keys=True), source="agentic_dispatcher",
    )
