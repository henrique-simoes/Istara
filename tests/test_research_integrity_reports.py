"""Tests for Istara Research Integrity System.

Covers: CodebookVersion, CodeApplication, ProjectReport models,
        Cohen's Kappa, Krippendorff's Alpha calculations,
        ValidationExecutor, ReportManager.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------- Backend path setup ----------
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.database import Base
from app.models.codebook_version import CodebookVersion
from app.models.code_application import CodeApplication
from app.models.project_report import ProjectReport
from app.models.research_validity import EvidenceUnit, ResearchEvidenceEdge
from app.models.task import Task, TaskStatus
from app.core.agent import AgentOrchestrator
from app.skills.intercoder import cohen_kappa, krippendorff_alpha
from app.skills.base import SkillOutput
from app.core.validation_executor import ValidationExecutor, ValidationResult
from app.core.report_manager import ReportManager, SCOPE_MAP, SYNTHESIS_SKILLS

# Ensure ALL models are registered with Base (mirrors database.init_db imports)
from app.models import agent, codebook, document, finding, message, project, session, task  # noqa: F401
from app.models import research_validity  # noqa: F401
from app.models import user  # noqa: F401
from app.models import llm_server, method_metric  # noqa: F401
from app.core.checkpoint import TaskCheckpoint  # noqa: F401
from app.core.context_hierarchy import ContextDocument  # noqa: F401
from app.core.scheduler import ScheduledTask  # noqa: F401
from app.models.context_dag import ContextDAGNode  # noqa: F401
from app.models.design_screen import DesignScreen, DesignBrief, DesignDecision  # noqa: F401
from app.models.loop_execution import LoopExecution  # noqa: F401
from app.models.agent_loop_config import AgentLoopConfig  # noqa: F401
from app.models.notification import Notification, NotificationPreference  # noqa: F401
from app.models.backup import BackupRecord  # noqa: F401
from app.models.channel_instance import ChannelInstance  # noqa: F401
from app.models.channel_message import ChannelMessage  # noqa: F401
from app.models.channel_conversation import ChannelConversation  # noqa: F401
from app.models.research_deployment import ResearchDeployment  # noqa: F401
from app.models.survey_integration import SurveyIntegration, SurveyLink  # noqa: F401
from app.models.mcp_server_config import MCPServerConfig  # noqa: F401
from app.models.mcp_access_policy import MCPAccessPolicy  # noqa: F401
from app.models.mcp_audit_log import MCPAuditEntry  # noqa: F401
from app.models.model_skill_stats import ModelSkillStats  # noqa: F401
from app.models.autoresearch_experiment import AutoresearchExperiment  # noqa: F401


# ============================================================
# Fixtures: in-memory async SQLite for model tests
# ============================================================

@pytest.fixture
async def db_session():
    """Create an in-memory async SQLite session for model tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def add_reportable_nugget_fixture(
    db_session,
    *,
    project_id: str,
    finding_id: str,
    task_id: str,
    skill_name: str = "user-interviews",
) -> None:
    evidence_unit_id = f"eu-{finding_id}"
    db_session.add(
        Task(
            id=task_id,
            project_id=project_id,
            title=f"Approved task for {finding_id}",
            skill_name=skill_name,
            status=TaskStatus.DONE,
            review_state="approved",
        )
    )
    db_session.add(
        finding.Nugget(
            id=finding_id,
            project_id=project_id,
            task_id=task_id,
            text=f"Accepted evidence for {finding_id}",
            source="canonical-corpus",
        )
    )
    db_session.add(
        EvidenceUnit(
            id=evidence_unit_id,
            project_id=project_id,
            task_id=task_id,
            source_id=f"task:{task_id}:nugget:{finding_id}",
            stable_id=f"test-unit:{evidence_unit_id}",
            unit_index=0,
            unit_type="source_span",
            source_type="test_fixture",
            method="test",
            phase="discover",
            source_text=f"Accepted evidence for {finding_id}",
        )
    )
    db_session.add(
        ResearchEvidenceEdge(
            id=f"edge-{project_id}-{finding_id}",
            project_id=project_id,
            source_type="nugget",
            source_id=finding_id,
            relation="grounded_in",
            target_type="evidence_unit",
            target_id=evidence_unit_id,
            evidence_unit_id=evidence_unit_id,
            task_id=task_id,
        )
    )
    db_session.add(
        CodeApplication(
            id=f"ca-{project_id}-{finding_id}",
            project_id=project_id,
            task_id=task_id,
            code_id="accepted-research-evidence",
            evidence_unit_id=evidence_unit_id,
            source_text=f"Accepted evidence for {finding_id}",
            promotion_status="accepted",
            reliability_status="accepted",
            reconciliation_status="accepted",
        )
    )


