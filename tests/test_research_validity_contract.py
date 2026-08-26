"""Research-validity contract tests for qualitative coding and promotion gates."""

import json
import re
import uuid
from pathlib import Path

import pytest

_RUNTIME_PERSONA_DIR = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
REPO_ROOT = Path(__file__).resolve().parents[1]


def _is_gitignored_runtime_persona(path: Path) -> bool:
    parts = path.parts
    return "personas" in parts and any(
        _RUNTIME_PERSONA_DIR.match(part) for part in parts
    )


def test_qualitative_coding_prompt_deterministically_injects_protocol_blocks():
    from app.core.research_validity import build_qualitative_coding_prompt

    prompt = build_qualitative_coding_prompt(
        evidence_units=[
            {
                "id": "eu-1",
                "source_text": "I get lost when I try to invite collaborators.",
                "source_location": "interview-01:42",
            }
        ],
        codebook={
            "status": "frozen",
            "codes": [
                {
                    "code_id": "collaboration-disorientation",
                    "definition": "Participant cannot understand invite or workspace sharing flows.",
                    "inclusion_criteria": ["Confusion about inviting collaborators"],
                    "exclusion_criteria": ["General navigation comments"],
                }
            ],
        },
    )

    assert "<qualitative_coding_protocol>" in prompt
    assert "<codebook>" in prompt
    assert "<evidence_units>" in prompt
    assert "<reliability_policy>" in prompt
    assert "Code evidence units, not keywords" in prompt


def test_coding_application_rejects_quote_outside_referenced_evidence_unit():
    from types import SimpleNamespace

    from app.services.research_validity_service import _usable_coding_applications

    unit = SimpleNamespace(
        id="eu-grounding-1",
        stable_id="stable-grounding-1",
        unit_index=1,
        source_text="The participant could not find the invitation control.",
    )
    parsed = {
        "applications": [
            {
                "evidence_unit_id": unit.id,
                "codes": ["invitation-discovery"],
                "quote": "The participant loved the invitation control.",
            }
        ]
    }

    assert (
        _usable_coding_applications(
            parsed,
            unit_by_id={unit.id: unit},
            units=[unit],
        )
        == []
    )


def test_contract_marks_visible_findings_as_provisional_until_reportable():
    from app.core.research_validity import RESEARCH_VALIDITY_CONTRACT

    rules = "\n".join(RESEARCH_VALIDITY_CONTRACT["non_negotiables"])

    assert (
        "Visible nuggets, facts, insights, or recommendations are provisional" in rules
    )
    assert "approved Done task state" in rules


def test_skill_output_defaults_research_artifacts_to_provisional_candidates():
    from app.skills.base import SkillOutput

    output = SkillOutput(
        success=True,
        summary="Candidate skill output",
        nuggets=[
            {
                "text": "Participant could not find billing settings.",
                "source": "interview",
            }
        ],
        facts=[{"text": "Billing settings were hard to find."}],
        insights=[{"text": "Navigation labels are not matching user expectations."}],
        recommendations=[{"text": "Rename billing settings entry point."}],
    )

    assert output.research_validity["status"] == "provisional"
    assert output.research_validity["report_allowed"] is False
    assert output.nuggets[0]["artifact_state"] == "candidate_atom"
    assert output.facts[0]["artifact_state"] == "candidate_fact"
    assert output.insights[0]["artifact_state"] == "candidate_insight"
    assert output.recommendations[0]["artifact_state"] == "candidate_recommendation"
    assert output.nuggets[0]["research_validity"]["report_allowed"] is False


def test_architecture_contract_covers_task_creation_surfaces():
    contract = REPO_ROOT / "docs/architecture/research-validity-contract.md"
    text = " ".join(contract.read_text(encoding="utf-8").split())

    assert "API, Kanban, chat, and LLM-callable system-action tools" in text
    assert "Attached input documents must belong to the active project" in text
    assert "do not create report evidence by themselves" in text


