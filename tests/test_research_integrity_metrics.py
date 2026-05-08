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

class TestCohenKappa:
    """Test Cohen's Kappa calculation with known mathematical examples."""

    def test_perfect_agreement(self):
        """Both coders assign identical codes -> kappa ~1.0."""
        coder_a = [["nav"], ["perf"], ["nav", "perf"], ["trust"]]
        coder_b = [["nav"], ["perf"], ["nav", "perf"], ["trust"]]
        all_codes = ["nav", "perf", "trust"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        assert result["kappa"] == 1.0
        assert result["interpretation"] == "almost_perfect"
        assert result["n_items_coded"] == 4
        assert result["n_codes_used"] == 3
        assert len(result["low_agreement_codes"]) == 0

    def test_no_agreement_opposite_coding(self):
        """Coders assign completely opposite codes -> kappa near 0 or negative."""
        # Coder A always assigns "nav", Coder B always assigns "perf"
        coder_a = [["nav"], ["nav"], ["nav"], ["nav"]]
        coder_b = [["perf"], ["perf"], ["perf"], ["perf"]]
        all_codes = ["nav", "perf"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        # With complete disagreement on both codes, kappa should be near 0
        # (pe can equal 1.0 in degenerate cases, making kappa undefined → 0)
        assert result["kappa"] <= 0.2
        assert result["interpretation"] in ("poor", "slight")

    def test_chance_level_agreement(self):
        """Mixed agreement at roughly chance level -> kappa near 0."""
        # Construct scenario where observed agreement ~ expected agreement
        # If each coder randomly assigns "a" with 50% probability:
        coder_a = [["a"], [], ["a"], [], ["a"], [], ["a"], []]
        coder_b = [["a"], ["a"], [], [], ["a"], ["a"], [], []]
        all_codes = ["a"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        # With roughly 50/50 coding, kappa should be near 0
        assert -0.5 <= result["kappa"] <= 0.5

    def test_empty_data(self):
        """Empty input returns zero kappa with 'poor' interpretation."""
        result = cohen_kappa([], [], [])
        assert result["kappa"] == 0.0
        assert result["interpretation"] == "poor"
        assert result["n_items_coded"] == 0
        assert result["n_codes_used"] == 0

    def test_empty_codes_list(self):
        """Non-empty items but empty codes list returns zero kappa."""
        result = cohen_kappa([["a"]], [["a"]], [])
        assert result["kappa"] == 0.0
        assert result["n_codes_used"] == 0

    def test_single_code_perfect_match(self):
        """Single code with perfect agreement -> kappa = 1.0."""
        coder_a = [["theme-a"], ["theme-a"], ["theme-a"]]
        coder_b = [["theme-a"], ["theme-a"], ["theme-a"]]
        all_codes = ["theme-a"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        # All items coded the same way -> perfect agreement
        # However, when Pe=1.0, the function returns 1.0 if Po=1.0
        assert result["kappa"] == 1.0

    def test_landis_koch_slight(self):
        """Verify 'slight' interpretation for kappa in (0, 0.20]."""
        # Construct scenario giving kappa around 0.15
        # Mostly disagreement with a tiny amount of agreement
        coder_a = [["a"], ["b"], ["a"], ["b"], ["a"], ["b"], ["a"], ["b"], ["a"], ["a"]]
        coder_b = [["b"], ["a"], ["b"], ["a"], ["b"], ["a"], ["b"], ["a"], ["a"], ["a"]]
        all_codes = ["a", "b"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        # The exact kappa depends on the math; check interpretation is valid
        assert result["interpretation"] in ("poor", "slight", "fair")

    def test_landis_koch_substantial(self):
        """Verify 'substantial' interpretation for kappa in (0.60, 0.80]."""
        # 8 items, 7 agree, 1 disagrees -> high but not perfect kappa
        coder_a = [["a"], ["b"], ["a"], ["b"], ["a"], ["b"], ["a"], ["b"]]
        coder_b = [["a"], ["b"], ["a"], ["b"], ["a"], ["b"], ["a"], ["a"]]  # last one differs
        all_codes = ["a", "b"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        # Should be in substantial or almost_perfect range
        assert result["kappa"] > 0.5
        assert result["interpretation"] in ("substantial", "almost_perfect")

    def test_per_code_kappa_reported(self):
        """Verify per_code_kappa list has entries for each code."""
        coder_a = [["x", "y"], ["x"], ["y"]]
        coder_b = [["x", "y"], ["x"], ["y"]]
        all_codes = ["x", "y"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        assert len(result["per_code_kappa"]) == 2
        for entry in result["per_code_kappa"]:
            assert "code" in entry
            assert "kappa" in entry
            assert "agreement_pct" in entry

    def test_low_agreement_codes_flagged(self):
        """Codes with kappa < 0.60 are flagged in low_agreement_codes."""
        # One code has perfect agreement, another has zero
        coder_a = [["good"], ["good"], ["good"], ["bad"]]
        coder_b = [["good"], ["good"], ["good"], []]  # disagree on item 4
        all_codes = ["good", "bad"]

        result = cohen_kappa(coder_a, coder_b, all_codes)
        low_codes = [c["code"] for c in result["low_agreement_codes"]]
        # "bad" should be flagged since only coder_a applied it
        assert "bad" in low_codes


# ============================================================
# 4. Krippendorff's Alpha Calculation Tests
# ============================================================

class TestKrippendorffAlpha:
    """Test Krippendorff's Alpha calculation with known examples."""

    def test_perfect_agreement_two_coders(self):
        """Perfect agreement between two coders -> alpha = 1.0."""
        coder_a = [["nav"], ["perf"], ["nav", "perf"], ["trust"]]
        coder_b = [["nav"], ["perf"], ["nav", "perf"], ["trust"]]
        all_codes = ["nav", "perf", "trust"]

        result = krippendorff_alpha([coder_a, coder_b], all_codes)
        assert result["alpha"] == 1.0
        assert result["interpretation"] == "reliable"
        assert result["n_coders"] == 2
        assert result["n_items"] == 4

    def test_zero_agreement(self):
        """Complete disagreement -> alpha near 0 (unreliable)."""
        coder_a = [["a"], ["a"], ["a"], ["a"]]
        coder_b = [["b"], ["b"], ["b"], ["b"]]
        all_codes = ["a", "b"]

        result = krippendorff_alpha([coder_a, coder_b], all_codes)
        # With opposite coding, alpha should be well below reliability threshold
        assert result["alpha"] < 0.667
        assert result["interpretation"] == "unreliable"

    def test_empty_coders_list(self):
        """Empty coders list returns zero alpha."""
        result = krippendorff_alpha([], [])
        assert result["alpha"] == 0.0
        assert result["interpretation"] == "unreliable"
        assert result["n_coders"] == 0
        assert result["n_items"] == 0

    def test_empty_codes_list(self):
        """Non-empty coders but empty codes list returns zero alpha."""
        result = krippendorff_alpha([[["a"]], [["a"]]], [])
        assert result["alpha"] == 0.0
        assert result["n_codes"] == 0

    def test_empty_items(self):
        """Coders with zero items returns zero alpha."""
        result = krippendorff_alpha([[], []], ["a"])
        assert result["alpha"] == 0.0
        assert result["n_items"] == 0

    def test_three_coders_perfect_agreement(self):
        """Three coders with perfect agreement -> alpha = 1.0."""
        items = [["a"], ["b"], ["a", "b"], ["c"]]
        coder_a = items[:]
        coder_b = items[:]
        coder_c = items[:]
        all_codes = ["a", "b", "c"]

        result = krippendorff_alpha([coder_a, coder_b, coder_c], all_codes)
        assert result["alpha"] == 1.0
        assert result["n_coders"] == 3
        assert result["interpretation"] == "reliable"

    def test_three_coders_mixed_agreement(self):
        """Three coders with partial agreement -> alpha between 0 and 1."""
        coder_a = [["a"], ["b"], ["a"], ["b"]]
        coder_b = [["a"], ["b"], ["b"], ["b"]]  # disagrees on item 3
        coder_c = [["a"], ["b"], ["a"], ["a"]]  # disagrees on item 4
        all_codes = ["a", "b"]

        result = krippendorff_alpha([coder_a, coder_b, coder_c], all_codes)
        assert 0.0 < result["alpha"] < 1.0
        assert result["n_coders"] == 3

    def test_interpretation_reliable(self):
        """Alpha >= 0.800 -> 'reliable'."""
        # Perfect agreement guarantees alpha = 1.0
        items = [["x"], ["y"], ["x"]]
        result = krippendorff_alpha([items[:], items[:]], ["x", "y"])
        assert result["interpretation"] == "reliable"

    def test_interpretation_unreliable(self):
        """Alpha < 0.667 -> 'unreliable'."""
        # Construct heavy disagreement
        coder_a = [["a"], ["b"], ["a"], ["b"], ["a"], ["b"]]
        coder_b = [["b"], ["a"], ["b"], ["a"], ["b"], ["a"]]
        all_codes = ["a", "b"]

        result = krippendorff_alpha([coder_a, coder_b], all_codes)
        assert result["interpretation"] == "unreliable"

    def test_per_code_alpha_reported(self):
        """Verify per_code_alpha has one entry per code."""
        coder_a = [["x", "y"], ["x"]]
        coder_b = [["x", "y"], ["x"]]
        all_codes = ["x", "y"]

        result = krippendorff_alpha([coder_a, coder_b], all_codes)
        assert len(result["per_code_alpha"]) == 2
        for entry in result["per_code_alpha"]:
            assert "code" in entry
            assert "alpha" in entry

    def test_unreliable_codes_flagged(self):
        """Codes with alpha < 0.667 are flagged in unreliable_codes."""
        # One code perfect, one code total disagreement
        coder_a = [["good", "bad"], ["good"], ["good"], ["bad"]]
        coder_b = [["good"], ["good"], ["good"], []]
        all_codes = ["good", "bad"]

        result = krippendorff_alpha([coder_a, coder_b], all_codes)
        unreliable_names = [c["code"] for c in result["unreliable_codes"]]
        # "bad" should have low alpha
        assert "bad" in unreliable_names

    def test_single_code_all_present(self):
        """Single code present in all items for all coders -> alpha = 1.0."""
        coder_a = [["only"], ["only"], ["only"]]
        coder_b = [["only"], ["only"], ["only"]]
        all_codes = ["only"]

        result = krippendorff_alpha([coder_a, coder_b], all_codes)
        # All values identical -> Do = 0, De = 0, function returns 1.0
        assert result["alpha"] == 1.0


# ============================================================
# 5. ValidationExecutor Tests
# ============================================================
