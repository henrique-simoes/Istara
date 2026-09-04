"""Report Manager — progressive document convergence.

Implements the Four-Layer Convergence Pyramid:
  L2: Analysis reports (1 per study method)
  L3: Synthesis (cross-method, triangulation)
  L4: Final deliverable (MECE-structured)

Based on: Minto Pyramid Principle (MECE), Weick Sensemaking,
Denzin Triangulation, Braun & Clarke Thematic Analysis.

Key principle: Many inputs → few outputs. Skill executions UPDATE
existing reports, not create new ones.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _rollback_after_report_error(db: AsyncSession, context: str, exc: Exception) -> None:
    """Clear failed report transactions so caller sessions stay usable."""
    logger.warning("%s failed: %s", context, exc)
    try:
        await db.rollback()
    except Exception as rollback_exc:
        logger.debug("%s rollback failed: %s", context, rollback_exc)


SCOPE_MAP = {
    "user-interviews": "Interview Analysis",
    "thematic-analysis": "Interview Analysis",
    "kappa-thematic-analysis": "Interview Analysis",
    "interview-question-generator": "Interview Analysis",
    "contextual-inquiry": "Contextual Inquiry",
    "usability-testing": "Usability Study",
    "heuristic-evaluation": "Usability Study",
    "ux-law-compliance": "Usability Study",
    "cognitive-walkthrough": "Usability Study",
    "browser-ux-audit": "Usability Study",
    "browser-accessibility-check": "Usability Study",
    "survey-design": "Survey Analysis",
    "survey-generator": "Survey Analysis",
    "nps-analysis": "Survey Analysis",
    "sus-umux-scoring": "Survey Analysis",
    "ab-test-analysis": "A/B Test Analysis",
    "competitive-analysis": "Competitive Analysis",
    "browser-competitive-benchmark": "Competitive Analysis",
    "desk-research": "Desk Research",
    "diary-studies": "Diary Study Analysis",
    "analytics-review": "Analytics Analysis",
    "card-sorting": "Information Architecture",
    "tree-testing": "Information Architecture",
    "research-synthesis": "Research Synthesis",
    "persona-creation": "Research Synthesis",
    "journey-mapping": "Research Synthesis",
    "affinity-mapping": "Research Synthesis",
    "empathy-mapping": "Research Synthesis",
    "research-quality-evaluation": "Quality Evaluation",
    "participant-simulation": "Simulation Analysis",
}

SYNTHESIS_SKILLS = {
    "research-synthesis",
    "persona-creation",
    "journey-mapping",
    "affinity-mapping",
    "empathy-mapping",
}


def _safe_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _merge_ids(existing: list[str], incoming: list[str]) -> list[str]:
    """Merge IDs deterministically while preserving first-seen order."""
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*existing, *incoming]:
        if not item or item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def _finding_count(report) -> int:
    return len(_safe_json_list(getattr(report, "finding_ids_json", None)))


async def _record_report_promotion_gate(
    *,
    project_id: str,
    task_id: str,
    allowed: bool,
    reason: str,
) -> None:
    from app.core.telemetry import telemetry_recorder

    await telemetry_recorder.record_research_validity_event(
        operation="report.promotion_gate",
        project_id=project_id,
        task_id=task_id,
        status="success" if allowed else "degraded",
        error_type=None if allowed else "report_promotion_blocked",
        error_message=None if allowed else reason[:160],
    )


async def _record_finding_promotion(
    *,
    project_id: str,
    task_id: str,
    skill_name: str,
) -> None:
    from app.core.telemetry import telemetry_recorder

    await telemetry_recorder.record_research_validity_event(
        operation="finding.promotion",
        project_id=project_id,
        task_id=task_id,
        skill_name=skill_name,
        status="success",
    )


class ReportManager:
    """Manages progressive refinement of project reports."""

    async def route_findings(
        self,
        project_id: str,
        skill_name: str,
        finding_ids: list[str],
        db: AsyncSession,
        consensus_score: float | None = None,
    ) -> None:
        """Route new findings to the correct report (find or create)."""
        finding_ids = await self._filter_reportable_finding_ids(
            project_id,
            finding_ids,
            db,
            skill_name=skill_name,
        )
        if not finding_ids:
            logger.info(
                "ReportManager: skipped report routing for project=%s skill=%s because no findings are reportable",
                project_id,
                skill_name,
            )
            return

        scope = SCOPE_MAP.get(skill_name, "General Analysis")
        layer = 3 if skill_name in SYNTHESIS_SKILLS else 2

        report = await self._find_or_create_report(project_id, scope, layer, db)

        existing = _safe_json_list(report.finding_ids_json)
        merged = _merge_ids(existing, finding_ids)
        report.finding_ids_json = json.dumps(merged)
        report.version += 1
        report.status = "in_progress"
        report.updated_at = datetime.now(UTC)

        # Track ensemble consensus score on the report
        if consensus_score is not None:
            try:
                content = json.loads(report.content_json or "{}")
                scores = content.get("consensus_scores", [])
                scores.append(consensus_score)
                content["consensus_scores"] = scores
                content["avg_consensus"] = sum(scores) / len(scores) if scores else 0
                report.content_json = json.dumps(content)
            except Exception:
                pass

        await db.commit()

        logger.info(
            "ReportManager: routed %d findings to '%s' (v%d, total=%d)",
            len(finding_ids),
            report.title,
            report.version,
            len(merged),
        )
        report_snapshot = SimpleNamespace(
            id=report.id,
            project_id=report.project_id,
            title=report.title,
            scope=report.scope,
            version=report.version,
            executive_summary=report.executive_summary,
            mece_categories_json=report.mece_categories_json,
            content_json=report.content_json,
            finding_ids_json=report.finding_ids_json,
        )

        # Generate executive summary when report has enough findings
        await self._generate_executive_summary(report_snapshot, db)

        # Generate MECE categories when report has 5+ findings
        await self._generate_mece_categories(report_snapshot, db)

        await self._check_synthesis_trigger(project_id, db)

    async def route_approved_task_findings(
        self,
        project_id: str,
        task_id: str,
        skill_name: str,
        db: AsyncSession,
        consensus_score: float | None = None,
    ) -> int:
        """Route task findings only after human review approves the Done task."""
        from app.models.finding import Fact, Insight, Nugget, Recommendation
        from app.models.task import Task, TaskStatus

        task = await db.get(Task, task_id)
        if (
            not task
            or task.project_id != project_id
            or task.status != TaskStatus.DONE
            or task.review_state != "approved"
        ):
            await _record_report_promotion_gate(
                project_id=project_id,
                task_id=task_id,
                allowed=False,
                reason="Task is not an approved Done task.",
            )
            return 0
        from app.services.research_validity_service import assess_task_research_validity

        validity = await assess_task_research_validity(db, project_id=project_id, task_id=task_id)
        await _record_report_promotion_gate(
            project_id=project_id,
            task_id=task_id,
            allowed=bool(validity["report_allowed"]),
            reason=str(validity["reason"]),
        )
        if not validity["report_allowed"]:
            logger.info(
                "ReportManager: skipped approved task %s because research-validity gate blocked reporting: %s",
                task_id,
                validity["reason"],
            )
            return 0

        finding_ids: list[str] = []
        for model_cls in [Nugget, Fact, Insight, Recommendation]:
            result = await db.execute(
                select(model_cls.id).where(
                    model_cls.project_id == project_id,
                    model_cls.task_id == task_id,
                )
            )
            finding_ids.extend(result.scalars().all())

        if not finding_ids or not skill_name:
            return 0

        await self.route_findings(
            project_id,
            skill_name,
            finding_ids,
            db,
            consensus_score=consensus_score,
        )
        return len(finding_ids)

    async def _filter_reportable_finding_ids(
        self,
        project_id: str,
        finding_ids: list[str],
        db: AsyncSession,
        skill_name: str = "",
    ) -> list[str]:
        """Exclude task-bound findings until their task is Done and approved."""
        if not finding_ids:
            return []

        from app.models.finding import Fact, Insight, Nugget, Recommendation
        from app.models.task import Task, TaskStatus

        requested_ids = set(finding_ids)
        task_id_by_finding_id: dict[str, str] = {}
        found_finding_ids: set[str] = set()
        unlinked_finding_ids: set[str] = set()
        for model_cls in [Nugget, Fact, Insight, Recommendation]:
            result = await db.execute(
                select(model_cls.id, model_cls.task_id).where(
                    model_cls.project_id == project_id,
                    model_cls.id.in_(requested_ids),
                )
            )
            for finding_id, task_id in result.all():
                found_finding_ids.add(finding_id)
                if task_id:
                    task_id_by_finding_id[finding_id] = task_id
                else:
                    unlinked_finding_ids.add(finding_id)

        if not task_id_by_finding_id:
            for finding_id in sorted(requested_ids - found_finding_ids):
                await _record_report_promotion_gate(
                    project_id=project_id,
                    task_id="",
                    allowed=False,
                    reason=f"Finding {finding_id} does not exist or is not managed by the Research Spine.",
                )
            for finding_id in sorted(unlinked_finding_ids):
                await _record_report_promotion_gate(
                    project_id=project_id,
                    task_id="",
                    allowed=False,
                    reason=f"Finding {finding_id} is not linked to a human-approved Done task.",
                )
            return []

        all_task_ids = set(task_id_by_finding_id.values())
        result = await db.execute(
            select(Task.id).where(
                Task.project_id == project_id,
                Task.id.in_(all_task_ids),
                Task.status == TaskStatus.DONE,
                Task.review_state == "approved",
            )
        )
        reportable_task_ids = set(result.scalars().all())
        for task_id in sorted(all_task_ids - reportable_task_ids):
            await _record_report_promotion_gate(
                project_id=project_id,
                task_id=task_id,
                allowed=False,
                reason="Task is not an approved Done task.",
            )
        if reportable_task_ids:
            from app.services.research_validity_service import assess_task_research_validity

            validity_allowed: set[str] = set()
            for task_id in reportable_task_ids:
                validity = await assess_task_research_validity(
                    db, project_id=project_id, task_id=task_id
                )
                await _record_report_promotion_gate(
                    project_id=project_id,
                    task_id=task_id,
                    allowed=bool(validity["report_allowed"]),
                    reason=str(validity["reason"]),
                )
                if validity["report_allowed"]:
                    validity_allowed.add(task_id)
            reportable_task_ids = validity_allowed

        reportable_finding_ids: list[str] = []
        for finding_id in finding_ids:
            task_id = task_id_by_finding_id.get(finding_id)
            if not task_id:
                continue
            if task_id in reportable_task_ids:
                reportable_finding_ids.append(finding_id)
                await _record_finding_promotion(
                    project_id=project_id,
                    task_id=task_id,
                    skill_name=skill_name,
                )
        return reportable_finding_ids

    async def _find_or_create_report(
        self, project_id: str, scope: str, layer: int, db: AsyncSession
    ):
        from app.models.project_report import ProjectReport

        result = await db.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.scope == scope,
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            report = ProjectReport(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=scope,
                layer=layer,
                report_type="synthesis" if layer >= 3 else "study_analysis",
                scope=scope,
                status="draft",
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)
            logger.info("ReportManager: created L%d report '%s'", layer, scope)

        return report

    async def _check_synthesis_trigger(self, project_id: str, db: AsyncSession) -> None:
        """When 2+ L2 analysis reports exist, create/update L3 synthesis."""
        from app.models.project_report import ProjectReport

        result = await db.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.layer == 2,
            )
        )
        l2_reports = result.scalars().all()

        if len(l2_reports) >= 2:
            all_ids = []
            for report in l2_reports:
                all_ids.extend(_safe_json_list(report.finding_ids_json))
            reportable_ids = await self._filter_reportable_finding_ids(
                project_id,
                all_ids,
                db,
                skill_name="research-synthesis",
            )
            if not reportable_ids:
                logger.info(
                    "ReportManager: skipped L3 synthesis for project=%s because no L2 findings passed Research Spine gates",
                    project_id,
                )
                return
            synth = await self._find_or_create_report(project_id, "Research Synthesis", 3, db)
            merged_ids = _merge_ids([], reportable_ids)
            synth.finding_ids_json = json.dumps(merged_ids)
            synth.version += 1
            synth.updated_at = datetime.now(UTC)
            await db.commit()
            logger.info(
                "ReportManager: synthesis updated with %d findings from %d L2 reports",
                len(all_ids),
                len(l2_reports),
            )

            # Auto-generate L4 final report when L3 has 10+ findings
            if len(merged_ids) >= 10:
                await self._generate_l4_report(project_id, synth, db)

    async def get_project_reports(self, project_id: str, db: AsyncSession) -> list[dict]:
        from app.models.project_report import ProjectReport

        result = await db.execute(
            select(ProjectReport)
            .where(ProjectReport.project_id == project_id)
            .order_by(ProjectReport.layer.desc(), ProjectReport.updated_at.desc())
        )
        return [r.to_dict() for r in result.scalars().all()]

    async def _generate_executive_summary(self, report, db: AsyncSession) -> None:
        """Generate an executive summary when a report has 3+ findings."""
        report_id = report.id
        report_project_id = report.project_id
        report_title = report.title
        report_scope = report.scope
        finding_ids = _safe_json_list(report.finding_ids_json)[:20]
        if len(finding_ids) < 3:
            return
        try:
            # Load finding texts
            from app.models.finding import Fact, Insight, Nugget, Recommendation

            findings_text = []
            for model_cls in [Recommendation, Insight, Fact, Nugget]:
                result = await db.execute(
                    select(model_cls).where(model_cls.id.in_(finding_ids)).limit(15)
                )
                for f in result.scalars().all():
                    findings_text.append(f.text if hasattr(f, "text") else str(f))
            await db.rollback()
            if not findings_text:
                return
            summary_prompt = (
                f"Create a professional consulting-grade executive summary for the '{report_scope}' study using the SCR (Situation-Complication-Resolution) framework.\n\n"
                f"Context: {len(findings_text)} key findings extracted.\n"
                "Findings:\n"
                + "\n".join(f"- {t[:200]}" for t in findings_text[:15])
                + "\n\nFormat the summary with clear headings: SITUATION, COMPLICATION, and RESOLUTION. Ensure it addresses executive stakeholders with high clarity and academic rigor."
            )
            # W5: the SCR executive summary goes through the
            # AgenticDispatcher (``report.exec_summary``).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="report.exec_summary",
                project_id=report_project_id,
                system=None,
                messages=[{"role": "user", "content": summary_prompt}],
                params=TurnParams(temperature=0.3),
                spine_phase="synthesis",
            )
            summary = outcome.text
            if summary and len(summary) > 20:
                from app.models.project_report import ProjectReport

                fresh_report = await db.get(ProjectReport, report_id)
                if fresh_report is None:
                    return
                fresh_report.executive_summary = summary
                await db.commit()
                logger.info("ReportManager: executive summary generated for '%s'", report_title)
        except Exception as e:
            await _rollback_after_report_error(db, "Executive summary generation", e)

    async def _generate_mece_categories(self, report, db: AsyncSession) -> None:
        """Generate MECE categories when a report has 5+ findings."""
        report_id = report.id
        report_project_id = report.project_id
        report_title = report.title
        finding_ids = _safe_json_list(report.finding_ids_json)[:20]
        existing_categories = _safe_json_list(report.mece_categories_json)
        if len(finding_ids) < 5:
            return
        # Skip if already categorized for this version
        if existing_categories:
            return
        try:
            from app.models.finding import Fact, Insight, Nugget, Recommendation

            findings_text = []
            for model_cls in [Recommendation, Insight, Fact, Nugget]:
                result = await db.execute(
                    select(model_cls).where(model_cls.id.in_(finding_ids)).limit(15)
                )
                for f in result.scalars().all():
                    fid = f.id if hasattr(f, "id") else ""
                    ftxt = f.text if hasattr(f, "text") else str(f)
                    findings_text.append({"id": fid, "text": ftxt[:100]})
            await db.rollback()
            if len(findings_text) < 3:
                return
            mece_prompt = (
                f"You are a top-tier management consultant. Categorize these {len(findings_text)} research findings into 3-5 MECE "
                "(Mutually Exclusive, Collectively Exhaustive) categories using the Minto Pyramid Principle.\n\n"
                "Constraints:\n"
                "1. Each category MUST have an 'Action Title' — a full sentence that states a conclusion (e.g., 'Users struggle with X because of Y').\n"
                "2. Provide a 'So-What' description for each category explaining the business/UX impact.\n"
                "3. Ensure categories do not overlap.\n\n"
                "Findings:\n"
                + "\n".join(f"- [{f['id'][:8]}] {f['text']}" for f in findings_text)
                + '\n\nRespond with a JSON array: [{"name": "Action Title Sentence", "description": "So-What explanation...", "finding_ids": ["id1", "id2"]}]'
            )
            # W5: MECE categorization goes through the AgenticDispatcher
            # (``report.mece``) as a structured call.
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.structured(
                purpose="report.mece",
                project_id=report_project_id,
                system=None,
                messages=[{"role": "user", "content": mece_prompt}],
                schema={
                    "type": "object",
                    "properties": {
                        "categories": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "finding_ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": ["name", "description", "finding_ids"],
                            },
                        },
                    },
                    "required": ["categories"],
                },
                params=TurnParams(temperature=0.3),
                spine_phase="synthesis",
            )
            categories = (
                outcome.value.get("categories")
                if outcome.status == "success" and outcome.value
                else None
            )
            if categories:
                from app.models.project_report import ProjectReport

                fresh_report = await db.get(ProjectReport, report_id)
                if fresh_report is None:
                    return
                fresh_report.mece_categories_json = json.dumps(categories)
                await db.commit()
                logger.info(
                    "ReportManager: MECE categories generated for '%s' (%d categories)",
                    report_title,
                    len(categories),
                )
        except Exception as e:
            await _rollback_after_report_error(db, "MECE categorization", e)

    async def _generate_l4_report(self, project_id: str, l3_report, db: AsyncSession) -> None:
        """Auto-generate L4 final report with template-driven document composition.

        Pipeline: Extract → Structure → Synthesize → Compose → Cite
        (Elicit/TrialMind pattern adapted for UX research)
        """
        from app.models.project_report import ProjectReport

        # Check if L4 already exists
        result = await db.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.layer == 4,
            )
        )
        existing_l4 = result.scalar_one_or_none()
        reportable_ids = await self._filter_reportable_finding_ids(
            project_id,
            _safe_json_list(l3_report.finding_ids_json),
            db,
            skill_name="final-report",
        )
        if not reportable_ids:
            logger.info(
                "ReportManager: skipped L4 final report for project=%s because no L3 findings passed Research Spine gates",
                project_id,
            )
            return
        reportable_ids_json = json.dumps(reportable_ids)
        finding_count = len(reportable_ids)

        if existing_l4:
            existing_l4.finding_ids_json = reportable_ids_json
            existing_l4.version += 1
            existing_l4.updated_at = datetime.now(UTC)
            l4 = existing_l4
        else:
            l4 = ProjectReport(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title="Final Research Report",
                layer=4,
                report_type="final_report",
                scope="Final Report",
                status="draft",
                finding_ids_json=reportable_ids_json,
            )
            db.add(l4)

        await db.commit()
        if not existing_l4:
            await db.refresh(l4)
        l4_id = l4.id
        l4_snapshot = SimpleNamespace(
            id=l4.id,
            project_id=project_id,
            title=l4.title,
            scope=l4.scope,
            version=l4.version,
            executive_summary=l4.executive_summary,
            mece_categories_json=l4.mece_categories_json,
            content_json=l4.content_json,
            finding_ids_json=l4.finding_ids_json,
        )

        # Generate executive summary and MECE categories
        await self._generate_executive_summary(l4_snapshot, db)
        await self._generate_mece_categories(l4_snapshot, db)

        # Generate full document via template-driven composition
        fresh_l4 = await db.get(ProjectReport, l4_id)
        if fresh_l4 is not None:
            await self._compose_full_report(fresh_l4, project_id, db)

        logger.info(
            "ReportManager: L4 report %s with %d findings",
            "updated" if existing_l4 else "created",
            finding_count,
        )

    # ── Template-Driven Report Composition ──────────────────────────

    REPORT_TEMPLATE = [
        {
            "section": "I. Executive Summary (SCR)",
            "source": "executive_summary",
            "format": "narrative",
        },
        {"section": "II. Research Methodology & Rigor", "source": "skills_used", "format": "list"},
        {
            "section": "III. Strategic Thematic Analysis (MECE)",
            "source": "mece_categories",
            "format": "structured",
        },
        {
            "section": "IV. Detailed Insights & Evidence Chain",
            "source": "insights",
            "format": "detailed_narrative",
        },
        {
            "section": "V. Supporting Evidence (Nuggets & Facts)",
            "source": "nuggets_and_facts",
            "format": "citation_table",
        },
        {
            "section": "VI. Actionable Recommendations (Pyramid Top)",
            "source": "recommendations",
            "format": "priority_table",
        },
        {
            "section": "VII. Validation & Consensus Metrics",
            "source": "ensemble_scores",
            "format": "metrics",
        },
        {"section": "VIII. Analysis Gaps & Next Steps", "source": "gaps", "format": "narrative"},
    ]

    async def _compose_full_report(self, report, project_id: str, db: AsyncSession) -> None:
        """Compose the full L4 report document from template sections."""
        try:
            from app.models.finding import Fact, Insight, Nugget, Recommendation

            report_id = report.id
            report_snapshot = SimpleNamespace(
                id=report.id,
                title=report.title,
                version=report.version,
                executive_summary=report.executive_summary,
                mece_categories_json=report.mece_categories_json,
                content_json=report.content_json,
            )
            finding_ids = _safe_json_list(report.finding_ids_json)[:50]

            # Load all findings by type
            findings = {"nuggets": [], "facts": [], "insights": [], "recommendations": []}
            for model_cls, key in [
                (Nugget, "nuggets"),
                (Fact, "facts"),
                (Insight, "insights"),
                (Recommendation, "recommendations"),
            ]:
                result = await db.execute(
                    select(model_cls).where(model_cls.id.in_(finding_ids)).limit(30)
                )
                for f in result.scalars().all():
                    findings[key].append(
                        {
                            "id": f.id,
                            "text": f.text if hasattr(f, "text") else str(f),
                            "source": getattr(f, "source", ""),
                            "confidence": getattr(f, "confidence", 0),
                            "phase": getattr(f, "phase", ""),
                        }
                    )

            # Get L2 report scopes (methodologies used)
            from app.models.project_report import ProjectReport

            l2_result = await db.execute(
                select(ProjectReport).where(
                    ProjectReport.project_id == project_id, ProjectReport.layer == 2
                )
            )
            methodologies = [r.scope for r in l2_result.scalars().all()]
            await db.rollback()

            # Compose each section
            sections = []
            for template in self.REPORT_TEMPLATE:
                section_content = await self._compose_section(
                    template,
                    findings,
                    report_snapshot,
                    methodologies,
                    project_id=project_id,
                )
                if section_content:
                    sections.append(f"## {template['section']}\n\n{section_content}")

            # Assemble full document
            full_doc = f"# {report_snapshot.title}\n\n" + "\n\n---\n\n".join(sections)

            # ── Iterative refinement loop (max 2 passes) ──
            # LLM scores each section, identifies the weakest, and re-composes it.
            # Stops when all sections score ≥7 or after 2 passes.
            MAX_REFINEMENT_PASSES = 2
            for pass_num in range(MAX_REFINEMENT_PASSES):
                try:
                    score_prompt = (
                        f"Rate each section of this research report (1-10). "
                        f"Identify the weakest section and suggest how to improve it.\n\n"
                        f"{full_doc[:3000]}\n\n"
                        f'Respond with JSON: {{"scores": {{"section_name": score}}, '
                        f'"weakest": "section_name", "reason": "...", "suggestion": "..."}}'
                    )
                    # W5: weakest-section scoring goes through the
                    # AgenticDispatcher (``report.weakest_section``) as a
                    # structured call.
                    from app.core.agentic import agentic
                    from app.core.agentic.types import TurnParams

                    outcome = await agentic.structured(
                        purpose="report.weakest_section",
                        project_id=project_id,
                        system=None,
                        messages=[{"role": "user", "content": score_prompt}],
                        schema={
                            "type": "object",
                            "properties": {
                                "scores": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                                "weakest": {"type": "string"},
                                "reason": {"type": "string"},
                                "suggestion": {"type": "string"},
                            },
                            "required": ["scores", "weakest", "suggestion"],
                        },
                        params=TurnParams(temperature=0.2),
                        spine_phase="review",
                    )
                    score_data = (
                        outcome.value if outcome.status == "success" and outcome.value else None
                    )
                    if not score_data:
                        break

                    scores = score_data.get("scores", {})
                    weakest = score_data.get("weakest", "")
                    suggestion = score_data.get("suggestion", "")

                    # Convergence: all sections ≥7 → stop refining
                    if scores and all(
                        s >= 7 for s in scores.values() if isinstance(s, (int, float))
                    ):
                        logger.info(f"Report refinement converged at pass {pass_num + 1}")
                        break

                    # Re-compose weakest section
                    for i, template in enumerate(self.REPORT_TEMPLATE):
                        if template["section"].lower() == weakest.lower():
                            refined = await self._compose_section(
                                template,
                                findings,
                                report_snapshot,
                                methodologies,
                                refinement_hint=suggestion,
                                project_id=project_id,
                            )
                            if refined:
                                sections[i] = f"## {template['section']}\n\n{refined}"
                                full_doc = f"# {report_snapshot.title}\n\n" + "\n\n---\n\n".join(
                                    sections
                                )
                                logger.info(
                                    f"Report refined: section '{weakest}' (pass {pass_num + 1})"
                                )
                            break
                except Exception as e:
                    logger.debug(f"Report refinement pass {pass_num + 1} skipped: {e}")
                    break

            # Store in content_json
            from app.models.project_report import ProjectReport

            fresh_report = await db.get(ProjectReport, report_id)
            if fresh_report is None:
                return
            content = json.loads(fresh_report.content_json or report_snapshot.content_json or "{}")
            content["full_document"] = full_doc
            content["sections"] = [t["section"] for t in self.REPORT_TEMPLATE]
            content["generated_at"] = datetime.now(UTC).isoformat()
            content["refinement_passes"] = (
                min(pass_num + 1, MAX_REFINEMENT_PASSES) if "pass_num" in dir() else 0
            )
            fresh_report.content_json = json.dumps(content)
            fresh_report.status = "review"
            await db.commit()

            # Create a Document record for the report
            try:
                from app.models.document import Document

                doc = Document(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=f"Final Research Report (v{fresh_report.version})",
                    file_name="final_research_report.md",
                    source="agent_output",
                    content_preview=full_doc[:500],
                    status="ready",
                )
                db.add(doc)
                await db.commit()
                logger.info("ReportManager: report document created")
            except Exception as e:
                await _rollback_after_report_error(db, "Report document creation", e)

        except Exception as e:
            await _rollback_after_report_error(db, "Full report composition", e)

    async def _compose_section(
        self,
        template: dict,
        findings: dict,
        report,
        methodologies: list,
        refinement_hint: str = "",
        project_id: str | None = None,
    ) -> str:
        """Compose a single report section from its template definition."""
        source = template["source"]
        fmt = template["format"]

        if source == "executive_summary":
            return report.executive_summary or "No executive summary available."

        if source == "skills_used":
            if not methodologies:
                return "No specific research methodologies were applied."
            return "The following research methods were used:\n\n" + "\n".join(
                f"- {m}" for m in methodologies
            )

        if source == "insights":
            items = findings.get("insights", [])
            if not items:
                return "No key insights were generated."

            if fmt == "detailed_narrative":
                prompt = (
                    f"You are a management consultant. Expand these {len(items)} insights into a "
                    "detailed, professional research section (~800 words).\n\n"
                    "Instructions:\n"
                    "1. For each insight, explain the underlying pattern, provide examples, and "
                    "contextualize it within the study's scope.\n"
                    "2. Use professional, objective language.\n"
                    "3. Connect insights where relationships exist.\n\n"
                    "Insights:\n" + "\n".join(f"- {i['text']}" for i in items)
                )
                try:
                    # W5: the detailed insights narrative goes through the
                    # AgenticDispatcher (``report.insights_narrative``).
                    from app.core.agentic import agentic
                    from app.core.agentic.types import TurnParams

                    outcome = await agentic.completion(
                        purpose="report.insights_narrative",
                        project_id=project_id or getattr(report, "project_id", None) or "",
                        system=None,
                        messages=[{"role": "user", "content": prompt}],
                        params=TurnParams(temperature=0.3),
                        spine_phase="synthesis",
                    )
                    return outcome.text or "Detailed narrative generation failed."
                except Exception:
                    fmt = "evidence_table"  # Fallback

            if fmt == "evidence_table":
                rows = [
                    "| # | Insight | Confidence | Phase |",
                    "|---|---------|------------|-------|",
                ]
                for i, item in enumerate(items, 1):
                    conf = (
                        f"{item.get('confidence', 0):.0%}"
                        if isinstance(item.get("confidence"), (int, float))
                        else "N/A"
                    )
                    rows.append(
                        f"| {i} | {item['text'][:100]} | {conf} | {item.get('phase', '')} |"
                    )
                return "\n".join(rows)
            return "\n".join(f"- {item['text']}" for item in items)

        if source == "nuggets_and_facts":
            nuggets = findings.get("nuggets", [])
            facts = findings.get("facts", [])
            if not nuggets and not facts:
                return "No supporting evidence collected."
            rows = ["| Type | Evidence | Source |", "|------|----------|--------|"]
            for n in nuggets[:15]:
                rows.append(f"| Nugget | {n['text'][:80]} | {n.get('source', 'N/A')[:30]} |")
            for f in facts[:10]:
                rows.append(f"| Fact | {f['text'][:80]} | {f.get('source', 'N/A')[:30]} |")
            return "\n".join(rows)

        if source == "recommendations":
            items = findings.get("recommendations", [])
            if not items:
                return "No actionable recommendations generated."

            prompt = (
                f"You are a management consultant. For each of these {len(items)} research recommendations, "
                "develop a professional, multi-paragraph justification (~500 words total).\n\n"
                "Constraints:\n"
                "1. State the recommendation clearly (The 'Pyramid Top').\n"
                "2. Provide 2-3 logical supporting reasons based on research findings.\n"
                "3. Suggest immediate next steps for implementation.\n\n"
                "Recommendations:\n" + "\n".join(f"- {r['text']}" for r in items)
            )
            try:
                # W5: the recommendations justification goes through the
                # AgenticDispatcher (``report.recommendations_narrative``).
                from app.core.agentic import agentic
                from app.core.agentic.types import TurnParams

                outcome = await agentic.completion(
                    purpose="report.recommendations_narrative",
                    project_id=project_id or getattr(report, "project_id", None) or "",
                    system=None,
                    messages=[{"role": "user", "content": prompt}],
                    params=TurnParams(temperature=0.3),
                    spine_phase="synthesis",
                )
                return outcome.text or "Recommendation detail generation failed."
            except Exception:
                rows = ["| # | Recommendation | Priority |", "|---|---------------|----------|"]
                for i, item in enumerate(items, 1):
                    rows.append(f"| {i} | {item['text'][:100]} | Medium |")
                return "\n".join(rows)

        if source == "mece_categories":
            categories = json.loads(report.mece_categories_json or "[]")
            if not categories:
                return "Strategic thematic analysis (MECE) not yet available."

            parts = []
            for cat in categories:
                name = cat.get("name", "Unknown Conclusion")
                desc = cat.get("description", "No supporting argument provided.")
                count = len(cat.get("finding_ids", []))

                # Deeper analysis for each MECE category
                parts.append(
                    f"### {name}\n"
                    f"**Strategic Takeaway**: {desc}\n\n"
                    f"*Evidence density: This conclusion is supported by {count} distinct research findings.*"
                )
            return "\n\n".join(parts)

        if source == "ensemble_scores":
            content = json.loads(report.content_json or "{}")
            scores = content.get("consensus_scores", [])
            if not scores:
                return "No ensemble validation data available."
            avg = content.get("avg_consensus", 0)
            return (
                f"**Average response-level consensus score**: {avg:.2f}\n"
                f"**Validation runs**: {len(scores)}\n"
                f"**Score range**: {min(scores):.2f} – {max(scores):.2f}\n\n"
                "These scores are heuristic response-level quality signals from "
                "Self-MoA, Dual Run, or Adversarial Review; they are not Fleiss' "
                "Kappa and cannot establish formal Research Spine reliability. "
                "Formal Fleiss/Cohen/Krippendorff metrics are computed only from "
                "independent coded evidence-unit matrices in a governed coding run."
            )

        if source == "gaps":
            # Ask LLM to identify gaps
            try:
                all_texts = [f["text"][:80] for f in findings.get("insights", [])[:10]]
                if not all_texts:
                    return "Insufficient findings to identify gaps."
                prompt = (
                    "Based on these research insights, identify 2-3 limitations or gaps "
                    "in the analysis that should be noted:\n\n"
                    + "\n".join(f"- {t}" for t in all_texts)
                )
                if refinement_hint:
                    prompt += f"\n\nRefinement guidance: {refinement_hint}"
                prompt += "\n\nBe specific and concise."
                # W5: the gaps/limitations analysis goes through the
                # AgenticDispatcher (``report.gaps_analysis``).
                from app.core.agentic import agentic
                from app.core.agentic.types import TurnParams

                outcome = await agentic.completion(
                    purpose="report.gaps_analysis",
                    project_id=project_id or getattr(report, "project_id", None) or "",
                    system=None,
                    messages=[{"role": "user", "content": prompt}],
                    params=TurnParams(temperature=0.3),
                    spine_phase="review",
                )
                return outcome.text or "No gaps analysis available."
            except Exception:
                return "Gap analysis could not be generated."

        return ""


report_manager = ReportManager()
