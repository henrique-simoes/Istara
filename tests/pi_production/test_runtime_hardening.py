"""Focused W0 regressions for recovery, budget propagation, and pool capacity."""

from __future__ import annotations

import asyncio

import pytest

from app.core.pi_runtime.pool import PiRuntimePool
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

from .harness import requires_node


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


@requires_node
@pytest.mark.asyncio
async def test_two_worker_pool_accepts_twenty_concurrent_sessions():
    """H-12: two bounded ten-session workers admit twenty independent sessions."""
    pool = PiRuntimePool()
    keys = [f"pool-{index}" for index in range(20)]
    try:
        await pool.ensure_started()
        await asyncio.gather(*(
            pool.open_session(key, system_prompt="test", history=[], revision="r", catalog=[])
            for key in keys
        ))
        assert len(pool._owners) == 20
        assert sum(worker.is_running for worker in pool._workers) == 2
        assert sorted(len(worker._sessions) for worker in pool._workers) == [10, 10]
    finally:
        await asyncio.gather(*(pool.close_session(key) for key in keys))
        await pool.shutdown()


def test_supervisor_has_explicit_whole_run_limits():
    """H-6: session.open receives the worker turn, wall-clock, and cost ceilings."""
    supervisor = PiRuntimeSupervisor(max_turns=3, run_timeout=4.5, max_cost_usd=0.25)
    assert (supervisor._max_turns, supervisor._run_timeout, supervisor._max_cost_usd) == (3, 4.5, 0.25)
