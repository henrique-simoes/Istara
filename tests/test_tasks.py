"""Tests for Tasks API routes — CRUD, move, attach/detach, lock/unlock."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.code_application import CodeApplication
from app.models.document import Document, DocumentStatus
from app.models.finding import Nugget
from app.models.project import Project
from app.models.research_validity import EvidenceUnit, ResearchEvidenceEdge
from app.models.task import Task, TaskStatus


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


async def _seed_project(name: str = "Tasks Test Project", *, is_paused: bool = False) -> Project:
    project = Project(
        id=str(uuid.uuid4()),
        name=f"{name} {uuid.uuid4()}",
        is_paused=is_paused,
    )
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


def _add_accepted_nugget_support(
    db,
    *,
    project_id: str,
    task_id: str,
    nugget_id: str,
    source_text: str,
) -> None:
    evidence_unit_id = str(uuid.uuid4())
    db.add(
        EvidenceUnit(
            id=evidence_unit_id,
            project_id=project_id,
            task_id=task_id,
            source_id=f"task:{task_id}:nugget:{nugget_id}",
            stable_id=f"test-unit:{evidence_unit_id}",
            unit_index=0,
            unit_type="source_span",
            source_type="test_fixture",
            method="test",
            phase="discover",
            source_text=source_text,
        )
    )
    db.add(
        ResearchEvidenceEdge(
            id=str(uuid.uuid4()),
            project_id=project_id,
            source_type="nugget",
            source_id=nugget_id,
            relation="grounded_in",
            target_type="evidence_unit",
            target_id=evidence_unit_id,
            evidence_unit_id=evidence_unit_id,
            task_id=task_id,
        )
    )
    db.add(
        CodeApplication(
            id=str(uuid.uuid4()),
            project_id=project_id,
            task_id=task_id,
            code_id="accepted-research-evidence",
            evidence_unit_id=evidence_unit_id,
            source_text=source_text,
            promotion_status="accepted",
            reliability_status="accepted",
            reconciliation_status="accepted",
        )
    )


async def _seed_document(project_id: str, title: str = "Task Document") -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=title,
        file_name=f"{title.lower().replace(' ', '-')}.txt",
        file_type=".txt",
        status=DocumentStatus.READY,
        content_text="Document evidence",
    )
    async with async_session() as db:
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    return doc


async def _seed_task(project_id: str, title: str = "Seeded Task") -> Task:
    task = Task(id=str(uuid.uuid4()), project_id=project_id, title=title, status=TaskStatus.BACKLOG)
    async with async_session() as db:
        db.add(task)
        await db.commit()
        await db.refresh(task)
    return task


async def _seed_agent_task(project_id: str, agent_id: str, title: str) -> Task:
    task = Task(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=title,
        status=TaskStatus.BACKLOG,
        agent_id=agent_id,
    )
    async with async_session() as db:
        db.add(task)
        await db.commit()
        await db.refresh(task)
    return task


@pytest.mark.asyncio
async def test_tasks_list_returns_list(auth_headers):
    """GET /api/tasks returns only tasks for the requested project."""
    await init_db()
    project = await _seed_project("List Tasks")
    other_project = await _seed_project("Other List Tasks")
    project_task = await _seed_task(project.id, "Visible Task")
    await _seed_task(other_project.id, "Hidden Task")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/tasks?project_id={project.id}", headers=auth_headers)
        assert response.status_code == 200
        task_ids = {task["id"] for task in response.json()}
        assert task_ids == {project_task.id}


@pytest.mark.asyncio
async def test_tasks_list_requires_project_scope_for_admin(auth_headers):
    """Project-facing task lists never fall back to a global admin feed."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/tasks", headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_task_by_id_routes_require_active_project_binding(auth_headers):
    """Task detail and mutation routes bind ids to the selected active project."""
    await init_db()
    active_project = await _seed_project("Active Task Scope")
    other_project = await _seed_project("Other Task Scope")
    active_task = await _seed_task(active_project.id, "Active detail")
    other_task = await _seed_task(other_project.id, "Other detail")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_scope = await ac.get(f"/api/tasks/{other_task.id}", headers=auth_headers)
        stale_read = await ac.get(
            f"/api/tasks/{other_task.id}?project_id={active_project.id}",
            headers=auth_headers,
        )
        scoped_read = await ac.get(
            f"/api/tasks/{active_task.id}?project_id={active_project.id}",
            headers=auth_headers,
        )
        stale_patch = await ac.patch(
            f"/api/tasks/{other_task.id}?project_id={active_project.id}",
            headers=auth_headers,
            json={"title": "Wrong active project"},
        )
        stale_move = await ac.post(
            f"/api/tasks/{other_task.id}/move?status=in_progress&project_id={active_project.id}",
            headers=auth_headers,
        )
        scoped_patch = await ac.patch(
            f"/api/tasks/{active_task.id}?project_id={active_project.id}",
            headers=auth_headers,
            json={"title": "Scoped update"},
        )

    assert missing_scope.status_code == 422
    assert missing_scope.json()["detail"] == "project_id is required"
    assert stale_read.status_code == 404
    assert scoped_read.status_code == 200
    assert scoped_read.json()["id"] == active_task.id
    assert stale_patch.status_code == 404
    assert stale_move.status_code == 404
    assert scoped_patch.status_code == 200
    assert scoped_patch.json()["title"] == "Scoped update"


