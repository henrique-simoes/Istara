"""Team-mode project RBAC tests."""

from types import SimpleNamespace
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.api.routes import connections as connection_routes
from app.core.auth import create_token
from app.core.connection_string import decode_connection_string
from app.main import app
from app.models.database import async_session, init_db
from app.models.document import Document, DocumentStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.session import ChatSession
from app.models.task import Task, TaskStatus


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    original_network_token = settings.network_access_token
    monkeypatch.setattr(connection_routes, "persist_env_value", lambda key, value: None)
    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    settings.team_mode = True
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret
    settings.network_access_token = original_network_token


def _headers(user_id: str, username: str, role: str) -> dict[str, str]:
    token = create_token(user_id, username, role)
    return {"Authorization": f"Bearer {token}"}


async def _seed_project(name: str) -> Project:
    project = Project(
        id=str(uuid.uuid4()),
        name=name,
        description="RBAC test project",
    )
    async with async_session() as db:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


async def _seed_member(project_id: str, user_id: str, role: str) -> None:
    async with async_session() as db:
        db.add(
            ProjectMember(
                id=str(uuid.uuid4()),
                project_id=project_id,
                user_id=user_id,
                role=role,
                added_by="test",
            )
        )
        await db.commit()


async def _seed_session(project_id: str, session_type: str = "chat") -> ChatSession:
    session = ChatSession(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=f"{session_type.title()} Session",
        session_type=session_type,
        agent_id="design-lead" if session_type == "design" else None,
    )
    async with async_session() as db:
        db.add(session)
        await db.commit()
        await db.refresh(session)
    return session


async def _seed_task(project_id: str) -> Task:
    task = Task(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title="RBAC Task",
        status=TaskStatus.BACKLOG,
    )
    async with async_session() as db:
        db.add(task)
        await db.commit()
        await db.refresh(task)
    return task


async def _seed_document(project_id: str) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title="RBAC Document",
        file_name="rbac.txt",
        file_type=".txt",
        status=DocumentStatus.READY,
        content_text="Document content",
    )
    async with async_session() as db:
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_admin_sees_all_projects_researcher_only_invited_projects():
    await init_db()
    invited = await _seed_project(f"Invited {uuid.uuid4()}")
    hidden = await _seed_project(f"Hidden {uuid.uuid4()}")
    researcher_id = f"researcher-{uuid.uuid4()}"
    await _seed_member(invited.id, researcher_id, "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_response = await ac.get(
            "/api/projects",
            headers=_headers("admin-user", "admin", "admin"),
        )
        researcher_response = await ac.get(
            "/api/projects",
            headers=_headers(researcher_id, "researcher", "researcher"),
        )

    assert admin_response.status_code == 200
    assert researcher_response.status_code == 200

    admin_ids = {p["id"] for p in admin_response.json()}
    researcher_ids = {p["id"] for p in researcher_response.json()}

    assert invited.id in admin_ids
    assert hidden.id in admin_ids
    assert invited.id in researcher_ids
    assert hidden.id not in researcher_ids
    invited_project = next(p for p in researcher_response.json() if p["id"] == invited.id)
    assert invited_project["current_user_project_role"] == "researcher"


