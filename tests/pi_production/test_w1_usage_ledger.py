"""W1 usage-ledger contracts: persistence-level exact-vs-estimated and exception paths.

F-W1-3: every dispatcher call — success, error, abort, endpoint-resolution
failure, legacy-executor failure — persists exactly one durable, queryable row
in ``agentic_usage_rows``. Pi and provider-reported legacy usage are exact;
only absent legacy provider usage is estimated (estimate=1). The ledger never
lives inside the 120-char ``route_id`` identity field.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import AgenticDispatchError, TurnParams
from app.core.pi_runtime.endpoints import PiEndpointResolutionError
from app.models.agentic_usage import AgenticUsageRow
from app.models.database import async_session, init_db
from app.models.telemetry_span import TelemetrySpan


class _StubPiService:
    """Pi seam stub: returns a scripted outcome or raises a scripted failure."""

    def __init__(self, outcome: dict | None = None, exc: Exception | None = None) -> None:
        self._outcome = outcome or {}
        self._exc = exc

    async def run_completion(self, **_kwargs):
        if self._exc is not None:
            raise self._exc
        return dict(self._outcome)


async def _usage_rows(project_id: str) -> list[AgenticUsageRow]:
    async with async_session() as db:
        result = await db.execute(
            select(AgenticUsageRow).where(AgenticUsageRow.project_id == project_id)
        )
        return list(result.scalars().all())


async def _trace_spans(project_id: str) -> list[TelemetrySpan]:
    async with async_session() as db:
        result = await db.execute(
            select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.event_kind == "agentic_usage",
            )
        )
        return list(result.scalars().all())


def _pid() -> str:
    return f"w1-ledger-{uuid.uuid4().hex[:12]}"


@pytest.mark.asyncio
async def test_pi_provider_usage_persists_one_exact_row():
    await init_db()
    project_id = _pid()
    outcome = {
        "text": "done",
        "status": "success",
        "stop_reason": "stop",
        "endpoint_id": "pi-faux",
        "model": "requested-model",
        "served_model": "served-model",
        "usage": {"input": 120, "output": 34, "cacheRead": 8, "cacheWrite": 2,
                  "cost": {"total": 0.0042}, "turn_count": 3},
        "tool_calls": [{"tool": "search_documents", "params": {}}],
    }
    result = await AgenticDispatcher(pi_service=_StubPiService(outcome)).completion(
        purpose="w1.ledger.pi", project_id=project_id, system="system",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(model="deepseek-v4-pro"),
        engine="pi", task_id="task-1", spine_phase="execution",
    )
    assert result.status == "success"
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.engine == "pi" and row.purpose == "w1.ledger.pi"
    assert row.estimate == 0  # Pi usage is exact from pi-ai, never estimated
    assert row.input_tokens == 120 and row.output_tokens == 34
    assert row.cache_read == 8 and row.cache_write == 2
    assert row.total_tokens == 164 and row.cost_usd == pytest.approx(0.0042)
    assert row.turns == 3 and row.tool_calls == 1
    assert row.endpoint_id == "pi-faux" and row.model == "served-model"
    assert row.task_id == "task-1" and row.spine_phase == "execution"
    assert row.outcome == "success" and row.stop_reason == "stop"
    assert row.latency_ms >= 0 and row.error_type == ""


@pytest.mark.asyncio
async def test_legacy_provider_reported_usage_is_exact_not_estimated():
    await init_db()
    project_id = _pid()

    async def legacy(**_kwargs):
        return {"text": "ok", "status": "success", "stop_reason": "stop",
                "usage": {"input_tokens": 55, "output_tokens": 21, "cost_usd": 0.001}}

    await AgenticDispatcher(legacy_executor=legacy).completion(
        purpose="w1.ledger.legacy", project_id=project_id, system="system",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(model="gpt-x"),
        engine="legacy",
    )
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    # Regression: provider-reported legacy usage must not be flagged estimated.
    assert row.estimate == 0
    assert row.input_tokens == 55 and row.output_tokens == 21
    assert row.total_tokens == 76 and row.cost_usd == pytest.approx(0.001)


@pytest.mark.asyncio
async def test_legacy_absent_provider_usage_is_estimated_and_flagged():
    await init_db()
    project_id = _pid()

    async def legacy(**_kwargs):
        return {"text": "an answer with no usage block", "status": "success"}

    await AgenticDispatcher(legacy_executor=legacy).completion(
        purpose="w1.ledger.estimate", project_id=project_id, system="system prompt",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(model="gpt-x"),
        engine="legacy",
    )
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.estimate == 1  # only absent provider usage is estimated
    assert row.input_tokens > 0 and row.output_tokens > 0
    assert row.total_tokens == row.input_tokens + row.output_tokens


@pytest.mark.asyncio
async def test_endpoint_resolution_failure_records_error_row():
    await init_db()
    project_id = _pid()
    service = _StubPiService(exc=PiEndpointResolutionError("unknown_pi_endpoint"))
    with pytest.raises(PiEndpointResolutionError):
        await AgenticDispatcher(pi_service=service).completion(
            purpose="w1.ledger.resolution", project_id=project_id, system="system",
            messages=[{"role": "user", "content": "hello"}], params=TurnParams(), engine="pi",
        )
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.outcome == "error" and row.error_type == "PiEndpointResolutionError"
    assert row.estimate == 0 and row.total_tokens == 0 and row.cost_usd == 0
    assert row.latency_ms >= 0


@pytest.mark.asyncio
async def test_legacy_executor_failure_and_unbound_engine_record_error_rows():
    await init_db()
    project_id = _pid()

    async def failing_legacy(**_kwargs):
        raise RuntimeError("provider exploded")

    with pytest.raises(RuntimeError, match="provider exploded"):
        await AgenticDispatcher(legacy_executor=failing_legacy).completion(
            purpose="w1.ledger.legacy_fail", project_id=project_id, system="system",
            messages=[{"role": "user", "content": "hello"}], params=TurnParams(), engine="legacy",
        )
    with pytest.raises(AgenticDispatchError, match="legacy_engine_not_bound"):
        dispatcher = AgenticDispatcher()
        dispatcher._legacy = None  # pin the fail-closed guard in _legacy_outcome
        await dispatcher.completion(
            purpose="w1.ledger.unbound", project_id=project_id, system="system",
            messages=[{"role": "user", "content": "hello"}], params=TurnParams(), engine="legacy",
        )
    rows = await _usage_rows(project_id)
    assert len(rows) == 2
    by_purpose = {row.purpose: row for row in rows}
    assert by_purpose["w1.ledger.legacy_fail"].outcome == "error"
    assert by_purpose["w1.ledger.legacy_fail"].error_type == "RuntimeError"
    assert by_purpose["w1.ledger.unbound"].outcome == "error"
    assert by_purpose["w1.ledger.unbound"].error_type == "AgenticDispatchError"
    assert all(row.total_tokens == 0 for row in rows)


@pytest.mark.asyncio
async def test_aborted_outcome_records_aborted_row_with_exact_usage():
    await init_db()
    project_id = _pid()
    outcome = {"text": "", "status": "aborted",
               "usage": {"input": 40, "output": 3, "cost": {"total": 0.0005}}}
    result = await AgenticDispatcher(pi_service=_StubPiService(outcome)).completion(
        purpose="w1.ledger.abort", project_id=project_id, system="system",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(), engine="pi",
    )
    assert result.status == "aborted"
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.outcome == "aborted" and row.estimate == 0
    assert row.input_tokens == 40 and row.output_tokens == 3
    assert row.cost_usd == pytest.approx(0.0005)


@pytest.mark.asyncio
async def test_trace_span_keeps_short_identity_route_id_not_packed_ledger():
    await init_db()
    project_id = _pid()
    outcome = {"text": "done", "status": "success", "endpoint_id": "pi-faux",
               "usage": {"input": 10, "output": 5}}
    await AgenticDispatcher(pi_service=_StubPiService(outcome)).completion(
        purpose="w1.ledger.span", project_id=project_id, system="system",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(), engine="pi",
        task_id="task-9",
    )
    spans = await _trace_spans(project_id)
    assert len(spans) == 1
    span = spans[0]
    assert len(span.route_id) <= 120
    assert not span.route_id.startswith("{")  # ledger is not packed into route_id
    assert "pi-faux" in span.route_id
    assert span.task_id == "task-9" and span.status == "success"
    assert "input_tokens" not in span.route_id and "cost" not in span.route_id
