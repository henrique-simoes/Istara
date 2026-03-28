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
                            finding_ids: list[str], db: AsyncSession) -> None:
        """Route new findings to the correct report (find or create)."""
        scope = SCOPE_MAP.get(skill_name, "General Analysis")
        layer = 3 if skill_name in SYNTHESIS_SKILLS else 2

        report = await self._find_or_create_report(project_id, scope, layer, db)

        existing = json.loads(report.finding_ids_json or "[]")
        merged = list(set(existing + finding_ids))
        report.finding_ids_json = json.dumps(merged)
        report.version += 1
        report.status = "in_progress"
        report.updated_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(
            "ReportManager: routed %d findings to '%s' (v%d)",
            len(finding_ids), report.title, report.version,
        )

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
            synth.version += 1
            synth.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(
                "ReportManager: synthesis updated with %d findings from %d L2 reports",
                len(all_ids), len(l2_reports),
            )

    async def get_project_reports(self, project_id: str, db: AsyncSession) -> list[dict]:
        from app.models.project_report import ProjectReport

        result = await db.execute(
            select(ProjectReport).where(
                ProjectReport.project_id == project_id
            ).order_by(ProjectReport.layer.desc(), ProjectReport.updated_at.desc())
        )
        return [r.to_dict() for r in result.scalars().all()]


report_manager = ReportManager()
