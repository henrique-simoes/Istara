"""Production scenario 7 (a2a.debate_report.slice) — governed A2A delegation.

Proves the orchestrator inbox dispatch (``_handle_delegate``) routes an admitted,
Pi-selected delegation through the real Pi Agent (``PiExecutionService.run_delegation``):
the delegated work executes real canonical tools under the authenticated project
scope and persists an A2A result. A non-Pi (or unselected) delegation runs no Pi
work.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from app.core.agent_lifecycle import AgentLifecycleMixin
from app.core.pi_runtime import seams
from app.models.agent import A2AMessage
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.task import Task

from .harness import faux_service, final_text, requires_node, tool_call
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

pytestmark = requires_node


def _lifecycle_host(agent_id: str) -> AgentLifecycleMixin:
    host = AgentLifecycleMixin.__new__(AgentLifecycleMixin)
    host._agent_id = agent_id
    return host


@pytest.mark.asyncio
async def test_scenario7_pi_delegation_runs_through_orchestrator_dispatch(monkeypatch):
    await init_db()
    project_id = f"pi-prod-s7-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 7"))
        await db.commit()

    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(
        seams,
        "_service",
        faux_service(
            [tool_call("create_task", {"title": "Delegated analysis"}), final_text("Delegation complete.")],
            sup,
        ),
    )

    host = _lifecycle_host("istara-main")
    msg = {
        "id": f"a2a-{uuid.uuid4()}",
        "project_id": project_id,
        "from_agent_id": "agent-a",
        "message_type": "delegate",
        "content": json.dumps(
            {
                "type": "pi_delegate",
                "project_id": project_id,
                "task": "Analyse the intake and open a task.",
                "metadata": {"pi_candidate": True, "project_id": project_id},
            }
        ),
    }

    try:
        async with async_session() as db:
            await host._handle_delegate(db, msg)
            await db.commit()
    finally:
        await sup.shutdown()

    # The delegated work executed a real canonical tool under project scope.
    async with async_session() as db:
        tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
        results = (
            await db.execute(
                select(A2AMessage).where(
                    A2AMessage.project_id == project_id,
                    A2AMessage.from_agent_id == "istara-main",
                    A2AMessage.message_type == "response",
                )
            )
        ).scalars().all()
    assert [t.title for t in tasks] == ["Delegated analysis"]
    assert len(results) == 1
    assert "Delegation complete." in results[0].content
    assert json.loads(results[0].extra_data or "{}").get("engine") == "pi"
    assert sup.is_running is False


@pytest.mark.asyncio
async def test_scenario7_non_pi_delegation_runs_no_pi_work(monkeypatch):
    """A delegate message without Pi selection creates no Pi session/task/result."""
    await init_db()
    project_id = f"pi-prod-s7neg-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 7 Neg"))
        await db.commit()

    called = {"pi": False}

    async def _boom(*args, **kwargs):
        called["pi"] = True
        raise AssertionError("Pi delegation must not run for a non-Pi delegate")

    monkeypatch.setattr("app.core.pi_runtime.seams.run_pi_delegation", _boom)

    host = _lifecycle_host("istara-main")
    msg = {
        "id": f"a2a-{uuid.uuid4()}",
        "project_id": project_id,
        "from_agent_id": "agent-a",
        "message_type": "delegate",
        "content": json.dumps(
            {"type": "pi_delegate", "project_id": project_id, "task": "no pi", "metadata": {}}
        ),
    }
    async with async_session() as db:
        await host._handle_delegate(db, msg)
        await db.commit()

    assert called["pi"] is False
    async with async_session() as db:
        tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    assert tasks == []
