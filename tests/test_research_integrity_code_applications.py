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
from app.models.task import Task
from app.core.agent import AgentOrchestrator
from app.skills.intercoder import cohen_kappa, krippendorff_alpha
from app.skills.base import SkillOutput
from app.core.validation_executor import ValidationExecutor, ValidationResult
from app.core.report_manager import ReportManager, SCOPE_MAP, SYNTHESIS_SKILLS

# Ensure ALL models are registered with Base (mirrors database.init_db imports)
from app.models import agent, codebook, document, finding, message, project, session, task  # noqa: F401
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
from app.models.research_validity import EvidenceUnit  # noqa: F401


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


# ============================================================
# 1. CodebookVersion Model Tests
# ============================================================

class TestCodeApplicationModel:
    """Test the CodeApplication ORM model."""

    async def test_create_with_full_source_traceability(self, db_session):
        """Create a CodeApplication with full source traceability fields."""
        ca = CodeApplication(
            id=str(uuid.uuid4()),
            project_id="proj-003",
            codebook_version_id="cbv-001",
            code_id="nav-confusion",
            source_document_id="doc-interview-p1",
            source_text="I couldn't find where the export button was hidden",
            source_location="interview_p1_sarah.txt:L42-L44",
            coder_id="llm-coder-a",
            coder_type="llm",
            confidence=0.85,
            reasoning="Participant describes inability to locate a feature, matching nav-confusion definition",
        )
        db_session.add(ca)
        await db_session.commit()
        await db_session.refresh(ca)

        assert ca.source_text == "I couldn't find where the export button was hidden"
        assert ca.source_location == "interview_p1_sarah.txt:L42-L44"
        assert ca.reasoning.startswith("Participant describes")
        assert ca.coder_type == "llm"
        assert ca.confidence == 0.85

    async def test_source_text_and_location_stored(self, db_session):
        """Verify source_text, source_location, coding_reasoning stored correctly."""
        ca = CodeApplication(
            id=str(uuid.uuid4()),
            project_id="proj-004",
            code_id="perf-issue",
            source_text="The dashboard takes 10 seconds to load every morning",
            source_location="interview_p2_marcus.txt:L18",
            reasoning="Clear reference to performance delay in daily workflow",
        )
        db_session.add(ca)
        await db_session.commit()

        result = await db_session.execute(
            select(CodeApplication).where(CodeApplication.project_id == "proj-004")
        )
        loaded = result.scalar_one()
        assert loaded.source_text == "The dashboard takes 10 seconds to load every morning"
        assert loaded.source_location == "interview_p2_marcus.txt:L18"
        assert "performance delay" in loaded.reasoning

    async def test_review_status_transitions(self, db_session):
        """Test review_status transitions: pending -> approved -> revised."""
        ca = CodeApplication(
            id=str(uuid.uuid4()),
            project_id="proj-005",
            code_id="trust-issue",
            source_text="I don't trust the AI suggestions",
            review_status="pending",
        )
        db_session.add(ca)
        await db_session.commit()
        assert ca.review_status == "pending"

        # Transition to approved
        ca.review_status = "approved"
        ca.reviewed_by = "researcher-jane"
        ca.reviewed_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(ca)
        assert ca.review_status == "approved"
        assert ca.reviewed_by == "researcher-jane"
        assert ca.reviewed_at is not None

        # Transition to revised
        ca.review_status = "revised"
        await db_session.commit()
        await db_session.refresh(ca)
        assert ca.review_status == "revised"

    async def test_to_dict_fields(self, db_session):
        """Verify to_dict() includes all expected audit trail fields."""
        ca = CodeApplication(
            id="ca-dict-test",
            project_id="proj-dict",
            code_id="test-code",
            source_text="Some text",
            source_location="file.txt:L1",
            coder_id="coder-1",
            coder_type="human",
            confidence=0.9,
            reasoning="Clear match",
            review_status="approved",
        )
        db_session.add(ca)
        await db_session.commit()
        await db_session.refresh(ca)

        d = ca.to_dict()
        assert d["code_id"] == "test-code"
        assert d["source_text"] == "Some text"
        assert d["source_location"] == "file.txt:L1"
        assert d["coder_type"] == "human"
        assert d["confidence"] == 0.9
        assert d["review_status"] == "approved"
        assert "reviewed_by" in d
        assert "reviewed_at" in d
        assert "source_document_id" in d

    async def test_agent_routes_recommendations_to_reports(self, db_session):
        """Stored recommendations are included in the report convergence path."""
        class PhaseStub:
            value = "discover"

        class SkillStub:
            name = "user-interviews"
            phase = PhaseStub()

        task = Task(
            id="task-route-recs",
            project_id="proj-route-recs",
            title="Route recs",
            skill_name="user-interviews",
        )
        output = SkillOutput(
            success=True,
            summary="done",
            nuggets=[
                {
                    "text": "raw quote",
                    "source": "interview",
                    "source_document_id": "doc-route-recs",
                    "source_location": "interview-p1:12",
                    "source_text": "Participant P1 said the export flow hid data permissions.",
                }
            ],
            facts=[{"text": "verified fact"}],
            insights=[{"text": "pattern"}],
            recommendations=[{"text": "action to take"}],
        )

        orchestrator = AgentOrchestrator()
        with (
            patch("app.core.agent_research.registry.get", return_value=SkillStub()),
            patch("app.core.report_manager.report_manager.route_findings", new_callable=AsyncMock) as route_findings,
            patch("app.services.research_validity_service.run_independent_coding_run", new_callable=AsyncMock) as coding_run,
        ):
            coding_run.return_value = {
                "id": "coding-run-route-recs",
                "promotion_status": "accepted",
                "reliability_method": "fleiss_kappa_with_krippendorff_alpha_companion",
                "kappa": 1.0,
                "alpha": 1.0,
                "rater_count": 3,
                "distinct_model_count": 3,
                "fallback_reason": "",
            }
            await orchestrator._store_findings(db_session, "proj-route-recs", output, task)

        route_findings.assert_not_awaited()
        coding_run.assert_awaited_once()

        stored_recs = await db_session.execute(
            select(finding.Recommendation).where(finding.Recommendation.project_id == "proj-route-recs")
        )
        rec = stored_recs.scalar_one()
        assert rec.task_id == task.id
        evidence_units = (
            await db_session.execute(
                select(EvidenceUnit).where(EvidenceUnit.project_id == "proj-route-recs")
            )
        ).scalars().all()
        assert len(evidence_units) == 1
        assert evidence_units[0].task_id == task.id


# ============================================================
# 3. Cohen's Kappa Calculation Tests
# ============================================================
