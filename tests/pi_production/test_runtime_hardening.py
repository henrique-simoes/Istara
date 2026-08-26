"""Focused W0 regressions for recovery, budget propagation, and pool capacity."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.agentic.types import TurnParams
from app.core.pi_runtime.endpoints import (
    DEFAULT_ENDPOINT_ID,
    PiEndpointResolutionError,
    PiEndpointResolver,
    ResolvedPiEndpoint,
)
from app.core.pi_runtime.engine import (
    PiExecutionService,
    _bind_payload,
    _enforce_test_provider_network_policy,
)
from app.core.pi_runtime.model_manager import PiModelManager
from app.core.pi_runtime.pool import PiRuntimePool
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

from .harness import faux_endpoint, final_text, requires_node, tool_call


def test_unit_suite_blocks_real_external_provider_before_worker_start(monkeypatch):
    monkeypatch.setenv("ISTARA_TEST_BLOCK_EXTERNAL_LLM", "1")
    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-live-forbidden",
        provider_kind="openai_compat",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key="unused-test-secret",
        timeout_ms=30_000,
        max_retries=0,
    )

    with pytest.raises(
        PiEndpointResolutionError, match="external_provider_blocked_in_test"
    ):
        _enforce_test_provider_network_policy(endpoint)


def test_unit_suite_allows_reserved_provider_test_domain(monkeypatch):
    monkeypatch.setenv("ISTARA_TEST_BLOCK_EXTERNAL_LLM", "1")
    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-scripted",
        provider_kind="openai_compat",
        base_url="https://provider.invalid/v1",
        model="scripted",
        api_key="unused-test-secret",
        timeout_ms=30_000,
        max_retries=0,
    )

    _enforce_test_provider_network_policy(endpoint)


@pytest.mark.asyncio
async def test_provider_only_turn_blocks_external_endpoint_before_worker_start(monkeypatch):
    """Provider-only turns must share the ordinary test network guard.

    The legacy ReAct bridge reaches this Pi seam directly; omitting the guard here
    would let a unit test resolve a real public endpoint and start the worker even
    though the streaming chat seam fails closed.
    """
    monkeypatch.setenv("ISTARA_TEST_BLOCK_EXTERNAL_LLM", "1")
    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-provider-live-forbidden",
        provider_kind="openai_compat",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key="unused-test-secret",
        timeout_ms=30_000,
        max_retries=0,
    )
    manager = PiModelManager(endpoints=[endpoint], include_local=False)
    manager._db_projected = True

    class NeverStarted:
        async def ensure_started(self):
            raise AssertionError("network policy must run before worker startup")

    service = PiExecutionService(supervisor=NeverStarted(), model_manager=manager)
    with pytest.raises(
        PiEndpointResolutionError, match="external_provider_blocked_in_test"
    ):
        await service.run_provider_turn(
            purpose="test.external-provider-guard",
            project_id="project-a",
            agent_id="agent-a",
            system="system",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            params=TurnParams(endpoint_id=endpoint.endpoint_id),
        )


def _faux_bind_payload(responses, *, faux_cost_usd: float | None = None) -> dict:
    """Serialize a faux endpoint into the ``provider.bind`` payload the worker
    consumes (mirrors ``test_frame_limits``; adds the test-only cost seam)."""
    endpoint = faux_endpoint(responses)
    payload = {
        "endpoint_id": endpoint.endpoint_id,
        "provider_kind": endpoint.provider_kind,
        "base_url": endpoint.base_url,
        "model": endpoint.model,
        "api_key": endpoint.api_key,
        "timeout_ms": endpoint.timeout_ms,
        "max_retries": endpoint.max_retries,
        "faux_responses": list(endpoint.faux_responses or ()),
    }
    if faux_cost_usd is not None:
        payload["faux_cost_usd"] = faux_cost_usd
    return payload


@requires_node
@pytest.mark.asyncio
async def test_reader_eof_retires_ready_worker_before_restart():
    """H-2: an EOF cannot leave a live/ready child reusable by the next turn."""
    supervisor = PiRuntimeSupervisor()
    try:
        await supervisor.ensure_started()
        first_pid = supervisor._proc.pid
        supervisor._proc.terminate()
        await asyncio.wait_for(supervisor._reader_task, timeout=5)
        assert not supervisor._ready.is_set()
        await supervisor.ensure_started()
        assert supervisor._proc.pid != first_pid
        assert supervisor._ready.is_set()
    finally:
        await supervisor.shutdown()


# ── H-12: bounded pool + deterministic session_key routing ──────────────────


def test_pool_size_follows_configured_worker_count():
    """The pool grows to the configured ``pi_worker_pool_size`` by default and
    is explicitly overridable (bounded, not one-per-session)."""
    assert len(PiRuntimePool()._workers) == settings.pi_worker_pool_size
    assert len(PiRuntimePool(pool_size=1)._workers) == 1
    assert len(PiRuntimePool(pool_size=4)._workers) == 4


def test_routing_is_deterministic_and_process_stable():
    """A ``session_key`` routes to the same worker every time and identically
    across pool instances — the contract uses ``blake2b``, not the salted
    built-in ``hash`` (which PYTHONHASHSEED randomizes per process)."""
    pool = PiRuntimePool(pool_size=2)
    other = PiRuntimePool(pool_size=2)
    keys = [f"proj-{index}:agent-{index}" for index in range(64)]
    routes = {key: pool._route_index(key) for key in keys}
    assert all(0 <= value < 2 for value in routes.values())
    # Stable within an instance and identical across a second instance.
    assert all(pool._route_index(key) == routes[key] for key in keys)
    assert all(other._route_index(key) == routes[key] for key in keys)
    # Routing owns the open path: a session lands on exactly its hashed worker.
    assert all(pool._worker_for_open(key) is pool._workers[routes[key]] for key in keys)
    # Traffic actually spreads across the whole pool.
    assert set(routes.values()) == {0, 1}


@pytest.mark.asyncio
async def test_pool_forwards_provider_only_turns_to_the_session_owner():
    class Owner:
        async def run_provider_turn(self, session_key, messages, tools):
            assert session_key == "provider-session"
            assert messages == [{"role": "user", "content": "hello"}]
            assert tools == [{"name": "lookup"}]
            yield {"type": "run.completed", "run_id": "provider-run"}

    pool = PiRuntimePool(pool_size=1)
    pool._owners["provider-session"] = Owner()

    frames = [
        frame
        async for frame in pool.run_provider_turn(
            "provider-session",
            [{"role": "user", "content": "hello"}],
            [{"name": "lookup"}],
        )
    ]

    assert frames == [{"type": "run.completed", "run_id": "provider-run"}]


@pytest.mark.asyncio
async def test_pi_turn_telemetry_uses_bounded_endpoint_identity_for_route_id(
    monkeypatch,
):
    record_span = AsyncMock()
    monkeypatch.setattr(
        "app.core.pi_runtime.engine.telemetry_recorder.record_span", record_span
    )
    service = PiExecutionService()
    endpoint = faux_endpoint([final_text("ok")])

    await service._record_turn_telemetry(
        endpoint,
        "project-id",
        "agent-id",
        {"type": "done", "usage": {"input_tokens": 10}, "stop_reason": "stop"},
        "pi_completion:test",
    )

    assert record_span.await_args.kwargs["route_id"] == endpoint.endpoint_id


@requires_node
@pytest.mark.asyncio
async def test_pool_runs_twenty_concurrent_turns_across_two_workers():
    """H-12: a default two-worker pool admits *and runs* 20 concurrent turns,
    routing each session to its stable hashed worker (10 per worker)."""
    pool = PiRuntimePool(pool_size=2)
    # Pick ten keys that deterministically route to each worker so the default
    # ten-session cap is saturated on both — the "20 across the pool"
    # acceptance, not 20 crowded onto one worker.
    buckets: dict[int, list[str]] = {0: [], 1: []}
    index = 0
    while len(buckets[0]) < 10 or len(buckets[1]) < 10:
        key = f"pool-sess-{index}"
        target = pool._route_index(key)
        if len(buckets[target]) < 10:
            buckets[target].append(key)
        index += 1
    keys = buckets[0] + buckets[1]

    async def handler(name, arguments):  # these turns issue no tool calls
        raise AssertionError("no tool call expected in the concurrent-turn pool test")

    async def drive(key: str) -> list[dict]:
        await pool.open_session(
            key, system_prompt="test", history=[], revision="r", catalog=[]
        )
        await pool.bind_provider(key, _faux_bind_payload([final_text("ok")]))
        return [frame async for frame in pool.run_turn(key, "go", handler)]

    try:
        await pool.ensure_started()
        results = await asyncio.gather(*(drive(key) for key in keys))
        # Every one of the twenty concurrent turns reached a clean terminal.
        assert all(
            any(frame["type"] == "run.completed" for frame in frames)
            for frames in results
        )
        # Deterministic routing held for every session under real concurrency.
        for key in keys:
            assert pool._owners[key] is pool._workers[pool._route_index(key)]
        # Both bounded workers carried real traffic: exactly ten sessions each.
        assert sum(worker.is_running for worker in pool._workers) == 2
        assert sorted(len(worker._sessions) for worker in pool._workers) == [10, 10]
    finally:
        await asyncio.gather(*(pool.close_session(key) for key in keys))
        await pool.shutdown()


# ── H-6: whole-run wall-clock and cost ceilings (behavioral) ────────────────


def test_supervisor_has_explicit_whole_run_limits():
    """H-6: session.open receives the worker turn, wall-clock, and cost ceilings."""
    supervisor = PiRuntimeSupervisor(max_turns=3, run_timeout=4.5, max_cost_usd=0.25)
    assert (
        supervisor._max_turns,
        supervisor._run_timeout,
        supervisor._max_cost_usd,
    ) == (3, 4.5, 0.25)


@requires_node
@pytest.mark.asyncio
async def test_run_fails_closed_when_cost_budget_exceeded():
    """H-6: a turn that completes but whose reported cost exceeds the per-run
    ceiling is surfaced to Python as ``run.failed:cost_budget_exceeded``."""
    supervisor = PiRuntimeSupervisor(max_cost_usd=0.5)

    async def handler(name, arguments):
        raise AssertionError("no tool call expected in the cost-budget test")

    try:
        await supervisor.ensure_started()
        await supervisor.open_session(
            "cost", system_prompt="t", history=[], revision="r", catalog=[]
        )
        await supervisor.bind_provider(
            "cost", _faux_bind_payload([final_text("done")], faux_cost_usd=5.0)
        )
        frames = [frame async for frame in supervisor.run_turn("cost", "go", handler)]
    finally:
        await supervisor.shutdown()

    failed = [frame for frame in frames if frame["type"] == "run.failed"]
    assert failed and failed[-1].get("error") == "cost_budget_exceeded"
    assert not any(frame["type"] == "run.completed" for frame in frames)


@requires_node
@pytest.mark.asyncio
async def test_run_fails_closed_when_wall_clock_budget_exceeded():
    """H-6: a run that stalls past the Python-propagated wall-clock ceiling is
    terminated worker-side and surfaced as ``run.failed:wall_clock_budget_exceeded``."""
    supervisor = PiRuntimeSupervisor(run_timeout=0.5)

    # The worker blocks awaiting this tool.result; the handler deliberately
    # outlives the 500 ms wall-clock ceiling, so the budget terminates the run,
    # then the withheld result returns and the driver reads the queued failure.
    async def slow_handler(name, arguments):
        await asyncio.sleep(1.5)
        return {"ok": True, "result": None}

    catalog = [{"name": "istara_create_task", "description": "t", "parameters": {}}]
    try:
        await supervisor.ensure_started()
        await supervisor.open_session(
            "wall", system_prompt="t", history=[], revision="r", catalog=catalog
        )
        await supervisor.bind_provider(
            "wall",
            _faux_bind_payload([tool_call("istara_create_task", {"title": "x"})]),
        )
        frames = [
            frame async for frame in supervisor.run_turn("wall", "go", slow_handler)
        ]
    finally:
        await supervisor.shutdown()

    failed = [frame for frame in frames if frame["type"] == "run.failed"]
    assert failed and failed[-1].get("error") == "wall_clock_budget_exceeded"
    assert not any(frame["type"] == "run.completed" for frame in frames)


# ── F-2: production cost pricing flows so the ceiling fails closed ───────────


def test_bind_payload_forwards_real_endpoint_pricing_but_not_faux():
    """A real endpoint's resolved pricing rides the ``provider.bind`` payload so
    the worker can price usage; a faux endpoint carries none (it prices itself
    through the scripted-cost seam instead)."""
    real = ResolvedPiEndpoint(
        endpoint_id="e",
        provider_kind="openai_compat",
        base_url="http://x",
        model="m",
        api_key="k",
        timeout_ms=1000,
        max_retries=0,
        cost_input_per_mtok=0.27,
        cost_output_per_mtok=1.10,
    )
    assert _bind_payload(real)["pricing"] == {
        "input_per_mtok": 0.27,
        "output_per_mtok": 1.10,
        "cache_read_per_mtok": 0.0,
        "cache_write_per_mtok": 0.0,
    }
    assert "pricing" not in _bind_payload(faux_endpoint([final_text("ok")]))


def test_bind_payload_preserves_non_secret_pi_provider_identity():
    endpoint = ResolvedPiEndpoint(
        endpoint_id="deepseek",
        provider_kind="openai_compat",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        api_key="secret",
        timeout_ms=1000,
        max_retries=0,
        pi_provider="deepseek",
    )
    payload = _bind_payload(endpoint)
    assert payload["pi_provider"] == "deepseek"
    assert "auth_provider" not in payload


def test_default_endpoint_is_priced_so_its_cost_ceiling_can_fail_closed():
    """The built-in default endpoint resolves with nonzero pricing for every
    category it can spend. A $0-priced default would make its per-run
    ``max_cost_usd`` ceiling unenforceable, and — because pi-ai prices each
    category independently and the worker fails a spent-but-$0-rated category
    closed — a cache-read turn on a default priced only for input/output would
    fail closed as unpriced. The rates are sourced from the configured model
    (deepseek-v4-pro) rather than an unrelated model's list price."""
    endpoint = PiEndpointResolver()._endpoints[DEFAULT_ENDPOINT_ID]
    assert endpoint.pi_provider == "deepseek"
    assert endpoint.model == "deepseek-v4-pro"
    assert endpoint.cost_input_per_mtok == pytest.approx(0.435)  # cache-miss input
    assert endpoint.cost_output_per_mtok == pytest.approx(0.87)  # output
    assert endpoint.cost_cache_read_per_mtok == pytest.approx(
        0.003625
    )  # cache-hit input
    # DeepSeek bills cache writes at the cache-miss input rate and reports no
    # separate cache-write token count, so that category is never spent.
    assert endpoint.cost_cache_write_per_mtok == 0.0


