"""One causal positive proof of Istara's complete Research Spine."""

import json
import re
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_source_to_three_model_reliability_human_done_and_report(monkeypatch):
    """No stage may be replaced by a manually pre-accepted downstream fixture."""
    from app.api.routes.tasks import _approve_task
    from app.core.agent import AgentOrchestrator
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
        CodingRun,
        ReconciliationDecision,
        ResearchEvidenceEdge,
    )
    from app.models.task import Task, TaskStatus
    from app.services import research_validity_service
    from app.skills.base import SkillOutput

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-spine-e2e-{suffix}"
    task_id = f"task-spine-e2e-{suffix}"
    document_ids = [f"doc-spine-e2e-{suffix}-{index}" for index in range(1, 4)]
    unit_ids = [
        f"eu-invite-{suffix}",
        f"eu-permission-{suffix}",
        f"eu-navigation-{suffix}",
    ]
    quotes = {
        unit_ids[0]: "The participant could not find the invitation control.",
        unit_ids[1]: "The participant could not understand workspace permissions.",
        unit_ids[2]: "The participant could not tell where to return to the workspace.",
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

    class DeterministicThreeCoderDispatcher:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def structured(self, **kwargs):  # noqa: ANN001
            purpose = kwargs.get("purpose")
            if purpose == "report.mece":
                return SimpleNamespace(status="success", value={"categories": []})
            model = kwargs["params"].model
            self.calls.append(model)
            evidence_units_match = re.search(
                r"<evidence_units>\s*(\[.*?\])\s*</evidence_units>",
                kwargs["messages"][-1]["content"],
                re.DOTALL,
            )
            assert evidence_units_match, "protected coding prompt must carry source evidence units"
            prompt_units = json.loads(evidence_units_match.group(1))
            applications = [
                {
                    "evidence_unit_id": item["id"],
                    "stable_id": item["stable_id"],
                    "unit_index": item["unit_index"],
                    "codes": [
                        "invite_discovery" if item_index == 0 else "permission_clarity"
                    ],
                    "primary_code": (
                        "invite_discovery" if item_index == 0 else "permission_clarity"
                    ),
                    "quote": item["source_text"],
                    "confidence": 0.95,
                    "rationale": "The code is grounded in the exact participant span.",
                }
                for item_index, item in enumerate(prompt_units)
            ]
            return SimpleNamespace(
                value={"applications": applications},
                # The fake provider reports the endpoint actually pinned by
                # the coder, preserving the same route-evidence invariant as
                # the real Pi worker.
                endpoint_id=f"endpoint-{model.rsplit('-', 1)[-1]}",
                # Deterministic tests must provide the same explicit
                # provider-served identity required by the live coder
                # path; the configured request label is not proof.
                served_model=model,
            )

        async def completion(self, **kwargs):  # noqa: ANN001
            return SimpleNamespace(
                text="SITUATION: participant friction.\nCOMPLICATION: controls are unclear.\nRESOLUTION: clarify them."
            )

    dispatcher = DeterministicThreeCoderDispatcher()
    coder_nodes = [CoderNode(index) for index in range(1, 4)]

    async def select_pi_coders(max_coders: int, *, project_id: str | None = None):
        assert max_coders == 3
        assert project_id == project_id_outer
        return [
            research_validity_service.CoderSpec(
                node=node,
                coder_id=f"model-coder:{node.loaded_models[0]}",
                model_name=node.loaded_models[0],
            )
            for node in coder_nodes
        ]

    project_id_outer = project_id
    monkeypatch.setattr(research_validity_service, "_select_pi_coders", select_pi_coders)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)

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
        documents = [
            Document(
                id=document_id,
                project_id=project_id,
                title=f"Participant interview {index}",
                status=DocumentStatus.READY,
                version=1,
                content_text=quotes[unit_id],
            )
            for index, (document_id, unit_id) in enumerate(zip(document_ids, unit_ids), start=1)
        ]
        db.add_all([project, task, *documents])
        output = SkillOutput(
            success=True,
            summary="Source-grounded participant evidence",
            nuggets=[
                {
                    "text": quotes[unit_id],
                    "source": "interview",
                    "source_document_id": document_ids[index],
                    "source_location": (
                        f"document:{document_ids[index]}:chars:0-{len(quotes[unit_id])}"
                    ),
                    "source_text": quotes[unit_id],
                }
                for index, unit_id in enumerate(unit_ids)
            ],
            facts=[{"text": "Participants cannot discover collaboration controls."}],
            insights=[{"text": "Collaboration onboarding lacks clear affordances."}],
            recommendations=[{"text": "Clarify invitation and permission controls."}],
        )
        orchestrator = AgentOrchestrator()
        await orchestrator._store_findings(db, project_id, output, task)
        await db.refresh(task)
        coding_run_id = json.loads(task.validation_result)["research_validity"]["coding_run_id"]
        coding_run_row = await db.get(CodingRun, coding_run_id)
        assert coding_run_row is not None
        coding_run = coding_run_row.to_dict()
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
        assert len(applications) == 9
        assert len(coders) == 3
        generated_units = (
            (
                await db.execute(
                    select(EvidenceUnit).where(
                        EvidenceUnit.project_id == project_id,
                        EvidenceUnit.task_id == task_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(generated_units) == 3
        assert all(unit.unit_type == "source_span" for unit in generated_units)
        assert {unit.source_document_id for unit in generated_units} == set(document_ids)
        assert {unit.source_text for unit in generated_units} == set(quotes.values())
        generated_unit_ids = {unit.id for unit in generated_units}
        assert {row.evidence_unit_id for row in applications} == generated_unit_ids
        assert {row.model_name for row in coders} == {"model-1", "model-2", "model-3"}

        nuggets = (
            (
                await db.execute(
                    select(Nugget).where(
                        Nugget.project_id == project_id,
                        Nugget.task_id == task_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        facts = (
            (
                await db.execute(
                    select(Fact).where(
                        Fact.project_id == project_id,
                        Fact.task_id == task_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        insights = (
            (
                await db.execute(
                    select(Insight).where(
                        Insight.project_id == project_id,
                        Insight.task_id == task_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        recommendations = (
            (
                await db.execute(
                    select(Recommendation).where(
                        Recommendation.project_id == project_id,
                        Recommendation.task_id == task_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(nuggets) == 3
        assert len(facts) == len(insights) == len(recommendations) == 1
        nugget_by_text = {nugget.text: nugget for nugget in nuggets}
        ordered_nugget_ids = [nugget_by_text[quotes[unit_id]].id for unit_id in unit_ids]
        fact_id = facts[0].id
        insight_id = insights[0].id
        recommendation_id = recommendations[0].id
        assert json.loads(facts[0].nugget_ids) == ordered_nugget_ids
        assert json.loads(insights[0].fact_ids) == [fact_id]
        assert json.loads(recommendations[0].insight_ids) == [insight_id]
        evidence_edges = (
            (
                await db.execute(
                    select(ResearchEvidenceEdge).where(
                        ResearchEvidenceEdge.project_id == project_id,
                        ResearchEvidenceEdge.task_id == task_id,
                        ResearchEvidenceEdge.source_type == "nugget",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(evidence_edges) == 3
        assert {edge.target_id for edge in evidence_edges} == generated_unit_ids

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
        partial_gate = await research_validity_service.assess_task_research_validity(
            db,
            project_id=project_id,
            task_id=task_id,
        )
        assert partial_gate["report_allowed"] is False
        assert partial_gate["unresolved_code_application_count"] == 8

        # A passing three-model reliability score does not reconcile the
        # remaining applications. Every application must receive its own
        # durable human decision before the task can become Done/reportable.
        for application in applications[1:]:
            decision = await research_validity_service.create_reconciliation_decision(
                db,
                project_id=project_id,
                code_application_id=application.id,
                decision_type="accepted",
                decided_by="human-researcher",
                rationale="The exact source span supports this accepted code.",
                source="human_review",
            )
            assert decision["source"] == "human_review"

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
        assert routed == 6
        report = (
            await db.execute(
                select(ProjectReport).where(ProjectReport.project_id == project_id)
            )
        ).scalar_one()
        report_finding_ids = set(json.loads(report.finding_ids_json))
        assert report_finding_ids == {
            *ordered_nugget_ids,
            fact_id,
            insight_id,
            recommendation_id,
        }

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
    assert len(decisions) == 9
    assert {decision.decided_by for decision in decisions} == {"human-researcher"}
