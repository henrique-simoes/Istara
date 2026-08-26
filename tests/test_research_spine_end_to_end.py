"""One causal positive proof of Istara's complete Research Spine."""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_source_to_three_model_reliability_human_done_and_report(monkeypatch):
    """No stage may be replaced by a manually pre-accepted downstream fixture."""
    from app.api.routes.tasks import _approve_task
    from app.core.report_manager import ReportManager
    from app.models.code_application import CodeApplication
    from app.models.database import async_session, init_db
    from app.models.document import Document, DocumentStatus
    from app.models.finding import Fact, Insight, Nugget, Recommendation
    from app.models.project import Project
    from app.models.project_report import ProjectReport
    from app.models.research_validity import (
        CodingRunCoder,
        EvidenceUnit,
        ReconciliationDecision,
        ResearchEvidenceEdge,
    )
    from app.models.task import Task, TaskStatus
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-spine-e2e-{suffix}"
    task_id = f"task-spine-e2e-{suffix}"
    document_id = f"doc-spine-e2e-{suffix}"
    unit_ids = [f"eu-invite-{suffix}", f"eu-permission-{suffix}"]
    quotes = {
        unit_ids[0]: "The participant could not find the invitation control.",
        unit_ids[1]: "The participant could not understand workspace permissions.",
    }

    class CoderNode:
        def __init__(self, index: int) -> None:
            self.node_id = f"node-{index}"
            self.name = self.node_id
            self.source = "test"
            self.provider_type = "test"
            self.endpoint_id = f"endpoint-{index}"
            self.provider_account_handle = f"account-{index}"
            self.is_healthy = True
            self.loaded_models = [f"model-{index}"]
            self.model_capabilities = {}

    class Router:
        nodes = [CoderNode(index) for index in range(1, 4)]

        def _sorted_servers(self, **kwargs):  # noqa: ANN001
            assert kwargs["project_id"] == project_id
            return self.nodes

    class DeterministicThreeCoderDispatcher:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def structured(self, **kwargs):  # noqa: ANN001
            model = kwargs["params"].model
            self.calls.append(model)
            applications = [
                {
                    "evidence_unit_id": unit_id,
                    "codes": ["invite_discovery" if unit_id == unit_ids[0] else "permission_clarity"],
                    "primary_code": (
                        "invite_discovery" if unit_id == unit_ids[0] else "permission_clarity"
                    ),
                    "quote": quotes[unit_id],
                    "confidence": 0.95,
                    "rationale": "The code is grounded in the exact participant span.",
                }
                for unit_id in unit_ids
            ]
            return SimpleNamespace(
                value={"applications": applications},
                endpoint_id=f"endpoint-{model}",
            )

    dispatcher = DeterministicThreeCoderDispatcher()
    monkeypatch.setattr(research_validity_service, "llm_router", Router())
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)
    monkeypatch.setattr(
        research_validity_service,
        "_use_pi_coding_plane",
        AsyncMock(return_value=False),
    )

    await init_db()
    async with async_session() as db:
        project = Project(id=project_id, name="Continuous Research Spine proof")
        task = Task(
            id=task_id,
            project_id=project_id,
            title="Synthesize participant evidence",
            skill_name="user-interviews",
            status=TaskStatus.IN_REVIEW,
            review_state="awaiting_review",
        )
        document = Document(
            id=document_id,
            project_id=project_id,
            title="Participant interview",
            status=DocumentStatus.READY,
            version=1,
            content_text="\n".join(quotes.values()),
        )
        db.add_all([project, task, document])
        for index, unit_id in enumerate(unit_ids):
            db.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id=project_id,
                    task_id=task_id,
                    source_document_id=document_id,
                    source_id=f"document:{document_id}:v1",
                    stable_id=f"document:{document_id}:v1:{index}",
                    unit_index=index,
                    unit_type="source_span",
                    source_type="user_upload",
                    source_text=quotes[unit_id],
                    metadata_json=json.dumps(
                        {"document_id": document_id, "document_version": 1}
                    ),
                )
            )
        await db.commit()

        coding_run = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            task_id=task_id,
            evidence_unit_ids=unit_ids,
            max_coders=3,
            created_by="researcher-a",
        )
        assert coding_run["promotion_status"] == "accepted"
        assert coding_run["reliability_method"] == (
            "fleiss_kappa_with_krippendorff_alpha_companion"
        )
        assert coding_run["kappa"] == pytest.approx(1.0)
        assert coding_run["alpha"] == pytest.approx(1.0)
        assert coding_run["distinct_model_count"] == 3
        assert dispatcher.calls == ["model-1", "model-2", "model-3"]

        applications = (
            (
                await db.execute(
                    select(CodeApplication).where(
                        CodeApplication.coding_run_id == coding_run["id"]
                    )
                )
            )
            .scalars()
            .all()
        )
        coders = (
            (
                await db.execute(
                    select(CodingRunCoder).where(
                        CodingRunCoder.coding_run_id == coding_run["id"]
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(applications) == 6
        assert len(coders) == 3
        assert {row.evidence_unit_id for row in applications} == set(unit_ids)
        assert {row.model_name for row in coders} == {"model-1", "model-2", "model-3"}

        human_acceptance = await research_validity_service.create_reconciliation_decision(
            db,
            project_id=project_id,
            code_application_id=applications[0].id,
            decision_type="accepted",
            decided_by="human-researcher",
            rationale="The exact source span supports this accepted code.",
            source="human_review",
        )
        assert human_acceptance["source"] == "human_review"

        nugget_id = f"nugget-spine-e2e-{suffix}"
        fact_id = f"fact-spine-e2e-{suffix}"
        insight_id = f"insight-spine-e2e-{suffix}"
        recommendation_id = f"recommendation-spine-e2e-{suffix}"
        db.add_all(
            [
                Nugget(
                    id=nugget_id,
                    project_id=project_id,
                    task_id=task_id,
                    text=quotes[unit_ids[0]],
                    source="interview",
                ),
                Fact(
                    id=fact_id,
                    project_id=project_id,
                    task_id=task_id,
                    text="Participants cannot discover collaboration controls.",
                    nugget_ids=json.dumps([nugget_id]),
                ),
                Insight(
                    id=insight_id,
                    project_id=project_id,
                    task_id=task_id,
                    text="Collaboration onboarding lacks clear affordances.",
                    fact_ids=json.dumps([fact_id]),
                ),
                Recommendation(
                    id=recommendation_id,
                    project_id=project_id,
                    task_id=task_id,
                    text="Clarify invitation and permission controls.",
                    insight_ids=json.dumps([insight_id]),
                ),
                ResearchEvidenceEdge(
                    id=f"edge-spine-e2e-{suffix}",
                    project_id=project_id,
                    source_type="nugget",
                    source_id=nugget_id,
                    relation="grounded_in",
                    target_type="evidence_unit",
                    target_id=unit_ids[0],
                    evidence_unit_id=unit_ids[0],
                    coding_run_id=coding_run["id"],
                    task_id=task_id,
                    reliability_status="accepted",
                ),
            ]
        )
        await db.commit()

        manager = ReportManager()
        blocked_before_human_done = await manager.route_approved_task_findings(
            project_id,
            task_id,
            task.skill_name,
            db,
        )
        assert blocked_before_human_done == 0
        assert (
            await db.execute(
                select(ProjectReport).where(ProjectReport.project_id == project_id)
            )
        ).scalars().all() == []

        review_event = await _approve_task(
            db,
            task,
            reviewed_by="human-researcher",
            note="Atomic chain and exact source evidence reviewed.",
        )
        # The public approval route commits before starting telemetry/report
        # side effects; preserve that transaction boundary so SQLite cannot
        # deadlock a second session on the pending review write.
        await db.commit()
        await db.refresh(task)
        assert review_event.outcome == "approved"
        assert task.status == TaskStatus.DONE
        assert task.review_state == "approved"

        routed = await manager.route_approved_task_findings(
            project_id,
            task_id,
            task.skill_name,
            db,
        )
        assert routed == 4
        report = (
            await db.execute(
                select(ProjectReport).where(ProjectReport.project_id == project_id)
            )
        ).scalar_one()
        assert json.loads(report.finding_ids_json) == [
            nugget_id,
            fact_id,
            insight_id,
            recommendation_id,
        ]

        trace = await research_validity_service.build_evidence_graph_traceability(
            db,
            project_id=project_id,
            report_id=report.id,
        )
        decisions = (
            (
                await db.execute(
                    select(ReconciliationDecision).where(
                        ReconciliationDecision.project_id == project_id
                    )
                )
            )
            .scalars()
            .all()
        )

    assert trace["summary"]["blocked_report_count"] == 0
    assert trace["report_dependencies"][0]["report_allowed_by_research_validity"] is True
    assert trace["report_dependencies"][0]["task_ids"] == [task_id]
    assert len(decisions) == 1
    assert decisions[0].decided_by == "human-researcher"
