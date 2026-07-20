"""Focused W0 regressions for recovery, budget propagation, and pool capacity."""

from __future__ import annotations

import asyncio

import pytest

from app.config import settings
from app.core.pi_runtime.pool import PiRuntimePool
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

from .harness import faux_endpoint, final_text, requires_node, tool_call


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
        await pool.open_session(key, system_prompt="test", history=[], revision="r", catalog=[])
        await pool.bind_provider(key, _faux_bind_payload([final_text("ok")]))
        return [frame async for frame in pool.run_turn(key, "go", handler)]

    try:
        await pool.ensure_started()
        results = await asyncio.gather(*(drive(key) for key in keys))
        # Every one of the twenty concurrent turns reached a clean terminal.
        assert all(any(frame["type"] == "run.completed" for frame in frames) for frames in results)
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
    assert (supervisor._max_turns, supervisor._run_timeout, supervisor._max_cost_usd) == (3, 4.5, 0.25)


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
        await supervisor.open_session("cost", system_prompt="t", history=[], revision="r", catalog=[])
        await supervisor.bind_provider("cost", _faux_bind_payload([final_text("done")], faux_cost_usd=5.0))
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
        await supervisor.open_session("wall", system_prompt="t", history=[], revision="r", catalog=catalog)
        await supervisor.bind_provider("wall", _faux_bind_payload([tool_call("istara_create_task", {"title": "x"})]))
        frames = [frame async for frame in supervisor.run_turn("wall", "go", slow_handler)]
    finally:
        await supervisor.shutdown()

    failed = [frame for frame in frames if frame["type"] == "run.failed"]
    assert failed and failed[-1].get("error") == "wall_clock_budget_exceeded"
    assert not any(frame["type"] == "run.completed" for frame in frames)
