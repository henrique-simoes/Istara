"""Project isolation tests for context hierarchy composition."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.context_hierarchy import ContextDocument, PLATFORM_CONTEXT, context_hierarchy


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
async def test_project_list_excludes_global_and_other_project_contexts(context_db: AsyncSession):
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

    composed = await context_hierarchy.compose_context(context_db, project_id="project-a")

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
