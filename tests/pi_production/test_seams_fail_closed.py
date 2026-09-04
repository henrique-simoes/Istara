"""Governed-seam fail-closed regression (RF3-2).

Every governed Pi seam must reject a non-success terminal (``error``/``aborted``)
*before* it returns a proposal, reply, or delegation result — even when the turn
already streamed partial output. Otherwise a worker failure leaks out as a
false-success candidate proposal or a user/A2A reply built from partial text,
contradicting the seams' fail-closed contract.

Two layers prove this:

* deterministic seam/engine tests inject an ``error`` *and* an ``aborted``
  terminal (with partial text) straight into each seam — no worker needed — so
  both non-success statuses are covered precisely;
* real-worker tests drive a genuine ``run.failed`` after partial ``assistant.delta``
  output end-to-end through the production callers and assert nothing is sent or
  persisted.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select

from app.api.routes import autoresearch as autoresearch_route
from app.channels.base import IncomingMessage
from app.config import settings
from app.core.agent_lifecycle import AgentLifecycleMixin
from app.core.pi_runtime import seams
from app.core.pi_runtime.endpoints import PiRuntimeTurnError
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.agent import A2AMessage
from app.models.channel_message import ChannelMessage
from app.models.database import async_session, init_db
from app.models.project import Project
from app.services import channel_service
from app.services.inbound_processor import process_inbound_channel_message

from .harness import error_after_partial, faux_service, requires_node


# ── deterministic terminals (no worker) ──────────────────────────────────────
def _terminal_result(status: str) -> dict:
    """A collected-turn result with partial text and a non-success status."""
    return {
        "text": "Partial output produced before the turn failed.",
        "tool_calls": [],
        "status": status,
        "usage": {},
        "stop_reason": None,
        "endpoint_id": "pi-faux",
        "error": "run_failed" if status == "error" else None,
    }


class _StubChannelService:
    def __init__(self, result: dict) -> None:
        self._result = result

    async def run_channel_turn(self, **_kwargs) -> dict:
        return self._result


class _StubDelegationService:
    def __init__(self, result: dict) -> None:
        self._result = result

    async def run_delegation(self, **_kwargs) -> dict:
        return self._result


class _StubCollectService(PiExecutionService):
    """Real autoresearch seam over a scripted ``_collect_turn`` terminal."""

    def __init__(self, result: dict) -> None:
        super().__init__()
        self._result = result

    async def _collect_turn(self, **_kwargs) -> dict:
        return self._result


async def _noop_tool_executor(name, params, project_id, agent_id) -> dict:
    return {"success": True, "result": {}}


def _lifecycle_host(agent_id: str) -> AgentLifecycleMixin:
    host = AgentLifecycleMixin.__new__(AgentLifecycleMixin)
    host._agent_id = agent_id
    return host


@pytest.mark.parametrize("status", ["error", "aborted"])
@pytest.mark.asyncio
async def test_channel_reply_rejects_nonsuccess_terminal_with_partial_text(
    monkeypatch, status
):
    """A channel reply is not built from an error/aborted turn's partial text."""
    monkeypatch.setattr(
        seams, "_service", _StubChannelService(_terminal_result(status))
    )
    reply = await seams.build_pi_channel_reply(
        message_channel="pi_local",
        channel_id="pi-local",
        instance_id="inst-1",
        project_id="p1",
        inbound_message_id="m1",
        inbound_text="hello",
        metadata={"pi_candidate": True},
    )
    assert reply is None  # fail closed despite non-empty partial text


@pytest.mark.parametrize("status", ["error", "aborted"])
@pytest.mark.asyncio
async def test_delegation_rejects_nonsuccess_terminal_with_partial_text(
    monkeypatch, status
):
    """A delegation result from an error/aborted turn is dropped, not returned."""
    monkeypatch.setattr(
        seams, "_service", _StubDelegationService(_terminal_result(status))
    )
    result = await seams.run_pi_delegation(
        project_id="p1",
        task_text="do the work",
        agent_id="istara-main",
        metadata={"pi_candidate": True},
    )
    assert result is None  # fail closed: caller never persists/sends partial text


