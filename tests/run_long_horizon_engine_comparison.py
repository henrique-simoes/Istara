"""Grand Long-Horizon Comparative Harness: Pi Agentic Engine vs. Istara Legacy Engine.

Inspired by Scenario 76, this script executes an exhaustive 8-phase simulated user research
trajectory on both:
  Engine A: Pi Agentic Engine (agentic_engine="pi")
  Engine B: Istara Legacy ReAct Engine (agentic_engine="legacy")

Research Lifecycle Tested:
  1. Multi-Source Ingestion & Task Decomposition
  2. Skill Catalog Discovery & Task Creation
  3. Active Codebook Consultation ("What's in the codebook now?")
  4. Mid-Turn Dynamic Steering & Survey Integration Querying
  5. Multi-Source Sharon Atomic DAG Promotion (Quote -> Nugget -> Fact -> Insight -> Rec)
  6. Task Review & Human Done Approval Gate (HTTP 409 guard)
  7. Barbara Minto SCQA Report Synthesis (100% MECE categories)
  8. Full Comparative Observability & Telemetry Scorecard
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure repo and backend are on path
REPO_ROOT = Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name in ("tests", "scratch") else Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.api.routes.tasks import _approve_task
from app.config import settings
from app.core.agent import AgentOrchestrator
from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import TurnParams, TurnResult
from app.core.report_manager import ReportManager
from app.core.research_validity import segment_evidence_units
from app.core.steering import steering_manager
from app.core.task_review import record_review_side_effects
from app.core.telemetry import telemetry_recorder
from app.models.code_application import CodeApplication
from app.models.codebook import Code, Codebook
from app.models.codebook_version import CodebookVersion
from app.models.database import async_session, init_db
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.message import Message
from app.models.project import Project
from app.models.project_report import ProjectReport
from app.models.research_validity import (
    CodingRun,
    CodingRunCoder,
    EvidenceUnit,
    ReconciliationDecision,
    ResearchEvidenceEdge,
)
from app.models.survey_integration import SurveyIntegration, SurveyLink
from app.models.task import Task, TaskStatus
from app.services import research_validity_service
from app.services.survey_ingestion import ingest_responses
from app.skills.base import SkillOutput
from app.skills.registry import load_default_skills, registry
from app.skills.system_actions import OPENAI_TOOLS, execute_tool
from sqlalchemy import select

logger = logging.getLogger("comparison_harness")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@dataclass
class TurnTelemetry:
    turn_index: int
    prompt: str
    engine: str
    status: str
    duration_s: float
    text: str
    tool_calls_count: int
    tools_invoked: list[str] = field(default_factory=list)
    tool_latencies_ms: list[float] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    error: str | None = None


@dataclass
class EngineBenchmarkResult:
    engine: str
    project_id: str
    task_id: str
    turns: list[TurnTelemetry] = field(default_factory=list)
    total_duration_s: float = 0.0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_cost_usd: float = 0.0
    tool_calls_total: int = 0
    tool_latencies: list[float] = field(default_factory=list)
    tool_errors: int = 0
    dag_nuggets: int = 0
    dag_facts: int = 0
    dag_insights: int = 0
    dag_recs: int = 0
    dag_edges: int = 0
    report_id: str = ""
    report_title: str = ""
    report_allowed: bool = False
    evidence_edge_count: int = 0
    intel_leaderboard: list[dict] = field(default_factory=list)
    quality_ema: float = 0.0


async def seed_project_assets(project_id: str, suffix: str) -> dict[str, str]:
    """Seed identical multi-modal research assets into the project."""
    async with async_session() as db:
        # 1. Project
        project = Project(
            id=project_id,
            name=f"CareNav Benchmark ({project_id})",
            description="Comparative Long-Horizon Evaluation of Istara Agentic Engines",
            agentic_engine="pi" if "pi" in project_id else "legacy",
            project_context="CareNav: Automated patient appointment readiness and caregiver access control platform.",
        )
        db.add(project)

        # 2. Canonical Documents
        # Document 1: Interview
        interview_text = (
            "# CareNav Patient & Caregiver Interview Transcript\n\n"
            "Participant: P-401 (Caregiver for elderly parent with congestive heart failure)\n"
            "Interviewer: Dr. Evelyn Vance\n\n"
            "Q: Can you describe your experience when your mother's readiness status changed unexpectedly?\n"
            "A: The queue is useful only when the source trail is visible before the status is accepted. "
            "Last week the system showed 'Cleared for Outpatient' but didn't link to the cardiologist's lab notes. "
            "We were left wondering whether the INR blood test had actually come through.\n\n"
            "Q: How do you feel about the caregiver access permissions?\n"
            "A: Caregiver access has to say exactly what is shared and what stays private. "
            "My mother wants me to manage her appointment logistics and medication schedule, but she does not "
            "want me reading her psychiatric counseling notes. If there is no clear boundary, she refuses to use the app.\n\n"
            "Q: What is the most critical feature the reporting layer should provide to clinicians?\n"
            "A: The report should keep the evidence path, not just the final recommendation. "
            "Physicians don't trust an AI summary that doesn't let them click straight to the patient quote or lab span."
        )
        doc_interview = Document(
            id=f"doc-carenav-interview-{suffix}",
            project_id=project_id,
            title="CR-001 CareNav Patient & Caregiver Interview",
            phase="discover",
            source=DocumentSource.USER_UPLOAD,
            status=DocumentStatus.READY,
            version=1,
            content_text=interview_text,
            content_preview=interview_text[:300],
            tags=json.dumps(["interview", "caregiver", "privacy", "transparency"]),
        )

        # Document 2: Competitor Benchmark
        benchmark_text = (
            "# CareNav Competitor Benchmark: Epic MyChart vs. Cerner HealtheLife\n\n"
            "1. Auditability: Epic provides an audit ledger but buries it behind 4 menu levels. "
            "Patients cannot verify automated triage flags without clinical administration intervention.\n\n"
            "2. Proxy Access: Neither competitor allows fine-grained role-based redaction for family caregivers. "
            "It is all-or-nothing: either full proxy access to all clinical records, or none.\n\n"
            "3. Recommendation Grounding: Competitor clinical alerts lack direct citation spans to raw source notes."
        )
        doc_benchmark = Document(
            id=f"doc-carenav-benchmark-{suffix}",
            project_id=project_id,
            title="CR-002 Competitor Benchmark Epic vs Cerner",
            phase="discover",
            source=DocumentSource.USER_UPLOAD,
            status=DocumentStatus.READY,
            version=1,
            content_text=benchmark_text,
            content_preview=benchmark_text[:300],
            tags=json.dumps(["competitive", "benchmark", "epic", "cerner"]),
        )

        # Document 3: Active Codebook Document
        codebook_doc_text = (
            "# CareNav Qualitative Codebook v1.0\n\n"
            "### Code: caregiver-privacy\n"
            "- Definition: Boundaries and controls governing caregiver access to patient health data.\n"
            "- Inclusion Criteria: Mentions of proxy access, shared vs private records, redaction, psychiatric notes separation.\n"
            "- Exclusion Criteria: General login issues or password resets.\n\n"
            "### Code: audit-trail-visibility\n"
            "- Definition: Requirement that status transitions display verifiable evidence trails.\n"
            "- Inclusion Criteria: Mentions of queue verification, source trail, audit logs, clinician lab note links.\n"
            "- Exclusion Criteria: Speed or UI color preferences.\n\n"
            "### Code: clinical-oversight\n"
            "- Definition: Physician verification protocols and clinical trust mechanisms.\n"
            "- Inclusion Criteria: Clinician review of AI recommendations, evidence path requirement for physicians.\n"
            "- Exclusion Criteria: Non-clinical administrative workflows."
        )
        doc_codebook = Document(
            id=f"doc-carenav-codebook-{suffix}",
            project_id=project_id,
            title="CareNav Active Codebook v1.0",
            phase="define",
            source=DocumentSource.PROJECT_FILE,
            status=DocumentStatus.READY,
            version=1,
            content_text=codebook_doc_text,
            content_preview=codebook_doc_text[:300],
            tags=json.dumps(["codebook", "qualitative", "definitions"]),
        )

        db.add_all([doc_interview, doc_benchmark, doc_codebook])

        # 3. Persistent Codebook Model & Codes
        codebook = Codebook(
            id=f"cb-{suffix}",
            project_id=project_id,
            name="CareNav Qualitative Codebook v1.0",
            version=1,
            description="Governed codebook for patient & caregiver transparency research",
            approach="inductive",
            status="in_use",
        )
        code1 = Code(
            id=f"code-{suffix}-1",
            codebook_id=codebook.id,
            name="caregiver-privacy",
            definition="Boundaries and controls governing caregiver access to patient health data.",
            inclusion_criteria="Mentions of proxy access, shared vs private records, redaction.",
            exclusion_criteria="General login issues.",
            code_type="descriptive",
        )
        code2 = Code(
            id=f"code-{suffix}-2",
            codebook_id=codebook.id,
            name="audit-trail-visibility",
            definition="Requirement that status transitions display verifiable evidence trails.",
            inclusion_criteria="Mentions of queue verification, source trail, audit logs.",
            exclusion_criteria="Speed or UI color preferences.",
            code_type="descriptive",
        )
        code3 = Code(
            id=f"code-{suffix}-3",
            codebook_id=codebook.id,
            name="clinical-oversight",
            definition="Physician verification protocols and clinical trust mechanisms.",
            inclusion_criteria="Clinician review of AI recommendations, evidence path requirement.",
            exclusion_criteria="Administrative workflows.",
            code_type="descriptive",
        )
        db.add(codebook)
        db.add_all([code1, code2, code3])

        # CodebookVersion for Research Spine
        cb_ver = CodebookVersion(
            id=f"cb-ver-{suffix}",
            project_id=project_id,
            version="1.0.0",
            created_by="cleo-orchestrator",
            change_log="Initial CareNav qualitative codebook version",
            methodology="codebook_ta",
            codes_json=json.dumps([c.to_dict() for c in [code1, code2, code3]]),
        )
        db.add(cb_ver)

        # 4. Survey Integration & Link with 10 Responses
        survey_int = SurveyIntegration(
            id=f"survey-int-{suffix}",
            platform="typeform",
            name="CareNav Patient & Caregiver Survey Platform",
            project_id=project_id,
            is_active=True,
        )
        survey_link = SurveyLink(
            id=f"survey-link-{suffix}",
            integration_id=survey_int.id,
            project_id=project_id,
            external_survey_id=f"carenav-survey-{suffix}",
            external_survey_name="Patient & Caregiver Experience Survey 2026",
            response_count=0,
        )
        db.add(survey_int)
        db.add(survey_link)
        await db.commit()

        # Seed 10 normalized survey responses
        simulated_survey_responses = [
            {
                "id": f"resp-{suffix}-01",
                "answers": [
                    {
                        "question": "How important is seeing the raw clinical note behind an appointment status?",
                        "answer": "Extremely important. I will not trust a green status badge without seeing the doctor's verified note.",
                    },
                    {
                        "question": "What is your biggest concern with family caregiver proxy access?",
                        "answer": "Privacy leaks. My son helps with my prescriptions, but my behavioral health records must remain completely private.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-02",
                "answers": [
                    {
                        "question": "How important is seeing the raw clinical note behind an appointment status?",
                        "answer": "Vital. When appointments are canceled or cleared automatically, we need the exact reason.",
                    },
                    {
                        "question": "What is your biggest concern with family caregiver proxy access?",
                        "answer": "Granular control. Caregivers need a checklist view without seeing all sensitive clinical history.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-03",
                "answers": [
                    {
                        "question": "How important is seeing the raw clinical note behind an appointment status?",
                        "answer": "Necessary for patient safety. Automated queues make mistakes without audit trails.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-04",
                "answers": [
                    {
                        "question": "What is your biggest concern with family caregiver proxy access?",
                        "answer": "Clear boundaries. Caregiver access must state explicitly what is shared and what stays private.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-05",
                "answers": [
                    {
                        "question": "How important is seeing the raw clinical note behind an appointment status?",
                        "answer": "The evidence path should be visible right on the appointment card.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-06",
                "answers": [
                    {
                        "question": "What is your biggest concern with family caregiver proxy access?",
                        "answer": "Role-based permissions are needed for elderly patients and adult children caregivers.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-07",
                "answers": [
                    {
                        "question": "How important is seeing the raw clinical note behind an appointment status?",
                        "answer": "Physicians and patients alike need direct links to original clinical records.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-08",
                "answers": [
                    {
                        "question": "What is your biggest concern with family caregiver proxy access?",
                        "answer": "Accidental exposure of confidential counseling notes to family members.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-09",
                "answers": [
                    {
                        "question": "How important is seeing the raw clinical note behind an appointment status?",
                        "answer": "Status changes must be backed by an immutable audit trail.",
                    },
                ],
            },
            {
                "id": f"resp-{suffix}-10",
                "answers": [
                    {
                        "question": "What is your biggest concern with family caregiver proxy access?",
                        "answer": "Caregiver proxy permissions should be editable per document type.",
                    },
                ],
            },
        ]

        survey_ingest_result = await ingest_responses(
            db, survey_link, simulated_survey_responses, project_id
        )
        logger.info(
            f"[{project_id}] Seeded survey: {survey_ingest_result.get('nuggets_created')} nuggets, "
            f"{survey_ingest_result.get('evidence_units_created')} evidence units from 10 responses."
        )

    return {
        "project_id": project_id,
        "interview_doc_id": doc_interview.id,
        "benchmark_doc_id": doc_benchmark.id,
        "codebook_doc_id": doc_codebook.id,
        "codebook_id": codebook.id,
        "codebook_version_id": cb_ver.id,
        "survey_link_id": survey_link.id,
    }


async def run_trajectory_for_engine(
    engine: str,
    endpoint_id: str = "pi-dashscope-qwen",
    model_name: str = "qwen3.7-max-2026-06-08",
) -> EngineBenchmarkResult:
    """Run the complete 8-phase research trajectory for a specified agentic engine."""
    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-comp-{engine}-{suffix}"
    agent_id = "cleo-orchestrator"
    session_id = f"session-{engine}-{suffix}"
    session_key = f"{project_id}:{session_id}"

    print("\n" + "=" * 80)
    print(f"STARTING COMPREHENSIVE BENCHMARK: ENGINE '{engine.upper()}'")
    print(f"  Project ID: {project_id}")
    print(f"  Endpoint: {endpoint_id} ({model_name})")
    print("=" * 80)

    # 1. Seed Assets
    print(f"\n[{engine.upper()} Phase 1/8] Seeding Canonical Research Corpus, Codebook & Survey Data...")
    assets = await seed_project_assets(project_id, suffix)

    dispatcher = AgenticDispatcher()
    messages_history: list[dict[str, Any]] = []
    turns_telemetry: list[TurnTelemetry] = []
    active_task_id: str | None = None

    tool_latencies: list[float] = []
    tool_calls_total = 0
    tool_errors_total = 0

    async def tool_executor_wrapper(name: str, params: dict[str, Any], proj_id: str, ag_id: str) -> dict[str, Any]:
        nonlocal tool_calls_total, tool_errors_total
        t_start = time.perf_counter()
        tool_calls_total += 1
        print(f"    -> [{engine.upper()} Tool Invocation #{tool_calls_total}] {name}({params})")
        try:
            res = await execute_tool(
                tool_name=name,
                params=params,
                project_id=proj_id,
                agent_id=ag_id,
            )
        except Exception as exc:
            import traceback
            print(f"       [CRITICAL: execute_tool raised {type(exc).__name__}: {exc}]")
            traceback.print_exc()
            raise
        duration_ms = (time.perf_counter() - t_start) * 1000.0
        tool_latencies.append(duration_ms)
        is_err = "error" in res or res.get("success") is False
        if is_err:
            tool_errors_total += 1
            print(f"       [Tool Error ({duration_ms:.1f}ms)]: {res.get('error')}")
        else:
            print(f"       [Tool Success ({duration_ms:.1f}ms)]")
        return res

    # Helper for driving a conversational turn
    async def drive_turn(turn_idx: int, user_prompt: str, steering_action: str | None = None) -> TurnResult:
        t0 = time.perf_counter()
        print(f"\n[{engine.upper()} Turn {turn_idx}] User: \"{user_prompt}\"")

        # Inject mid-turn steering if requested
        if steering_action:
            print(f"  [Steering Event Injected]: \"{steering_action}\"")
            await steering_manager.steer(agent_id, steering_action, project_id=project_id)

        system_prompt = (
            "You are Cleo, Istara's expert lead UX Researcher and Research Spine orchestrator. "
            "You follow the Sharon Atomic Research framework and Barbara Minto's Pyramid Principle. "
            "Use native tools when requested to list tasks, inspect documents, consult findings, "
            "or manage research work. When users ask what is in the codebook, consult the codebook documents "
            "or search findings to provide the active qualitative codes."
        )

        turn_tools_invoked: list[str] = []
        turn_tool_latencies: list[float] = []

        async def tracked_tool_executor(name, params, p_id, a_id):
            turn_tools_invoked.append(name)
            t_sub = time.perf_counter()
            r = await tool_executor_wrapper(name, params, p_id, a_id)
            turn_tool_latencies.append((time.perf_counter() - t_sub) * 1000.0)
            return r

        result = await dispatcher.chat_turn(
            project_id=project_id,
            agent_id=agent_id,
            session_key=session_key,
            session_id=session_id,
            system_prompt=system_prompt,
            messages=list(messages_history),
            user_text=user_prompt,
            tool_executor=tracked_tool_executor,
            tool_names=[t["function"]["name"] for t in OPENAI_TOOLS],
            tools=OPENAI_TOOLS,
            params=TurnParams(
                model=model_name,
                endpoint_id=endpoint_id,
                temperature=0.0,
                max_tokens=1000,
            ),
            engine=engine,
        )

        dur_s = time.perf_counter() - t0
        cost = result.usage.get("cost_usd", 0.0) or 0.0

        print(f"  [{engine.upper()} Turn {turn_idx} Result ({dur_s:.2f}s)]: status={result.status}, "
              f"tools={len(turn_tools_invoked)}, tokens={result.usage.get('total_tokens', 0)}")
        print(f"  Assistant: {result.text[:220]}...")

        # Update message history
        messages_history.append({"role": "user", "content": user_prompt})
        messages_history.append({"role": "assistant", "content": result.text})

        # Record telemetry
        turn_tel = TurnTelemetry(
            turn_index=turn_idx,
            prompt=user_prompt,
            engine=engine,
            status=result.status,
            duration_s=dur_s,
            text=result.text,
            tool_calls_count=len(turn_tools_invoked),
            tools_invoked=turn_tools_invoked,
            tool_latencies_ms=turn_tool_latencies,
            usage=result.usage,
            cost_usd=cost,
            error=result.usage.get("error"),
        )
        turns_telemetry.append(turn_tel)
        return result

    # ── TURN 1: Project Framing & Document Discovery ──
    t1_res = await drive_turn(
        1,
        "Hello Cleo. We are beginning research on appointment readiness and caregiver access control. "
        "Please search and list what documents we currently have available in this project.",
    )

    # ── TURN 2: Skill Catalog Discovery & Task Creation ──
    t2_res = await drive_turn(
        2,
        "We need to thoroughly analyze the CareNav patient and caregiver interview. "
        "Please create a research task titled 'CareNav Qualitative Interview Analysis' "
        "with skill 'user-interviews' and priority 'high'.",
    )

    # Retrieve created task ID from database
    async with async_session() as db:
        tasks = (
            (await db.execute(select(Task).where(Task.project_id == project_id)))
            .scalars()
            .all()
        )
        assert tasks, "Expected a created Task in project"
        active_task_id = tasks[0].id
        print(f"  [Verified DB Task]: ID={active_task_id}, Title='{tasks[0].title}', Skill='{tasks[0].skill_name}'")

    # ── TURN 3: Active Codebook Probe ──
    # User asks: "what's in the codebook now?"
    t3_res = await drive_turn(
        3,
        "Before we proceed to qualitative coding, what's in the codebook now? "
        "Search the project documents to list the exact qualitative codes, definitions, and inclusion criteria.",
    )

    # ── TURN 4: Survey Findings & Dynamic Mid-Turn Steering ──
    t4_res = await drive_turn(
        4,
        "Let's check the current findings in this project.",
        steering_action="Wait, before finalizing... what do survey responses say? Check survey findings for patient and caregiver sentiment.",
    )

    # ── TURN 5: Multi-Source Evidence Segmentation & Atomic DAG Elevation ──
    print(f"\n[{engine.upper()} Phase 5/8] Elevating Multi-Source Evidence into Sharon Atomic Research DAG...")
    canonical_quotes = [
        "The queue is useful only when the source trail is visible before the status is accepted.",
        "Caregiver access has to say exactly what is shared and what stays private.",
        "The report should keep the evidence path, not just the final recommendation.",
    ]

    async with async_session() as db:
        # Segment and persist source Evidence Units for the interview
        eu_drafts = []
        unit_ids = []
        for idx, quote in enumerate(canonical_quotes, 1):
            uid = f"eu-{engine}-{suffix}-{idx}"
            unit_ids.append(uid)
            eu_drafts.append(
                EvidenceUnit(
                    id=uid,
                    project_id=project_id,
                    task_id=active_task_id,
                    source_id=assets["interview_doc_id"],
                    source_document_id=assets["interview_doc_id"],
                    stable_id=f"{assets['interview_doc_id']}#EU-{idx:04d}",
                    unit_index=idx,
                    source_text=quote,
                    source_location=f"document:{assets['interview_doc_id']}:section:{idx}",
                    unit_type="source_span",
                )
            )
        db.add_all(eu_drafts)
        await db.commit()

        # Execute 3-Model Independent Qualitative Coding Run
        coding_run = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            task_id=active_task_id,
            evidence_unit_ids=unit_ids,
            created_by="cleo-orchestrator",
        )
        print(f"  Coding Run ID: {coding_run.get('id')}, κ: {coding_run.get('kappa')}, α: {coding_run.get('alpha')}")

        # Reconcile Code Applications
        apps = (
            (await db.execute(select(CodeApplication).where(CodeApplication.coding_run_id == coding_run["id"])))
            .scalars()
            .all()
        )
        for app in apps:
            await research_validity_service.create_reconciliation_decision(
                db,
                project_id=project_id,
                code_application_id=app.id,
                decision_type="accepted",
                decided_by="human-researcher",
                rationale="Grounded in verbatim CareNav interview source span.",
                source="human_review",
            )
        await db.commit()

        # Sharon Atomic DAG Elevation: Quote -> Nugget -> Fact -> Insight -> Recommendation
        task_row = await db.get(Task, active_task_id)
        skill_out = SkillOutput(
            success=True,
            summary=f"CareNav Evidence Synthesis ({engine.upper()})",
            nuggets=[
                {
                    "text": canonical_quotes[0],
                    "source": "interview",
                    "source_document_id": assets["interview_doc_id"],
                    "source_location": f"document:{assets['interview_doc_id']}:section:1",
                    "source_text": canonical_quotes[0],
                },
                {
                    "text": canonical_quotes[1],
                    "source": "interview",
                    "source_document_id": assets["interview_doc_id"],
                    "source_location": f"document:{assets['interview_doc_id']}:section:2",
                    "source_text": canonical_quotes[1],
                },
                {
                    "text": canonical_quotes[2],
                    "source": "interview",
                    "source_document_id": assets["interview_doc_id"],
                    "source_location": f"document:{assets['interview_doc_id']}:section:3",
                    "source_text": canonical_quotes[2],
                },
            ],
            facts=[
                {"text": "Caregivers require explicit visibility into shared versus private health records."},
                {"text": "Patients distrust status transitions when the underlying evidence audit trail is obscured."},
            ],
            insights=[
                {"text": "Trust in automated care navigation depends directly on bidirectional source traceability."}
            ],
            recommendations=[
                {"text": "Implement an end-to-end evidence ledger for all appointment readiness status changes."}
            ],
        )
        orchestrator = AgentOrchestrator()
        await orchestrator._store_findings(db, project_id, skill_out, task_row)
        await db.commit()

        # Count DAG nodes
        nuggets_count = len((await db.execute(select(Nugget).where(Nugget.project_id == project_id))).scalars().all())
        facts_count = len((await db.execute(select(Fact).where(Fact.project_id == project_id))).scalars().all())
        insights_count = len((await db.execute(select(Insight).where(Insight.project_id == project_id))).scalars().all())
        recs_count = len((await db.execute(select(Recommendation).where(Recommendation.project_id == project_id))).scalars().all())
        edges_count = len((await db.execute(select(ResearchEvidenceEdge).where(ResearchEvidenceEdge.project_id == project_id))).scalars().all())
        print(f"  DAG Summary: {nuggets_count} Nuggets, {facts_count} Facts, {insights_count} Insights, {recs_count} Recs, {edges_count} Edges")

    # ── TURN 6: Task Review & Human Done Gate ──
    print(f"\n[{engine.upper()} Phase 6/8] Human Task Review & Research-Validity Done Gate...")
    t6_res = await drive_turn(
        6,
        f"Move task '{active_task_id}' to in_review so it can undergo human verification.",
    )

    # Verify agent cannot move task directly to Done
    illegal_done_attempt = await execute_tool(
        "move_task",
        {"task_id": active_task_id, "status": "done"},
        project_id,
        agent_id,
    )
    print(f"  [HTTP 409 Guard Verification]: {illegal_done_attempt.get('result') or illegal_done_attempt.get('error')}")

    # Formal Human Review Approval
    async with async_session() as db:
        from app.services.research_validity_reconciliation import _is_unresolved_code_application
        task_code_rows = (
            (await db.execute(
                select(CodeApplication).where(
                    CodeApplication.project_id == project_id,
                    CodeApplication.task_id == active_task_id,
                )
            ))
            .scalars()
            .all()
        )
        unresolved = [row for row in task_code_rows if _is_unresolved_code_application(row)]
        if unresolved:
            print(f"  Human Reconciliation: Reconciling {len(unresolved)} remaining code application(s)...")
            for app in unresolved:
                await research_validity_service.create_reconciliation_decision(
                    db,
                    project_id=project_id,
                    code_application_id=app.id,
                    decision_type="accepted",
                    decided_by="human-researcher",
                    rationale=f"Human reviewer accepted grounded CareNav evidence ({engine.upper()}).",
                    source="human_review",
                )
            await db.commit()

        task_row = await db.get(Task, active_task_id)
        review_event = await _approve_task(
            db,
            task_row,
            reviewed_by="human-researcher",
            note=f"Grounded in CareNav corpus and 10-response survey data ({engine.upper()}).",
        )
        await db.commit()
        await record_review_side_effects(review_event)
        await db.refresh(task_row)
        print(f"  [Human Approval Outcome]: {review_event.outcome}, Status: {task_row.status.value}")

    # ── TURN 7: Barbara Minto SCQA Report Synthesis ──
    print(f"\n[{engine.upper()} Phase 7/8] Barbara Minto SCQA Strategic Report Synthesis...")
    async with async_session() as db:
        task_row = await db.get(Task, active_task_id)
        report_mgr = ReportManager()
        routed_count = await report_mgr.route_approved_task_findings(
            project_id,
            active_task_id,
            task_row.skill_name,
            db,
        )
        print(f"  Routed {routed_count} validated findings to ProjectReport.")

        reports = (await db.execute(select(ProjectReport).where(ProjectReport.project_id == project_id))).scalars().all()
        assert reports, "Expected synthesized ProjectReport"
        active_report = reports[0]
        print(f"  Report Generated: ID={active_report.id}, Title='{active_report.title}'")

        trace = await research_validity_service.build_evidence_graph_traceability(
            db,
            project_id=project_id,
            report_id=active_report.id,
        )
        rep_dep = trace["report_dependencies"][0]
        report_allowed = rep_dep["report_allowed_by_research_validity"]
        edge_count = trace["summary"]["evidence_graph_edge_count"]
        print(f"  Evidence Traceability: Allowed={report_allowed}, Edges={edge_count}")

    # ── TURN 8: Trajectory Summary from Assistant ──
    t8_res = await drive_turn(
        8,
        "Summarize our completed research trajectory, highlighting how the interview quotes, "
        "survey findings, and codebook governed our recommendations.",
    )

    # ── Observability & Telemetry Audit ──
    print(f"\n[{engine.upper()} Phase 8/8] Collecting Centralized Model Intelligence & OpenTelemetry Spans...")
    intel = await telemetry_recorder.get_model_intelligence(project_id)
    leaderboard = intel.get("leaderboard", [])
    model_ema = 0.0
    for entry in leaderboard:
        if entry.get("model") == model_name:
            model_ema = entry.get("quality_ema", 0.0)

    # Compute aggregates
    total_dur = sum(t.duration_s for t in turns_telemetry)
    tot_tokens = sum(t.usage.get("total_tokens", 0) for t in turns_telemetry)
    in_tokens = sum(t.usage.get("input_tokens", 0) for t in turns_telemetry)
    out_tokens = sum(t.usage.get("output_tokens", 0) for t in turns_telemetry)
    cache_tokens = sum(t.usage.get("cache_read", 0) for t in turns_telemetry)
    cost_total = sum(t.cost_usd for t in turns_telemetry)

    benchmark_res = EngineBenchmarkResult(
        engine=engine,
        project_id=project_id,
        task_id=active_task_id,
        turns=turns_telemetry,
        total_duration_s=total_dur,
        total_tokens=tot_tokens,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        cached_tokens=cache_tokens,
        total_cost_usd=cost_total,
        tool_calls_total=tool_calls_total,
        tool_latencies=tool_latencies,
        tool_errors=tool_errors_total,
        dag_nuggets=nuggets_count,
        dag_facts=facts_count,
        dag_insights=insights_count,
        dag_recs=recs_count,
        dag_edges=edges_count,
        report_id=active_report.id,
        report_title=active_report.title,
        report_allowed=report_allowed,
        evidence_edge_count=edge_count,
        intel_leaderboard=leaderboard,
        quality_ema=model_ema,
    )

    print(f"\nCOMPLETED BENCHMARK FOR {engine.upper()}:")
    print(f"  Total Duration: {total_dur:.2f}s across {len(turns_telemetry)} turns")
    print(f"  Tool Invocations: {tool_calls_total} (Errors: {tool_errors_total})")
    print(f"  Tokens: {tot_tokens} (In: {in_tokens}, Out: {out_tokens}, Cached: {cache_tokens})")
    print(f"  Cost: ${cost_total:.6f} USD")
    print(f"  Report: '{active_report.title}' (Allowed: {report_allowed})")

    return benchmark_res


async def main() -> None:
    print("=" * 80)
    print("GRAND LONG-HORIZON COMPARATIVE HARNESS: PI VS. ISTARA LEGACY")
    print("=" * 80)

    load_default_skills()
    await init_db()

    target_engine = "all"
    for arg in sys.argv[1:]:
        if arg.startswith("--engine="):
            target_engine = arg.split("=", 1)[1].strip().lower()

    output_arg = next((arg.split("=", 1)[1] for arg in sys.argv[1:] if arg.startswith("--output=")), None)
    if output_arg:
        output_path = Path(output_arg)
    else:
        output_path = REPO_ROOT / "comparison_results.json"

    # Load existing results if present
    existing_payload = {}
    if output_path.exists():
        try:
            existing_payload = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            existing_payload = {}

    pi_result = None
    legacy_result = None

    if target_engine in ("all", "pi"):
        pi_result = await run_trajectory_for_engine("pi")

    if target_engine in ("all", "legacy"):
        legacy_result = await run_trajectory_for_engine("legacy")

    # Generate Comparative Report
    print("\n" + "=" * 80)
    print("GENERATING COMPREHENSIVE COMPARATIVE SCORECARD & ARTIFACT")
    print("=" * 80)

    def serialize_engine_result(res: EngineBenchmarkResult | None) -> dict[str, Any] | None:
        if not res:
            return None
        return {
            "project_id": res.project_id,
            "turns_count": len(res.turns),
            "total_duration_s": res.total_duration_s,
            "total_tokens": res.total_tokens,
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "cached_tokens": res.cached_tokens,
            "total_cost_usd": res.total_cost_usd,
            "tool_calls_total": res.tool_calls_total,
            "tool_errors": res.tool_errors,
            "avg_tool_latency_ms": (
                sum(res.tool_latencies) / len(res.tool_latencies)
                if res.tool_latencies
                else 0.0
            ),
            "dag_nuggets": res.dag_nuggets,
            "dag_facts": res.dag_facts,
            "dag_insights": res.dag_insights,
            "dag_recs": res.dag_recs,
            "dag_edges": res.dag_edges,
            "report_allowed": res.report_allowed,
            "evidence_edge_count": res.evidence_edge_count,
            "quality_ema": res.quality_ema,
            "turns": [
                {
                    "turn": t.turn_index,
                    "prompt": t.prompt,
                    "duration_s": t.duration_s,
                    "tool_calls": t.tools_invoked,
                    "tokens": t.usage.get("total_tokens", 0),
                    "text_preview": t.text[:120],
                }
                for t in res.turns
            ],
        }

    report_payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pi_engine": serialize_engine_result(pi_result) or existing_payload.get("pi_engine"),
        "legacy_engine": serialize_engine_result(legacy_result) or existing_payload.get("legacy_engine"),
    }

    output_arg = next((arg.split("=", 1)[1] for arg in sys.argv[1:] if arg.startswith("--output=")), None)
    if output_arg:
        output_path = Path(output_arg)
    else:
        output_path = REPO_ROOT / "comparison_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    print(f"\nSaved raw comparison JSON to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
