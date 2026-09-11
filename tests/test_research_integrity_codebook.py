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
from app.models import (
    agent,
    codebook,
    document,
    finding,
    message,
    project,
    session,
    task,
)  # noqa: F401
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

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ============================================================
# 1. CodebookVersion Model Tests
# ============================================================


class TestCodebookVersionModel:
    """Test the CodebookVersion ORM model."""

    async def test_create_codebook_version_stores_all_fields(self, db_session):
        """Create a CodebookVersion, verify all fields stored correctly."""
        codes = [
            {
                "label": "nav-confusion",
                "brief_definition": "User confused by navigation",
                "full_definition": "Participant expresses difficulty finding features via main nav",
                "exclusion_criteria": "General frustration not related to navigation",
                "typical_example": "I couldn't find where the settings were",
                "boundary_example": "The menu is kind of hidden",
            }
        ]
        cbv = CodebookVersion(
            id=str(uuid.uuid4()),
            project_id="proj-001",
            version="1.0.0",
            codes_json=json.dumps(codes),
            change_log="Initial codebook creation",
            created_by="coder-a",
            methodology="codebook_ta",
        )
        db_session.add(cbv)
        await db_session.commit()
        await db_session.refresh(cbv)

        assert cbv.project_id == "proj-001"
        assert cbv.version == "1.0.0"
        assert cbv.created_by == "coder-a"
        assert cbv.methodology == "codebook_ta"
        assert cbv.change_log == "Initial codebook creation"
        assert cbv.created_at is not None

    async def test_codes_json_structure_with_six_components(self, db_session):
        """Verify codes_json structure contains the 6 required Saldana components."""
        required_keys = {
            "label",
            "brief_definition",
            "full_definition",
            "exclusion_criteria",
            "typical_example",
            "boundary_example",
        }
        codes = [
            {
                "label": "perf-frustration",
                "brief_definition": "User frustrated by slow performance",
                "full_definition": "Participant describes delays or sluggishness as blocking their workflow",
                "exclusion_criteria": "References to speed in a positive light",
                "typical_example": "Loading takes forever when I switch tabs",
                "boundary_example": "It's a bit slow sometimes",
            },
            {
                "label": "data-loss-fear",
                "brief_definition": "User worried about losing data",
                "full_definition": "Participant expresses concern that work might be lost",
                "exclusion_criteria": "Concerns about data privacy (not loss)",
                "typical_example": "I always save three times because I'm afraid it won't stick",
                "boundary_example": "I hope this saves properly",
            },
        ]
        cbv = CodebookVersion(
            id=str(uuid.uuid4()),
            project_id="proj-002",
            codes_json=json.dumps(codes),
        )
        db_session.add(cbv)
        await db_session.commit()

        parsed = json.loads(cbv.codes_json)
        assert len(parsed) == 2
        for code_entry in parsed:
            assert required_keys.issubset(set(code_entry.keys())), (
                f"Missing keys: {required_keys - set(code_entry.keys())}"
            )

    async def test_version_incrementing(self, db_session):
        """Test creating successive codebook versions."""
        base_id = "proj-ver-test"
        for i, ver in enumerate(["1.0.0", "1.1.0", "2.0.0"]):
            cbv = CodebookVersion(
                id=str(uuid.uuid4()),
                project_id=base_id,
                version=ver,
                codes_json="[]",
                change_log=f"Version bump to {ver}",
            )
            db_session.add(cbv)
        await db_session.commit()

        result = await db_session.execute(
            select(CodebookVersion)
            .where(CodebookVersion.project_id == base_id)
            .order_by(CodebookVersion.created_at)
        )
        versions = [r.version for r in result.scalars().all()]
        assert versions == ["1.0.0", "1.1.0", "2.0.0"]

    async def test_to_dict_returns_parsed_codes(self, db_session):
        """Verify to_dict() returns parsed JSON codes, not raw string."""
        codes = [{"label": "test-code", "brief_definition": "A test"}]
        cbv = CodebookVersion(
            id=str(uuid.uuid4()),
            project_id="proj-dict",
            codes_json=json.dumps(codes),
        )
        db_session.add(cbv)
        await db_session.commit()
        await db_session.refresh(cbv)

        d = cbv.to_dict()
        assert isinstance(d["codes"], list)
        assert d["codes"][0]["label"] == "test-code"
        assert d["version"] == "1.0.0"  # default

    async def test_to_dict_invalid_codes_json_returns_empty_list(self, db_session):
        """Corrupt codebook JSON should not break the Codebook menu."""
        cbv = CodebookVersion(
            id=str(uuid.uuid4()),
            project_id="proj-invalid-json",
            codes_json="{not valid json",
        )
        db_session.add(cbv)
        await db_session.commit()
        await db_session.refresh(cbv)

        assert cbv.to_dict()["codes"] == []


# ============================================================
# 2. CodeApplication Model Tests
# ============================================================