@pytest.mark.parametrize("status", ["error", "aborted"])
@pytest.mark.asyncio
async def test_autoresearch_turn_raises_typed_error_on_nonsuccess_terminal(status):
    """A non-success autoresearch turn raises instead of fabricating a proposal."""
    service = _StubCollectService(_terminal_result(status))
    with pytest.raises(PiRuntimeTurnError) as excinfo:
        await service.run_autoresearch_turn(
            project_id="p1",
            agent_id="autoresearch",
            system_prompt="sys",
            objective="propose one experiment",
            tool_executor=_noop_tool_executor,
            loop_type="model_temp",
            target="extraction",
        )
    # Typed failure preserves the terminal status (never a candidate proposal).
    assert excinfo.value.status == status


# ── real-worker: genuine run.failed after partial output ─────────────────────
@requires_node
@pytest.mark.asyncio
async def test_channel_fails_closed_on_real_error_after_partial_output(monkeypatch):
    """End-to-end: a real ``run.failed`` after streamed text persists no outbound."""
    await init_db()
    project_id = f"pi-prod-fc-chan-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi FC channel"))
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db,
            platform="pi_local",
            name="Pi Local FC",
            config={"enabled": True},
            project_id=project_id,
        )
    instance_id = instance.id

    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(
        seams,
        "_service",
        faux_service(
            [error_after_partial("Partial channel reply before failure.")], sup
        ),
    )
    try:
        response = await process_inbound_channel_message(
            IncomingMessage(
                channel="pi_local",
                channel_id="pi-local",
                sender_id="participant-1",
                sender_name="Participant",
                text="please note this",
                instance_id=instance_id,
                metadata={"pi_candidate": True},
            )
        )
    finally:
        await sup.shutdown()

    assert response is None  # fail closed despite partial streamed text
    async with async_session() as db:
        msgs = (
            (
                await db.execute(
                    select(ChannelMessage).where(
                        ChannelMessage.channel_instance_id == instance_id
                    )
                )
            )
            .scalars()
            .all()
        )
    # Inbound is still recorded; no outbound reply was fabricated from a failed turn.
    assert [m.direction for m in msgs] == ["inbound"]
    assert sup.is_running is False


@requires_node
@pytest.mark.asyncio
async def test_delegation_fails_closed_on_real_error_after_partial_output(monkeypatch):
    """End-to-end: a failed delegation turn sends no A2A response with partial text."""
    await init_db()
    project_id = f"pi-prod-fc-deleg-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi FC delegation"))
        await db.commit()

    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(
        seams,
        "_service",
        faux_service(
            [error_after_partial("Partial delegation result before failure.")], sup
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

    async with async_session() as db:
        results = (
            (
                await db.execute(
                    select(A2AMessage).where(
                        A2AMessage.project_id == project_id,
                        A2AMessage.from_agent_id == "istara-main",
                        A2AMessage.message_type == "response",
                    )
                )
            )
            .scalars()
            .all()
        )
    assert results == []  # fail closed: no partial delegation result sent
    assert sup.is_running is False


@requires_node
@pytest.mark.asyncio
async def test_autoresearch_fails_closed_on_real_error_after_partial_output(
    monkeypatch,
):
    """End-to-end: a failed governed turn returns a typed 503, not a proposal."""
    await init_db()
    project_id = f"pi-prod-fc-auto-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi FC autoresearch"))
        await db.commit()

    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(
        seams,
        "_service",
        faux_service([error_after_partial("Partial hypothesis before failure.")], sup),
    )

    async def fake_scope(*args, **kwargs):
        return project_id

    monkeypatch.setattr(settings, "autoresearch_enabled", True)
    monkeypatch.setattr(autoresearch_route, "_require_active_project_scope", fake_scope)
    monkeypatch.setattr(
        autoresearch_route, "_get_engine", lambda: SimpleNamespace(is_running=False)
    )

    added: list[object] = []
    background_tasks = BackgroundTasks()
    background_tasks.add_task = lambda fn, *a, **k: added.append((fn, a, k))

    try:
        with pytest.raises(HTTPException) as excinfo:
            await autoresearch_route.start_experiment(
                autoresearch_route.StartExperimentRequest(
                    loop_type="model_temp",
                    target="extraction",
                    max_iterations=5,
                    project_id=project_id,
                    dry_run=False,
                ),
                SimpleNamespace(headers={"x-istara-agent-engine": "pi"}),
                background_tasks,
                None,
            )
    finally:
        await sup.shutdown()

    assert excinfo.value.status_code == 503
    assert "Pi runtime turn failed" in str(excinfo.value.detail)
    assert added == []  # no legacy loop scheduled, no candidate proposal returned
    assert sup.is_running is False
