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
            len(finding_ids),
            report.title,
            report.version,
            report.finding_count,
        )

        # Generate executive summary when report has enough findings
        await self._generate_executive_summary(report, db)

        # Generate MECE categories when report has 5+ findings
        await self._generate_mece_categories(report, db)

        await self._check_synthesis_trigger(project_id, db)

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
            synth = await self._find_or_create_report(project_id, "Research Synthesis", 3, db)
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
                len(all_ids),
                len(l2_reports),
            )

            # Auto-generate L4 final report when L3 has 10+ findings
            if synth.finding_count >= 10:
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
                f"Create a professional consulting-grade executive summary for the '{report.scope}' study using the SCR (Situation-Complication-Resolution) framework.\n\n"
                f"Context: {len(findings_text)} key findings extracted.\n"
                "Findings:\n"
                + "\n".join(f"- {t[:200]}" for t in findings_text[:15])
                + "\n\nFormat the summary with clear headings: SITUATION, COMPLICATION, and RESOLUTION. Ensure it addresses executive stakeholders with high clarity and academic rigor."
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
            response = await llm_router.chat(
                [{"role": "user", "content": mece_prompt}], temperature=0.3
            )
            content = response.get("message", {}).get("content", "")
            import re

            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                categories = json.loads(json_match.group())
                report.mece_categories_json = json.dumps(categories)
                await db.commit()
                logger.info(
                    "ReportManager: MECE categories generated for '%s' (%d categories)",
                    report.title,
                    len(categories),
                )
        except Exception as e:
            logger.debug(f"MECE categorization skipped: {e}")

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

        if existing_l4:
            existing_l4.finding_ids_json = l3_report.finding_ids_json
            existing_l4.finding_count = l3_report.finding_count
            existing_l4.version += 1
            existing_l4.updated_at = datetime.now(timezone.utc)
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
                finding_ids_json=l3_report.finding_ids_json,
                finding_count=l3_report.finding_count,
            )
            db.add(l4)

        await db.commit()
        if not existing_l4:
            await db.refresh(l4)

        # Generate executive summary and MECE categories
        await self._generate_executive_summary(l4, db)
        await self._generate_mece_categories(l4, db)

        # Generate full document via template-driven composition
        await self._compose_full_report(l4, project_id, db)

        logger.info(
            "ReportManager: L4 report %s with %d findings",
            "updated" if existing_l4 else "created",
            l4.finding_count,
        )

    # ── Template-Driven Report Composition ──────────────────────────

    REPORT_TEMPLATE = [
        {"section": "I. Executive Summary (SCR)", "source": "executive_summary", "format": "narrative"},
        {"section": "II. Research Methodology & Rigor", "source": "skills_used", "format": "list"},
        {"section": "III. Strategic Thematic Analysis (MECE)", "source": "mece_categories", "format": "structured"},
        {"section": "IV. Detailed Insights & Evidence Chain", "source": "insights", "format": "detailed_narrative"},
        {"section": "V. Supporting Evidence (Nuggets & Facts)", "source": "nuggets_and_facts", "format": "citation_table"},
        {"section": "VI. Actionable Recommendations (Pyramid Top)", "source": "recommendations", "format": "priority_table"},
        {"section": "VII. Validation & Consensus Metrics", "source": "ensemble_scores", "format": "metrics"},
        {"section": "VIII. Analysis Gaps & Next Steps", "source": "gaps", "format": "narrative"},
    ]

    async def _compose_full_report(self, report, project_id: str, db: AsyncSession) -> None:
        """Compose the full L4 report document from template sections."""
        try:
            from app.core.llm_router import llm_router
            from app.models.finding import Nugget, Fact, Insight, Recommendation

            finding_ids = json.loads(report.finding_ids_json or "[]")[:50]

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

            # Compose each section
            sections = []
            for template in self.REPORT_TEMPLATE:
                section_content = await self._compose_section(
                    template, findings, report, methodologies, llm_router
                )
                if section_content:
                    sections.append(f"## {template['section']}\n\n{section_content}")

            # Assemble full document
            full_doc = f"# {report.title}\n\n" + "\n\n---\n\n".join(sections)

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
                    score_response = await llm_router.chat(
                        [{"role": "user", "content": score_prompt}], temperature=0.2
                    )
                    score_text = score_response.get("message", {}).get("content", "")

                    import re as _re

                    json_match = _re.search(r'\{.*"weakest".*\}', score_text, _re.DOTALL)
                    if not json_match:
                        break

                    score_data = json.loads(json_match.group())
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
                                report,
                                methodologies,
                                llm_router,
                                refinement_hint=suggestion,
                            )
                            if refined:
                                sections[i] = f"## {template['section']}\n\n{refined}"
                                full_doc = f"# {report.title}\n\n" + "\n\n---\n\n".join(sections)
                                logger.info(
                                    f"Report refined: section '{weakest}' (pass {pass_num + 1})"
                                )
                            break
                except Exception as e:
                    logger.debug(f"Report refinement pass {pass_num + 1} skipped: {e}")
                    break

            # Store in content_json
            content = json.loads(report.content_json or "{}")
            content["full_document"] = full_doc
            content["sections"] = [t["section"] for t in self.REPORT_TEMPLATE]
            content["generated_at"] = datetime.now(timezone.utc).isoformat()
            content["refinement_passes"] = (
                min(pass_num + 1, MAX_REFINEMENT_PASSES) if "pass_num" in dir() else 0
            )
            report.content_json = json.dumps(content)
            report.status = "review"
            await db.commit()

            # Create a Document record for the report
            try:
                from app.models.document import Document

                doc = Document(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=f"Final Research Report (v{report.version})",
                    file_name="final_research_report.md",
                    source="agent_output",
                    content_preview=full_doc[:500],
                    status="ready",
                )
                db.add(doc)
                await db.commit()
                logger.info("ReportManager: report document created")
            except Exception as e:
                logger.debug(f"Report document creation skipped: {e}")

        except Exception as e:
            logger.warning(f"Full report composition failed: {e}")

    async def _compose_section(
        self,
        template: dict,
        findings: dict,
        report,
        methodologies: list,
        llm_router,
        refinement_hint: str = "",
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
                    "Insights:\n"
                    + "\n".join(f"- {i['text']}" for i in items)
                )
                try:
                    response = await llm_router.chat([{"role": "user", "content": prompt}], temperature=0.3)
                    return response.get("message", {}).get("content", "Detailed narrative generation failed.")
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
                "Recommendations:\n"
                + "\n".join(f"- {r['text']}" for r in items)
            )
            try:
                response = await llm_router.chat([{"role": "user", "content": prompt}], temperature=0.3)
                return response.get("message", {}).get("content", "Recommendation detail generation failed.")
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
                f"**Average consensus score**: {avg:.2f}\n"
                f"**Validation runs**: {len(scores)}\n"
                f"**Score range**: {min(scores):.2f} – {max(scores):.2f}\n\n"
                "Consensus is computed using Fleiss' Kappa + cosine similarity across "
                "multiple model runs (Self-MoA, Dual Run, Adversarial Review)."
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
                response = await llm_router.chat(
                    [{"role": "user", "content": prompt}], temperature=0.3
                )
                return response.get("message", {}).get("content", "No gaps analysis available.")
            except Exception:
                return "Gap analysis could not be generated."

        return ""


report_manager = ReportManager()
