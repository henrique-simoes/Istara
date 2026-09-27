"""Contextual Inquiry skill — observe users in their natural environment."""

import json
import logging

from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType

logger = logging.getLogger(__name__)


# W5: schema for the AgenticDispatcher structured path of ``execute``
# (``skill.discover_analyze``); the dispatcher validates against it. Formalized
# from the analysis prompt's response shape — every key is read via ``.get``
# downstream, so nothing is required.
CONTEXTUAL_INQUIRY_SCHEMA = {
    "type": "object",
    "properties": {
        "activities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "frequency": {"type": "string"},
                },
            },
        },
        "environment_factors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "factor": {"type": "string"},
                    "impact": {"type": "string"},
                },
            },
        },
        "interactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "with": {"type": "string"},
                },
            },
        },
        "pain_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "severity": {"type": "number"},
                    "workaround": {"type": "string"},
                },
            },
        },
        "workflow_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "participants": {"type": "number"},
                },
            },
        },
        "nuggets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "context": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "opportunities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "impact": {"type": "string"},
                },
            },
        },
        "summary": {"type": "string"},
    },
    "required": [],
}


class ContextualInquirySkill(BaseSkill):
    @property
    def name(self) -> str:
        return "contextual-inquiry"

    @property
    def display_name(self) -> str:
        return "Contextual Inquiry"

    @property
    def description(self) -> str:
        return (
            "Structure and analyze contextual inquiry observations — studying users "
            "in their natural work environment."
        )

    @property
    def phase(self) -> SkillPhase:
        return SkillPhase.DISCOVER

    @property
    def skill_type(self) -> SkillType:
        return SkillType.QUALITATIVE

    async def plan(self, skill_input: SkillInput) -> dict:
        prompt = f"""Create a contextual inquiry observation plan for UX research.
Context: {skill_input.project_context or "General UX research"}
User context: {skill_input.user_context or "Not specified"}

Include:
1. Observation objectives (what to look for)
2. Pre-visit preparation checklist
3. Observation framework (AEIOU: Activities, Environments, Interactions, Objects, Users)
4. Interview prompts to use during observation ("Tell me what you're doing now", \
"Why did you do that?")
5. Note-taking template structure
6. Post-observation debrief questions
7. Ethical considerations and consent requirements

Format as Markdown."""
        # W5: observation plan generation goes through the
        # AgenticDispatcher (``skill.discover_plan``).
        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        outcome = await agentic.completion(
            purpose="skill.discover_plan",
            project_id=skill_input.project_id,
            system=None,
            messages=[{"role": "user", "content": prompt}],
            params=TurnParams(temperature=0.7),
            spine_phase="plan",
        )
        plan_text = outcome.text
        return {"skill": self.name, "plan": plan_text}

    def _prompt(self, skill_input: SkillInput, text: str) -> str:
        return f"""Analyze these contextual inquiry observation notes for UX research.

Project context: {skill_input.project_context or "Not specified"}

Observation notes:
{text}

Extract and structure:
1. **Activities observed** — what users were doing, step by step
2. **Environment factors** — physical/digital context affecting behavior
3. **Interactions** — how users interacted with tools, people, systems
4. **Pain points** — friction, workarounds, frustrations observed
5. **Workflow patterns** — recurring sequences, habits, shortcuts
6. **Nuggets** — specific quotes or observations (with context)
7. **Opportunities** — unmet needs or improvement areas
8. **Cultural/social factors** — team dynamics, norms, communication patterns

Respond in JSON:
{{"activities": [{{"description": "...", "frequency": "common|occasional|rare"}}],
"environment_factors": [{{"factor": "...", "impact": "positive|negative|neutral"}}],
"interactions": [{{"description": "...", "with": "tool|person|system"}}],
"pain_points": [{{"description": "...", "severity": 1-5, "workaround": "..."}}],
"workflow_patterns": [{{"pattern": "...", "participants": 0}}],
"nuggets": [{{"text": "...", "context": "...", "tags": ["..."]}}],
"opportunities": [{{"description": "...", "impact": "low|medium|high"}}],
"summary": "..."}}"""

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        # Every window of the input is analysed (D-16); nuggets keep the file they came from.
        from app.skills.skill_windows import analyse_in_windows, synthesise_findings

        if not skill_input.files and not skill_input.user_context:
            return SkillOutput(
                success=False,
                summary="No input provided.",
                errors=["Provide files or inline notes."],
            )
        data, labelled, coverage = await analyse_in_windows(
            skill_input,
            build_prompt=lambda text: self._prompt(skill_input, text),
            schema=CONTEXTUAL_INQUIRY_SCHEMA,
            empty_label="contextual-inquiry",
        )
        nuggets = [
            {"text": n["text"], "source": source, "tags": n.get("tags", [])}
            for source, window_nuggets in labelled
            for n in window_nuggets
            if isinstance(n, dict) and n.get("text")
        ]

        facts, insights, recommendations, errors = await synthesise_findings(
            skill_input, method="contextual inquiry", nuggets=nuggets, analysis=data
        )
        return SkillOutput(
            success=bool(nuggets),
            summary=data.get(
                "summary", f"Analyzed contextual inquiry notes. Found {len(nuggets)} nuggets."
            ),
            nuggets=nuggets,
            facts=facts,
            insights=insights,
            recommendations=recommendations,
            errors=errors,
            artifacts={
                "analysis.json": json.dumps(data, indent=2),
                "input_coverage.json": json.dumps(coverage, indent=2),
            },
        )