def test_project_agent_instructions_make_research_spine_non_optional():
    agent_rules = " ".join(
        (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8").split()
    )
    contract = " ".join(
        (REPO_ROOT / "docs/architecture/research-validity-contract.md")
        .read_text(encoding="utf-8")
        .split()
    )

    required_phrases = [
        "Every product feature that ingests, creates, processes, retrieves, summarizes, validates, visualizes, routes, promotes, or reports user research data",
        "skills, task creation and execution, ReAct/tool calls, chat, documents, interviews, surveys, AURA-style research, integrations, deployments, interfaces",
        "If a feature currently bypasses the spine, classify it as architecture debt",
        "Compass Forge impact output is the starting map for change radius, not a substitute for architectural judgment",
    ]
    for phrase in required_phrases[:3]:
        assert phrase in agent_rules
    assert required_phrases[3] in contract
    assert (
        "Features do not get separate research objectives or parallel shortcuts"
        in contract
    )


def test_chat_runtime_prompt_injects_protected_research_spine_gate():
    from app.api.routes.chat import _research_spine_chat_contract

    block = _research_spine_chat_contract()

    assert block.startswith("<promotion_gate>")
    assert (
        "Do not present raw model output, RAG snippets, memories, or tool output as accepted research."
        in block
    )
    assert "human-approved Done tasks" in block
    assert block.endswith("</promotion_gate>")


def test_static_research_artifact_constructors_stay_inside_approved_boundaries():
    """New production surfaces must not bypass the Research Spine by accident."""

    repo_root = REPO_ROOT
    allowed_files = {
        "backend/app/api/routes/findings.py",
        "backend/app/api/routes/interfaces_mock.py",
        "backend/app/api/routes/interfaces_screens.py",
        "backend/app/api/routes/tasks.py",
        "backend/app/core/agent_research.py",
        "backend/app/core/report_manager.py",
        "backend/app/services/deployment_service.py",
        "backend/app/services/survey_ingestion.py",
        "backend/app/skills/design_tools.py",
    }
    artifact_pattern = re.compile(
        r"\b(Nugget|Fact|Insight|Recommendation|DesignDecision|ProjectReport)\s*\("
    )
    violations: list[str] = []
    for path in sorted((repo_root / "backend/app").rglob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        if "/models/" in rel or "/alembic/" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        if artifact_pattern.search(text) and rel not in allowed_files:
            violations.append(rel)

    assert not violations, (
        "Research artifact constructors must live in approved provisional/spine/report "
        f"boundaries. Unexpected files: {violations}"
    )


def test_static_design_decision_constructors_mark_provisional_rationale():
    """Interface-generated design decisions must carry their provisional state."""

    constructor_files = [
        REPO_ROOT / "backend/app/api/routes/interfaces_mock.py",
        REPO_ROOT / "backend/app/api/routes/interfaces_screens.py",
        REPO_ROOT / "backend/app/skills/design_tools.py",
    ]
    violations: list[str] = []
    for path in constructor_files:
        text = path.read_text(encoding="utf-8")
        if (
            "DesignDecision(" in text
            and "provisional_design_decision_rationale" not in text
        ):
            violations.append(path.relative_to(REPO_ROOT).as_posix())

    assert not violations, (
        "DesignDecision constructors outside Findings must visibly mark generated "
        f"artifacts as provisional Research Spine candidates: {violations}"
    )


def test_docs_and_skill_prompts_do_not_describe_trusted_nugget_first_flow():
    """Docs/prompts may mention Atomic artifacts only as accepted spine outputs."""

    roots = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "README.pt-BR.md",
        REPO_ROOT / "TESTING.md",
        REPO_ROOT / "docs/architecture",
        REPO_ROOT / "docs/features/content",
        REPO_ROOT / "docs/scientific_audit",
        REPO_ROOT / "backend/app/agents/personas",
        REPO_ROOT / "backend/app/skills/definitions",
        REPO_ROOT / "tests/simulation/scenarios",
    ]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(
                path
                for path in root.rglob("*")
                if path.suffix in {".md", ".json", ".mjs"}
                and not _is_gitignored_runtime_persona(path)
            )

    forbidden = [
        re.compile(r"Accepted code applications become", re.IGNORECASE),
        re.compile(r"Códigos aceitos viram", re.IGNORECASE),
        re.compile(r"Raw quote or observation \(Nugget\)", re.IGNORECASE),
        re.compile(r"Citação bruta ou observação \(Nugget\)", re.IGNORECASE),
        re.compile(r"documents?\s*[-=]+>\s*nuggets?", re.IGNORECASE),
        re.compile(r"docs?\s*[-=]+>\s*nuggets?", re.IGNORECASE),
        re.compile(r"-\s*Chain:\s*Nugget", re.IGNORECASE),
        re.compile(r"-\s*Use the chain:\s*Nugget", re.IGNORECASE),
        re.compile(r"Store findings in Atomic Research hierarchy", re.IGNORECASE),
        re.compile(r"Persist results in the Atomic Research chain", re.IGNORECASE),
        re.compile(r"ATOMIC RESEARCH EVIDENCE CHAIN", re.IGNORECASE),
        re.compile(
            r"Atomic Research framework provides the structural hierarchy",
            re.IGNORECASE,
        ),
        re.compile(r"Produce findings in Atomic Research format", re.IGNORECASE),
        re.compile(r"Construct the full evidence chain:\s*nuggets", re.IGNORECASE),
        re.compile(r"traceable from nuggets through to recommendations", re.IGNORECASE),
        re.compile(r"Organize nuggets", re.IGNORECASE),
        re.compile(r"NUGGET EXTRACTION", re.IGNORECASE),
    ]
    violations: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern.search(text):
                violations.append(f"{path}:{pattern.pattern}")
                break

    assert not violations, (
        "Docs/prompts must not teach trusted-before-validation Atomic Research flow: "
        f"{violations[:20]}"
    )


def test_segment_evidence_units_preserves_speaker_turns_and_stable_ids():
    from app.core.research_validity import segment_evidence_units

    units = segment_evidence_units(
        project_id="proj-validity",
        source_id="interview-01",
        source_location="interview-01.md",
        source_text=(
            "MODERATOR: Tell me about onboarding.\n"
            "P01: I did not know where to invite my team.\n\n"
            "The observer noted repeated hesitation around workspace setup."
        ),
        participant_id="P01",
        method="interview",
        phase="discover",
    )

    assert [unit.stable_id for unit in units][:2] == [
        "interview-01#EU-0001",
        "interview-01#EU-0002",
    ]
    assert units[1].speaker == "P01"
    assert units[1].participant_id == "P01"
    assert units[1].start_offset is not None
    assert units[1].end_offset is not None


@pytest.mark.asyncio
async def test_persisted_evidence_units_emit_content_free_telemetry():
    from app.core.telemetry import telemetry_recorder
    from app.models.database import async_session, init_db
    from app.services.research_validity_service import (
        persist_task_nugget_evidence_units,
    )

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-eu-telemetry-{suffix}"
    task_id = f"task-eu-telemetry-{suffix}"
    await init_db()

    async with async_session() as db:
        units = await persist_task_nugget_evidence_units(
            db,
            project_id=project_id,
            task_id=task_id,
            nugget_id=f"nugget-eu-telemetry-{suffix}",
            source_text=(
                "P01: I could not invite my team during onboarding.\n"
                "P02: The workspace permissions were unclear."
            ),
            source_location="interview-telemetry.md",
            method="interview",
            phase="discover",
        )
        await db.commit()

    audit = await telemetry_recorder.get_research_validity_audit(project_id)
    assert len(units) == 2
    assert audit["operation_counts"]["evidence_unit.extract"] == 2
    assert set(audit["evidence_unit_ids"]) == {unit.id for unit in units}
    assert audit["retrieval_mode_counts"]["hybrid"] == 2


@pytest.mark.asyncio
async def test_survey_ingestion_creates_source_evidence_units_not_reportable_trusted_nuggets():
    from sqlalchemy import select

    from app.models.database import async_session, init_db
    from app.models.finding import Nugget
    from app.models.research_validity import EvidenceUnit
    from app.models.survey_integration import SurveyIntegration, SurveyLink
    from app.services.finding_validity_service import finding_research_validity_map
    from app.services.survey_ingestion import ingest_responses

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-survey-spine-{suffix}"
    await init_db()
    integration = SurveyIntegration(
        id=f"integration-survey-spine-{suffix}",
        platform="typeform",
        name="Prototype feedback",
        project_id=project_id,
    )
    link = SurveyLink(
        id=f"link-survey-spine-{suffix}",
        integration_id=integration.id,
        project_id=project_id,
        external_survey_id="survey-01",
        external_survey_name="Prototype feedback",
    )

    async with async_session() as db:
        db.add(integration)
        db.add(link)
        await db.flush()
        summary = await ingest_responses(
            db,
            link,
            [
                {
                    "id": "resp-001",
                    "answers": [
                        {
                            "question": "What blocked onboarding?",
                            "answer": "The invite screen made permissions unclear.",
                        }
                    ],
                }
            ],
            project_id,
        )
        units = list(
            (
                await db.execute(
                    select(EvidenceUnit).where(EvidenceUnit.project_id == project_id)
                )
            )
            .scalars()
            .all()
        )
        nuggets = list(
            (await db.execute(select(Nugget).where(Nugget.project_id == project_id)))
            .scalars()
            .all()
        )
        validity = await finding_research_validity_map(
            db, project_id=project_id, findings=nuggets
        )

    assert summary["nuggets_created"] == 1
    assert summary["evidence_units_created"] == len(units)
    assert len(units) >= 1
    assert {unit.source_type for unit in units} == {"survey_response"}
    assert {unit.unit_type for unit in units} == {"source_span"}
    assert any("invite screen" in unit.source_text for unit in units)
    assert validity[nuggets[0].id]["status"] == "provisional"
    assert validity[nuggets[0].id]["report_allowed"] is False


@pytest.mark.asyncio
async def test_deployment_response_enters_spine_as_source_evidence_unit():
    from sqlalchemy import select

    from app.models.channel_conversation import ChannelConversation
    from app.models.database import async_session, init_db
    from app.models.research_deployment import ResearchDeployment
    from app.models.research_validity import EvidenceUnit
    from app.services.deployment_service import handle_response

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-deploy-spine-{suffix}"
    deployment_id = f"deployment-spine-{suffix}"
    conversation_id = f"conversation-spine-{suffix}"
    await init_db()

    async with async_session() as db:
        db.add(
            ResearchDeployment(
                id=deployment_id,
                project_id=project_id,
                name="Onboarding interview",
                deployment_type="interview",
                questions_json=json.dumps([{"text": "What felt risky?"}]),
                config_json=json.dumps({"adaptive": False}),
                state="active",
            )
        )
        db.add(
            ChannelConversation(
                id=conversation_id,
                channel_instance_id=f"channel-spine-{suffix}",
                project_id=project_id,
                participant_id="P01",
                deployment_id=deployment_id,
            )
        )
        await db.commit()

        result = await handle_response(
            db,
            deployment_id,
            conversation_id,
            "I did not trust the data export permission screen.",
            project_id=project_id,
        )
        units = list(
            (
                await db.execute(
                    select(EvidenceUnit).where(EvidenceUnit.project_id == project_id)
                )
            )
            .scalars()
            .all()
        )

    assert result["action"] == "complete"
    assert result["nugget_id"]
    assert len(units) >= 1
    assert {unit.source_type for unit in units} == {"deployment_response"}
    assert {unit.unit_type for unit in units} == {"source_span"}
    assert any("data export permission" in unit.source_text for unit in units)


@pytest.mark.asyncio
async def test_channel_deployment_skill_outputs_candidate_artifacts(monkeypatch):
    from types import SimpleNamespace

    from app.skills.base import SkillInput
    from app.skills.discover.channel_deployment import ChannelResearchDeploymentSkill

    analysis_payload = {
        "themes": [{"name": "permission anxiety", "frequency": 1}],
        "nuggets": [
            {
                "text": "Participant hesitated at the export permission prompt.",
                "source": "deployment:onboarding:response:1",
                "source_quote": "I am not sure what this export permission does.",
                "tags": ["trust", "permissions"],
            }
        ],
        "insights": [
            {
                "text": "Export permissions create trust friction.",
                "confidence": "medium",
                "impact": "high",
            }
        ],
        "recommendations": [
            {
                "text": "Clarify export permission scope before granting access.",
                "priority": "high",
                "effort": "medium",
            }
        ],
        "data_quality": {"overall_quality": "medium"},
    }

    class _StubAgentic:
        """W9: the skill analyzes through the dispatcher's structured verb."""

        async def structured(self, **kwargs):  # noqa: ANN001
            assert kwargs.get("purpose") == "skill.discover_analyze"
            assert kwargs.get("project_id") == "proj-channel-skill"
            return SimpleNamespace(
                text=json.dumps(analysis_payload),
                value=analysis_payload,
                status="success",
                usage={},
                stop_reason="stop",
                endpoint_id="ep-stub",
                tool_calls=[],
            )

    monkeypatch.setattr("app.core.agentic.agentic", _StubAgentic())

    output = await ChannelResearchDeploymentSkill().execute(
        SkillInput(
            project_id="proj-channel-skill",
            parameters={
                "mode": "analyze",
                "deployment_name": "onboarding",
                "deployment_type": "interview",
                "responses": [
                    {
                        "id": "response-1",
                        "answer": "I am not sure what this export permission does.",
                    }
                ],
            },
        )
    )
    artifact = json.loads(output.artifacts["deployment_analysis.json"])

    assert output.success is True
    assert "candidate nuggets" in output.summary
    assert output.nuggets[0]["artifact_state"] == "candidate_atom"
    assert output.insights[0]["artifact_state"] == "candidate_insight"
    assert output.recommendations[0]["artifact_state"] == "candidate_recommendation"
    assert output.nuggets[0]["research_validity"]["report_allowed"] is False
    assert artifact["research_validity"]["status"] == "provisional"
    assert artifact["candidate_nuggets"][0]["source_quote"]


def test_three_model_gate_accepts_only_item_by_rater_agreement():
    from app.core.research_validity import evaluate_reliability_gate

    applications = [
        {
            "coder_id": "coder-a",
            "model_name": "model-a",
            "evidence_unit_id": "eu-1",
            "codes": ["nav"],
        },
        {
            "coder_id": "coder-b",
            "model_name": "model-b",
            "evidence_unit_id": "eu-1",
            "codes": ["nav"],
        },
        {
            "coder_id": "coder-c",
            "model_name": "model-c",
            "evidence_unit_id": "eu-1",
            "codes": ["nav"],
        },
        {
            "coder_id": "coder-a",
            "model_name": "model-a",
            "evidence_unit_id": "eu-2",
            "codes": ["trust"],
        },
        {
            "coder_id": "coder-b",
            "model_name": "model-b",
            "evidence_unit_id": "eu-2",
            "codes": ["trust"],
        },
        {
            "coder_id": "coder-c",
            "model_name": "model-c",
            "evidence_unit_id": "eu-2",
            "codes": ["trust"],
        },
    ]

    result = evaluate_reliability_gate(applications)

    assert result["method"] == "fleiss_kappa_with_krippendorff_alpha_companion"
    assert result["kappa"] == 1.0
    assert result["promotion_status"] == "accepted"
    assert result["matrix"]["matrix"]["eu-1"]["coder-a"] == ["nav"]
    assert result["item_promotion_statuses"] == {"eu-1": "accepted", "eu-2": "accepted"}
    assert result["accepted_evidence_unit_ids"] == ["eu-1", "eu-2"]


def test_passing_run_does_not_bulk_accept_disagreed_items():
    from app.core.research_validity import evaluate_reliability_gate

    applications = []
    for index in range(1, 7):
        base_code = "nav" if index <= 3 else "trust"
        for coder_id, model_name in (
            ("coder-a", "model-a"),
            ("coder-b", "model-b"),
            ("coder-c", "model-c"),
        ):
            code = "nav" if index == 6 and coder_id == "coder-c" else base_code
            applications.append(
                {
                    "coder_id": coder_id,
                    "model_name": model_name,
                    "evidence_unit_id": f"eu-{index}",
                    "codes": [code],
                }
            )

    result = evaluate_reliability_gate(applications)

    assert result["kappa"] >= 0.60
    assert result["promotion_status"] == "accepted"
    assert result["item_promotion_statuses"]["eu-1"] == "accepted"
    assert result["item_promotion_statuses"]["eu-6"] == "needs_reconciliation"
    assert "eu-6" in result["reconciliation_evidence_unit_ids"]


def test_low_consensus_routes_to_reconciliation_not_promotion():
    from app.core.research_validity import evaluate_reliability_gate

    applications = [
        {
            "coder_id": "coder-a",
            "model_name": "model-a",
            "evidence_unit_id": "eu-1",
            "codes": ["nav"],
        },
        {
            "coder_id": "coder-b",
            "model_name": "model-b",
            "evidence_unit_id": "eu-1",
            "codes": ["trust"],
        },
        {
            "coder_id": "coder-c",
            "model_name": "model-c",
            "evidence_unit_id": "eu-1",
            "codes": ["price"],
        },
        {
            "coder_id": "coder-a",
            "model_name": "model-a",
            "evidence_unit_id": "eu-2",
            "codes": ["nav"],
        },
        {
            "coder_id": "coder-b",
            "model_name": "model-b",
            "evidence_unit_id": "eu-2",
            "codes": ["trust"],
        },
        {
            "coder_id": "coder-c",
            "model_name": "model-c",
            "evidence_unit_id": "eu-2",
            "codes": ["price"],
        },
    ]

    result = evaluate_reliability_gate(applications)

    assert result["method"] == "fleiss_kappa_with_krippendorff_alpha_companion"
    assert result["kappa"] is not None
    assert result["kappa"] < 0.60
    assert result["promotion_status"] == "needs_reconciliation"


def test_reused_model_identity_is_not_counted_as_independent_ensemble():
    from app.core.research_validity import evaluate_reliability_gate

    applications = [
        {
            "coder_id": "pass-1",
            "model_name": "same-model",
            "evidence_unit_id": "eu-1",
            "codes": ["nav"],
        },
        {
            "coder_id": "pass-2",
            "model_name": "same-model",
            "evidence_unit_id": "eu-1",
            "codes": ["nav"],
        },
    ]

    result = evaluate_reliability_gate(applications)

    assert result["method"] == "invalid_independence"
    assert result["promotion_status"] == "needs_reconciliation"
    assert "reused a model identity" in result["fallback_reason"]


def test_single_model_path_is_lower_assurance():
    from app.core.research_validity import evaluate_reliability_gate

    result = evaluate_reliability_gate(
        [
            {
                "coder_id": "coder-a",
                "model_name": "model-a",
                "evidence_unit_id": "eu-1",
                "codes": ["nav"],
            }
        ]
    )

    assert result["method"] == "single_coder_lower_assurance"
    assert result["promotion_status"] == "needs_human_review"
    assert result["kappa"] is None


@pytest.mark.asyncio
async def test_research_validity_summary_route_uses_project_scope(admin_auth_headers):
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.models.database import init_db

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/research-validity/test-project/summary",
            headers=admin_auth_headers,
        )

    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert (
            response.json()["report_gate"]
            == "accepted_reconciled_evidence_from_approved_done_tasks_only"
        )