@pytest.mark.asyncio
async def test_uninvited_project_detail_is_concealed_as_404():
    await init_db()
    project = await _seed_project(f"Concealed {uuid.uuid4()}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/projects/{project.id}",
            headers=_headers(f"researcher-{uuid.uuid4()}", "researcher", "researcher"),
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_viewer_can_read_visible_project_but_cannot_update_it():
    await init_db()
    project = await _seed_project(f"Viewer {uuid.uuid4()}")
    viewer_id = f"viewer-{uuid.uuid4()}"
    await _seed_member(project.id, viewer_id, "viewer")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        read_response = await ac.get(
            f"/api/projects/{project.id}",
            headers=_headers(viewer_id, "viewer", "viewer"),
        )
        write_response = await ac.patch(
            f"/api/projects/{project.id}",
            headers=_headers(viewer_id, "viewer", "viewer"),
            json={"name": "Viewer should not write"},
        )

    assert read_response.status_code == 200
    assert write_response.status_code == 403


@pytest.mark.asyncio
async def test_researcher_permission_request_is_reviewed_by_project_admin():
    await init_db()
    project = await _seed_project(f"Permission Request {uuid.uuid4()}")
    researcher_id = f"researcher-request-{uuid.uuid4()}"
    project_admin_id = f"project-admin-request-{uuid.uuid4()}"
    await _seed_member(project.id, researcher_id, "researcher")
    await _seed_member(project.id, project_admin_id, "project_admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/permission-requests",
            headers=_headers(researcher_id, "researcher", "researcher"),
            json={
                "project_id": project.id,
                "action": "project.folder",
                "title": "Request folder change",
                "details": "Please link the moderated study folder.",
            },
        )
        assert created.status_code == 201
        request_id = created.json()["id"]

        listed = await ac.get(
            f"/api/permission-requests?project_id={project.id}&status=pending",
            headers=_headers(project_admin_id, "project-admin", "researcher"),
        )
        assert listed.status_code == 200
        assert any(item["id"] == request_id for item in listed.json()["requests"])

        reviewed = await ac.patch(
            f"/api/permission-requests/{request_id}?project_id={project.id}",
            headers=_headers(project_admin_id, "project-admin", "researcher"),
            json={"status": "approved", "review_note": "Approved for this study."},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "approved"
        assert reviewed.json()["reviewer_user_id"] == project_admin_id


@pytest.mark.asyncio
async def test_permission_request_review_requires_active_project_binding():
    await init_db()
    active_project = await _seed_project(f"Active Permission Scope {uuid.uuid4()}")
    other_project = await _seed_project(f"Other Permission Scope {uuid.uuid4()}")
    researcher_id = f"researcher-request-scope-{uuid.uuid4()}"
    project_admin_id = f"project-admin-request-scope-{uuid.uuid4()}"
    await _seed_member(other_project.id, researcher_id, "researcher")
    await _seed_member(active_project.id, project_admin_id, "project_admin")
    await _seed_member(other_project.id, project_admin_id, "project_admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/permission-requests",
            headers=_headers(researcher_id, "researcher", "researcher"),
            json={
                "project_id": other_project.id,
                "action": "project.folder",
                "title": "Request folder change",
            },
        )
        assert created.status_code == 201
        request_id = created.json()["id"]

        no_project = await ac.patch(
            f"/api/permission-requests/{request_id}",
            headers=_headers(project_admin_id, "project-admin", "researcher"),
            json={"status": "approved"},
        )
        assert no_project.status_code == 400
        assert no_project.json()["detail"] == "project_id is required"

        wrong_active_project = await ac.patch(
            f"/api/permission-requests/{request_id}?project_id={active_project.id}",
            headers=_headers(project_admin_id, "project-admin", "researcher"),
            json={"status": "approved"},
        )
        assert wrong_active_project.status_code == 404

        reviewed = await ac.patch(
            f"/api/permission-requests/{request_id}?project_id={other_project.id}",
            headers=_headers(project_admin_id, "project-admin", "researcher"),
            json={"status": "approved"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "approved"
        assert reviewed.json()["project_id"] == other_project.id


@pytest.mark.asyncio
async def test_non_admin_permission_request_mine_requires_active_project_scope():
    await init_db()
    project_a = await _seed_project(f"Mine Permission A {uuid.uuid4()}")
    project_b = await _seed_project(f"Mine Permission B {uuid.uuid4()}")
    researcher_id = f"researcher-mine-request-{uuid.uuid4()}"
    await _seed_member(project_a.id, researcher_id, "researcher")
    await _seed_member(project_b.id, researcher_id, "researcher")
    headers = _headers(researcher_id, "researcher", "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created_a = await ac.post(
            "/api/permission-requests",
            headers=headers,
            json={
                "project_id": project_a.id,
                "action": "project.folder",
                "title": "Request A",
            },
        )
        created_b = await ac.post(
            "/api/permission-requests",
            headers=headers,
            json={
                "project_id": project_b.id,
                "action": "project.folder",
                "title": "Request B",
            },
        )
        assert created_a.status_code == 201
        assert created_b.status_code == 201
        request_a_id = created_a.json()["id"]
        request_b_id = created_b.json()["id"]

        unscoped = await ac.get("/api/permission-requests?mine=true", headers=headers)
        assert unscoped.status_code == 400
        assert unscoped.json()["detail"] == "project_id is required"

        scoped = await ac.get(
            f"/api/permission-requests?project_id={project_a.id}&mine=true",
            headers=headers,
        )
        assert scoped.status_code == 200
        request_ids = {item["id"] for item in scoped.json()["requests"]}
        assert request_a_id in request_ids
        assert request_b_id not in request_ids


@pytest.mark.asyncio
async def test_global_admin_permission_request_queue_remains_global():
    await init_db()
    project_a = await _seed_project(f"Admin Permission A {uuid.uuid4()}")
    project_b = await _seed_project(f"Admin Permission B {uuid.uuid4()}")
    researcher_a_id = f"researcher-admin-request-a-{uuid.uuid4()}"
    researcher_b_id = f"researcher-admin-request-b-{uuid.uuid4()}"
    await _seed_member(project_a.id, researcher_a_id, "researcher")
    await _seed_member(project_b.id, researcher_b_id, "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created_a = await ac.post(
            "/api/permission-requests",
            headers=_headers(researcher_a_id, "researcher-a", "researcher"),
            json={
                "project_id": project_a.id,
                "action": "project.folder",
                "title": "Admin queue A",
            },
        )
        created_b = await ac.post(
            "/api/permission-requests",
            headers=_headers(researcher_b_id, "researcher-b", "researcher"),
            json={
                "project_id": project_b.id,
                "action": "project.folder",
                "title": "Admin queue B",
            },
        )
        assert created_a.status_code == 201
        assert created_b.status_code == 201
        request_a_id = created_a.json()["id"]
        request_b_id = created_b.json()["id"]

        listed = await ac.get(
            "/api/permission-requests?status=pending",
            headers=_headers("admin-user", "admin", "admin"),
        )
        assert listed.status_code == 200
        listed_ids = {item["id"] for item in listed.json()["requests"]}
        assert request_a_id in listed_ids
        assert request_b_id in listed_ids

        reviewed = await ac.patch(
            f"/api/permission-requests/{request_a_id}",
            headers=_headers("admin-user", "admin", "admin"),
            json={"status": "approved"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "approved"
        assert reviewed.json()["project_id"] == project_a.id


@pytest.mark.asyncio
async def test_viewer_can_read_chat_history_but_cannot_send_chat_or_create_session():
    await init_db()
    project = await _seed_project(f"Viewer Chat {uuid.uuid4()}")
    viewer_id = f"viewer-chat-{uuid.uuid4()}"
    await _seed_member(project.id, viewer_id, "viewer")
    headers = _headers(viewer_id, "viewer", "viewer")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        history_response = await ac.get(
            f"/api/chat/history/{project.id}",
            headers=headers,
        )
        chat_response = await ac.post(
            "/api/chat",
            headers=headers,
            json={"message": "Can I write?", "project_id": project.id},
        )
        session_response = await ac.post(
            "/api/sessions",
            headers=headers,
            json={"project_id": project.id, "title": "Viewer session"},
        )

    assert history_response.status_code == 200
    assert chat_response.status_code == 403
    assert session_response.status_code == 403


@pytest.mark.asyncio
async def test_chat_rejects_session_from_another_project():
    await init_db()
    visible_project = await _seed_project(f"Visible Chat {uuid.uuid4()}")
    other_project = await _seed_project(f"Other Chat {uuid.uuid4()}")
    foreign_session = await _seed_session(other_project.id, "chat")
    researcher_id = f"researcher-chat-session-{uuid.uuid4()}"
    await _seed_member(visible_project.id, researcher_id, "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            headers=_headers(researcher_id, "researcher", "researcher"),
            json={
                "message": "This should not attach to a foreign session",
                "project_id": visible_project.id,
                "session_id": foreign_session.id,
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_voice_transcription_requires_project_id_before_transcription(monkeypatch):
    await init_db()
    calls: list[str] = []

    monkeypatch.setattr(
        "app.core.transcription.convert_audio_to_wav",
        lambda path: calls.append("convert") or path,
    )
    monkeypatch.setattr(
        "app.core.transcription.transcribe_audio",
        lambda path, language=None: calls.append("transcribe") or SimpleNamespace(
            text="should not run",
            language="en",
            confidence=1.0,
            icr_kappa=1.0,
            icr_confidence="high",
            needs_review=False,
            tags=[],
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_scope = await ac.post(
            "/api/chat/voice",
            headers=_headers(f"admin-voice-{uuid.uuid4()}", "admin", "admin"),
            files={"audio": ("sample.ogg", b"not-a-real-audio-file", "audio/ogg")},
        )
        blank_scope = await ac.post(
            "/api/chat/voice",
            headers=_headers(f"admin-voice-{uuid.uuid4()}", "admin", "admin"),
            data={"project_id": "   "},
            files={"audio": ("sample.ogg", b"not-a-real-audio-file", "audio/ogg")},
        )

    assert missing_scope.status_code == 422
    assert blank_scope.status_code == 400
    assert calls == []


@pytest.mark.asyncio
async def test_chat_voice_transcription_requires_project_researcher_role_before_audio_processing(monkeypatch):
    await init_db()
    project = await _seed_project(f"Voice Upload {uuid.uuid4()}")
    hidden_project_id = str(uuid.uuid4())
    viewer_id = f"viewer-voice-{uuid.uuid4()}"
    researcher_id = f"researcher-voice-{uuid.uuid4()}"
    outsider_id = f"outsider-voice-{uuid.uuid4()}"
    await _seed_member(project.id, viewer_id, "viewer")
    await _seed_member(project.id, researcher_id, "researcher")
    calls: list[tuple[str, str | None]] = []

    def fake_convert(path: str) -> str:
        calls.append(("convert", None))
        return path

    def fake_transcribe(path: str, language: str | None = None) -> SimpleNamespace:
        calls.append(("transcribe", language))
        return SimpleNamespace(
            text="Scoped voice note",
            language=language or "en",
            confidence=0.91,
            icr_kappa=0.82,
            icr_confidence="high",
            needs_review=False,
            tags=["usability"],
        )

    monkeypatch.setattr("app.core.transcription.convert_audio_to_wav", fake_convert)
    monkeypatch.setattr("app.core.transcription.transcribe_audio", fake_transcribe)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        viewer_response = await ac.post(
            "/api/chat/voice",
            headers=_headers(viewer_id, "viewer", "viewer"),
            data={"project_id": project.id},
            files={"audio": ("sample.ogg", b"not-a-real-audio-file", "audio/ogg")},
        )
        outsider_response = await ac.post(
            "/api/chat/voice",
            headers=_headers(outsider_id, "researcher", "researcher"),
            data={"project_id": project.id},
            files={"audio": ("sample.ogg", b"not-a-real-audio-file", "audio/ogg")},
        )
        hidden_response = await ac.post(
            "/api/chat/voice",
            headers=_headers(f"admin-voice-{uuid.uuid4()}", "admin", "admin"),
            data={"project_id": hidden_project_id},
            files={"audio": ("sample.ogg", b"not-a-real-audio-file", "audio/ogg")},
        )
        researcher_response = await ac.post(
            "/api/chat/voice",
            headers=_headers(researcher_id, "researcher", "researcher"),
            data={"project_id": project.id, "language": "pt"},
            files={"audio": ("sample.ogg", b"not-a-real-audio-file", "audio/ogg")},
        )

    assert viewer_response.status_code == 403
    assert outsider_response.status_code == 404
    assert hidden_response.status_code == 404
    assert researcher_response.status_code == 200
    assert calls == [("convert", None), ("transcribe", "pt")]
    assert researcher_response.json()["text"] == "Scoped voice note"


@pytest.mark.asyncio
async def test_uninvited_chat_history_is_concealed_as_404():
    await init_db()
    project = await _seed_project(f"Hidden Chat {uuid.uuid4()}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/chat/history/{project.id}",
            headers=_headers(f"researcher-{uuid.uuid4()}", "researcher", "researcher"),
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_viewer_can_read_design_chat_history_but_cannot_send_design_chat():
    await init_db()
    project = await _seed_project(f"Viewer Design Chat {uuid.uuid4()}")
    viewer_id = f"viewer-design-{uuid.uuid4()}"
    await _seed_member(project.id, viewer_id, "viewer")
    headers = _headers(viewer_id, "viewer", "viewer")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        history_response = await ac.get(
            f"/api/interfaces/design-chat/{project.id}/history",
            headers=headers,
        )
        chat_response = await ac.post(
            "/api/interfaces/design-chat",
            headers=headers,
            json={"message": "Can I write?", "project_id": project.id},
        )

    assert history_response.status_code == 200
    assert chat_response.status_code == 403


@pytest.mark.asyncio
async def test_design_chat_rejects_session_from_another_project():
    await init_db()
    visible_project = await _seed_project(f"Visible Design {uuid.uuid4()}")
    other_project = await _seed_project(f"Other Design {uuid.uuid4()}")
    foreign_session = await _seed_session(other_project.id, "design")
    researcher_id = f"researcher-design-session-{uuid.uuid4()}"
    await _seed_member(visible_project.id, researcher_id, "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/interfaces/design-chat",
            headers=_headers(researcher_id, "researcher", "researcher"),
            json={
                "message": "This should not attach to a foreign design session",
                "project_id": visible_project.id,
                "session_id": foreign_session.id,
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_admin_can_manage_project_members_but_cannot_delete_project():
    await init_db()
    project = await _seed_project(f"Project Admin {uuid.uuid4()}")
    project_admin_id = f"project-admin-{uuid.uuid4()}"
    target_user_id = f"target-{uuid.uuid4()}"
    await _seed_member(project.id, project_admin_id, "project_admin")
    await _seed_member(project.id, target_user_id, "viewer")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        role_response = await ac.patch(
            f"/api/projects/{project.id}/members/{target_user_id}",
            headers=_headers(project_admin_id, "pa", "researcher"),
            json={"role": "member"},
        )
        delete_response = await ac.delete(
            f"/api/projects/{project.id}",
            headers=_headers(project_admin_id, "pa", "researcher"),
        )

    assert role_response.status_code == 200
    assert role_response.json()["role"] == "researcher"
    assert delete_response.status_code == 403


@pytest.mark.asyncio
async def test_researcher_cannot_create_project_in_team_mode():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/projects",
            headers=_headers(f"researcher-{uuid.uuid4()}", "researcher", "researcher"),
            json={"name": "Unauthorized project"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_overview_is_admin_only():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_response = await ac.get(
            "/api/admin/overview",
            headers=_headers("admin-user", "admin", "admin"),
        )
        researcher_response = await ac.get(
            "/api/admin/overview",
            headers=_headers(f"researcher-{uuid.uuid4()}", "researcher", "researcher"),
        )

    assert admin_response.status_code == 200
    assert "projects" in admin_response.json()
    assert researcher_response.status_code == 403


@pytest.mark.asyncio
async def test_connection_strings_split_user_invite_from_compute_donation():
    await init_db()
    project = await _seed_project(f"Compute Donation {uuid.uuid4()}")
    headers = _headers("admin-user", "admin", "admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        invite_response = await ac.post(
            "/api/connections/generate",
            headers=headers,
            json={"server_url": "http://localhost:3000", "label": "Researcher", "role": "researcher"},
        )
        donation_response = await ac.post(
            "/api/connections/compute-donation/generate",
            headers=headers,
            json={
                "server_url": "http://localhost:3000",
                "label": "Node",
                "allowed_project_ids": [project.id],
            },
        )
        donation_string = donation_response.json()["connection_string"]
        validate_response = await ac.post(
            "/api/connections/validate",
            json={"connection_string": donation_string},
        )
        redeem_response = await ac.post(
            "/api/connections/redeem",
            json={
                "connection_string": donation_string,
                "username": f"node-{uuid.uuid4()}",
                "password": "password123",
            },
        )

    assert invite_response.status_code == 200
    invite_payload = decode_connection_string(invite_response.json()["connection_string"])
    assert invite_payload["kind"] == "user_invite"
    assert "network_token" not in invite_payload

    assert donation_response.status_code == 200
    donation_payload = decode_connection_string(donation_string)
    assert donation_payload["kind"] == "compute_donation"
    assert donation_payload["allowed_project_ids"] == [project.id]
    assert donation_response.json()["allowed_project_ids"] == [project.id]
    assert "jwt" not in donation_payload
    assert validate_response.status_code == 200
    assert validate_response.json()["token_type"] == "compute_donation"
    assert redeem_response.status_code == 400


@pytest.mark.asyncio
async def test_viewer_can_read_tasks_and_documents_but_cannot_mutate_them():
    await init_db()
    project = await _seed_project(f"Viewer Resources {uuid.uuid4()}")
    viewer_id = f"viewer-resources-{uuid.uuid4()}"
    await _seed_member(project.id, viewer_id, "viewer")
    task = await _seed_task(project.id)
    document = await _seed_document(project.id)
    headers = _headers(viewer_id, "viewer", "viewer")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        tasks_response = await ac.get(f"/api/tasks?project_id={project.id}", headers=headers)
        task_detail_response = await ac.get(
            f"/api/tasks/{task.id}?project_id={project.id}",
            headers=headers,
        )
        documents_response = await ac.get(f"/api/documents?project_id={project.id}", headers=headers)
        create_task_response = await ac.post(
            "/api/tasks",
            headers=headers,
            json={"project_id": project.id, "title": "Nope"},
        )
        update_task_response = await ac.patch(
            f"/api/tasks/{task.id}?project_id={project.id}",
            headers=headers,
            json={"title": "Nope"},
        )
        update_document_response = await ac.patch(
            f"/api/documents/{document.id}?project_id={project.id}",
            headers=headers,
            json={"title": "Nope"},
        )

    assert tasks_response.status_code == 200
    assert task_detail_response.status_code == 200
    assert documents_response.status_code == 200
    assert create_task_response.status_code == 403
    assert update_task_response.status_code == 403
    assert update_document_response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_read_project_metrics_but_cannot_reprocess_files():
    await init_db()
    project = await _seed_project(f"Viewer Metrics {uuid.uuid4()}")
    viewer_id = f"viewer-metrics-{uuid.uuid4()}"
    await _seed_member(project.id, viewer_id, "viewer")
    headers = _headers(viewer_id, "viewer", "viewer")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        metrics_response = await ac.get(f"/api/metrics/{project.id}", headers=headers)
        reprocess_response = await ac.post(f"/api/files/{project.id}/reprocess", headers=headers)

    assert metrics_response.status_code == 200
    assert reprocess_response.status_code == 403


@pytest.mark.asyncio
async def test_uninvited_project_metrics_are_concealed_as_404():
    await init_db()
    project = await _seed_project(f"Hidden Metrics {uuid.uuid4()}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/metrics/{project.id}",
            headers=_headers(f"researcher-metrics-{uuid.uuid4()}", "researcher", "researcher"),
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mcp_policy_is_admin_only_and_client_registry_is_project_scoped():
    await init_db()
    project = await _seed_project(f"MCP RBAC {uuid.uuid4()}")
    project_admin_id = f"project-admin-mcp-{uuid.uuid4()}"
    await _seed_member(project.id, project_admin_id, "project_admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        researcher_policy = await ac.get(
            "/api/mcp/server/policy",
            headers=_headers(f"researcher-mcp-{uuid.uuid4()}", "researcher", "researcher"),
        )
        researcher_clients = await ac.get(
            "/api/mcp/clients",
            headers=_headers(f"researcher-mcp-{uuid.uuid4()}", "researcher", "researcher"),
        )
        project_admin_clients = await ac.get(
            f"/api/mcp/clients?project_id={project.id}",
            headers=_headers(project_admin_id, "project-admin-mcp", "researcher"),
        )
        admin_policy = await ac.get(
            "/api/mcp/server/policy",
            headers=_headers("admin-mcp", "admin", "admin"),
        )

    assert researcher_policy.status_code == 403
    assert researcher_clients.status_code == 400
    assert researcher_clients.json()["detail"] == "project_id is required"
    assert project_admin_clients.status_code == 200
    assert admin_policy.status_code == 200


@pytest.mark.asyncio
async def test_compute_is_researcher_visible_but_steering_and_meta_hyperagent_are_admin_only():
    await init_db()
    project = await _seed_project(f"System Compute {uuid.uuid4()}")
    researcher_id = f"researcher-system-{uuid.uuid4()}"
    await _seed_member(project.id, researcher_id, "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        researcher_headers = _headers(researcher_id, "researcher", "researcher")
        compute_response = await ac.get(
            f"/api/compute/stats?project_id={project.id}",
            headers=researcher_headers,
        )
        steering_response = await ac.get("/api/steering", headers=researcher_headers)
        meta_response = await ac.get("/api/meta-hyperagent/status", headers=researcher_headers)

        admin_project_response = await ac.get(
            f"/api/compute/stats?project_id={project.id}",
            headers=_headers("admin-system", "admin", "admin"),
        )
        admin_unscoped_response = await ac.get(
            "/api/compute/stats",
            headers=_headers("admin-system", "admin", "admin"),
        )

    assert compute_response.status_code == 200
    assert steering_response.status_code == 403
    assert meta_response.status_code == 403
    assert admin_project_response.status_code == 200
    assert admin_unscoped_response.status_code == 400
    assert admin_unscoped_response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_compute_donation_strings_require_explicit_project_scope(monkeypatch):
    await init_db()
    monkeypatch.setattr(settings, "network_access_token", "test-network-token")
    project = await _seed_project(f"Compute Scope {uuid.uuid4()}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing_scope = await ac.post(
            "/api/connections/compute-donation/generate",
            headers=_headers("admin-compute-scope", "admin", "admin"),
            json={"server_url": "http://localhost:3000", "label": "Unscoped donor"},
        )
        scoped = await ac.post(
            "/api/connections/compute-donation/generate",
            headers=_headers("admin-compute-scope", "admin", "admin"),
            json={
                "server_url": "http://localhost:3000",
                "label": "Scoped donor",
                "allowed_project_ids": [project.id],
            },
        )

    assert missing_scope.status_code == 422
    assert scoped.status_code == 200
    body = scoped.json()
    assert body["allowed_project_ids"] == [project.id]
    payload = decode_connection_string(body["connection_string"])
    assert payload["kind"] == "compute_donation"
    assert payload["allowed_project_ids"] == [project.id]


@pytest.mark.asyncio
async def test_legacy_voice_transcribe_respects_project_researcher_role():
    await init_db()
    project = await _seed_project(f"Voice RBAC {uuid.uuid4()}")
    viewer_id = f"viewer-voice-project-{uuid.uuid4()}"
    researcher_id = f"researcher-voice-project-{uuid.uuid4()}"
    await _seed_member(project.id, viewer_id, "viewer")
    await _seed_member(project.id, researcher_id, "researcher")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        viewer_response = await ac.post(
            "/api/chat/voice-transcribe",
            headers=_headers(viewer_id, "viewer", "viewer"),
            json={"project_id": project.id, "dummy": True},
        )
        researcher_response = await ac.post(
            "/api/chat/voice-transcribe",
            headers=_headers(researcher_id, "researcher", "researcher"),
            json={"project_id": project.id, "dummy": True},
        )

    assert viewer_response.status_code == 403
    assert researcher_response.status_code == 200
    assert researcher_response.json()["text"] == "Mock transcription"
