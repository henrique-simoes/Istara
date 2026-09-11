"""Project isolation tests for context hierarchy composition."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.context_hierarchy import (
    ContextDocument,
    PLATFORM_CONTEXT,
    context_hierarchy,
)
from app.main import app
from app.models.database import async_session, init_db
from app.models.project import Project


@pytest.fixture(autouse=True)
def reset_settings():
    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest_asyncio.fixture
async def context_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ContextDocument.__table__.create)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as db:
        yield db

    await engine.dispose()


async def _seed_context_documents(db: AsyncSession) -> None:
    db.add_all(
        [
            ContextDocument(
                id="global-maintenance",
                name="Global Maintenance",
                level=1,
                level_type="company",
                project_id="",
                content="Global company defaults must stay admin-only.",
                priority=50,
            ),
            ContextDocument(
                id="project-a-product",
                name="Project A Product",
                level=2,
                level_type="product",
                project_id="project-a",
                content="Project A product language.",
                priority=20,
            ),
            ContextDocument(
                id="project-a-context",
                name="Project A Context",
                level=3,
                level_type="project",
                project_id="project-a",
                content="Project A research goals.",
                priority=10,
            ),
            ContextDocument(
                id="project-b-context",
                name="Project B Context",
                level=3,
                level_type="project",
                project_id="project-b",
                content="Project B confidential context.",
                priority=10,
            ),
        ]
    )
    await db.commit()


@pytest.mark.asyncio
async def test_project_list_excludes_global_and_other_project_contexts(
    context_db: AsyncSession,
):
    await _seed_context_documents(context_db)

    contexts = await context_hierarchy.list_contexts(context_db, project_id="project-a")

    assert [context.name for context in contexts] == [
        "Project A Product",
        "Project A Context",
    ]
    assert all(context.project_id == "project-a" for context in contexts)


@pytest.mark.asyncio
async def test_composed_context_uses_platform_defaults_and_active_project_only(
    context_db: AsyncSession,
):
    await _seed_context_documents(context_db)

    composed = await context_hierarchy.compose_context(
        context_db, project_id="project-a"
    )

    assert PLATFORM_CONTEXT in composed
    assert "Project A product language." in composed
    assert "Project A research goals." in composed
    assert "Global company defaults must stay admin-only." not in composed
    assert "Project B confidential context." not in composed


@pytest.mark.asyncio
async def test_admin_unscoped_context_list_and_composition_exclude_project_rows(
    context_db: AsyncSession,
):
    await _seed_context_documents(context_db)

    contexts = await context_hierarchy.list_contexts(context_db)
    composed = await context_hierarchy.compose_context(context_db)

    assert [context.name for context in contexts] == ["Global Maintenance"]
    assert "Global company defaults must stay admin-only." in composed
    assert "Project A research goals." not in composed
    assert "Project B confidential context." not in composed


async def _seed_api_context_documents() -> tuple[str, str, str, str, str]:
    project_a = f"context-api-a-{uuid.uuid4()}"
    project_b = f"context-api-b-{uuid.uuid4()}"
    read_doc_id = f"context-read-{uuid.uuid4()}"
    delete_doc_id = f"context-delete-{uuid.uuid4()}"
    global_doc_id = f"context-global-{uuid.uuid4()}"
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="Context API A"),
                Project(id=project_b, name="Context API B"),
                ContextDocument(
                    id=read_doc_id,
                    name="Project A Read Context",
                    level=3,
                    level_type="project",
                    project_id=project_a,
                    content="Project A route content.",
                    priority=10,
                ),
                ContextDocument(
                    id=delete_doc_id,
                    name="Project A Delete Context",
                    level=3,
                    level_type="project",
                    project_id=project_a,
                    content="Project A delete content.",
                    priority=10,
                ),
                ContextDocument(
                    id=global_doc_id,
                    name="Global Maintenance Context",
                    level=1,
                    level_type="company",
                    project_id="",
                    content="Admin-only maintenance context.",
                    priority=10,
                ),
            ]
        )
        await db.commit()
    return project_a, project_b, read_doc_id, delete_doc_id, global_doc_id


@pytest.mark.asyncio
async def test_context_by_id_routes_require_active_project_scope(admin_auth_headers):
    await init_db()
    (
        project_a,
        project_b,
        read_doc_id,
        delete_doc_id,
        global_doc_id,
    ) = await _seed_api_context_documents()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing = await ac.get(
            f"/api/contexts/{read_doc_id}", headers=admin_auth_headers
        )
        wrong = await ac.get(
            f"/api/contexts/{read_doc_id}?project_id={project_b}",
            headers=admin_auth_headers,
        )
        correct = await ac.get(
            f"/api/contexts/{read_doc_id}?project_id={project_a}",
            headers=admin_auth_headers,
        )
        wrong_update = await ac.patch(
            f"/api/contexts/{read_doc_id}?project_id={project_b}",
            headers=admin_auth_headers,
            json={"content": "wrong"},
        )
        correct_update = await ac.patch(
            f"/api/contexts/{read_doc_id}?project_id={project_a}",
            headers=admin_auth_headers,
            json={"content": "updated"},
        )
        delete_missing = await ac.delete(
            f"/api/contexts/{delete_doc_id}", headers=admin_auth_headers
        )
        delete_wrong = await ac.delete(
            f"/api/contexts/{delete_doc_id}?project_id={project_b}",
            headers=admin_auth_headers,
        )
        delete_correct = await ac.delete(
            f"/api/contexts/{delete_doc_id}?project_id={project_a}",
            headers=admin_auth_headers,
        )
        global_unscoped = await ac.get(
            f"/api/contexts/{global_doc_id}", headers=admin_auth_headers
        )
        global_project_scoped = await ac.get(
            f"/api/contexts/{global_doc_id}?project_id={project_a}",
            headers=admin_auth_headers,
        )

    assert missing.status_code == 400
    assert missing.json()["detail"] == "project_id is required"
    assert wrong.status_code == 404
    assert correct.status_code == 200
    assert correct.json()["project_id"] == project_a

    assert wrong_update.status_code == 404
    assert correct_update.status_code == 200

    assert delete_missing.status_code == 400
    assert delete_wrong.status_code == 404
    assert delete_correct.status_code == 204

    assert global_unscoped.status_code == 200
    assert global_unscoped.json()["project_id"] == ""
    assert global_project_scoped.status_code == 404
