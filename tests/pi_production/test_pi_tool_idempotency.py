"""Durable Pi authority mutation replay and crash-recovery barriers."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.core.pi_runtime.idempotency import execute_with_idempotency
from app.core.pi_runtime.supervisor import (
    PiRuntimeSupervisor,
    current_tool_call_context,
)
from app.models.database import async_session, init_db
from app.models.pi_tool_execution import PiToolExecution
from app.models.project import Project


@pytest.mark.asyncio
async def test_supervisor_scopes_run_metadata_without_changing_tool_arguments():
    supervisor = PiRuntimeSupervisor()
    seen: list[dict[str, str]] = []

    async def handler(name, args):
        assert name == "create_task"
        assert args == {"title": "Scoped"}
        seen.append(current_tool_call_context())
        return {"ok": True, "result": "accepted"}

    result = await supervisor._safe_tool_call(
        handler,
        {
            "session_key": "session-scoped",
            "run_id": "run-scoped",
            "tool_call_id": "call-scoped",
            "name": "create_task",
            "arguments": {"title": "Scoped"},
        },
    )

    assert result == {"ok": True, "result": "accepted"}
    assert seen == [
        {
            "session_key": "session-scoped",
            "run_id": "run-scoped",
            "tool_call_id": "call-scoped",
        }
    ]
    assert current_tool_call_context() == {}


@pytest.mark.asyncio
async def test_completed_mutation_replays_without_second_authority_call():
    await init_db()
    project_id = f"pi-idem-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi idempotency"))
        await db.commit()

    calls: list[dict] = []

    async def executor(name, args, pid, aid):
        calls.append({"name": name, "args": args, "project_id": pid, "agent_id": aid})
        return {"success": True, "result": "Task created: task-1"}

    first = await execute_with_idempotency(
        base_key="user-message-1",
        project_id=project_id,
        agent_id="agent-1",
        operation="pi_runtime_chat_turn",
        session_key="session-1",
        run_id="run-1",
        tool_call_id="call-1",
        tool_name="create_task",
        args={"title": "Research"},
        executor=executor,
    )
    second = await execute_with_idempotency(
        base_key="user-message-1",
        project_id=project_id,
        agent_id="agent-1",
        operation="pi_runtime_chat_turn",
        session_key="session-1",
        run_id="run-after-restart",
        tool_call_id="call-new",
        tool_name="create_task",
        args={"title": "Research"},
        executor=executor,
    )

    assert first == second == {"success": True, "result": "Task created: task-1"}
    assert len(calls) == 1
    async with async_session() as db:
        rows = (
            (
                await db.execute(
                    select(PiToolExecution).where(
                        PiToolExecution.project_id == project_id
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert rows[0].status == "succeeded"
    assert rows[0].args_hash


@pytest.mark.asyncio
async def test_unfinished_mutation_fails_closed_without_reexecution():
    await init_db()
    project_id = f"pi-idem-recovery-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi recovery barrier"))
        await db.commit()

    calls = 0

    async def executor(name, args, pid, aid):
        nonlocal calls
        calls += 1
        return {"success": True, "result": "must not run"}

    from app.core.pi_runtime.idempotency import make_idempotency_key

    key, args_hash = make_idempotency_key(
        "user-message-2", project_id, "create_task", {"title": "Recover"}
    )
    async with async_session() as db:
        db.add(
            PiToolExecution(
                id=str(uuid.uuid4()),
                project_id=project_id,
                idempotency_key=key,
                tool_name="create_task",
                args_hash=args_hash,
                operation="pi_runtime_chat_turn",
                worker_session_key="session-2",
                run_id="run-crashed",
                tool_call_id="call-crashed",
                status="started",
                result_json="",
                error="",
                attempt_count=1,
            )
        )
        await db.commit()

    outcome = await execute_with_idempotency(
        base_key="user-message-2",
        project_id=project_id,
        agent_id="agent-1",
        operation="pi_runtime_chat_turn",
        session_key="session-2",
        run_id="run-retry",
        tool_call_id="call-retry",
        tool_name="create_task",
        args={"title": "Recover"},
        executor=executor,
    )
    assert outcome["success"] is False
    assert outcome["error"] == "tool_recovery_required"
    assert calls == 0


@pytest.mark.asyncio
async def test_cancellation_leaves_started_barrier_for_reconciliation():
    await init_db()
    project_id = f"pi-idem-cancel-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi cancellation"))
        await db.commit()

    async def cancelled(name, args, pid, aid):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await execute_with_idempotency(
            base_key="user-message-3",
            project_id=project_id,
            agent_id="agent-1",
            operation="pi_runtime_chat_turn",
            session_key="session-3",
            run_id="run-cancel",
            tool_call_id="call-cancel",
            tool_name="create_task",
            args={"title": "Cancel"},
            executor=cancelled,
        )
    async with async_session() as db:
        row = (
            await db.execute(
                select(PiToolExecution).where(PiToolExecution.project_id == project_id)
            )
        ).scalar_one()
    assert row.status == "started"
