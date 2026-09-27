"""Research operations around deployments and surveys (professional-readiness Phase 1).

Consent default for new deployments, raw-data CSV export, and idempotent survey re-sync.
"""

from __future__ import annotations

import app.core.agentic  # noqa: F401  (import-order guard, see tests/test_deployments.py)

import csv
import io
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.channels.base import IncomingMessage
from app.main import app
from app.models.channel_instance import ChannelInstance
from app.models.database import async_session, init_db
from app.models.finding import Nugget
from app.models.project import Project
from app.models.research_validity import EvidenceUnit
from app.models.survey_integration import SurveyIntegration, SurveyLink
from app.services.inbound_processor import process_inbound_channel_message


async def _project_and_channel() -> tuple[str, str]:
    await init_db()
    project_id = str(uuid.uuid4())
    instance_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name=f"Ops {project_id[:8]}"))
        db.add(
            ChannelInstance(
                id=instance_id,
                platform="slack",
                name="Ops Slack",
                config_json="{}",
                project_id=project_id,
                is_active=True,
            )
        )
        await db.commit()
    return project_id, instance_id


@pytest.mark.asyncio
async def test_new_deployments_ask_for_consent_by_default(admin_auth_headers):
    project_id, instance_id = await _project_and_channel()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={
                "project_id": project_id,
                "name": "Default consent",
                "questions": [{"text": "Q1?"}],
                "channel_instance_ids": [instance_id],
            },
        )
        explicit_off = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={
                "project_id": project_id,
                "name": "No consent step",
                "questions": [{"text": "Q1?"}],
                "channel_instance_ids": [instance_id],
                "config": {"consent_required": False},
            },
        )
    assert created.status_code == 201, created.text
    assert created.json()["config"]["consent_required"] is True
    assert created.json()["config"]["consent_message"]
    assert explicit_off.status_code == 201
    assert explicit_off.json()["config"]["consent_required"] is False


@pytest.mark.asyncio
async def test_raw_data_export_is_a_pseudonymous_csv(admin_auth_headers):
    project_id, instance_id = await _project_and_channel()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={
                "project_id": project_id,
                "name": "Export study",
                "questions": [{"text": "What slows you down?"}, {"text": "What do you like?"}],
                "channel_instance_ids": [instance_id],
                "config": {
                    "consent_required": True,
                    "screener": [{"text": "Weekly exporter?", "accept": ["yes"]}],
                },
            },
        )
        deployment_id = created.json()["id"]
        activated = await ac.post(
            f"/api/deployments/{deployment_id}/activate?project_id={project_id}",
            headers=admin_auth_headers,
        )
        assert activated.status_code == 200

        async def say(sender: str, text: str):
            await process_inbound_channel_message(
                IncomingMessage(
                    channel="slack",
                    channel_id=f"D-{sender}",
                    sender_id=sender,
                    sender_name=f"Real Name {sender}",
                    text=text,
                    instance_id=instance_id,
                )
            )

        for text in ["hi", "yes", "yes", "Exports are slow", "Search"]:
            await say("U1", text)
        for text in ["hi", "no"]:
            await say("U2", text)

        exported = await ac.get(
            f"/api/deployments/{deployment_id}/export.csv?project_id={project_id}",
            headers=admin_auth_headers,
        )

    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    assert "attachment" in exported.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert "Real Name" not in exported.text and "U1" not in exported.text
    answers = [r for r in rows if r["answer"]]
    assert [(r["participant"], r["question"], r["answer"]) for r in answers] == [
        ("P01", "What slows you down?", "Exports are slow"),
        ("P01", "What do you like?", "Search"),
    ]
    assert {r["participant"]: r["consent"] for r in rows} == {"P01": "given", "P02": "declined"}
    assert answers[0]["screener"] == "Weekly exporter?=yes"
    assert answers[0]["evidence_unit_id"]


@pytest.mark.asyncio
async def test_viewer_cannot_export_raw_participant_data(admin_auth_headers):
    from app.config import settings
    from app.core.auth import create_token

    project_id, instance_id = await _project_and_channel()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={"project_id": project_id, "name": "Private", "questions": [{"text": "Q?"}],
                  "channel_instance_ids": [instance_id]},
        )
        original = settings.team_mode
        settings.team_mode = True
        try:
            viewer = create_token("viewer-u", "viewer-u", "viewer", mfa_verified=True)
            denied = await ac.get(
                f"/api/deployments/{created.json()['id']}/export.csv?project_id={project_id}",
                headers={"Authorization": f"Bearer {viewer}"},
            )
        finally:
            settings.team_mode = original
    assert denied.status_code in {403, 404}


async def _survey_link(project_id: str) -> SurveyLink:
    integration = SurveyIntegration(
        id=str(uuid.uuid4()),
        platform="typeform",
        name="Typeform",
        config_json="{}",
        project_id=project_id,
    )
    link = SurveyLink(
        id=str(uuid.uuid4()),
        integration_id=integration.id,
        project_id=project_id,
        external_survey_id="form-1",
        external_survey_name="Onboarding survey",
    )
    async with async_session() as db:
        db.add(integration)
        db.add(link)
        await db.commit()
    return link


