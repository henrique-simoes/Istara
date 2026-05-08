"""Learned skill candidate routing and ReAct tool definitions."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.telemetry import telemetry_recorder
from app.models.model_skill_stats import ModelSkillStats
from app.skills.base import SkillInput, SkillOutput
from app.skills.registry import registry
from app.skills.skill_manager import skill_manager

logger = logging.getLogger("app.core.agent")

SKILL_KEYWORDS: dict[str, str] = {
    "interview": "user-interviews",
    "transcript": "user-interviews",
    "survey": "survey-design",
    "questionnaire": "survey-generator",
    "competitive": "competitive-analysis",
    "competitor": "competitive-analysis",
    "persona": "persona-creation",
    "journey": "journey-mapping",
    "affinity": "affinity-mapping",
    "thematic": "thematic-analysis",
    "usability": "usability-testing",
    "heuristic": "heuristic-evaluation",
    "ux audit": "browser-ux-audit",
    "site audit": "browser-ux-audit",
    "accessibility check": "browser-accessibility-check",
    "a11y": "browser-accessibility-check",
    "competitive benchmark": "browser-competitive-benchmark",
    "competitor audit": "browser-competitive-benchmark",
    "quality evaluation": "research-quality-evaluation",
    "evaluate quality": "research-quality-evaluation",
    "llm as judge": "research-quality-evaluation",
    "game theory participant simulation": "participant-simulation",
    "participant simulation": "participant-simulation",
    "game theory": "participant-simulation",
    "card sort": "card-sorting",
    "tree test": "tree-testing",
    "a/b test": "ab-test-analysis",
    "sus ": "sus-umux-scoring",
    "umux": "sus-umux-scoring",
    "nps": "nps-analysis",
    "stakeholder": "stakeholder-interviews",
    "diary": "diary-studies",
    "ethnograph": "field-studies",
    "field study": "field-studies",
    "accessibility": "accessibility-audit",
    "wcag": "accessibility-audit",
    "analytics": "analytics-review",
    "hmw": "hmw-statements",
    "how might we": "hmw-statements",
    "jobs to be done": "jtbd-analysis",
    "jtbd": "jtbd-analysis",
    "empathy map": "empathy-mapping",
    "user flow": "user-flow-mapping",
    "synthesis": "research-synthesis",
    "report": "research-synthesis",
    "prioriti": "prioritization-matrix",
    "concept test": "concept-testing",
    "cognitive walk": "cognitive-walkthrough",
    "design critique": "design-critique",
    "expert review": "design-critique",
    "prototype": "prototype-feedback",
    "workshop": "workshop-facilitation",
    "design system": "design-system-audit",
    "handoff": "handoff-documentation",
    "presentation": "stakeholder-presentation",
    "retro": "research-retro",
    "longitudinal": "longitudinal-tracking",
    "taxonomy": "taxonomy-generator",
    "kappa": "kappa-thematic-analysis",
    "intercoder": "kappa-thematic-analysis",
    "ai detect": "survey-ai-detection",
    "bot detect": "survey-ai-detection",
}

SUCCESS_OUTCOMES = {"success", "kept", "completed", "verified"}
FAILURE_OUTCOMES = {"failure", "failed", "reverted", "timeout", "rejected"}
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)


@dataclass
class SkillCandidate:
    name: str
    display_name: str
    description: str
    phase: str
    score: float = 0.0
    matched_via: str = "ranked"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "phase": self.phase,
            "score": round(self.score, 4),
            "matched_via": self.matched_via,
            "reasons": self.reasons[:6],
        }


def _tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(text or "")}


def _candidate_for_skill(skill) -> SkillCandidate:
    return SkillCandidate(
        name=skill.name,
        display_name=skill.display_name,
        description=skill.description,
        phase=skill.phase.value,
    )


def _bump(
    candidates: dict[str, SkillCandidate],
    skill_name: str,
    amount: float,
    reason: str,
    matched_via: str,
) -> None:
    skill = registry.get(skill_name)
    if not skill:
        return
    candidate = candidates.setdefault(skill_name, _candidate_for_skill(skill))
    candidate.score += amount
    if matched_via != "ranked" and candidate.matched_via == "ranked":
        candidate.matched_via = matched_via
    if reason not in candidate.reasons:
        candidate.reasons.append(reason)


async def _telemetry_quality_boost(
    skill_names: set[str],
    db: AsyncSession | None,
) -> dict[str, float]:
    if not skill_names:
        return {}

    async def _query(session: AsyncSession) -> dict[str, float]:
        result = await session.execute(
            select(ModelSkillStats).where(ModelSkillStats.skill_name.in_(skill_names))
        )
        boosts: dict[str, float] = {}
        for row in result.scalars().all():
            if row.executions <= 0:
                continue
            quality = max(0.0, min(1.0, float(row.quality_ema or 0.0)))
            sample_weight = min(1.0, row.executions / 10)
            source_weight = 1.0 if row.source == "production" else 0.75
            boosts[row.skill_name] = max(
                boosts.get(row.skill_name, 0.0),
                quality * sample_weight * source_weight * 0.12,
            )
        return boosts

    try:
        if db is not None:
            return await _query(db)
        from app.models.database import async_session

        async with async_session() as session:
            return await _query(session)
    except Exception as exc:
        logger.debug("Skill candidate telemetry boost skipped: %s", exc)
        return {}


async def _reasoning_memory_boosts(
    *,
    project_id: str,
    agent_id: str,
    query: str,
    db: AsyncSession | None,
) -> dict[str, tuple[float, list[str]]]:
    try:
        from app.core.reasoning_bank import reasoning_bank

        memories = await reasoning_bank.retrieve(
            project_id=project_id,
            agent_id=agent_id or None,
            query=query,
            source_kinds=["skill", "autoresearch"],
            limit=12,
            db=db,
        )
    except Exception as exc:
        logger.debug("ReasoningBank skill candidate retrieval skipped: %s", exc)
        return {}

    boosts: dict[str, tuple[float, list[str]]] = {}
    for memory in memories:
        haystack = " ".join(
            [
                str(memory.get("domain") or ""),
                " ".join(memory.get("tags") or []),
                str(memory.get("title") or ""),
                str(memory.get("description") or ""),
                str(memory.get("content") or "")[:500],
            ]
        ).lower()
        score = float(memory.get("retrieval_score") or 0.0)
        outcome = str(memory.get("outcome") or "").lower()
        for skill in registry.list_all():
            name = skill.name.lower()
            if name not in haystack and name.replace("-", " ") not in haystack:
                continue
            direction = -1.0 if outcome in FAILURE_OUTCOMES else 1.0
            weight = 0.14 if outcome in SUCCESS_OUTCOMES else 0.08
            delta = direction * min(0.12, max(0.02, score * weight))
            previous, reasons = boosts.get(skill.name, (0.0, []))
            reasons.append(f"reasoning_bank:{outcome or 'observed'}")
            boosts[skill.name] = (previous + delta, reasons)
    return boosts


def _meta_hyperagent_notes() -> list[str]:
    module = sys.modules.get("app.core.meta_hyperagent")
    meta_hyperagent = getattr(module, "meta_hyperagent", None) if module else None
    if meta_hyperagent is None:
        return []

    try:
        notes: list[str] = []
        for variant in meta_hyperagent.get_active_variants():
            if variant.get("target_system") == "skill_selection":
                notes.append(f"meta_variant:{variant.get('parameter_path')}")
        recent = meta_hyperagent.get_recent_observations(limit=1)
        if recent:
            selection = recent[-1].get("skill_selection") or {}
            if selection.get("success_rate") is not None:
                notes.append(f"meta_success_rate:{selection['success_rate']}")
        return notes
    except Exception:
        return []


async def rank_skill_candidates(
    *,
    task: Any,
    project: Any | None = None,
    agent_id: str = "",
    limit: int | None = None,
    db: AsyncSession | None = None,
    include_semantic: bool = False,
) -> list[SkillCandidate]:
    """Return a small learned candidate set for ReAct/planning skill use."""

    all_skills = registry.list_all()
    if not all_skills:
        return []

    query = f"{getattr(task, 'title', '')} {getattr(task, 'description', '') or ''}".strip()
    project_id = getattr(project, "id", None) or getattr(task, "project_id", "") or ""
    agent_key = agent_id or getattr(task, "agent_id", "") or ""
    candidates: dict[str, SkillCandidate] = {}

    explicit = (getattr(task, "skill_name", "") or "").strip()
    if explicit:
        _bump(candidates, explicit, 2.0, "explicit-task-skill", "explicit")

    query_lower = query.lower()
    for keyword, skill_name in SKILL_KEYWORDS.items():
        if keyword in query_lower:
            _bump(candidates, skill_name, 1.1, f"keyword:{keyword}", "keyword")

    query_tokens = _tokens(query)
    for skill in all_skills:
        skill_text = f"{skill.name} {skill.display_name} {skill.description}"
        skill_tokens = _tokens(skill_text)
        overlap = query_tokens & skill_tokens
        if overlap:
            amount = min(0.28, 0.08 + len(overlap) / max(10, len(query_tokens)) * 0.4)
            _bump(
                candidates,
                skill.name,
                amount,
                f"lexical:{','.join(sorted(overlap)[:4])}",
                "lexical",
            )

    for skill in all_skills:
        stats = skill_manager.get_usage_stats(skill.name)
        executions = int(stats.get("executions", 0) or 0)
        if executions <= 0:
            continue
        success_rate = float(stats.get("success_rate", stats.get("successes", 0) / max(executions, 1)) or 0.0)
        avg_quality = float(stats.get("avg_quality", stats.get("total_quality", 0) / max(executions, 1)) or 0.0)
        utility = float(stats.get("utility_score", 0.5) or 0.5)
        amount = min(0.18, success_rate * 0.06 + avg_quality * 0.07 + utility * 0.05)
        _bump(candidates, skill.name, amount, "memento_usage", "learned")

    telemetry_boosts = await _telemetry_quality_boost({s.name for s in all_skills}, db)
    for skill_name, amount in telemetry_boosts.items():
        _bump(candidates, skill_name, amount, "telemetry_model_quality", "learned")

    memory_boosts = await _reasoning_memory_boosts(
        project_id=project_id,
        agent_id=agent_key,
        query=query,
        db=db,
    )
    for skill_name, (amount, reasons) in memory_boosts.items():
        _bump(candidates, skill_name, amount, ",".join(sorted(set(reasons)))[:80], "learned")

    if include_semantic and query_tokens:
        try:
            from app.core.embeddings import embed_text

            task_vec = await embed_text(query[:1200])
            if task_vec:
                for skill in all_skills:
                    desc_vec = await embed_text(f"{skill.display_name} {skill.description}"[:512])
                    if not desc_vec:
                        continue
                    dot = sum(x * y for x, y in zip(task_vec, desc_vec))
                    na = math.sqrt(sum(x * x for x in task_vec))
                    nb = math.sqrt(sum(x * x for x in desc_vec))
                    cosine = dot / (na * nb) if na and nb else 0.0
                    if cosine >= 0.35:
                        _bump(
                            candidates,
                            skill.name,
                            min(0.3, cosine * 0.25),
                            f"semantic:{cosine:.2f}",
                            "semantic",
                        )
        except Exception as exc:
            logger.debug("Semantic skill candidate boost skipped: %s", exc)

    meta_notes = _meta_hyperagent_notes()
    if meta_notes:
        for candidate in candidates.values():
            candidate.reasons.extend(note for note in meta_notes if note not in candidate.reasons)

    floor = max(0.0, float(getattr(settings, "agent_react_skill_min_candidate_score", 0.12)))
    selected = [candidate for candidate in candidates.values() if candidate.score >= floor]
    selected.sort(key=lambda item: item.score, reverse=True)
    return selected[: max(1, int(limit or settings.agent_react_skill_candidate_limit))]


def format_candidate_skill_context(candidates: list[SkillCandidate]) -> str:
    if not candidates:
        return ""
    lines = ["## Candidate Research Skills"]
    for candidate in candidates:
        reason = "; ".join(candidate.reasons[:4])
        lines.append(
            f"- {candidate.name} ({candidate.phase}, score={candidate.score:.2f}): "
            f"{candidate.description[:180]} | why: {reason}"
        )
    return "\n".join(lines)


def build_run_skill_tool(candidates: list[SkillCandidate]) -> list[dict[str, Any]]:
    """Return one constrained tool whose skill_name is limited to candidates."""

    names = [candidate.name for candidate in candidates]
    if not names:
        return []
    descriptions = "; ".join(
        f"{candidate.name}: {candidate.description[:100]}" for candidate in candidates
    )
    return [
        {
            "type": "function",
            "function": {
                "name": "run_skill",
                "description": (
                    "Run one of Istara's ranked research skills when the task requires "
                    f"domain-specific UXR analysis. Candidate skills: {descriptions}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "enum": names,
                            "description": "The ranked candidate skill to run.",
                        },
                        "objective": {
                            "type": "string",
                            "description": "Specific research objective for this skill call.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Why this skill is needed now.",
                        },
                        "context": {
                            "type": "string",
                            "description": "Extra context or constraints to pass to the skill.",
                        },
                        "use_project_files": {
                            "type": "boolean",
                            "description": "Whether to attach available project files.",
                        },
                    },
                    "required": ["skill_name", "objective", "rationale"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def compact_skill_observation(skill_name: str, output: SkillOutput) -> dict[str, Any]:
    return {
        "skill_name": skill_name,
        "success": output.success,
        "json_success": output.json_success,
        "summary": (output.summary or "")[:1200],
        "counts": {
            "nuggets": len(output.nuggets),
            "facts": len(output.facts),
            "insights": len(output.insights),
            "recommendations": len(output.recommendations),
        },
        "suggestions": list(output.suggestions or [])[:3],
        "errors": list(output.errors or [])[:3],
    }


async def execute_ranked_skill_tool(
    *,
    skill_name: str,
    skill_input: SkillInput,
    trace_id: str,
    agent_id: str,
    project_id: str,
    task_id: str | None,
    timeout_seconds: float | None = None,
) -> tuple[SkillOutput, float]:
    """Execute a skill from a ReAct tool call and record local telemetry."""

    skill = registry.get(skill_name)
    if not skill:
        return (
            SkillOutput(
                success=False,
                summary=f"Skill not found: {skill_name}",
                errors=[f"Unknown skill: {skill_name}"],
            ),
            0.0,
        )
    started = time.perf_counter()
    status = "success"
    error_type = None
    error_message = None
    try:
        output = await asyncio.wait_for(
            skill.execute(skill_input),
            timeout=max(1.0, float(timeout_seconds or settings.agent_react_skill_tool_timeout_seconds)),
        )
        status = "success" if output.success else "error"
        return output, (time.perf_counter() - started) * 1000
    except TimeoutError as exc:
        status = "timeout"
        error_type = "timeout"
        error_message = str(exc)
        return (
            SkillOutput(
                success=False,
                summary=f"Skill timed out: {skill_name}",
                errors=["timeout"],
            ),
            (time.perf_counter() - started) * 1000,
        )
    except Exception as exc:
        status = "error"
        error_type = type(exc).__name__
        error_message = str(exc)
        return (
            SkillOutput(
                success=False,
                summary=f"Skill execution failed: {skill_name}",
                errors=[str(exc)],
            ),
            (time.perf_counter() - started) * 1000,
        )
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        await telemetry_recorder.record_span(
            trace_id=trace_id,
            operation="skill_execute",
            skill_name=skill_name,
            agent_id=agent_id,
            project_id=project_id,
            task_id=task_id,
            duration_ms=duration_ms,
            status=status,
            error_type=error_type,
            error_message=error_message,
            tool_name="run_skill",
            source="production",
        )