@pytest.mark.asyncio
async def test_codebook_version_create_records_governed_lifecycle_telemetry(
    admin_auth_headers,
):
    from httpx import ASGITransport, AsyncClient

    from app.core.telemetry import telemetry_recorder
    from app.main import app
    from app.models.database import init_db

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-codebook-telemetry-{suffix}"
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/api/codebook-versions",
            headers=admin_auth_headers,
            json={
                "project_id": project_id,
                "version": "1.0.0",
                "codes": [
                    {
                        "code_id": "invite-friction",
                        "definition": "Invite setup blocks teamwork.",
                    }
                ],
                "change_log": "Initial governed codebook.",
                "created_by": "researcher-a",
            },
        )
        second = await ac.post(
            "/api/codebook-versions",
            headers=admin_auth_headers,
            json={
                "project_id": project_id,
                "version": "1.1.0",
                "codes": [
                    {
                        "code_id": "permission-ambiguity",
                        "definition": "Permissions are unclear.",
                    }
                ],
                "change_log": "Governed revision.",
                "created_by": "researcher-a",
            },
        )

    assert first.status_code == 201
    assert second.status_code == 201
    audit = await telemetry_recorder.get_research_validity_audit(project_id)
    assert audit["operation_counts"]["codebook.freeze"] == 1
    assert audit["operation_counts"]["codebook.revise"] == 1
    assert set(audit["codebook_version_ids"]) == {
        first.json()["id"],
        second.json()["id"],
    }


