"""F-W1-R1-2: real-path usage-ledger exactness (no rich usage stubs).

The delta review found the green ledger suite proved the accounting rules only
against hand-built usage dicts. These tests exercise the REAL seams end to end:

* the real Istara legacy executor (``legacy.py`` ``_react_loop``) driving a
  scripted Pi provider authority, so a multi-turn ReAct loop persists
  *cumulative* provider usage with the real turn count, provider-reported usage
  is exact, and *absent* provider usage is estimated by the ledger (never a
  fabricated exact-zero row); and
* the real Pi worker over the real ``openai_compat`` stack against a loopback
  reporting cache usage, so the worker-computed cache-read tokens and turn count
  survive ``run.completed`` → engine → dispatcher → the persisted ledger row.

The complementary worker-side proofs live in ``pi-runtime/test/hardening.test.mjs``
("run.completed usage carries cache tokens …" / "… cumulative across a real
multi-turn tool loop").
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from sqlalchemy import select

from app.core.agentic import legacy
from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import TurnParams
from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.agentic_usage import AgenticUsageRow
from app.models.database import async_session, init_db

from .harness import requires_node


class _ScriptedPiAuthority:
    """Scripted Pi Model Management seam used by the real Istara loop."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.calls = 0

    def _next(self) -> dict[str, Any]:
        self.calls += 1
        response = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return legacy._normalize_chat(response)

    async def run_provider_turn(self, **kwargs):
        outcome = self._next()
        outcome.update(endpoint_id="pi-scripted", model="gpt-x")
        return outcome

    async def run_completion(self, **kwargs):
        outcome = self._next()
        outcome.update(endpoint_id="pi-scripted", model="gpt-x")
        return outcome

    async def run_ensemble(self, **kwargs):
        samples = [await self.run_completion(**kwargs) for _ in range(kwargs["n"])]
        return {
            "samples": samples,
            "endpoint_ids": [sample["endpoint_id"] for sample in samples],
            "usage": legacy._sum_usage(samples),
            "usage_estimation": {
                "request_texts": [json.dumps(kwargs["messages"])] * len(samples),
                "response_texts": [sample["text"] for sample in samples],
                "turns": len(samples),
            },
            "status": "success",
        }


async def _usage_rows(project_id: str) -> list[AgenticUsageRow]:
    async with async_session() as db:
        result = await db.execute(
            select(AgenticUsageRow).where(AgenticUsageRow.project_id == project_id)
        )
        return list(result.scalars().all())


def _pid() -> str:
    return f"w1-realacct-{uuid.uuid4().hex[:12]}"


# ── real legacy executor seam ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_real_legacy_react_accumulates_multi_turn_usage(monkeypatch):
    """A real two-turn legacy ReAct loop persists cumulative provider usage and
    the actual turn count — not the final turn's usage recorded as one turn."""
    await init_db()
    project_id = _pid()
    fake = _ScriptedPiAuthority([
        # Turn 1: a tool call; provider reports 100 in / 10 out.
        {"message": {"content": "", "tool_calls": [
            {"function": {"name": "search_documents", "arguments": {}}}]},
         "prompt_eval_count": 100, "eval_count": 10},
        # Turn 2: final text; provider reports 200 in / 20 out.
        {"message": {"content": "final answer"},
         "prompt_eval_count": 200, "eval_count": 20},
    ])

    async def tool_executor(name, arguments, pid, aid):
        return {"ok": True, "result": "done"}

    result = await AgenticDispatcher(pi_service=fake).react(
        purpose="w1.realacct.react", project_id=project_id, agent_id="istara-main",
        session_key=None, system="system", messages=[], user_text="do the task",
        tool_executor=tool_executor, tool_names=["search_documents"],
        params=TurnParams(model="gpt-x"), engine="legacy",
    )
    assert result.status == "success"
    assert fake.calls == 2  # the loop really ran two provider turns
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.estimate == 0  # provider-reported usage is exact
    assert row.input_tokens == 300 and row.output_tokens == 30  # cumulative, not final-turn-only
    assert row.total_tokens == 330
    assert row.turns == 2  # the real turn count, not the defaulted 1


