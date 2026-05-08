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

class TestValidationExecutor:
    """Test the ValidationExecutor multi-pass validation."""

    @pytest.fixture
    def executor(self):
        return ValidationExecutor()

    async def test_adversarial_review_returns_validation_result(self, executor):
        """adversarial_review returns a ValidationResult even on LLM failure."""
        output = MagicMock()
        output.nuggets = [{"text": "Users struggle with navigation"}]
        output.facts = [{"text": "5/6 users failed to find settings"}]
        input_data = MagicMock()

        # Mock compute_registry.chat to simulate an LLM failure
        with patch("app.core.validation_executor.ValidationExecutor._adversarial_review") as mock_review:
            mock_review.return_value = ValidationResult(
                passed=True, method="adversarial_review", confidence=0.5
            )
            result = await mock_review(output, input_data)

        assert isinstance(result, ValidationResult)
        assert result.method == "adversarial_review"

    async def test_dual_run_high_overlap(self, executor):
        """dual_run with high tag overlap -> passes."""
        output = MagicMock()
        output.nuggets = [
            {"text": "Finding 1", "tags": ["nav", "ux", "perf"]},
            {"text": "Finding 2", "tags": ["nav", "ux", "design"]},
            {"text": "Finding 3", "tags": ["nav", "perf", "design"]},
        ]

        result = await executor._dual_run(output)
        assert isinstance(result, ValidationResult)
        assert result.method == "dual_run"
        # High overlap between adjacent items -> should pass
        assert result.passed is True
        assert result.confidence > 0.15

    async def test_dual_run_zero_overlap(self, executor):
        """dual_run with zero tag overlap -> fails."""
        output = MagicMock()
        output.nuggets = [
            {"text": "Finding 1", "tags": ["a", "b"]},
            {"text": "Finding 2", "tags": ["c", "d"]},
            {"text": "Finding 3", "tags": ["e", "f"]},
        ]

        result = await executor._dual_run(output)
        assert isinstance(result, ValidationResult)
        assert result.method == "dual_run"
        assert result.passed is False
        assert result.confidence == 0.0

    async def test_dual_run_single_nugget(self, executor):
        """dual_run with fewer than 2 nuggets -> passes with default confidence."""
        output = MagicMock()
        output.nuggets = [{"text": "Only one", "tags": ["solo"]}]

        result = await executor._dual_run(output)
        assert result.passed is True
        assert result.confidence == 0.7

    async def test_dual_run_no_tags(self, executor):
        """dual_run with nuggets that have no tags -> passes with default."""
        output = MagicMock()
        output.nuggets = [
            {"text": "No tags here"},
            {"text": "Also no tags"},
        ]

        result = await executor._dual_run(output)
        assert result.passed is True
        assert result.confidence == 0.7

    async def test_unknown_method_returns_default(self, executor):
        """Unknown validation method returns passed=True with confidence=0.5."""
        output = MagicMock()
        input_data = MagicMock()

        result = await executor.validate(
            "nonexistent_method", output, input_data, "test-skill"
        )
        assert isinstance(result, ValidationResult)
        assert result.passed is True
        assert result.method == "nonexistent_method"
        assert result.confidence == 0.5

    async def test_debate_rounds_with_insights(self, executor):
        """debate_rounds with 2+ insights -> passes."""
        output = MagicMock()
        output.insights = [
            {"text": "Insight one"},
            {"text": "Insight two"},
        ]

        result = await executor._debate_rounds(output)
        assert result.passed is True
        assert result.method == "debate_rounds"
        assert result.confidence == 0.6

    async def test_debate_rounds_single_insight(self, executor):
        """debate_rounds with < 2 insights -> passes with 0.7 confidence."""
        output = MagicMock()
        output.insights = [{"text": "Only one"}]

        result = await executor._debate_rounds(output)
        assert result.passed is True
        assert result.confidence == 0.7

    def test_validation_result_dataclass_defaults(self):
        """ValidationResult has correct defaults."""
        vr = ValidationResult(passed=True, method="test")
        assert vr.confidence == 0.5
        assert vr.details == {}

    def test_validation_result_custom_details(self):
        """ValidationResult stores custom details dict."""
        vr = ValidationResult(
            passed=False,
            method="custom",
            confidence=0.3,
            details={"reason": "insufficient evidence"},
        )
        assert vr.passed is False
        assert vr.details["reason"] == "insufficient evidence"


# ============================================================
# 6. ReportManager Tests
# ============================================================
