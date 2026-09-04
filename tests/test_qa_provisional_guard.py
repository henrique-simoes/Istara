"""Synthetic-QA provisional promotion guard tests (backend).

Enforces master plan §6.4/§9: evidence units stamped ``is_qa_provisional``
(the QA seeder's real-ingestion marker) can NEVER be promoted — a coding run
over them fails closed to ``blocked`` regardless of reliability scores.
"""

from __future__ import annotations

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import create_token
from app.main import app
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.research_validity import EvidenceUnit
from app.services import research_validity_service


@pytest.fixture(autouse=True)
def reset_settings():
    from app.config import settings

    original_team_mode = settings.team_mode
    original_jwt_secret = settings.jwt_secret
    yield
    settings.team_mode = original_team_mode
    settings.jwt_secret = original_jwt_secret


@pytest.fixture
def auth_headers():
    from app.config import settings

    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    token = create_token("user1", "testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_coding_run_fails_closed_on_provisional_qa_units():
    await init_db()
    project_id = f"qa-provisional-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="QA Provisional Project"))
        await db.commit()

    unit_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            EvidenceUnit(
                id=unit_id,
                project_id=project_id,
                source_id="document:qa-synthetic-doc:v1",
                stable_id="document:qa-synthetic-doc:v1#EU-0001",
                unit_index=1,
                source_text="Synthetic QA source span that must stay provisional.",
                source_location="qa-synthetic-doc:1",
                metadata_json=json.dumps(
                    {
                        "is_qa_provisional": True,
                        "source_kind": "synthetic_qa",
                        "promotion_blocked": True,
                        "qa_run_boundary": "synthetic_qa_provisional",
                    }
                ),
            )
        )
        await db.commit()
        result = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            evidence_unit_ids=[unit_id],
            created_by="qa-fixer",
        )

    assert result["status"] == "blocked"
    assert result["promotion_status"] == "blocked"
    assert "provisional" in result["fallback_reason"]
    # No coder was selected and no code application was persisted.
    assert result["rater_count"] == 0


@pytest.mark.asyncio
async def test_normal_units_are_not_affected_by_guard():
    await init_db()
    project_id = f"qa-normal-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="QA Normal Project"))
        await db.commit()

    unit_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(
            EvidenceUnit(
                id=unit_id,
                project_id=project_id,
                source_id="interview-01",
                stable_id="interview-01#EU-0001",
                unit_index=1,
                source_text="A real source span.",
                source_location="interview-01:1",
                metadata_json="{}",
            )
        )
        await db.commit()
        result = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            evidence_unit_ids=[unit_id],
            created_by="qa-fixer",
        )

    # Without the provisional marker the guard must not fire; with no healthy
    # coders in the test env the run is blocked for lack of coders, never for
    # the provisional boundary.
    assert "provisional" not in result["fallback_reason"]


@pytest.mark.asyncio
async def test_documents_api_stamps_qa_provisional_metadata(auth_headers):
    """The seeder's real ingestion path must stamp provisional metadata.

    POST /api/documents with ``qa_provisional=true`` (exactly what the QA
    seeder sends) must persist EvidenceUnit rows carrying
    ``is_qa_provisional``/``promotion_blocked`` in metadata — the durable
    provenance boundary that keeps synthetic rows non-reportable.
    """
    await init_db()
    project_id = f"qa-stamp-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="QA Stamp Project"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/documents",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "title": "synthetic-coding-001",
                "file_name": "synthetic-coding-001.txt",
                "file_type": "txt",
                "content_text": "Synthetic coding task: ambiguous acceptance criteria.",
                "qa_provisional": True,
                "source_kind": "synthetic_qa",
            },
        )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    async with async_session() as db:
        units = (
            (
                await db.execute(
                    select(EvidenceUnit).where(
                        EvidenceUnit.source_document_id == doc_id
                    )
                )
            )
            .scalars()
            .all()
        )
    assert units
    for unit in units:
        metadata = json.loads(unit.metadata_json or "{}")
        assert metadata["is_qa_provisional"] is True
        assert metadata["source_kind"] == "synthetic_qa"
        assert metadata["promotion_blocked"] is True

    # And a normal document (no flag) stays unmarked.
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/documents",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "title": "normal note",
                "file_name": "normal.txt",
                "file_type": "txt",
                "content_text": "A normal project note.",
            },
        )
    assert response.status_code == 201
    normal_doc_id = response.json()["id"]
    async with async_session() as db:
        units = (
            (
                await db.execute(
                    select(EvidenceUnit).where(
                        EvidenceUnit.source_document_id == normal_doc_id
                    )
                )
            )
            .scalars()
            .all()
        )
    assert units
    for unit in units:
        metadata = json.loads(unit.metadata_json or "{}")
        assert not metadata.get("is_qa_provisional", False)