@pytest.mark.asyncio
async def test_real_legacy_provider_usage_is_exact(monkeypatch):
    """The real ``_normalize_chat`` maps an ollama ``usage`` block to an exact,
    unestimated ledger row."""
    await init_db()
    project_id = _pid()
    fake = _ScriptedPiAuthority([
        {"message": {"content": "ok"},
         "usage": {"prompt_tokens": 55, "completion_tokens": 21, "total_tokens": 76}},
    ])

    await AgenticDispatcher(pi_service=fake).completion(
        purpose="w1.realacct.exact", project_id=project_id, system="system",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(model="gpt-x"),
        engine="legacy",
    )
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.estimate == 0
    assert row.input_tokens == 55 and row.output_tokens == 21 and row.total_tokens == 76


@pytest.mark.asyncio
async def test_real_legacy_absent_usage_is_estimated(monkeypatch):
    """When the real legacy provider reports no usage, ``_normalize_chat`` leaves
    it absent so the ledger runs its ``count_tokens`` estimator and flags the row
    estimated — never a fabricated exact-zero row that suppresses estimation."""
    await init_db()
    project_id = _pid()
    fake = _ScriptedPiAuthority([
        {"message": {"content": "an answer with no usage block at all"}},
    ])

    await AgenticDispatcher(pi_service=fake).completion(
        purpose="w1.realacct.estimate", project_id=project_id, system="system prompt",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(model="gpt-x"),
        engine="legacy",
    )
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.estimate == 1
    assert row.input_tokens > 0 and row.output_tokens > 0
    assert row.total_tokens == row.input_tokens + row.output_tokens


@pytest.mark.asyncio
async def test_real_legacy_react_mixed_usage_is_estimated_not_partial_exact(monkeypatch):
    """F-W1-R2-1: a ReAct loop whose first turn reports provider usage and whose
    final turn reports none is *mixed*. Exactness is all-or-nothing, so the
    aggregate must NOT be persisted as a partial exact total — the old bug
    dropped the absent turn and recorded input=100/output=10/turns=2/estimate=0.
    The ledger must instead estimate the complete dispatch and flag it."""
    await init_db()
    project_id = _pid()
    fake = _ScriptedPiAuthority([
        # Turn 1: a tool call; provider reports 100 in / 10 out.
        {"message": {"content": "", "tool_calls": [
            {"function": {"name": "search_documents", "arguments": {}}}]},
         "prompt_eval_count": 100, "eval_count": 10},
        # Turn 2: final text; provider reports NO usage at all.
        {"message": {"content": "final answer"}},
    ])

    async def tool_executor(name, arguments, pid, aid):
        return {"ok": True, "result": "done"}

    result = await AgenticDispatcher(pi_service=fake).react(
        purpose="w1.realacct.react.mixed", project_id=project_id, agent_id="istara-main",
        session_key=None, system="system", messages=[], user_text="do the task",
        tool_executor=tool_executor, tool_names=["search_documents"],
        params=TurnParams(model="gpt-x"), engine="legacy",
    )
    assert result.status == "success"
    assert fake.calls == 2  # the loop really ran two provider turns
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    # Mixed run → governed text estimate, never the reported subset as exact.
    assert row.estimate == 1
    assert not (row.input_tokens == 100 and row.output_tokens == 10)  # not the partial subset
    assert row.input_tokens > 0 and row.output_tokens > 0
    assert row.total_tokens == row.input_tokens + row.output_tokens
    assert row.turns == 2


@pytest.mark.asyncio
async def test_real_legacy_ensemble_all_reported_usage_is_exact_cumulative(monkeypatch):
    """A legacy ensemble whose every sample reports provider usage persists the
    cumulative exact total with one turn per sample — the exact path this fix
    must keep intact."""
    await init_db()
    project_id = _pid()
    fake = _ScriptedPiAuthority([
        {"message": {"content": "a"}, "prompt_eval_count": 100, "eval_count": 10},
        {"message": {"content": "b"}, "prompt_eval_count": 200, "eval_count": 20},
    ])

    result = await AgenticDispatcher(pi_service=fake).ensemble(
        purpose="w1.realacct.ensemble.exact", project_id=project_id, system="system",
        messages=[{"role": "user", "content": "hello"}], n=2,
        params=TurnParams(model="gpt-x"), engine="legacy",
    )
    assert result.status == "success"
    assert fake.calls == 2
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.estimate == 0  # every sample reported → exact
    assert row.input_tokens == 300 and row.output_tokens == 30
    assert row.total_tokens == 330
    assert row.turns == 2  # one turn per sample, not the defaulted 1


