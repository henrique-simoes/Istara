"""One-row-per-dispatch usage ledger for agentic invocations.

Contract (master plan §5.5): every ``AgenticDispatcher`` call — success, error,
abort, endpoint-resolution failure, or legacy-executor failure — persists
exactly one durable, queryable row in ``agentic_usage_rows`` carrying the full
accounting payload. Exactness rules:

* Pi rows are exact when every sample carries provider-reported numbers from
  pi-ai ``Usage`` (incl. ``cost.total``); a mixed/absent Pi ensemble carries an
  explicit whole-dispatch estimate instead of a partial exact total.
* Legacy rows with provider-reported usage are exact.
* Absent provider usage is estimated with the existing ``count_tokens``
  estimator and flagged ``estimate=True`` — estimated and exact numbers are
  never mixed silently. Pre-dispatch failures (endpoint resolution, unbound or
  raising legacy executor) consumed nothing and persist zeroed exact rows with
  ``error_type`` set.

A short identity-only trace span (``event_kind="agentic_usage"``) is also
recorded for trace continuity; the ledger itself never lives inside the
120-char ``route_id`` identity field. Identity fields follow the CF-SPEC-7
rule: endpoint/node ids only, never URLs or keys.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.core.telemetry import telemetry_recorder
from app.core.token_counter import count_tokens
from app.models.agentic_usage import AgenticUsageRow
from app.models.database import async_session

logger = logging.getLogger(__name__)


def _provider_usage(outcome: dict[str, Any]) -> dict[str, Any] | None:
    """Return the provider-reported usage dict, or None when absent."""
    usage = outcome.get("usage")
    if not isinstance(usage, dict) or not usage:
        return None
    return usage


def _reported_sample_usage(sample: Any) -> dict[str, Any] | None:
    """Return one provider receipt only when it is present and non-estimated."""
    if not isinstance(sample, dict):
        return None
    usage = sample.get("usage")
    if (
        not isinstance(usage, dict)
        or not usage
        or bool(usage.get("estimate", False))
        or usage.get("usage_reported") is False
    ):
        return None
    if usage.get("usage_reported") is not True:
        numbers = _usage_numbers(usage)
        measured = (
            numbers["input_tokens"]
            or numbers["output_tokens"]
            or numbers["cache_read"]
            or numbers["cache_write"]
            or numbers["cost_usd"]
        )
        if not measured:
            return None
    return usage


def _pi_ensemble_usage(outcome: dict[str, Any]) -> dict[str, Any] | None:
    """Aggregate Pi samples only when every sample has a provider receipt.

    Pi's execution seam retains a compatibility aggregate for callers, but the
    ledger and public dispatcher result must not expose a partial exact total.
    A missing or estimated receipt therefore returns ``None`` and lets the
    ledger estimate the whole dispatch from the preserved sample texts.
    """
    samples = outcome.get("samples")
    if not isinstance(samples, list):
        return _provider_usage(outcome)
    if not samples:
        return None
    receipts = [_reported_sample_usage(sample) for sample in samples]
    if any(receipt is None for receipt in receipts):
        return None
    totals = [_usage_numbers(receipt) for receipt in receipts if receipt is not None]
    return {
        "input_tokens": sum(item["input_tokens"] for item in totals),
        "output_tokens": sum(item["output_tokens"] for item in totals),
        "cache_read": sum(item["cache_read"] for item in totals),
        "cache_write": sum(item["cache_write"] for item in totals),
        "total_tokens": sum(item["total_tokens"] for item in totals),
        "cost_usd": sum(item["cost_usd"] for item in totals),
        "turns": sum(item["turns"] for item in totals),
        "estimate": False,
    }


def authoritative_usage(engine: str, outcome: dict[str, Any]) -> dict[str, Any]:
    """Return the usage shape safe to expose to a dispatcher caller."""
    usage = _pi_ensemble_usage(outcome) if engine == "pi" else _provider_usage(outcome)
    return usage or {}


def _usage_numbers(usage: dict[str, Any]) -> dict[str, Any]:
    """Normalize pi-ai (camelCase) and legacy (snake_case) usage shapes."""
    input_tokens = int(usage.get("input_tokens", usage.get("input", 0)) or 0)
    output_tokens = int(usage.get("output_tokens", usage.get("output", 0)) or 0)
    cache_read = int(usage.get("cache_read", usage.get("cacheRead", 0)) or 0)
    cache_write = int(usage.get("cache_write", usage.get("cacheWrite", 0)) or 0)
    total = int(
        usage.get(
            "total_tokens",
            usage.get("totalTokens", input_tokens + output_tokens + cache_read + cache_write),
        )
        or 0
    )
    cost_raw = usage.get("cost")
    if isinstance(cost_raw, dict):
        cost = float(cost_raw.get("total", 0) or 0)
    elif cost_raw is not None:
        cost = float(cost_raw or 0)
    else:
        cost = float(usage.get("cost_usd", 0) or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read": cache_read,
        "cache_write": cache_write,
        "total_tokens": total,
        "cost_usd": cost,
        "turns": int(usage.get("turn_count", usage.get("turns", 1)) or 1),
    }


def _estimated_numbers(
    outcome: dict[str, Any], *, request_text: str, response_text: str | None
) -> dict[str, Any]:
    """Estimate a complete legacy dispatch from ephemeral per-call provenance."""
    trace = outcome.get("usage_estimation")
    if isinstance(trace, dict):
        request_texts = trace.get("request_texts")
        response_texts = trace.get("response_texts")
        if isinstance(request_texts, list) and isinstance(response_texts, list):
            safe_requests = [text for text in request_texts if isinstance(text, str)]
            safe_responses = [text for text in response_texts if isinstance(text, str)]
            if safe_requests or safe_responses:
                input_tokens = sum(count_tokens(text) for text in safe_requests)
                output_tokens = sum(count_tokens(text) for text in safe_responses)
                turns = int(trace.get("turns") or max(len(safe_requests), len(safe_responses), 1))
                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_read": 0,
                    "cache_write": 0,
                    "total_tokens": input_tokens + output_tokens,
                    "cost_usd": 0.0,
                    "turns": turns,
                }
    samples = outcome.get("samples")
    if isinstance(samples, list) and samples:
        responses = [
            sample.get("text")
            for sample in samples
            if isinstance(sample, dict) and isinstance(sample.get("text"), str)
        ]
        input_tokens = count_tokens(request_text) * len(samples)
        output_tokens = sum(count_tokens(text) for text in responses)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": 0,
            "cache_write": 0,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": 0.0,
            "turns": len(samples),
        }
    input_tokens = count_tokens(request_text)
    output_tokens = count_tokens(response_text or "")
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read": 0,
        "cache_write": 0,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": 0.0,
        "turns": 1,
    }


def _accounting_numbers(
    *,
    engine: str,
    outcome: dict[str, Any],
    request_text: str | None,
    response_text: str | None,
) -> tuple[dict[str, Any], bool]:
    """Select exact provider numbers, a complete estimate, or zero usage."""
    usage = _pi_ensemble_usage(outcome) if engine == "pi" else _provider_usage(outcome)
    if usage is not None:
        return _usage_numbers(usage), bool(usage.get("estimate", False))
    can_estimate = request_text is not None and (
        engine == "legacy"
        or (engine == "pi" and isinstance(outcome.get("samples"), list))
        or isinstance(outcome.get("usage_estimation"), dict)
    )
    if can_estimate:
        return _estimated_numbers(
            outcome, request_text=request_text or "", response_text=response_text
        ), True
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read": 0,
        "cache_write": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "turns": 0,
    }, False


def build_usage_row(
    *,
    engine: str,
    purpose: str,
    project_id: str,
    agent_id: str,
    outcome: dict[str, Any],
    model: str | None = None,
    started_at: float | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    spine_phase: str | None = None,
    node_id: str | None = None,
    request_text: str | None = None,
    response_text: str | None = None,
    error_type: str | None = None,
) -> AgenticUsageRow:
    """Build the ledger row for one dispatch, applying exact/estimate rules."""
    latency_ms = (time.perf_counter() - started_at) * 1000 if started_at else 0.0
    numbers, estimate = _accounting_numbers(
        engine=engine,
        outcome=outcome,
        request_text=request_text,
        response_text=response_text,
    )
    status = str(outcome.get("status", "success"))
    return AgenticUsageRow(
        id=uuid.uuid4().hex[:36],
        engine=engine,
        purpose=purpose[:120],
        project_id=project_id or "",
        session_id=session_id,
        agent_id=agent_id or "",
        task_id=task_id,
        spine_phase=(spine_phase or "")[:40],
        endpoint_id=str(outcome.get("endpoint_id") or "")[:120],
        node_id=(node_id or str(outcome.get("node_id") or ""))[:120],
        model=(model or str(outcome.get("model") or ""))[:200],
        input_tokens=numbers["input_tokens"],
        output_tokens=numbers["output_tokens"],
        cache_read=numbers["cache_read"],
        cache_write=numbers["cache_write"],
        total_tokens=numbers["total_tokens"],
        cost_usd=numbers["cost_usd"],
        tool_calls=len(outcome.get("tool_calls") or []),
        turns=numbers["turns"],
        latency_ms=latency_ms,
        stop_reason=str(outcome.get("stop_reason") or "")[:60],
        outcome=status if status in ("success", "error", "aborted") else "error",
        estimate=1 if estimate else 0,
        error_type=(error_type or str(outcome.get("error_type") or ""))[:80],
    )


async def record_agentic_usage(
    *,
    engine: str,
    purpose: str,
    project_id: str,
    agent_id: str,
    outcome: dict[str, Any],
    model: str | None = None,
    started_at: float | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    spine_phase: str | None = None,
    node_id: str | None = None,
    request_text: str | None = None,
    response_text: str | None = None,
    error_type: str | None = None,
) -> None:
    """Persist exactly one usage-ledger row plus a short identity trace span.

    Never load-bearing and never content-bearing: no endpoint URLs, keys,
    prompts, or responses — only counts and identity handles.
    """
    row = build_usage_row(
        engine=engine,
        purpose=purpose,
        project_id=project_id,
        agent_id=agent_id,
        outcome=outcome,
        model=model,
        started_at=started_at,
        session_id=session_id,
        task_id=task_id,
        spine_phase=spine_phase,
        node_id=node_id,
        request_text=request_text,
        response_text=response_text,
        error_type=error_type,
    )
    try:
        async with async_session() as session:
            session.add(row)
            await session.commit()
    except Exception as exc:  # telemetry is never load-bearing
        logger.debug("agentic usage ledger write failed: %s", exc)
    identity = row.endpoint_id or row.node_id or "unresolved"
    route_id = f"agentic:{engine}:{identity}"[:120]
    try:
        await telemetry_recorder.record_span(
            trace_id=f"agentic-{uuid.uuid4().hex}",
            operation=purpose,
            model_name=row.model,
            agent_id=row.agent_id,
            project_id=row.project_id,
            task_id=row.task_id,
            duration_ms=row.latency_ms,
            status=row.outcome,
            error_type=row.error_type or None,
            event_kind="agentic_usage",
            route_id=route_id,
            source="agentic_dispatcher",
        )
    except Exception:  # pragma: no cover - record_span already swallows errors
        logger.debug("agentic usage trace span failed")