# ============================================================
# 1. CodebookVersion Model Tests
# ============================================================

class TestReportManager:
    """Test the ReportManager progressive document convergence."""

    async def _add_reportable_nugget(
        self,
        db_session,
        *,
        project_id: str,
        finding_id: str,
        task_id: str,
        skill_name: str = "user-interviews",
    ) -> None:
        evidence_unit_id = f"eu-{finding_id}"
        db_session.add(
            Task(
                id=task_id,
                project_id=project_id,
                title=f"Approved task for {finding_id}",
                skill_name=skill_name,
                status=TaskStatus.DONE,
                review_state="approved",
            )
        )
        db_session.add(
            finding.Nugget(
                id=finding_id,
                project_id=project_id,
                task_id=task_id,
                text=f"Accepted evidence for {finding_id}",
                source="canonical-corpus",
            )
        )
        db_session.add(
            EvidenceUnit(
                id=evidence_unit_id,
                project_id=project_id,
                task_id=task_id,
                source_id=f"task:{task_id}:nugget:{finding_id}",
                stable_id=f"test-unit:{evidence_unit_id}",
                unit_index=0,
                unit_type="source_span",
                source_type="test_fixture",
                method="test",
                phase="discover",
                source_text=f"Accepted evidence for {finding_id}",
            )
        )
        db_session.add(
            ResearchEvidenceEdge(
                id=f"edge-{finding_id}",
                project_id=project_id,
                source_type="nugget",
                source_id=finding_id,
                relation="grounded_in",
                target_type="evidence_unit",
                target_id=evidence_unit_id,
                evidence_unit_id=evidence_unit_id,
                task_id=task_id,
            )
        )
        db_session.add(
            CodeApplication(
                id=f"ca-{finding_id}",
                project_id=project_id,
                task_id=task_id,
                code_id="accepted-research-evidence",
                evidence_unit_id=evidence_unit_id,
                source_text=f"Accepted evidence for {finding_id}",
                promotion_status="accepted",
                reliability_status="accepted",
                reconciliation_status="accepted",
            )
        )

    def test_skill_to_scope_mapping(self):
        """Verify SCOPE_MAP maps known skills to correct scopes."""
        assert SCOPE_MAP["user-interviews"] == "Interview Analysis"
        assert SCOPE_MAP["thematic-analysis"] == "Interview Analysis"
        assert SCOPE_MAP["kappa-thematic-analysis"] == "Interview Analysis"
        assert SCOPE_MAP["usability-testing"] == "Usability Study"
        assert SCOPE_MAP["heuristic-evaluation"] == "Usability Study"
        assert SCOPE_MAP["survey-design"] == "Survey Analysis"
        assert SCOPE_MAP["ab-test-analysis"] == "A/B Test Analysis"
        assert SCOPE_MAP["competitive-analysis"] == "Competitive Analysis"
        assert SCOPE_MAP["desk-research"] == "Desk Research"
        assert SCOPE_MAP["card-sorting"] == "Information Architecture"
        assert SCOPE_MAP["research-synthesis"] == "Research Synthesis"
        assert SCOPE_MAP["persona-creation"] == "Research Synthesis"
        assert SCOPE_MAP["journey-mapping"] == "Research Synthesis"

    def test_synthesis_skills_set(self):
        """Verify SYNTHESIS_SKILLS contains the expected skill names."""
        expected = {
            "research-synthesis", "persona-creation", "journey-mapping",
            "affinity-mapping", "empathy-mapping",
        }
        assert SYNTHESIS_SKILLS == expected

    def test_unknown_skill_defaults_to_general_analysis(self):
        """Skills not in SCOPE_MAP default to 'General Analysis'."""
        assert SCOPE_MAP.get("totally-unknown-skill", "General Analysis") == "General Analysis"

    async def test_find_or_create_report_creates_new(self, db_session):
        """_find_or_create_report creates a new report when none exists."""
        manager = ReportManager()
        report = await manager._find_or_create_report(
            "proj-rm-001", "Interview Analysis", 2, db_session
        )

        assert report.project_id == "proj-rm-001"
        assert report.scope == "Interview Analysis"
        assert report.title == "Interview Analysis"
        assert report.layer == 2
        assert report.report_type == "study_analysis"
        assert report.status == "draft"

    async def test_find_or_create_report_reuses_existing(self, db_session):
        """_find_or_create_report returns existing report if scope matches."""
        manager = ReportManager()
        report1 = await manager._find_or_create_report(
            "proj-rm-002", "Usability Study", 2, db_session
        )
        report2 = await manager._find_or_create_report(
            "proj-rm-002", "Usability Study", 2, db_session
        )

        assert report1.id == report2.id

    async def test_route_findings_updates_existing_report(self, db_session):
        """route_findings merges finding_ids into existing report."""
        manager = ReportManager()
        project_id = "proj-rm-003"
        for finding_id in ["f-1", "f-2", "f-3", "f-4"]:
            await self._add_reportable_nugget(
                db_session,
                project_id=project_id,
                finding_id=finding_id,
                task_id=f"task-{finding_id}",
            )
        await db_session.commit()

        # First call creates report and adds findings
        await manager.route_findings(
            project_id, "thematic-analysis", ["f-1", "f-2"], db_session
        )

        # Second call adds more findings to the same report
        await manager.route_findings(
            project_id, "user-interviews", ["f-3", "f-4"], db_session
        )

        # Both skills map to "Interview Analysis" scope
        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.scope == "Interview Analysis",
            )
        )
        report = result.scalar_one()
        finding_ids = json.loads(report.finding_ids_json)

        assert set(finding_ids) == {"f-1", "f-2", "f-3", "f-4"}
        assert report.version >= 2  # updated at least twice
        assert report.status == "in_progress"

    async def test_route_findings_deduplicates(self, db_session):
        """route_findings does not duplicate finding IDs."""
        manager = ReportManager()
        project_id = "proj-rm-004"
        for finding_id in ["f-1", "f-2", "f-3"]:
            await self._add_reportable_nugget(
                db_session,
                project_id=project_id,
                finding_id=finding_id,
                task_id=f"task-{finding_id}",
            )
        await db_session.commit()

        await manager.route_findings(
            project_id, "thematic-analysis", ["f-1", "f-2"], db_session
        )
        await manager.route_findings(
            project_id, "thematic-analysis", ["f-2", "f-3"], db_session
        )

        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.scope == "Interview Analysis",
            )
        )
        report = result.scalar_one()
        finding_ids = json.loads(report.finding_ids_json)
        assert len(finding_ids) == 3  # f-1, f-2, f-3 (no duplicates)

    async def test_route_findings_blocks_taskless_unmanaged_findings(self, db_session):
        """route_findings cannot create reports from IDs outside the Research Spine."""
        manager = ReportManager()

        await manager.route_findings(
            "proj-rm-taskless-block",
            "thematic-analysis",
            ["taskless-or-missing-finding"],
            db_session,
        )

        result = await db_session.execute(
            select(ProjectReport).where(ProjectReport.project_id == "proj-rm-taskless-block")
        )
        assert result.scalars().all() == []

    async def test_task_bound_findings_wait_for_human_approved_done_task(self, db_session):
        """Task-bound findings should not reach reports while the task is still in review."""
        manager = ReportManager()
        task_row = Task(
            id="task-report-gate",
            project_id="proj-report-gate",
            title="Review pending evidence",
            skill_name="user-interviews",
            status=TaskStatus.IN_REVIEW,
            review_state="awaiting_review",
        )
        nugget = finding.Nugget(
            id="nugget-report-gate",
            project_id="proj-report-gate",
            task_id=task_row.id,
            text="Pending review quote",
            source="interview",
        )
        db_session.add_all([task_row, nugget])
        await db_session.commit()

        await manager.route_findings(
            "proj-report-gate",
            "user-interviews",
            [nugget.id],
            db_session,
        )
        result = await db_session.execute(
            select(ProjectReport).where(ProjectReport.project_id == "proj-report-gate")
        )
        assert result.scalars().all() == []

        task_row.status = TaskStatus.DONE
        task_row.review_state = "approved"
        await db_session.commit()

        routed_count = await manager.route_approved_task_findings(
            "proj-report-gate",
            task_row.id,
            "user-interviews",
            db_session,
        )
        assert routed_count == 0

        evidence_unit_id = "eu-report-gate"
        db_session.add(
            EvidenceUnit(
                id=evidence_unit_id,
                project_id="proj-report-gate",
                task_id=task_row.id,
                source_id=f"task:{task_row.id}:nugget:{nugget.id}",
                stable_id="test-unit:eu-report-gate",
                unit_index=0,
                unit_type="source_span",
                source_type="test_fixture",
                method="test",
                phase="discover",
                source_text="Pending review quote",
            )
        )
        db_session.add(
            ResearchEvidenceEdge(
                id="edge-report-gate",
                project_id="proj-report-gate",
                source_type="nugget",
                source_id=nugget.id,
                relation="grounded_in",
                target_type="evidence_unit",
                target_id=evidence_unit_id,
                evidence_unit_id=evidence_unit_id,
                task_id=task_row.id,
            )
        )
        db_session.add(
            CodeApplication(
                id="ca-report-gate",
                project_id="proj-report-gate",
                task_id=task_row.id,
                code_id="pending-review-quote",
                evidence_unit_id=evidence_unit_id,
                source_text="Pending review quote",
                promotion_status="accepted",
                reliability_status="accepted",
                reconciliation_status="accepted",
            )
        )
        await db_session.commit()

        routed_count = await manager.route_approved_task_findings(
            "proj-report-gate",
            task_row.id,
            "user-interviews",
            db_session,
        )
        assert routed_count == 1

        result = await db_session.execute(
            select(ProjectReport).where(ProjectReport.project_id == "proj-report-gate")
        )
        report = result.scalar_one()
        assert json.loads(report.finding_ids_json) == [nugget.id]

    async def test_synthesis_skill_creates_layer_3(self, db_session):
        """Synthesis skills create layer 3 reports."""
        manager = ReportManager()
        await self._add_reportable_nugget(
            db_session,
            project_id="proj-rm-005",
            finding_id="f-synth-1",
            task_id="task-f-synth-1",
            skill_name="research-synthesis",
        )
        await db_session.commit()

        await manager.route_findings(
            "proj-rm-005", "research-synthesis", ["f-synth-1"], db_session
        )

        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == "proj-rm-005",
                ProjectReport.scope == "Research Synthesis",
            )
        )
        report = result.scalar_one()
        assert report.layer == 3
        assert report.report_type == "synthesis"

    async def test_l4_report_uses_derived_finding_count(self, db_session):
        """L4 generation should not depend on a non-persisted finding_count column."""
        manager = ReportManager()
        finding_ids = [f"f-{i}" for i in range(10)]
        for finding_id in finding_ids:
            await add_reportable_nugget_fixture(
                db_session,
                project_id="proj-rm-l4-derived",
                finding_id=finding_id,
                task_id=f"task-{finding_id}",
            )
        l3 = ProjectReport(
            id="report-l3-derived-count",
            project_id="proj-rm-l4-derived",
            title="Research Synthesis",
            layer=3,
            report_type="synthesis",
            scope="Research Synthesis",
            finding_ids_json=json.dumps(finding_ids),
        )
        db_session.add(l3)
        await db_session.commit()
        await db_session.refresh(l3)

        with (
            patch.object(manager, "_generate_executive_summary", new=AsyncMock()),
            patch.object(manager, "_generate_mece_categories", new=AsyncMock()),
            patch.object(manager, "_compose_full_report", new=AsyncMock()),
        ):
            await manager._generate_l4_report("proj-rm-l4-derived", l3, db_session)

        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == "proj-rm-l4-derived",
                ProjectReport.layer == 4,
            )
        )
        l4 = result.scalar_one()
        assert l4.to_dict()["finding_count"] == 10
        assert json.loads(l4.finding_ids_json) == finding_ids

    async def test_get_project_reports(self, db_session):
        """get_project_reports returns reports ordered by layer desc."""
        manager = ReportManager()
        project_id = "proj-rm-006"
        await add_reportable_nugget_fixture(
            db_session,
            project_id=project_id,
            finding_id="f-1",
            task_id="task-f-1",
            skill_name="thematic-analysis",
        )
        await add_reportable_nugget_fixture(
            db_session,
            project_id=project_id,
            finding_id="f-2",
            task_id="task-f-2",
            skill_name="usability-testing",
        )
        await add_reportable_nugget_fixture(
            db_session,
            project_id=project_id,
            finding_id="f-3",
            task_id="task-f-3",
            skill_name="research-synthesis",
        )
        await db_session.commit()

        # Create L2 and L3 reports
        await manager.route_findings(
            project_id, "thematic-analysis", ["f-1"], db_session
        )
        await manager.route_findings(
            project_id, "usability-testing", ["f-2"], db_session
        )
        await manager.route_findings(
            project_id, "research-synthesis", ["f-3"], db_session
        )

        reports = await manager.get_project_reports(project_id, db_session)
        assert len(reports) >= 2
        # First report should be highest layer
        layers = [r["layer"] for r in reports]
        assert layers == sorted(layers, reverse=True)

    async def test_route_findings_preserves_finding_order(self, db_session):
        """Report IDs stay deterministic for stable UI diffs and exports."""
        manager = ReportManager()
        project_id = "proj-rm-order"
        for finding_id in ["f-1", "f-2", "f-3"]:
            await add_reportable_nugget_fixture(
                db_session,
                project_id=project_id,
                finding_id=finding_id,
                task_id=f"task-{finding_id}",
            )
        await db_session.commit()

        await manager.route_findings(
            project_id, "thematic-analysis", ["f-1", "f-2"], db_session
        )
        await manager.route_findings(
            project_id, "thematic-analysis", ["f-2", "f-3"], db_session
        )

        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.scope == "Interview Analysis",
            )
        )
        report = result.scalar_one()
        assert json.loads(report.finding_ids_json) == ["f-1", "f-2", "f-3"]

    async def test_executive_summary_uses_recommendation_text(self, db_session):
        """Reports that contain recommendations should not summarize only lower-level findings."""
        manager = ReportManager()
        rec = finding.Recommendation(
            id="rec-summary",
            project_id="proj-summary-rec",
            text="Replace buried exports with a visible report action.",
        )
        report = ProjectReport(
            id="report-summary-rec",
            project_id="proj-summary-rec",
            title="Recommendation Report",
            scope="Usability Study",
            finding_ids_json=json.dumps(["rec-summary", "missing-1", "missing-2"]),
        )
        db_session.add_all([rec, report])
        await db_session.commit()

        async def fake_chat(messages, temperature=0.3, project_id=None):
            assert "Replace buried exports" in messages[0]["content"]
            assert project_id == "proj-summary-rec"
            return {"message": {"content": "SITUATION\nA summary with recommendations."}}

        with patch("app.core.llm_router.llm_router.chat", new=fake_chat):
            await manager._generate_executive_summary(report, db_session)

        await db_session.refresh(report)
        assert report.executive_summary.startswith("SITUATION")


