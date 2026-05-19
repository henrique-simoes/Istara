"""Tests for Notifications API routes — list, unread, mark-read, mark-all-read, preferences."""

from datetime import datetime, timezone
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.config import settings
from app.models.database import async_session, init_db
from app.core.auth import create_token
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_member import ProjectMember


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


@pytest.mark.asyncio
async def test_notifications_list_requires_active_project_scope_for_admin(auth_headers):
    """Project-facing notification lists require an active project for every role."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/notifications", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


@pytest.mark.asyncio
async def test_notifications_requires_auth():
    """Notifications requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/notifications")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_notifications_accept_frontend_filter_aliases(auth_headers):
    """Frontend plural aliases and date aliases should filter the API response."""
    await init_db()
    marker = f"alias-{uuid.uuid4()}"
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Alias notification project"),
                Notification(
                    id=str(uuid.uuid4()),
                    type="agent_status",
                    title=f"{marker} keep",
                    message="agent failed",
                    category="agent_status",
                    severity="error",
                    project_id=project_id,
                    read=False,
                    metadata_json='{"source":"test"}',
                    created_at=now,
                ),
                Notification(
                    id=str(uuid.uuid4()),
                    type="system",
                    title=f"{marker} skip",
                    message="system info",
                    category="system",
                    severity="info",
                    project_id=project_id,
                    read=True,
                    created_at=now,
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/notifications",
            params={
                "project_id": project_id,
                "categories": "agent_status,system",
                "severities": "error",
                "unread_only": "true",
                "from_date": now.date().isoformat(),
                "search": marker,
                "page": 1,
                "page_size": 20,
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["total_pages"] == 1
    assert data["notifications"][0]["title"] == f"{marker} keep"
    assert data["notifications"][0]["metadata"] == {"source": "test"}


@pytest.mark.asyncio
async def test_global_admin_notification_bulk_routes_are_project_scoped(auth_headers):
    """Global admins cannot use project-facing notification routes as a global inbox."""
    await init_db()
    settings.team_mode = True
    project_id = str(uuid.uuid4())
    hidden_project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Visible admin notifications"),
                Project(id=hidden_project_id, name="Hidden admin notifications"),
                Notification(
                    id=str(uuid.uuid4()),
                    type="document_created",
                    title="visible admin unread",
                    message="visible",
                    category="document",
                    severity="info",
                    project_id=project_id,
                    read=False,
                ),
                Notification(
                    id=str(uuid.uuid4()),
                    type="document_created",
                    title="hidden admin unread",
                    message="hidden",
                    category="document",
                    severity="info",
                    project_id=hidden_project_id,
                    read=False,
                ),
                Notification(
                    id=str(uuid.uuid4()),
                    type="system",
                    title="global admin unread",
                    message="global",
                    category="system",
                    severity="info",
                    read=False,
                ),
            ]
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        no_scope_list = await ac.get("/api/notifications", headers=auth_headers)
        no_scope_count = await ac.get("/api/notifications/unread-count", headers=auth_headers)
        no_scope_mark = await ac.post("/api/notifications/read-all", json={}, headers=auth_headers)
        list_response = await ac.get(
            "/api/notifications",
            params={"project_id": project_id},
            headers=auth_headers,
        )
        count_response = await ac.get(
            "/api/notifications/unread-count",
            params={"project_id": project_id},
            headers=auth_headers,
        )
        mark_response = await ac.post(
            "/api/notifications/read-all",
            json={"project_id": project_id},
            headers=auth_headers,
        )

    assert no_scope_list.status_code == 400
    assert no_scope_list.json()["detail"] == "project_id is required"
    assert no_scope_count.status_code == 400
    assert no_scope_count.json()["detail"] == "project_id is required"
    assert no_scope_mark.status_code == 400
    assert no_scope_mark.json()["detail"] == "project_id is required"
    assert list_response.status_code == 200
    assert [n["title"] for n in list_response.json()["notifications"]] == [
        "visible admin unread"
    ]
    assert count_response.json() == {"count": 1}
    assert mark_response.status_code == 200
    assert mark_response.json()["count"] == 1

    async with async_session() as db:
        rows = (
            await db.execute(
                select(Notification.title, Notification.read).where(
                    Notification.title.in_(
                        [
                            "visible admin unread",
                            "hidden admin unread",
                            "global admin unread",
                        ]
                    )
                )
            )
        ).all()
    assert dict(rows) == {
        "visible admin unread": True,
        "hidden admin unread": False,
        "global admin unread": False,
    }


@pytest.mark.asyncio
async def test_project_member_notifications_are_scoped_without_admin():
    """Project users must provide active project scope for notification bulk views."""
    await init_db()
    settings.team_mode = True
    user_id = f"user-{uuid.uuid4()}"
    project_id = str(uuid.uuid4())
    hidden_project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Visible notifications"),
                Project(id=hidden_project_id, name="Hidden notifications"),
                ProjectMember(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    user_id=user_id,
                    role="viewer",
                    added_by="test",
                ),
                Notification(
                    id=str(uuid.uuid4()),
                    type="document_created",
                    title="visible unread",
                    message="visible",
                    category="document",
                    severity="info",
                    project_id=project_id,
                    read=False,
                ),
                Notification(
                    id=str(uuid.uuid4()),
                    type="document_created",
                    title="hidden unread",
                    message="hidden",
                    category="document",
                    severity="info",
                    project_id=hidden_project_id,
                    read=False,
                ),
                Notification(
                    id=str(uuid.uuid4()),
                    type="system",
                    title="global unread",
                    message="global",
                    category="system",
                    severity="info",
                    read=False,
                ),
            ]
        )
        await db.commit()

    headers = {"Authorization": f"Bearer {create_token(user_id, 'scoped', 'researcher')}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        no_scope_list = await ac.get("/api/notifications", headers=headers)
        no_scope_count = await ac.get("/api/notifications/unread-count", headers=headers)
        no_scope_mark = await ac.post("/api/notifications/read-all", json={}, headers=headers)
        hidden_response = await ac.get(
            "/api/notifications",
            params={"project_id": hidden_project_id},
            headers=headers,
        )
        list_response = await ac.get(
            "/api/notifications",
            params={"project_id": project_id},
            headers=headers,
        )
        count_response = await ac.get(
            "/api/notifications/unread-count",
            params={"project_id": project_id},
            headers=headers,
        )
        mark_response = await ac.post(
            "/api/notifications/read-all",
            json={"project_id": project_id},
            headers=headers,
        )

    assert no_scope_list.status_code == 400
    assert no_scope_list.json()["detail"] == "project_id is required"
    assert no_scope_count.status_code == 400
    assert no_scope_count.json()["detail"] == "project_id is required"
    assert no_scope_mark.status_code == 400
    assert no_scope_mark.json()["detail"] == "project_id is required"
    assert hidden_response.status_code == 404
    assert list_response.status_code == 200
    assert [n["title"] for n in list_response.json()["notifications"]] == ["visible unread"]
    assert count_response.json() == {"count": 1}
    assert mark_response.status_code == 200
    assert mark_response.json()["count"] == 1

    async with async_session() as db:
        rows = (
            await db.execute(
                select(Notification.title, Notification.read).where(
                    Notification.title.in_(["visible unread", "hidden unread", "global unread"])
                )
            )
        ).all()
    assert dict(rows) == {
        "visible unread": True,
        "hidden unread": False,
        "global unread": False,
    }


@pytest.mark.asyncio
async def test_notification_item_actions_are_bound_to_active_project():
    """Stale notification ids from another accessible project cannot be mutated."""
    await init_db()
    settings.team_mode = True
    user_id = f"user-{uuid.uuid4()}"
    project_id = str(uuid.uuid4())
    other_project_id = str(uuid.uuid4())
    read_id = str(uuid.uuid4())
    delete_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_id, name="Notification item scope"),
                Project(id=other_project_id, name="Other notification item scope"),
                ProjectMember(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    user_id=user_id,
                    role="researcher",
                    added_by="test",
                ),
                ProjectMember(
                    id=str(uuid.uuid4()),
                    project_id=other_project_id,
                    user_id=user_id,
                    role="researcher",
                    added_by="test",
                ),
                Notification(
                    id=read_id,
                    type="document_created",
                    title="read me in active project",
                    message="visible",
                    category="document",
                    severity="info",
                    project_id=project_id,
                    read=False,
                ),
                Notification(
                    id=delete_id,
                    type="document_created",
                    title="delete me in active project",
                    message="visible",
                    category="document",
                    severity="info",
                    project_id=project_id,
                    read=False,
                ),
                Notification(
                    id=other_id,
                    type="document_created",
                    title="other project item",
                    message="other",
                    category="document",
                    severity="info",
                    project_id=other_project_id,
                    read=False,
                ),
            ]
        )
        await db.commit()

    headers = {"Authorization": f"Bearer {create_token(user_id, 'scoped', 'researcher')}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        no_scope_read = await ac.post(
            f"/api/notifications/{read_id}/read",
            json={},
            headers=headers,
        )
        wrong_scope_read = await ac.post(
            f"/api/notifications/{read_id}/read",
            params={"project_id": other_project_id},
            json={},
            headers=headers,
        )
        correct_scope_read = await ac.post(
            f"/api/notifications/{read_id}/read",
            params={"project_id": project_id},
            json={},
            headers=headers,
        )
        no_scope_delete = await ac.delete(
            f"/api/notifications/{delete_id}",
            headers=headers,
        )
        wrong_scope_delete = await ac.delete(
            f"/api/notifications/{delete_id}",
            params={"project_id": other_project_id},
            headers=headers,
        )
        correct_scope_delete = await ac.delete(
            f"/api/notifications/{delete_id}",
            params={"project_id": project_id},
            headers=headers,
        )

    assert no_scope_read.status_code == 400
    assert no_scope_read.json()["detail"] == "project_id is required"
    assert wrong_scope_read.status_code == 404
    assert correct_scope_read.status_code == 200
    assert no_scope_delete.status_code == 400
    assert no_scope_delete.json()["detail"] == "project_id is required"
    assert wrong_scope_delete.status_code == 404
    assert correct_scope_delete.status_code == 204

    async with async_session() as db:
        rows = (
            await db.execute(
                select(Notification.id, Notification.read).where(
                    Notification.id.in_([read_id, delete_id, other_id])
                )
            )
        ).all()

    assert dict(rows) == {
        read_id: True,
        other_id: False,
    }


@pytest.mark.asyncio
async def test_notification_preferences_use_wrapped_payload_and_validate_categories(auth_headers):
    """Preference updates should match the frontend API helper and reject orphans."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ok = await ac.put(
            "/api/notifications/preferences",
            json={"preferences": [{"category": "system", "show_toast": False}]},
            headers=auth_headers,
        )
        bad = await ac.put(
            "/api/notifications/preferences",
            json={"preferences": [{"category": "not_real"}]},
            headers=auth_headers,
        )

    assert ok.status_code == 200
    assert ok.json()["preferences"][0]["category"] == "system"
    assert ok.json()["preferences"][0]["show_toast"] is False
    assert bad.status_code == 400
