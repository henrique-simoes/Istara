"""Production scenario 9 (research.spine.step_tracker) — a governed research
spine driven from a real Pi turn: the Pi run opens a task with the canonical
``create_task`` tool, provisional source/evidence is persisted through the real
``research_validity_service`` as ``candidate_only``, and governance keeps the work
provisional — it is not reportable and the model cannot mark it Done.

This is the production-path replacement for the deleted
``write_pi_source_evidence_chain`` / ``exercise_pi_done_report_gate`` exercisers:
acceptance/reportability is computed by Istara governance, never manufactured.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.database import async_session, init_db
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.finding import Nugget
from app.models.project import Project
from app.models.research_validity import EvidenceUnit
from app.models.task import Task
from app.services.research_validity_service import (
    assess_task_research_validity,
    persist_task_nugget_evidence_units,
)
from app.skills.system_actions import execute_tool

from .harness import faux_service, final_text, requires_node, tool_call

pytestmark = requires_node

_SYS = "You run inside Istara. Pi owns the loop; research validity is Istara-governed."


@pytest.mark.asyncio
async def test_scenario9_provisional_evidence_stays_candidate_and_cannot_be_reported_or_done():
    await init_db()
    project_id = f"pi-prod-s9-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 9"))
        await db.commit()

    # The Pi run opens the research task via the real canonical tool.
    sup = PiRuntimeSupervisor()
    svc = faux_service(
        [
            tool_call("create_task", {"title": "Investigate retention drivers"}),
            final_text("Opened the research task."),
        ],
        sup,
    )

    async def authority_exec(name, params, pid, aid):
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        async for _ in svc.run_chat_turn(
            project_id=project_id,
            agent_id="istara-main",
            system_prompt=_SYS,
            history=[],
            user_text="Open a research task on retention.",
            tool_executor=authority_exec,
            session_key=f"{project_id}:spine",
        ):
            pass
    finally:
        await sup.shutdown()

    async with async_session() as db:
        task = (
            await db.execute(select(Task).where(Task.project_id == project_id))
        ).scalar_one()
    task_id = task.id

    # Provisional source/evidence is persisted through the real spine service as
    # candidate-only (what a Pi research step may produce — no acceptance).
    source_text = "Cohort A shows a 30-day retention lift after onboarding changes."
    async with async_session() as db:
        document = Document(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="Retention source",
            description="Pi research source unit.",
            file_name="retention.md",
            file_type="md",
            status=DocumentStatus.READY,
            source=DocumentSource.TASK_OUTPUT,
            task_id=task_id,
            phase="develop",
            content_preview=source_text,
            content_text=source_text,
        )
        document.set_agent_ids(["istara-main"])
        document.set_skill_names(["pi-research"])
        document.set_tags(["retention"])
        db.add(document)
        nugget = Nugget(
            id=str(uuid.uuid4()),
            project_id=project_id,
            agent_id="istara-main",
            task_id=task_id,
            text="Onboarding changes lifted 30-day retention.",
            source=document.id,
            source_location="retention.md#unit-1",
            tags=json.dumps(["retention"]),
            phase="develop",
            confidence=0.9,
        )
        db.add(nugget)
        await db.flush()
        units = await persist_task_nugget_evidence_units(
            db,
            project_id=project_id,
            task_id=task_id,
            nugget_id=nugget.id,
            source_text=source_text,
            source_location="retention.md#unit-1",
            source_document_id=document.id,
            method="pi_research_step",
            phase="develop",
            candidate_only=True,
        )
        await db.commit()
        unit_ids = [u.id for u in units]

    # The evidence is candidate-only (provisional), never an accepted source span.
    async with async_session() as db:
        stored = (
            (
                await db.execute(
                    select(EvidenceUnit).where(EvidenceUnit.id.in_(unit_ids))
                )
            )
            .scalars()
            .all()
        )
    assert stored
    assert all(u.unit_type == "candidate_atom" for u in stored)

    # Governance computes reportability: provisional work is NOT report-eligible.
    async with async_session() as db:
        assessment = await assess_task_research_validity(
            db, project_id=project_id, task_id=task_id
        )
    assert assessment["report_allowed"] is False

    # The model cannot manufacture Done — the canonical tool refuses it.
    done_attempt = await execute_tool(
        "move_task",
        {"task_id": task_id, "status": "done"},
        project_id,
        agent_id="istara-main",
    )
    assert done_attempt["success"] is True  # the tool call itself succeeds...
    assert "cannot mark tasks Done" in done_attempt["result"]  # ...but Done is refused

    async with async_session() as db:
        after = await db.get(Task, task_id)
    assert after.status.value != "done"
    assert sup.is_running is False