@pytest.mark.asyncio
async def test_tasks_list_requires_auth():
    """Tasks listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/tasks")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_agent_task_picker_skips_paused_project_tasks():
    """Paused projects must not feed work into the agent execution loop."""
    from app.core.agent import AgentOrchestrator

    await init_db()
    agent_id = f"pause-test-{uuid.uuid4()}"
    paused_project = await _seed_project("Paused Agent Project", is_paused=True)
    active_project = await _seed_project("Active Agent Project")
    paused_task = await _seed_agent_task(paused_project.id, agent_id, "Do not run")
    active_task = await _seed_agent_task(active_project.id, agent_id, "Allowed to run")

    orchestrator = AgentOrchestrator(agent_id=agent_id)
    async with async_session() as db:
        picked = await orchestrator._pick_next_task(db)

    assert picked is not None
    assert picked.id == active_task.id
    assert picked.id != paused_task.id


@pytest.mark.asyncio
async def test_agent_execute_task_defers_when_project_paused():
    """The execution path itself also guards against races after a project is paused."""
    from app.core.agent import AgentOrchestrator

    await init_db()
    project = await _seed_project("Paused Direct Execution", is_paused=True)
    task = await _seed_agent_task(project.id, "pause-direct-agent", "Should stay idle")
    orchestrator = AgentOrchestrator(agent_id="pause-direct-agent")

    async with async_session() as db:
        db_task = await db.get(Task, task.id)
        db_project = await db.get(Project, project.id)
        await orchestrator._execute_task(db, db_task, db_project)
        await db.refresh(db_task)

        assert db_task.status == TaskStatus.BACKLOG
        assert db_task.progress == 0
        assert "paused" in db_task.agent_notes.lower()


@pytest.mark.asyncio
async def test_task_move_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/move returns 404 for non-existent task."""
    await init_db()
    project = await _seed_project("Missing Move Scope")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/non-existent-id/move?status=in_progress&project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_task_lock_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/lock returns 404 for non-existent task."""
    await init_db()
    project = await _seed_project("Missing Lock Scope")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/non-existent-id/lock?project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_task_unlock_nonexistent_returns_404(auth_headers):
    """POST /api/tasks/{id}/unlock returns 404 for non-existent task."""
    await init_db()
    project = await _seed_project("Missing Unlock Scope")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/non-existent-id/unlock?project_id={project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_human_approval_moves_review_task_to_done(auth_headers):
    """Only a human review action moves an In Review task to Done."""
    await init_db()
    project = await _seed_project("Review Flow")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Approve reviewed work"},
        )
        assert created.status_code == 201
        task_id = created.json()["id"]

        moved = await ac.post(
            f"/api/tasks/{task_id}/move?status=in_review&project_id={project.id}",
            headers=auth_headers,
        )
        assert moved.status_code == 200
        assert moved.json()["status"] == "in_review"
        assert moved.json()["review_state"] == "awaiting_review"

        approved = await ac.post(
            f"/api/tasks/{task_id}/review/approve?project_id={project.id}",
            headers=auth_headers,
            json={"reviewed_by": "tester", "note": "Looks correct."},
        )
        assert approved.status_code == 200
        payload = approved.json()
        assert payload["task"]["status"] == "done"
        assert payload["task"]["review_state"] == "approved"
        assert payload["event"]["outcome"] == "approved"
        from app.core.telemetry import telemetry_recorder

        audit = await telemetry_recorder.get_research_validity_audit(project.id)
        assert audit["operation_counts"]["kanban.status_transition"] == 2
        assert audit["operation_counts"]["human_review.decision"] == 1


@pytest.mark.asyncio
async def test_task_review_side_effects_observe_committed_task(auth_headers, monkeypatch):
    """Review side effects must run after commit so separate DB sessions never self-lock."""
    await init_db()
    project = await _seed_project("Review Side Effects")
    observed = []

    async def fake_side_effects(event, score=None):
        async with async_session() as db:
            task = await db.get(Task, event.task_id)
            observed.append({"status": task.status.value, "review_state": task.review_state})

    monkeypatch.setattr("app.core.task_review.record_review_side_effects", fake_side_effects)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Approve with side effects"},
        )
        task_id = created.json()["id"]
        await ac.post(f"/api/tasks/{task_id}/move?status=in_review&project_id={project.id}", headers=auth_headers)

        approved = await ac.post(
            f"/api/tasks/{task_id}/review/approve?project_id={project.id}",
            headers=auth_headers,
            json={"reviewed_by": "tester", "note": "Committed before telemetry."},
        )

    assert approved.status_code == 200
    assert observed == [{"status": "done", "review_state": "approved"}]


@pytest.mark.asyncio
async def test_task_approval_blocks_uncoded_reportable_findings(auth_headers):
    """A research task with findings cannot move to Done before coded evidence is accepted."""
    await init_db()
    project = await _seed_project("Approval Validity Gate")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Approve only after coding"},
        )
        assert created.status_code == 201
        task_id = created.json()["id"]

        async with async_session() as db:
            db.add(
                Nugget(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    task_id=task_id,
                    text="Participant could not find the invite flow.",
                    source="interview",
                )
            )
            await db.commit()

        moved = await ac.post(
            f"/api/tasks/{task_id}/move?status=in_review&project_id={project.id}",
            headers=auth_headers,
        )
        assert moved.status_code == 200

        blocked = await ac.post(
            f"/api/tasks/{task_id}/review/approve?project_id={project.id}",
            headers=auth_headers,
            json={"reviewed_by": "tester", "note": "Trying to approve uncoded evidence."},
        )
        assert blocked.status_code == 409
        assert "no coded evidence applications" in blocked.json()["detail"]

        async with async_session() as db:
            _add_accepted_nugget_support(
                db,
                project_id=project.id,
                task_id=task_id,
                nugget_id=(
                    await db.execute(
                        select(Nugget.id).where(
                            Nugget.project_id == project.id,
                            Nugget.task_id == task_id,
                        )
                    )
                ).scalar_one(),
                source_text="Participant could not find the invite flow.",
            )
            await db.commit()

        approved = await ac.post(
            f"/api/tasks/{task_id}/review/approve?project_id={project.id}",
            headers=auth_headers,
            json={"reviewed_by": "tester", "note": "Coded evidence accepted."},
        )
        assert approved.status_code == 200
        assert approved.json()["task"]["status"] == "done"


@pytest.mark.asyncio
async def test_task_report_gate_blocks_aggregate_reliability_bulk_acceptance(auth_headers):
    """One accepted code application must not make every task finding reportable."""
    await init_db()
    project = await _seed_project("Item Level Report Gate")
    task_id = str(uuid.uuid4())
    supported_nugget_id = str(uuid.uuid4())
    unsupported_nugget_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(
            Task(
                id=task_id,
                project_id=project.id,
                title="Do not bulk accept findings",
                status=TaskStatus.DONE,
                review_state="approved",
            )
        )
        db.add_all(
            [
                Nugget(
                    id=supported_nugget_id,
                    project_id=project.id,
                    task_id=task_id,
                    text="Supported quote",
                    source="interview",
                ),
                Nugget(
                    id=unsupported_nugget_id,
                    project_id=project.id,
                    task_id=task_id,
                    text="Unsupported quote",
                    source="interview",
                ),
            ]
        )
        _add_accepted_nugget_support(
            db,
            project_id=project.id,
            task_id=task_id,
            nugget_id=supported_nugget_id,
            source_text="Supported quote",
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        blocked = await ac.post(
            f"/api/tasks/{task_id}/reports?project_id={project.id}",
            headers=auth_headers,
        )
        assert blocked.status_code == 409
        assert "without accepted/reconciled source evidence" in blocked.json()["detail"]

    async with async_session() as db:
        _add_accepted_nugget_support(
            db,
            project_id=project.id,
            task_id=task_id,
            nugget_id=unsupported_nugget_id,
            source_text="Unsupported quote",
        )
        await db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        allowed = await ac.post(
            f"/api/tasks/{task_id}/reports?project_id={project.id}",
            headers=auth_headers,
        )
        assert allowed.status_code == 200
        assert allowed.json()["report"]["finding_count"] == 2


@pytest.mark.asyncio
async def test_task_report_gate_blocks_done_task_without_accepted_evidence(auth_headers):
    """A Done task with only notes cannot become report content."""
    await init_db()
    project = await _seed_project("Empty Report Gate")
    task_id = str(uuid.uuid4())

    async with async_session() as db:
        db.add(
            Task(
                id=task_id,
                project_id=project.id,
                title="Done but no accepted evidence",
                description="Operational notes are not research evidence.",
                status=TaskStatus.DONE,
                review_state="approved",
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        blocked = await ac.post(
            f"/api/tasks/{task_id}/reports?project_id={project.id}",
            headers=auth_headers,
        )

    assert blocked.status_code == 409
    assert "no accepted/reconciled evidence" in blocked.json()["detail"]


@pytest.mark.asyncio
async def test_task_atomic_snapshot_exposes_finding_research_validity():
    """Kanban/review snapshots must show whether task findings are accepted or provisional."""
    await init_db()
    project = await _seed_project("Atomic Snapshot Validity")
    task_id = str(uuid.uuid4())
    nugget_id = str(uuid.uuid4())

    async with async_session() as db:
        task = Task(
            id=task_id,
            project_id=project.id,
            title="Show validity in review",
            status=TaskStatus.DONE,
            review_state="approved",
        )
        db.add(task)
        db.add(
            Nugget(
                id=nugget_id,
                project_id=project.id,
                task_id=task_id,
                text="Accepted source span",
                source="interview",
            )
        )
        _add_accepted_nugget_support(
            db,
            project_id=project.id,
            task_id=task_id,
            nugget_id=nugget_id,
            source_text="Accepted source span",
        )
        await db.commit()
        await db.refresh(task)

        from app.core.task_review import build_atomic_snapshot

        snapshot = await build_atomic_snapshot(db, task)

    item = snapshot["nuggets"]["items"][0]
    assert item["id"] == nugget_id
    assert item["research_validity"]["status"] == "accepted"
    assert item["research_validity"]["report_allowed"] is True


@pytest.mark.asyncio
async def test_done_task_revision_returns_to_backlog_with_feedback(auth_headers):
    """A Done task can be flagged later and must leave Done for agent action."""
    await init_db()
    project = await _seed_project("Revision Flow")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Reopen wrong work"},
        )
        task_id = created.json()["id"]
        await ac.post(f"/api/tasks/{task_id}/move?status=in_review&project_id={project.id}", headers=auth_headers)
        await ac.post(f"/api/tasks/{task_id}/review/approve?project_id={project.id}", headers=auth_headers, json={})

        revised = await ac.post(
            f"/api/tasks/{task_id}/review/request-revision?project_id={project.id}",
            headers=auth_headers,
            json={
                "what_to_review": "The synthesis missed the pricing evidence; rerun with the pricing document.",
                "next_status": "backlog",
                "failure_category": "missing_evidence",
                "labels": [{"name": "pricing", "color": "#2563eb", "kind": "task"}],
            },
        )
        assert revised.status_code == 200
        payload = revised.json()
        assert payload["task"]["status"] == "backlog"
        assert payload["task"]["review_state"] == "rejected_after_done"
        assert payload["task"]["failure_streak"] == 1
        assert payload["event"]["next_status"] == "backlog"
        assert payload["event"]["failure_category"] == "missing_evidence"
        from app.core.telemetry import telemetry_recorder

        audit = await telemetry_recorder.get_research_validity_audit(project.id)
        assert audit["operation_counts"]["kanban.status_transition"] == 3
        assert audit["operation_counts"]["human_review.decision"] == 2


@pytest.mark.asyncio
async def test_revision_cannot_send_task_back_to_review(auth_headers):
    """Rejected work must return to backlog or in progress, not In Review."""
    await init_db()
    project = await _seed_project("Invalid Revision Target")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "Invalid revision target"},
        )
        task_id = created.json()["id"]
        await ac.post(f"/api/tasks/{task_id}/move?status=in_review&project_id={project.id}", headers=auth_headers)
        response = await ac.post(
            f"/api/tasks/{task_id}/review/request-revision?project_id={project.id}",
            headers=auth_headers,
            json={"what_to_review": "Needs more evidence.", "next_status": "in_review"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_cannot_mark_task_done(auth_headers):
    """Generic task patching cannot bypass the human review approval path."""
    await init_db()
    project = await _seed_project("Patch Done Bypass")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={"project_id": project.id, "title": "No patch done bypass"},
        )
        task_id = created.json()["id"]
        response = await ac.patch(
            f"/api/tasks/{task_id}?project_id={project.id}",
            headers=auth_headers,
            json={"status": "done"},
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_task_create_rejects_foreign_input_document(auth_headers):
    """Task inputs must belong to the same project as the task."""
    await init_db()
    project = await _seed_project("Task Project")
    other_project = await _seed_project("Other Document Project")
    foreign_doc = await _seed_document(other_project.id, "Foreign Evidence")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/tasks",
            headers=auth_headers,
            json={
                "project_id": project.id,
                "title": "Analyze local documents only",
                "input_document_ids": [foreign_doc.id],
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_task_attach_rejects_foreign_document(auth_headers):
    """Attach/detach endpoints must not link documents from another project."""
    await init_db()
    project = await _seed_project("Attach Project")
    other_project = await _seed_project("Foreign Attach Project")
    task = await _seed_task(project.id)
    foreign_doc = await _seed_document(other_project.id, "Attach Foreign Evidence")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/tasks/{task.id}/attach?document_id={foreign_doc.id}&direction=input&project_id={project.id}",
            headers=auth_headers,
        )

    assert response.status_code == 404
