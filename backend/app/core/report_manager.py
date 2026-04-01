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
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
    "survey-design": "Survey Analysis",
    "survey-generator": "Survey Analysis",
    "nps-analysis": "Survey Analysis",
    "sus-umux-scoring": "Survey Analysis",
    "ab-test-analysis": "A/B Test Analysis",
    "competitive-analysis": "Competitive Analysis",
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
}

SYNTHESIS_SKILLS = {
    "research-synthesis", "persona-creation", "journey-mapping",
    "affinity-mapping", "empathy-mapping",
}


class ReportManager:
    """Manages progressive refinement of project reports."""

    async def route_findings(self, project_id: str, skill_name: str,
                            finding_ids: list[str], db: AsyncSession,
                            consensus_score: float | None = None) -> None:
        """Route new findings to the correct report (find or create)."""
        scope = SCOPE_MAP.get(skill_name, "General Analysis")
        layer = 3 if skill_name in SYNTHESIS_SKILLS else 2

        report = await self._find_or_create_report(project_id, scope, layer, db)

        existing = json.loads(report.finding_ids_json or "[]")
        merged = list(set(existing + finding_ids))
        report.finding_ids_json = json.dumps(merged)
        report.finding_count = len(merged)
        report.version += 1
        report.status = "in_progress"
        report.updated_at = datetime.now(timezone.utc)

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
            len(finding_ids), report.title, report.version, report.finding_count,
        )

        # Generate executive summary when report has enough findings
        await self._generate_executive_summary(report, db)

        # Generate MECE categories when report has 5+ findings
        await self._generate_mece_categories(report, db)

        await self._check_synthesis_trigger(project_id, db)

    async def _find_or_create_report(self, project_id: str, scope: str,
                                      layer: int, db: AsyncSession):
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
            synth = await self._find_or_create_report(
                project_id, "Research Synthesis", 3, db
            )
            all_ids = []
            for r in l2_reports:
                ids = json.loads(r.finding_ids_json or "[]")
                all_ids.extend(ids)
            synth.finding_ids_json = json.dumps(list(set(all_ids)))
            synth.finding_count = len(set(all_ids))
            synth.version += 1
            synth.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(
                "ReportManager: synthesis updated with %d findings from %d L2 reports",
                len(all_ids), len(l2_reports),
            )

            # Auto-generate L4 final report when L3 has 10+ findings
            if synth.finding_count >= 10:
                await self._generate_l4_report(project_id, synth, db)

    async def get_project_reports(self, project_id: str, db: AsyncSession) -> list[dict]:
        from app.models.project_report import ProjectReport

        result = await db.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id
            ).order_by(ProjectReport.layer.desc(), ProjectReport.updated_at.desc())
        )
        return [r.to_dict() for r in result.scalars().all()]

    async def _generate_executive_summary(self, report, db: AsyncSession) -> None:
        """Generate an executive summary when a report has 3+ findings."""
        if report.finding_count < 3:
            return
        try:
            from app.core.llm_router import llm_router
            finding_ids = json.loads(report.finding_ids_json or "[]")[:20]
            # Load finding texts
            from app.models.finding import Nugget, Fact, Insight
            findings_text = []
            for model_cls in [Insight, Fact, Nugget]:
                result = await db.execute(
                    select(model_cls).where(model_cls.id.in_(finding_ids)).limit(15)
                )
                for f in result.scalars().all():
                    findings_text.append(f.text if hasattr(f, "text") else str(f))
            if not findings_text:
                return
            summary_prompt = (
                f"Write a 2-3 sentence executive summary of these {len(findings_text)} "
                f"UX research findings for the '{report.scope}' study:\n\n"
                + "\n".join(f"- {t[:100]}" for t in findings_text[:15])
            )
            response = await llm_router.chat(
                [{"role": "user", "content": summary_prompt}], temperature=0.3
            )
            summary = response.get("message", {}).get("content", "")
            if summary and len(summary) > 20:
                report.executive_summary = summary
                await db.commit()
                logger.info("ReportManager: executive summary generated for '%s'", report.title)
        except Exception as e:
            logger.debug(f"Executive summary generation skipped: {e}")

    async def _generate_mece_categories(self, report, db: AsyncSession) -> None:
        """Generate MECE categories when a report has 5+ findings."""
        if report.finding_count < 5:
            return
        # Skip if already categorized for this version
        existing = json.loads(report.mece_categories_json or "[]")
        if existing:
            return
        try:
            from app.core.llm_router import llm_router
            from app.models.finding import Nugget, Fact, Insight
            finding_ids = json.loads(report.finding_ids_json or "[]")[:20]
            findings_text = []
            for model_cls in [Insight, Fact, Nugget]:
                result = await db.execute(
                    select(model_cls).where(model_cls.id.in_(finding_ids)).limit(15)
                )
                for f in result.scalars().all():
                    fid = f.id if hasattr(f, "id") else ""
                    ftxt = f.text if hasattr(f, "text") else str(f)
                    findings_text.append({"id": fid, "text": ftxt[:100]})
            if len(findings_text) < 3:
                return
            mece_prompt = (
                f"Categorize these {len(findings_text)} research findings into 3-7 MECE "
                "(Mutually Exclusive, Collectively Exhaustive) categories.\n\n"
                "Findings:\n"
                + "\n".join(f"- [{f['id'][:8]}] {f['text']}" for f in findings_text)
                + '\n\nRespond with a JSON array: [{"name": "Category Name", "description": "...", "finding_ids": ["id1", "id2"]}]'
            )
            response = await llm_router.chat(
                [{"role": "user", "content": mece_prompt}], temperature=0.3
            )
            content = response.get("message", {}).get("content", "")
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                categories = json.loads(json_match.group())
                report.mece_categories_json = json.dumps(categories)
                await db.commit()
                logger.info("ReportManager: MECE categories generated for '%s' (%d categories)", report.title, len(categories))
        except Exception as e:
            logger.debug(f"MECE categorization skipped: {e}")

    async def _generate_l4_report(self, project_id: str, l3_report, db: AsyncSession) -> None:
        """Auto-generate L4 final report from L3 synthesis."""
        from app.models.project_report import ProjectReport

        # Check if L4 already exists
        result = await db.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id,
                ProjectReport.layer == 4,
            )
        )
        existing_l4 = result.scalar_one_or_none()
        if existing_l4:
            # Update existing L4 with latest L3 findings
            existing_l4.finding_ids_json = l3_report.finding_ids_json
            existing_l4.finding_count = l3_report.finding_count
            existing_l4.version += 1
            existing_l4.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await self._generate_executive_summary(existing_l4, db)
            await self._generate_mece_categories(existing_l4, db)
            logger.info("ReportManager: L4 final report updated (v%d)", existing_l4.version)
            return

        # Create new L4
        l4 = ProjectReport(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="Final Research Report",
            layer=4,
            report_type="final_report",
            scope="Final Report",
            status="draft",
            finding_ids_json=l3_report.finding_ids_json,
            finding_count=l3_report.finding_count,
        )
        db.add(l4)
        await db.commit()
        await db.refresh(l4)

        # Generate content for L4
        await self._generate_executive_summary(l4, db)
        await self._generate_mece_categories(l4, db)
        logger.info("ReportManager: L4 final report created with %d findings", l4.finding_count)


report_manager = ReportManager()