class _PricedUsageStubHandler(BaseHTTPRequestHandler):
    """A loopback openai_compat stub that reports real token usage so the worker
    can price it (2M tokens) — the non-faux fixture the cost ceiling needs."""

    def log_message(self, *args):  # silence
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        content = {"choices": [{"index": 0, "delta": {"content": "Priced reply."}}]}
        self.wfile.write(f"data: {json.dumps(content)}\n\n".encode())
        done = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        self.wfile.write(f"data: {json.dumps(done)}\n\n".encode())
        usage = {
            "choices": [],
            "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
        }
        self.wfile.write(f"data: {json.dumps(usage)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class _CacheReadUsageStubHandler(BaseHTTPRequestHandler):
    """A loopback openai_compat stub whose prompt is fully cache-hit: it reports
    1M cache-read tokens (``prompt_cache_hit_tokens``) and zero cache-miss input.
    pi-ai prices cache reads independently, so a binding priced only for
    input/output prices this turn at $0 unless the cache-read category is
    checked — the exact partial-pricing gap the fail-closed path must catch."""

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
        usage = {
            "choices": [],
            "usage": {
                "prompt_tokens": 1_000_000,
                "prompt_cache_hit_tokens": 1_000_000,
                "completion_tokens": 0,
            },
        }
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
async def test_real_priced_turn_over_budget_fails_closed_through_engine():
    """Full-stack non-faux proof: a real ``openai_compat`` turn whose usage
    prices above the per-run ceiling surfaces ``cost_budget_exceeded`` end to end
    (config pricing → ``_bind_payload`` → worker rates → cumulative ceiling).
    A zero-priced real binding would price the same 2M tokens at $0 and complete."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PricedUsageStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-priced-loopback",
        provider_kind="openai_compat",
        base_url=base_url,
        model="stub-model",
        api_key="loopback-test-key",
        timeout_ms=30000,
        max_retries=0,
        cost_input_per_mtok=1.0,  # 1M input -> $1.00
        cost_output_per_mtok=2.0,  # 1M output -> $2.00, total $3.00 over the $0.50 cap
    )
    supervisor = PiRuntimeSupervisor(max_cost_usd=0.5)
    service = PiExecutionService(
        resolver=_FixedResolver(endpoint), supervisor=supervisor
    )

    async def _no_tools(name, params, pid, aid):  # pragma: no cover - not exercised
        return {"success": True, "result": "unused"}

    events: list[dict] = []
    try:
        async for event in service.run_chat_turn(
            project_id=f"pi-priced-{uuid.uuid4()}",
            agent_id="istara-main",
            system_prompt="Pi owns the loop.",
            history=[],
            user_text="Say hello.",
            tool_executor=_no_tools,
            allowed_tools=[],
        ):
            events.append(event)
    finally:
        await supervisor.shutdown()
        server.shutdown()

    errors = [event for event in events if event["type"] == "error"]
    assert errors and errors[-1].get("error") == "cost_budget_exceeded"
    assert not any(event["type"] == "done" for event in events)


@requires_node
@pytest.mark.asyncio
async def test_real_cache_read_unpriced_turn_fails_closed_through_engine():
    """Full-stack non-faux proof of the partial-pricing gap: a real
    ``openai_compat`` turn that spends cache-read tokens on an endpoint priced
    only for input/output surfaces ``cost_budget_unpriced`` end to end. pi-ai
    prices each usage category independently, so leaving cache-read at $0 would
    otherwise under-count this fully-cached turn to $0 and complete fail-open."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CacheReadUsageStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = ResolvedPiEndpoint(
        endpoint_id="pi-cache-unpriced-loopback",
        provider_kind="openai_compat",
        base_url=base_url,
        model="stub-model",
        api_key="loopback-test-key",
        timeout_ms=30000,
        max_retries=0,
        cost_input_per_mtok=1.0,  # priced
        cost_output_per_mtok=2.0,  # priced
        cost_cache_read_per_mtok=0.0,  # NOT priced — the spent category is $0-rated
    )
    supervisor = PiRuntimeSupervisor(max_cost_usd=0.5)
    service = PiExecutionService(
        resolver=_FixedResolver(endpoint), supervisor=supervisor
    )

    async def _no_tools(name, params, pid, aid):  # pragma: no cover - not exercised
        return {"success": True, "result": "unused"}

    events: list[dict] = []
    try:
        async for event in service.run_chat_turn(
            project_id=f"pi-cache-unpriced-{uuid.uuid4()}",
            agent_id="istara-main",
            system_prompt="Pi owns the loop.",
            history=[],
            user_text="Say hello.",
            tool_executor=_no_tools,
            allowed_tools=[],
        ):
            events.append(event)
    finally:
        await supervisor.shutdown()
        server.shutdown()

    errors = [event for event in events if event["type"] == "error"]
    assert errors and errors[-1].get("error") == "cost_budget_unpriced"
    assert not any(event["type"] == "done" for event in events)