# ============================================================
# 7. ProjectReport Model Tests
# ============================================================

class TestProjectReportModel:
    """Test the ProjectReport ORM model at each pyramid layer."""

    async def test_create_layer_2_analysis_report(self, db_session):
        """Create a layer 2 (study analysis) report."""
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-001",
            title="Interview Analysis",
            layer=2,
            report_type="study_analysis",
            scope="Interview Analysis",
            status="draft",
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        assert report.layer == 2
        assert report.report_type == "study_analysis"
        assert report.version == 1

    async def test_create_layer_3_synthesis_report(self, db_session):
        """Create a layer 3 (synthesis) report."""
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-002",
            title="Research Synthesis",
            layer=3,
            report_type="synthesis",
            scope="Research Synthesis",
            status="draft",
        )
        db_session.add(report)
        await db_session.commit()

        assert report.layer == 3
        assert report.report_type == "synthesis"

    async def test_create_layer_4_final_report(self, db_session):
        """Create a layer 4 (final deliverable) report."""
        mece_categories = [
            {"name": "Navigation", "findings": ["f-1", "f-2"]},
            {"name": "Performance", "findings": ["f-3"]},
        ]
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-003",
            title="Final Research Report",
            layer=4,
            report_type="final_deliverable",
            scope="Final Report",
            status="draft",
            executive_summary="Research identified 3 key themes across 5 studies.",
            mece_categories_json=json.dumps(mece_categories),
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        assert report.layer == 4
        assert report.executive_summary.startswith("Research identified")
        parsed_mece = json.loads(report.mece_categories_json)
        assert len(parsed_mece) == 2

    async def test_convergence_layer_3_requires_2_plus_layer_2(self, db_session):
        """Layer 3 synthesis is only triggered when 2+ layer 2 reports exist."""
        manager = ReportManager()
        project_id = "proj-pr-conv"
        await add_reportable_nugget_fixture(
            db_session,
            project_id=project_id,
            finding_id="f-1",
            task_id="task-f-1",
            skill_name="thematic-analysis",
        )
        await add_reportable_nugget_fixture(
            db_session,
            project_id=project_id,
            finding_id="f-2",
            task_id="task-f-2",
            skill_name="usability-testing",
        )
        await db_session.commit()

        # Create only one L2 report
        await manager.route_findings(
            project_id, "thematic-analysis", ["f-1"], db_session
        )

        # Check no auto-synthesis created yet
        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == "proj-pr-conv",
                ProjectReport.layer == 3,
            )
        )
        l3_reports = result.scalars().all()
        # There should be no L3 report yet (only 1 L2 exists)
        assert len(l3_reports) == 0

        # Add a second L2 report (different scope)
        await manager.route_findings(
            project_id, "usability-testing", ["f-2"], db_session
        )

        # Now check that L3 synthesis was auto-created
        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == "proj-pr-conv",
                ProjectReport.layer == 3,
            )
        )
        l3_reports = result.scalars().all()
        assert len(l3_reports) >= 1

        # Verify the synthesis report aggregates findings from both L2 reports
        synth = l3_reports[0]
        synth_findings = json.loads(synth.finding_ids_json)
        assert "f-1" in synth_findings
        assert "f-2" in synth_findings

    async def test_synthesis_revalidates_l2_findings_before_layer_3(self, db_session):
        """Layer 3 synthesis must not trust stale L2 report IDs as accepted evidence."""
        manager = ReportManager()
        project_id = "proj-pr-l3-revalidates"
        db_session.add_all(
            [
                ProjectReport(
                    id="report-l2-stale-a",
                    project_id=project_id,
                    title="Stale Interview Analysis",
                    layer=2,
                    report_type="study_analysis",
                    scope="Interview Analysis",
                    finding_ids_json=json.dumps(["legacy-unverified-a"]),
                ),
                ProjectReport(
                    id="report-l2-stale-b",
                    project_id=project_id,
                    title="Stale Usability Analysis",
                    layer=2,
                    report_type="study_analysis",
                    scope="Usability Analysis",
                    finding_ids_json=json.dumps(["legacy-unverified-b"]),
                ),
            ]
        )
        await db_session.commit()

        await manager._check_synthesis_trigger(project_id, db_session)

        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.layer == 3,
            )
        )
        assert result.scalars().all() == []

    async def test_to_dict_finding_count(self, db_session):
        """to_dict() returns correct finding_count from finding_ids_json."""
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-dict",
            title="Test Report",
            finding_ids_json=json.dumps(["f-a", "f-b", "f-c"]),
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        d = report.to_dict()
        assert d["finding_count"] == 3
        assert d["title"] == "Test Report"
        assert d["layer"] == 2  # default
        assert d["status"] == "draft"  # default
        assert d["created_at"] is not None
        assert d["updated_at"] is not None

    async def test_to_dict_invalid_json_fields_do_not_raise(self, db_session):
        """Bad persisted report JSON should degrade to empty UI collections."""
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-bad-json",
            title="Bad JSON Report",
            finding_ids_json="{bad",
            mece_categories_json="{also bad",
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        data = report.to_dict()
        assert data["finding_count"] == 0
        assert data["mece_categories"] == []

    async def test_to_dict_returns_parsed_content_json(self, db_session):
        """Layer 4 reports expose parsed content for report consumers."""
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-content-json",
            title="Final Report",
            layer=4,
            content_json=json.dumps({"full_document": "# Final Report\n\nComplete synthesis."}),
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        data = report.to_dict()
        assert data["content"]["full_document"].startswith("# Final Report")

    async def test_version_increments_on_update(self, db_session):
        """Report version increments when findings are routed."""
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-ver",
            title="Versioned Report",
            scope="Interview Analysis",
            version=1,
        )
        db_session.add(report)
        await db_session.commit()

        assert report.version == 1

        # Simulate route_findings updating the report
        report.version += 1
        report.finding_ids_json = json.dumps(["f-1"])
        await db_session.commit()
        await db_session.refresh(report)

        assert report.version == 2

    async def test_triangulation_matrix_stored(self, db_session):
        """Verify triangulation_matrix_json stores cross-method links."""
        matrix = {
            "nav-confusion": {
                "interview": ["f-1", "f-2"],
                "usability": ["f-5"],
                "survey": ["f-8"],
            }
        }
        report = ProjectReport(
            id=str(uuid.uuid4()),
            project_id="proj-pr-tri",
            title="Triangulated Synthesis",
            layer=3,
            triangulation_matrix_json=json.dumps(matrix),
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        parsed = json.loads(report.triangulation_matrix_json)
        assert "nav-confusion" in parsed
        assert len(parsed["nav-confusion"]["interview"]) == 2
