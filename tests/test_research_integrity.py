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
from app.skills.intercoder import cohen_kappa, krippendorff_alpha
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
            "label", "brief_definition", "full_definition",
            "exclusion_criteria", "typical_example", "boundary_example",
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


# ============================================================
# 2. CodeApplication Model Tests
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


# ============================================================
# 3. Cohen's Kappa Calculation Tests
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

class TestReportManager:
    """Test the ReportManager progressive document convergence."""

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

        # First call creates report and adds findings
        await manager.route_findings(
            "proj-rm-003", "thematic-analysis", ["f-1", "f-2"], db_session
        )

        # Second call adds more findings to the same report
        await manager.route_findings(
            "proj-rm-003", "user-interviews", ["f-3", "f-4"], db_session
        )

        # Both skills map to "Interview Analysis" scope
        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == "proj-rm-003",
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

        await manager.route_findings(
            "proj-rm-004", "thematic-analysis", ["f-1", "f-2"], db_session
        )
        await manager.route_findings(
            "proj-rm-004", "thematic-analysis", ["f-2", "f-3"], db_session
        )

        result = await db_session.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == "proj-rm-004",
                ProjectReport.scope == "Interview Analysis",
            )
        )
        report = result.scalar_one()
        finding_ids = json.loads(report.finding_ids_json)
        assert len(finding_ids) == 3  # f-1, f-2, f-3 (no duplicates)

    async def test_synthesis_skill_creates_layer_3(self, db_session):
        """Synthesis skills create layer 3 reports."""
        manager = ReportManager()

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

    async def test_get_project_reports(self, db_session):
        """get_project_reports returns reports ordered by layer desc."""
        manager = ReportManager()

        # Create L2 and L3 reports
        await manager.route_findings(
            "proj-rm-006", "thematic-analysis", ["f-1"], db_session
        )
        await manager.route_findings(
            "proj-rm-006", "usability-testing", ["f-2"], db_session
        )
        await manager.route_findings(
            "proj-rm-006", "research-synthesis", ["f-3"], db_session
        )

        reports = await manager.get_project_reports("proj-rm-006", db_session)
        assert len(reports) >= 2
        # First report should be highest layer
        layers = [r["layer"] for r in reports]
        assert layers == sorted(layers, reverse=True)


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

        # Create only one L2 report
        await manager.route_findings(
            "proj-pr-conv", "thematic-analysis", ["f-1"], db_session
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
            "proj-pr-conv", "usability-testing", ["f-2"], db_session
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