@pytest.mark.asyncio
async def test_independent_coding_run_persists_model_codes_and_reliability(monkeypatch):
    from sqlalchemy import select

    from app.models.code_application import CodeApplication
    from app.models.database import async_session, init_db
    from app.models.research_validity import CodingRunCoder, EvidenceUnit
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-coding-run-{suffix}"
    task_id = f"task-coding-run-{suffix}"
    unit_ids = [f"eu-coding-1-{suffix}", f"eu-coding-2-{suffix}"]
    source_quotes = {
        unit_id: f"Participant struggled with invitation setup {index}."
        for index, unit_id in enumerate(unit_ids, 1)
    }

    class FakeCoderNode:
        """Selection-only coder node: W9 runs the coding through the
        dispatcher (``_pi_coder_runner``), so the node only carries the
        attributes ``_select_project_coders`` reads."""

        def __init__(self, node_id: str, model_name: str) -> None:
            self.node_id = node_id
            self.name = node_id
            self.source = "local"
            self.provider_type = "fake"
            self.is_healthy = True
            self.loaded_models = [model_name]
            self.model_capabilities = {}
            self.provider_account_handle = f"account-{node_id}"

    class _StubAgentic:
        def __init__(self) -> None:
            self.calls = 0

        async def structured(self, **kwargs):  # noqa: ANN001
            from types import SimpleNamespace

            assert kwargs["purpose"] == "validity.coder"
            assert kwargs["project_id"] == project_id
            assert "<qualitative_coding_protocol>" in kwargs["messages"][-1]["content"]
            self.calls += 1
            applications = [
                {
                    "evidence_unit_id": unit_id,
                    "codes": ["collaboration-disorientation"],
                    "primary_code": "collaboration-disorientation",
                    "quote": source_quotes[unit_id],
                    "confidence": 0.92,
                    "rationale": "The participant is blocked by team invitation setup.",
                }
                for unit_id in unit_ids
            ]
            return SimpleNamespace(
                text=json.dumps({"applications": applications}),
                value={"applications": applications},
                status="success",
                usage={},
                stop_reason="stop",
                endpoint_id="ep-stub",
                tool_calls=[],
            )

    class FakeRouter:
        def __init__(self) -> None:
            self.nodes = [
                FakeCoderNode("node-a", "model-a"),
                FakeCoderNode("node-b", "model-b"),
                FakeCoderNode("node-c", "model-c"),
            ]

        def _sorted_servers(self, **kwargs):  # noqa: ANN001
            assert kwargs["project_id"] == project_id
            return self.nodes

    await init_db()
    monkeypatch.setattr(research_validity_service, "llm_router", FakeRouter())
    stub = _StubAgentic()
    monkeypatch.setattr("app.core.agentic.agentic", stub)
    # Isolate from the engine-plane lookup (covered by the W7 suite): this
    # test exercises the legacy-engine coder-selection path.
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        research_validity_service, "_use_pi_coding_plane", AsyncMock(return_value=False)
    )

    async with async_session() as db:
        for index, unit_id in enumerate(unit_ids, 1):
            db.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id=project_id,
                    task_id=task_id,
                    source_id="interview-01",
                    stable_id=f"interview-01#EU-{index:04d}",
                    unit_index=index,
                    source_text=f"Participant struggled with invitation setup {index}.",
                    source_location=f"interview-01:{index}",
                )
            )
        await db.commit()

        result = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            task_id=task_id,
            evidence_unit_ids=unit_ids,
            created_by="test-researcher",
        )

        # Perfect raw agreement across only one observed category has expected
        # agreement 1.0, so Fleiss' kappa is undefined rather than evidence of
        # beyond-chance reliability.
        assert result["promotion_status"] == "needs_reconciliation"
        assert (
            result["reliability_method"]
            == "fleiss_kappa_with_krippendorff_alpha_companion"
        )
        assert result["kappa"] is None
        assert result["rater_count"] == 3
        assert result["code_application_count"] == 6
        assert {route["model"] for route in result["route_evidence"]} == {
            "model-a",
            "model-b",
            "model-c",
        }

        app_rows = (
            (
                await db.execute(
                    select(CodeApplication).where(
                        CodeApplication.coding_run_id == result["id"]
                    )
                )
            )
            .scalars()
            .all()
        )
        coder_rows = (
            (
                await db.execute(
                    select(CodingRunCoder).where(
                        CodingRunCoder.coding_run_id == result["id"]
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(app_rows) == 6
    assert len(coder_rows) == 3
    assert {row.reliability_status for row in app_rows} == {"needs_reconciliation"}
    assert {row.promotion_status for row in app_rows} == {"needs_reconciliation"}
    assert {row.task_id for row in app_rows} == {task_id}


@pytest.mark.asyncio
async def test_independent_coding_run_repairs_empty_model_application_response(
    monkeypatch,
):
    from sqlalchemy import select

    from app.models.code_application import CodeApplication
    from app.models.database import async_session, init_db
    from app.models.research_validity import EvidenceUnit
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-coding-repair-{suffix}"
    unit_id = f"eu-coding-repair-{suffix}"

    class RepairableCoderNode:
        """Selection-only coder node (see the dispatcher note above)."""

        node_id = "node-repair"
        name = "node-repair"
        source = "local"
        provider_type = "fake"
        is_healthy = True
        loaded_models = ["model-repair"]
        model_capabilities = {}

    class _StubAgentic:
        def __init__(self) -> None:
            self.calls = 0

        async def structured(self, **kwargs):  # noqa: ANN001
            from types import SimpleNamespace

            assert kwargs["project_id"] == project_id
            self.calls += 1
            if self.calls == 1:
                value = {"items": []}
            else:
                value = {
                    "code_applications": [
                        {
                            "stable_id": "repair-source#EU-0001",
                            "unit_index": 1,
                            "codes": ["repairable_coding_output"],
                            "quote": "Participant needs clearer prep guidance.",
                            "confidence": 0.72,
                            "rationale": "The evidence unit describes a guidance gap.",
                        }
                    ]
                }
            return SimpleNamespace(
                text=json.dumps(value),
                value=value,
                status="success",
                usage={},
                stop_reason="stop",
                endpoint_id="ep-stub",
                tool_calls=[],
            )

    stub = _StubAgentic()

    class FakeRouter:
        def _sorted_servers(self, **kwargs):  # noqa: ANN001
            assert kwargs["project_id"] == project_id
            return [RepairableCoderNode()]

    await init_db()
    monkeypatch.setattr(research_validity_service, "llm_router", FakeRouter())
    monkeypatch.setattr("app.core.agentic.agentic", stub)
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        research_validity_service, "_use_pi_coding_plane", AsyncMock(return_value=False)
    )

    async with async_session() as db:
        db.add(
            EvidenceUnit(
                id=unit_id,
                project_id=project_id,
                source_id="repair-source",
                stable_id="repair-source#EU-0001",
                unit_index=1,
                source_text="Participant needs clearer prep guidance.",
                source_location="repair-source:1",
            )
        )
        await db.commit()

        result = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            evidence_unit_ids=[unit_id],
            created_by="test-researcher",
        )

        app_rows = (
            (
                await db.execute(
                    select(CodeApplication).where(
                        CodeApplication.coding_run_id == result["id"]
                    )
                )
            )
            .scalars()
            .all()
        )

    assert stub.calls == 2
    assert result["code_application_count"] == 1
    assert len(app_rows) == 1
    assert app_rows[0].code_id == "repairable_coding_output"


@pytest.mark.asyncio
async def test_task_research_validity_gate_blocks_unreconciled_report_inputs():
    from app.models.code_application import CodeApplication
    from app.models.database import async_session, init_db
    from app.models.research_validity import CodingRun
    from app.services.research_validity_service import assess_task_research_validity

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-report-gate-{suffix}"
    task_id = f"task-report-gate-{suffix}"
    await init_db()

    async with async_session() as db:
        db.add(
            CodingRun(
                id=f"run-report-gate-{suffix}",
                project_id=project_id,
                task_id=task_id,
                status="completed",
                promotion_status="needs_reconciliation",
                fallback_reason="kappa below threshold",
            )
        )
        db.add(
            CodeApplication(
                id=f"ca-report-gate-{suffix}",
                project_id=project_id,
                task_id=task_id,
                code_id="trust-friction",
                promotion_status="needs_reconciliation",
            )
        )
        await db.commit()

        blocked = await assess_task_research_validity(
            db,
            project_id=project_id,
            task_id=task_id,
        )
        assert blocked["report_allowed"] is False
        assert "unreconciled code application" in blocked["reason"]

        run = await db.get(CodingRun, f"run-report-gate-{suffix}")
        app = await db.get(CodeApplication, f"ca-report-gate-{suffix}")
        run.promotion_status = "accepted"
        app.promotion_status = "accepted"
        await db.commit()

        allowed = await assess_task_research_validity(
            db,
            project_id=project_id,
            task_id=task_id,
        )
        assert allowed["report_allowed"] is True


@pytest.mark.asyncio
async def test_reconciliation_decisions_resolve_low_consensus_before_reports():
    from sqlalchemy import select

    from app.models.code_application import CodeApplication
    from app.models.database import async_session, init_db
    from app.models.research_validity import (
        CodingRun,
        ReconciliationDecision,
        ResearchEvidenceEdge,
    )
    from app.services.research_validity_service import (
        assess_task_research_validity,
        create_reconciliation_decision,
    )

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-reconcile-{suffix}"
    task_id = f"task-reconcile-{suffix}"
    run_id = f"run-reconcile-{suffix}"
    accept_id = f"ca-reconcile-accept-{suffix}"
    reject_id = f"ca-reconcile-reject-{suffix}"
    await init_db()

    async with async_session() as db:
        db.add(
            CodingRun(
                id=run_id,
                project_id=project_id,
                task_id=task_id,
                status="completed",
                promotion_status="needs_reconciliation",
                fallback_reason="kappa below threshold",
            )
        )
        for app_id, code_id in (
            (accept_id, "collaboration-friction"),
            (reject_id, "pricing-friction"),
        ):
            db.add(
                CodeApplication(
                    id=app_id,
                    project_id=project_id,
                    task_id=task_id,
                    coding_run_id=run_id,
                    evidence_unit_id=f"eu-{suffix}",
                    code_id=code_id,
                    route_id=f"route-{code_id}",
                    donor_id=f"donor-{code_id}",
                    route_evidence_json=json.dumps(
                        {"model": f"model-{code_id}", "outcome": "served"}
                    ),
                    promotion_status="needs_reconciliation",
                    reliability_status="needs_reconciliation",
                    reconciliation_status="unreconciled",
                )
            )
        await db.commit()

        blocked = await assess_task_research_validity(
            db, project_id=project_id, task_id=task_id
        )
        assert blocked["report_allowed"] is False
        assert blocked["unresolved_code_application_count"] == 2

        accepted_decision = await create_reconciliation_decision(
            db,
            project_id=project_id,
            code_application_id=accept_id,
            decision_type="accepted",
            decided_by="researcher-a",
            rationale="Source quote supports the collaboration code after human review.",
        )
        assert accepted_decision["code_application"]["promotion_status"] == "accepted"
        still_blocked = await assess_task_research_validity(
            db, project_id=project_id, task_id=task_id
        )
        assert still_blocked["report_allowed"] is False
        assert still_blocked["unresolved_code_application_count"] == 1

        rejected_decision = await create_reconciliation_decision(
            db,
            project_id=project_id,
            code_application_id=reject_id,
            decision_type="rejected",
            decided_by="researcher-a",
            rationale="The pricing interpretation is not grounded in this evidence unit.",
        )
        assert rejected_decision["code_application"]["promotion_status"] == "rejected"

        allowed = await assess_task_research_validity(
            db, project_id=project_id, task_id=task_id
        )
        assert allowed["report_allowed"] is True
        assert allowed["accepted_code_application_count"] == 1
        assert allowed["unresolved_code_application_count"] == 0

        run = await db.get(CodingRun, run_id)
        assert run.promotion_status == "accepted_after_reconciliation"
        decisions = (
            (
                await db.execute(
                    select(ReconciliationDecision).where(
                        ReconciliationDecision.coding_run_id == run_id
                    )
                )
            )
            .scalars()
            .all()
        )
        edges = (
            (
                await db.execute(
                    select(ResearchEvidenceEdge).where(
                        ResearchEvidenceEdge.coding_run_id == run_id,
                        ResearchEvidenceEdge.relation == "reconciled_by",
                    )
                )
            )
            .scalars()
            .all()
        )
    assert {decision.decision_type for decision in decisions} == {
        "accepted",
        "rejected",
    }
    assert len(edges) == 2


@pytest.mark.asyncio
async def test_evidence_graph_traceability_marks_report_low_agreement_dependencies(
    admin_auth_headers,
):
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.models.code_application import CodeApplication
    from app.models.database import async_session, init_db
    from app.models.finding import Fact, Insight, Nugget, Recommendation
    from app.models.project_report import ProjectReport
    from app.models.research_validity import (
        CodingRun,
        EvidenceUnit,
        ResearchEvidenceEdge,
    )
    from app.services.research_validity_service import (
        build_evidence_graph_traceability,
        create_reconciliation_decision,
    )

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-graph-trace-{suffix}"
    task_id = f"task-graph-trace-{suffix}"
    report_id = f"report-graph-trace-{suffix}"
    finding_id = f"rec-graph-trace-{suffix}"
    nugget_id, fact_id, insight_id = (
        f"nugget-graph-trace-{suffix}",
        f"fact-graph-trace-{suffix}",
        f"insight-graph-trace-{suffix}",
    )
    code_application_id, evidence_unit_id = (
        f"ca-graph-trace-{suffix}",
        f"eu-graph-trace-{suffix}",
    )
    run_id = f"run-graph-trace-{suffix}"
    await init_db()
    async with async_session() as db:
        db.add_all(
            [
                Nugget(
                    id=nugget_id,
                    project_id=project_id,
                    task_id=task_id,
                    text="I did not know how to invite my team.",
                    source="interview",
                ),
                Fact(
                    id=fact_id,
                    project_id=project_id,
                    task_id=task_id,
                    text="Participants miss the collaborator invite entry point.",
                    nugget_ids=json.dumps([nugget_id]),
                ),
                Insight(
                    id=insight_id,
                    project_id=project_id,
                    task_id=task_id,
                    text="Collaborator onboarding is blocked by unclear invite affordances.",
                    fact_ids=json.dumps([fact_id]),
                ),
                Recommendation(
                    id=finding_id,
                    project_id=project_id,
                    task_id=task_id,
                    text="Simplify collaborator invitations before onboarding launch.",
                    insight_ids=json.dumps([insight_id]),
                ),
            ]
        )
        db.add(
            ProjectReport(
                id=report_id,
                project_id=project_id,
                title="Onboarding Synthesis",
                layer=3,
                scope="onboarding",
                finding_ids_json=json.dumps([finding_id]),
            )
        )
        db.add(
            CodingRun(
                id=run_id,
                project_id=project_id,
                task_id=task_id,
                status="completed",
                promotion_status="needs_reconciliation",
                fallback_reason="kappa below threshold",
            )
        )
        db.add(
            CodeApplication(
                id=code_application_id,
                project_id=project_id,
                task_id=task_id,
                coding_run_id=run_id,
                evidence_unit_id=evidence_unit_id,
                code_id="collaboration-friction",
                source_text="I did not know how to invite my team.",
                promotion_status="needs_reconciliation",
                reliability_status="needs_reconciliation",
                reconciliation_status="unreconciled",
            )
        )
        db.add(
            EvidenceUnit(
                id=evidence_unit_id,
                project_id=project_id,
                task_id=task_id,
                source_id=f"task:{task_id}:nugget:{nugget_id}",
                stable_id=f"trace-unit:{evidence_unit_id}",
                unit_index=0,
                unit_type="source_span",
                source_type="test_fixture",
                method="interview",
                phase="discover",
                source_text="I did not know how to invite my team.",
            )
        )
        db.add(
            ResearchEvidenceEdge(
                id=f"edge-graph-trace-{suffix}",
                project_id=project_id,
                source_type="nugget",
                source_id=nugget_id,
                relation="grounded_in",
                target_type="evidence_unit",
                target_id=evidence_unit_id,
                evidence_unit_id=evidence_unit_id,
                task_id=task_id,
            )
        )
        await db.commit()

        trace = await build_evidence_graph_traceability(
            db,
            project_id=project_id,
            report_id=report_id,
        )
        assert trace["retrieval_mode"] == "graph+hybrid"
        assert trace["summary"]["blocked_report_count"] == 1
        assert trace["report_dependencies"][0]["low_agreement_dependency_count"] == 1
        assert trace["task_dependencies"][0]["report_gate"]["report_allowed"] is False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/research-validity/{project_id}/traceability",
            params={"report_id": report_id},
            headers=admin_auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["summary"]["blocked_report_count"] == 1

    async with async_session() as db:
        await create_reconciliation_decision(
            db,
            project_id=project_id,
            code_application_id=code_application_id,
            decision_type="accepted",
            decided_by="researcher-a",
            rationale="The report dependency is grounded after human reconciliation.",
        )
        resolved_trace = await build_evidence_graph_traceability(
            db,
            project_id=project_id,
            report_id=report_id,
        )
    assert resolved_trace["summary"]["blocked_report_count"] == 0
    assert (
        resolved_trace["report_dependencies"][0]["report_allowed_by_research_validity"]
        is True
    )
    assert resolved_trace["reconciliation_decisions"][0]["decision_type"] == "accepted"


@pytest.mark.asyncio
async def test_evidence_graph_traceability_fails_closed_without_task_gate():
    from app.models.database import async_session, init_db
    from app.models.finding import Recommendation
    from app.models.project_report import ProjectReport
    from app.services.research_validity_service import build_evidence_graph_traceability

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-graph-missing-gate-{suffix}"
    report_id = f"report-graph-missing-gate-{suffix}"
    finding_id = f"rec-graph-missing-gate-{suffix}"

    await init_db()
    async with async_session() as db:
        db.add(
            Recommendation(
                id=finding_id,
                project_id=project_id,
                text="Legacy recommendation with no Done task evidence.",
            )
        )
        db.add(
            ProjectReport(
                id=report_id,
                project_id=project_id,
                title="Legacy Ungated Report",
                layer=3,
                scope="legacy",
                finding_ids_json=json.dumps([finding_id]),
            )
        )
        await db.commit()

        trace = await build_evidence_graph_traceability(
            db,
            project_id=project_id,
            report_id=report_id,
        )

    assert trace["report_dependencies"][0]["task_ids"] == []
    assert (
        trace["report_dependencies"][0]["report_allowed_by_research_validity"] is False
    )
    assert trace["summary"]["blocked_report_count"] == 1


@pytest.mark.asyncio
async def test_report_promotion_gate_records_research_validity_telemetry():
    from sqlalchemy import select

    from app.core.report_manager import ReportManager
    from app.core.telemetry import telemetry_recorder
    from app.models.code_application import CodeApplication
    from app.models.database import async_session, init_db
    from app.models.finding import Nugget
    from app.models.project_report import ProjectReport
    from app.models.research_validity import EvidenceUnit, ResearchEvidenceEdge
    from app.models.task import Task, TaskStatus

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-report-telemetry-{suffix}"
    task_id = f"task-report-telemetry-{suffix}"
    nugget_id = f"nugget-report-telemetry-{suffix}"
    manager = ReportManager()
    await init_db()

    async with async_session() as db:
        db.add(
            Task(
                id=task_id,
                project_id=project_id,
                title="Review onboarding evidence",
                skill_name="user-interviews",
                status=TaskStatus.IN_REVIEW,
                review_state="awaiting_review",
            )
        )
        db.add(
            Nugget(
                id=nugget_id,
                project_id=project_id,
                task_id=task_id,
                text="Participant could not find the invite flow.",
                source="interview",
            )
        )
        await db.commit()

        await manager.route_findings(project_id, "user-interviews", [nugget_id], db)
        reports = (
            (
                await db.execute(
                    select(ProjectReport).where(ProjectReport.project_id == project_id)
                )
            )
            .scalars()
            .all()
        )
        assert reports == []

        blocked_audit = await telemetry_recorder.get_research_validity_audit(project_id)
        assert blocked_audit["operation_counts"]["report.promotion_gate"] >= 1
        assert blocked_audit["operation_counts"].get("finding.promotion", 0) == 0
        assert blocked_audit["status_counts"]["degraded"] >= 1

        task = await db.get(Task, task_id)
        task.status = TaskStatus.DONE
        task.review_state = "approved"
        await db.commit()

        routed_count = await manager.route_approved_task_findings(
            project_id,
            task_id,
            "user-interviews",
            db,
        )
        assert routed_count == 0

        evidence_unit_id = f"eu-report-telemetry-{suffix}"
        db.add(
            EvidenceUnit(
                id=evidence_unit_id,
                project_id=project_id,
                task_id=task_id,
                source_id=f"task:{task_id}:nugget:{nugget_id}",
                stable_id=f"report-unit:{evidence_unit_id}",
                unit_index=0,
                unit_type="source_span",
                source_type="test_fixture",
                method="interview",
                phase="discover",
                source_text="Participant could not find the invite flow.",
            )
        )
        db.add(
            ResearchEvidenceEdge(
                id=f"edge-report-telemetry-{suffix}",
                project_id=project_id,
                source_type="nugget",
                source_id=nugget_id,
                relation="grounded_in",
                target_type="evidence_unit",
                target_id=evidence_unit_id,
                evidence_unit_id=evidence_unit_id,
                task_id=task_id,
            )
        )
        db.add(
            CodeApplication(
                id=f"ca-report-telemetry-{suffix}",
                project_id=project_id,
                task_id=task_id,
                code_id="invite-flow-friction",
                evidence_unit_id=evidence_unit_id,
                source_text="Participant could not find the invite flow.",
                promotion_status="accepted",
                reliability_status="accepted",
                reconciliation_status="accepted",
            )
        )
        await db.commit()

        routed_count = await manager.route_approved_task_findings(
            project_id,
            task_id,
            "user-interviews",
            db,
        )
        assert routed_count == 1

        allowed_audit = await telemetry_recorder.get_research_validity_audit(project_id)
        assert allowed_audit["operation_counts"]["report.promotion_gate"] >= 2
        assert allowed_audit["operation_counts"]["finding.promotion"] >= 1
        assert allowed_audit["status_counts"]["success"] >= 1