@pytest.mark.asyncio
async def test_real_legacy_ensemble_mixed_usage_is_estimated_not_partial_exact(monkeypatch):
    """F-W1-R2-1 (ensemble seam): an ensemble where one sample reports provider
    usage and another reports none is mixed — estimated for the complete
    dispatch, never the reported subset (input=100/output=10) persisted exact."""
    await init_db()
    project_id = _pid()
    fake = _ScriptedPiAuthority([
        {"message": {"content": "a"}, "prompt_eval_count": 100, "eval_count": 10},
        {"message": {"content": "b with no usage block"}},  # provider reports nothing
    ])

    result = await AgenticDispatcher(pi_service=fake).ensemble(
        purpose="w1.realacct.ensemble.mixed", project_id=project_id, system="system prompt",
        messages=[{"role": "user", "content": "hello"}], n=2,
        params=TurnParams(model="gpt-x"), engine="legacy",
    )
    assert result.status == "success"
    assert fake.calls == 2
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    # Mixed → estimated, not the reported subset recorded as an exact total.
    assert row.estimate == 1
    assert not (row.input_tokens == 100 and row.output_tokens == 10)
    assert row.input_tokens > 3  # both provider requests, not the old single-request estimate
    assert row.output_tokens > 0  # both non-empty sample outputs are represented
    assert row.total_tokens == row.input_tokens + row.output_tokens
    assert row.turns == 2


# ── real Pi worker seam (full stack, non-faux) ───────────────────────────────


class _CacheUsageStubHandler(BaseHTTPRequestHandler):
    """Loopback ``openai_compat`` stub reporting a partially cache-hit prompt so
    the REAL worker computes cache-read usage the ledger must persist: 400
    cache-miss input + 600 cache-read + 50 output."""

    def log_message(self, *args):  # silence
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        content = {"choices": [{"index": 0, "delta": {"content": "Cached reply."}}]}
        self.wfile.write(f"data: {json.dumps(content)}\n\n".encode())
        done = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        self.wfile.write(f"data: {json.dumps(done)}\n\n".encode())
        usage = {"choices": [], "usage": {
            "prompt_tokens": 1000, "prompt_cache_hit_tokens": 600, "completion_tokens": 50}}
        self.wfile.write(f"data: {json.dumps(usage)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class _FixedResolver:
    def __init__(self, endpoint: ResolvedPiEndpoint) -> None:
        self._endpoint = endpoint

    def resolve(self, endpoint_id: str, *, model=None) -> ResolvedPiEndpoint:
        return self._endpoint


@requires_node
@pytest.mark.asyncio
async def test_real_pi_worker_usage_reaches_ledger_with_cache_and_turns():
    """Full-stack non-faux proof: a real ``openai_compat`` turn whose provider
    reports cache-read usage persists the worker-computed cache tokens and the
    turn count through ``run.completed`` → engine → dispatcher → the ledger row
    (both were dropped/defaulted before the fix), exact and unestimated."""
    await init_db()
    project_id = _pid()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CacheUsageStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-cache-ledger-loopback",
        provider_kind="openai_compat",
        base_url=base_url,
        model="stub-model",
        api_key="loopback-test-key",
        timeout_ms=30000,
        max_retries=0,
        # Price every category this turn spends (input/output/cache-read) so the
        # default per-run cost ceiling is satisfied — a few thousand tokens cost
        # well under a cent. This test proves token accounting, not the ceiling.
        cost_input_per_mtok=1.0,
        cost_output_per_mtok=2.0,
        cost_cache_read_per_mtok=0.4,
    )
    supervisor = PiRuntimeSupervisor()
    service = PiExecutionService(resolver=_FixedResolver(endpoint), supervisor=supervisor)
    try:
        result = await AgenticDispatcher(pi_service=service).completion(
            purpose="w1.realacct.pi", project_id=project_id, system="system",
            messages=[{"role": "user", "content": "hello"}],
            params=TurnParams(), engine="pi",
        )
    finally:
        await supervisor.shutdown()
        server.shutdown()

    assert result.status == "success"
    rows = await _usage_rows(project_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.engine == "pi" and row.estimate == 0
    assert row.output_tokens == 50
    assert row.cache_read == 600  # dropped entirely before the fix
    assert row.cache_write == 0
    assert row.input_tokens == 400  # cache-miss input = prompt_tokens - cache-hit
    assert row.total_tokens == 1050  # input + output + cache_read + cache_write
    assert row.turns == 1  # a single assistant turn, not the defaulted-but-correct 1
