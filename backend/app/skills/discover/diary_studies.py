"""Diary Studies skill — longitudinal self-reported user experiences."""

import json
import logging

from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType

logger = logging.getLogger(__name__)


# W5: schema for the AgenticDispatcher structured path of ``execute``
# (``skill.discover_analyze``); the dispatcher validates against it. Formalized
# from the analysis prompt's response shape — every key is read via ``.get``
# downstream, so nothing is required.
DIARY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "temporal_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "timeframe": {"type": "string"},
                },
            },
        },
        "emotional_arc": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "phase": {"type": "string"},
                    "sentiment": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "behaviors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "behavior": {"type": "string"},
                    "frequency": {"type": "string"},
                },
            },
        },
        "triggers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "trigger": {"type": "string"},
                    "resulting_behavior": {"type": "string"},
                },
            },
        },
        "pain_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "persistent": {"type": "boolean"},
                    "severity": {"type": "number"},
                },
            },
        },
        "nuggets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "day": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "summary": {"type": "string"},
    },
    "required": [],
}


class DiaryStudiesSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "diary-studies"

    @property
    def display_name(self) -> str:
        return "Diary Studies"

    @property
    def description(self) -> str:
        return (
            "Design diary study prompts, analyze entries over time, identify "
            "behavioral patterns and emotional arcs across longitudinal self-reported data."
        )

    @property
    def phase(self) -> SkillPhase:
        return SkillPhase.DISCOVER

    @property
    def skill_type(self) -> SkillType:
        return SkillType.QUALITATIVE

    async def plan(self, skill_input: SkillInput) -> dict:
        # Byte-exact prompt text: the first "Include:" line ends with a space
        # before the newline; the explicit "\n" concat keeps that byte without
        # introducing source-level trailing whitespace (ruff W291).
        prompt = (
            "Design a diary study plan for UX research.\n"
            f"Context: {skill_input.project_context or 'General UX research'}\n\n"
            "Include: study duration recommendation, entry frequency, prompt design "
            "(structured + open-ended), \n"
            "participant guidelines, reminder strategy, sample diary prompts for each day/phase,\n"
            "analysis approach, and dropout mitigation strategies. Format as Markdown."
        )
        # W5: diary study plan generation goes through the
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
        return f"""Analyze these diary study entries for UX research patterns.
Context: {skill_input.project_context or "N/A"}

Entries:
{text}

Extract:
1. Temporal patterns (how behavior/sentiment changes over time)
2. Emotional arc (mood/satisfaction trajectory)
3. Recurring behaviors and habits
4. Trigger events (what prompts specific behaviors)
5. Pain points that persist vs. resolve
6. Adaptation patterns (how users learn/adjust)
7. Key nuggets with timestamps
8. Participant-level summaries

JSON format:
{{"temporal_patterns": [{{"pattern": "...", "timeframe": "..."}}],
"emotional_arc": [{{"phase": "...", "sentiment": "positive|neutral|negative", \
"description": "..."}}],
"behaviors": [{{"behavior": "...", "frequency": "daily|weekly|occasional"}}],
"triggers": [{{"trigger": "...", "resulting_behavior": "..."}}],
"pain_points": [{{"issue": "...", "persistent": true, "severity": 1-5}}],
"nuggets": [{{"text": "...", "day": "...", "tags": ["..."]}}],
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
            schema=DIARY_ANALYSIS_SCHEMA,
            empty_label="diary-study",
        )
        nuggets = [
            {"text": n["text"], "source": source, "tags": n.get("tags", [])}
            for source, window_nuggets in labelled
            for n in window_nuggets
            if isinstance(n, dict) and n.get("text")
        ]

        facts, insights, recommendations, errors = await synthesise_findings(
            skill_input, method="diary study", nuggets=nuggets, analysis=data
        )
        return SkillOutput(
            success=bool(nuggets),
            summary=data.get(
                "summary", f"Analyzed diary entries. {len(nuggets)} nuggets extracted."
            ),
            nuggets=nuggets,
            facts=facts,
            insights=insights,
            recommendations=recommendations,
            errors=errors,
            artifacts={
                "diary_analysis.json": json.dumps(data, indent=2),
                "input_coverage.json": json.dumps(coverage, indent=2),
            },
        )
