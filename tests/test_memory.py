"""Tests for Memory API routes — list, search, stats, agentNotes, deleteSource."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.core.rag import RAGContext, RetrievalResult
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.core.auth import create_token


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


async def _seed_project() -> Project:
    project = Project(id=str(uuid.uuid4()), name=f"Memory {uuid.uuid4()}")
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


@pytest.mark.asyncio
async def test_memory_list_returns_list(auth_headers):
    """GET /api/memory/{project_id} returns memory entries."""
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/memory/{project.id}", headers=auth_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_memory_list_requires_auth():
    """Memory listing requires authentication in team mode."""
    await init_db()
    settings.team_mode = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/memory/test-project")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_memory_search_returns_response(auth_headers):
    """GET /api/memory/{project_id}/search returns search results."""
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/memory/{project.id}/search", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"results": [], "query": "", "total": 0}


@pytest.mark.asyncio
async def test_memory_stats_returns_response(auth_headers):
    """GET /api/memory/{project_id}/stats returns stats."""
    await init_db()
    project = await _seed_project()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/memory/{project.id}/stats", headers=auth_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_memory_routes_reject_unknown_project(auth_headers):
    """Memory APIs should not open project storage for unknown projects."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_response = await ac.get("/api/memory/not-a-project", headers=auth_headers)
        search_response = await ac.get(
            "/api/memory/not-a-project/search",
            headers=auth_headers,
            params={"q": "pricing"},
        )
        stats_response = await ac.get("/api/memory/not-a-project/stats", headers=auth_headers)

    assert list_response.status_code == 404
    assert search_response.status_code == 404
    assert stats_response.status_code == 404


@pytest.mark.asyncio
async def test_memory_routes_conceal_uninvited_projects_in_team_mode():
    """Project memory must only be visible to members of that project."""
    await init_db()
    settings.team_mode = True
    visible = await _seed_project()
    hidden = await _seed_project()
    await _seed_member(visible.id, "researcher-1", "researcher")
    headers = {"Authorization": f"Bearer {create_token('researcher-1', 'researcher', 'researcher')}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        visible_response = await ac.get(f"/api/memory/{visible.id}", headers=headers)
        hidden_response = await ac.get(f"/api/memory/{hidden.id}", headers=headers)

    assert visible_response.status_code == 200
    assert hidden_response.status_code == 404


@pytest.mark.asyncio
async def test_memory_search_supports_q_alias_and_metadata_filters(auth_headers, monkeypatch):
    await init_db()
    project = await _seed_project()
    captured: dict[str, object] = {}

    async def fake_retrieve_context(project_id: str, query: str, top_k: int | None = None, **kwargs):
        captured.update(
            {
                "project_id": project_id,
                "query": query,
                "top_k": top_k,
                **kwargs,
            }
        )
        return RAGContext(
            query=query,
            retrieved=[
                RetrievalResult(
                    text="Pricing was hard to understand.",
                    source="interview.pdf",
                    page=2,
                    score=0.73,
                )
            ],
            context_text="",
        )

    monkeypatch.setattr("app.api.routes.memory.retrieve_context", fake_retrieve_context)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/memory/{project.id}/search",
            headers=auth_headers,
            params={"q": "pricing", "top_k": 7, "source": "interview.pdf", "file_type": ".pdf"},
        )

    assert response.status_code == 200
    assert captured["query"] == "pricing"
    assert captured["top_k"] == 7
    assert captured["source_filter"] == "interview.pdf"
    assert captured["file_type_filter"] == "pdf"
    assert response.json()["filters"] == {"source": "interview.pdf", "file_type": "pdf"}