@pytest.mark.asyncio
async def test_survey_resync_does_not_duplicate_responses():
    from app.services.survey_ingestion import ingest_responses

    await init_db()
    project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Survey dedupe"))
        await db.commit()
    link = await _survey_link(project_id)
    responses = [
        {"id": "r1", "answers": [{"question": "Why?", "answer": "Speed"},
                                 {"question": "Else?", "answer": "No"}]},
        {"id": "r2", "answers": [{"question": "Why?", "answer": "Speed"}]},
    ]
    results = []
    for _ in range(3):
        async with async_session() as db:
            fresh = await db.get(SurveyLink, link.id)
            results.append(await ingest_responses(db, fresh, responses, project_id))
        responses = responses + [{"id": "r3", "answers": [{"question": "Why?", "answer": "Price"}]}]

    async with async_session() as db:
        nugget_count = await db.scalar(
            select(func.count()).select_from(Nugget).where(Nugget.project_id == project_id)
        )
        unit_count = await db.scalar(
            select(func.count()).select_from(EvidenceUnit).where(
                EvidenceUnit.project_id == project_id
            )
        )
        refreshed = await db.get(SurveyLink, link.id)
    assert [r["nuggets_created"] for r in results] == [3, 1, 0]
    assert nugget_count == 4 and unit_count == 4
    assert refreshed.response_count == 3


@pytest.mark.asyncio
async def test_responses_without_ids_are_never_merged():
    from app.services.survey_ingestion import ingest_responses

    await init_db()
    project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Survey anonymous"))
        await db.commit()
    link = await _survey_link(project_id)
    anonymous = [{"answers": [{"question": "Why?", "answer": "Yes"}]}] * 2
    async with async_session() as db:
        fresh = await db.get(SurveyLink, link.id)
        result = await ingest_responses(db, fresh, anonymous, project_id)
    assert result["nuggets_created"] == 2


@pytest.mark.asyncio
async def test_survey_link_raw_export(admin_auth_headers):
    from app.services.survey_ingestion import ingest_responses

    await init_db()
    project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Survey export"))
        await db.commit()
    link = await _survey_link(project_id)
    async with async_session() as db:
        fresh = await db.get(SurveyLink, link.id)
        await ingest_responses(
            db,
            fresh,
            [{"id": "r1", "answers": [{"question": "Why?", "answer": "Speed, mostly"}]}],
            project_id,
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        exported = await ac.get(
            f"/api/surveys/links/{link.id}/export.csv?project_id={project_id}",
            headers=admin_auth_headers,
        )
    assert exported.status_code == 200, exported.text
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert [(r["response_id"], r["question"], r["answer"]) for r in rows] == [
        ("r1", "Why?", "Speed, mostly")
    ]
    assert json.loads(json.dumps(rows))[0]["evidence_unit_id"]


@pytest.mark.asyncio
async def test_coders_see_the_question_as_context_not_as_a_unit():
    from app.services.research_validity_evidence_units import _coding_unit_payload
    from app.services.survey_ingestion import ingest_responses

    await init_db()
    project_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name="Survey context"))
        await db.commit()
    link = await _survey_link(project_id)
    async with async_session() as db:
        fresh = await db.get(SurveyLink, link.id)
        await ingest_responses(
            db, fresh, [{"id": "r9", "answers": [{"question": "Why switch?", "answer": "Price"}]}],
            project_id,
        )
        units = (
            (await db.execute(select(EvidenceUnit).where(EvidenceUnit.project_id == project_id)))
            .scalars()
            .all()
        )
    assert [u.source_text for u in units] == ["Price"]
    payload = _coding_unit_payload(units[0])
    assert payload["asked"] == "Why switch?"
    assert payload["source_text"] == "Price"


@pytest.mark.asyncio
async def test_overview_counts_conversations_finishers_and_answers(admin_auth_headers):
    project_id, instance_id = await _project_and_channel()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await ac.post(
            "/api/deployments",
            headers=admin_auth_headers,
            json={
                "project_id": project_id,
                "name": "Counted",
                "questions": [{"text": "Only question?"}],
                "channel_instance_ids": [instance_id],
                "config": {"consent_required": False},
            },
        )
        await ac.post(
            f"/api/deployments/{created.json()['id']}/activate?project_id={project_id}",
            headers=admin_auth_headers,
        )
        for sender, texts in {"A": ["hi", "answer A"], "B": ["hi"]}.items():
            for text in texts:
                await process_inbound_channel_message(
                    IncomingMessage(channel="slack", channel_id=f"D-{sender}", sender_id=sender,
                                    sender_name=sender, text=text, instance_id=instance_id)
                )
        overview = await ac.get(
            f"/api/deployments/overview?project_id={project_id}", headers=admin_auth_headers
        )
    assert overview.status_code == 200
    body = overview.json()
    assert (body["conversations_started"], body["participants_finished"], body["answers_stored"]) == (
        2,
        1,
        1,
    )


def test_consent_status_names_participants_who_were_never_asked():
    from app.services.deployment_service import _consent_status

    required = {"consent_required": True}
    assert _consent_status({"consent": {"given": True}}, required) == "given"
    assert _consent_status({"consent": {"given": False}}, required) == "declined"
    assert _consent_status({"state": "consent"}, required) == "pending"
    assert _consent_status({"state": "closed_quota"}, required) == "not_asked"
    assert _consent_status({}, {"consent_required": False}) == "not_asked"
