"""Diary Studies skill — longitudinal self-reported user experiences."""

import json
import logging
from app.core.file_processor import process_file
from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType
from pathlib import Path

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
        return "Design diary study prompts, analyze entries over time, identify behavioral patterns and emotional arcs across longitudinal self-reported data."

    @property
    def phase(self) -> SkillPhase:
        return SkillPhase.DISCOVER

    @property
    def skill_type(self) -> SkillType:
        return SkillType.QUALITATIVE

    async def plan(self, skill_input: SkillInput) -> dict:
        prompt = f"""Design a diary study plan for UX research.
Context: {skill_input.project_context or "General UX research"}

Include: study duration recommendation, entry frequency, prompt design (structured + open-ended), 
participant guidelines, reminder strategy, sample diary prompts for each day/phase,
analysis approach, and dropout mitigation strategies. Format as Markdown."""
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

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        texts = []
        for f in skill_input.files or []:
            r = process_file(Path(f))
            if not r.error and r.chunks:
                texts.append("\n".join(c.text for c in r.chunks))

        # Fallback: use user_context as inline diary data
        if not texts and skill_input.user_context:
            texts.append(skill_input.user_context)

        if not texts:
            return SkillOutput(
                success=False,
                summary="No diary entries provided.",
                errors=["Upload diary entry files."],
            )

        prompt = f"""Analyze these diary study entries for UX research patterns.
Context: {skill_input.project_context or "N/A"}

Entries:
{chr(10).join(texts)[:8000]}

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
"emotional_arc": [{{"phase": "...", "sentiment": "positive|neutral|negative", "description": "..."}}],
"behaviors": [{{"behavior": "...", "frequency": "daily|weekly|occasional"}}],
"triggers": [{{"trigger": "...", "resulting_behavior": "..."}}],
"pain_points": [{{"issue": "...", "persistent": true, "severity": 1-5}}],
"nuggets": [{{"text": "...", "day": "...", "tags": ["..."]}}],
"summary": "..."}}"""

        # W5: diary-entry analysis goes through the AgenticDispatcher
        # (``skill.discover_analyze``) with DIARY_ANALYSIS_SCHEMA driving
        # the engine.
        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        try:
            outcome = await agentic.structured(
                purpose="skill.discover_analyze",
                project_id=skill_input.project_id,
                system=None,
                messages=[{"role": "user", "content": prompt}],
                schema=DIARY_ANALYSIS_SCHEMA,
                params=TurnParams(temperature=0.3),
                spine_phase="synthesis",
            )
            data = outcome.value if outcome.status == "success" and outcome.value else {}
        except Exception as e:
            # F-W5-2: the Pi engine raises PiRuntimeTurnError on invalid
            # structured output instead of returning status != "success";
            # degrade to the same empty-result fallback.
            logger.warning("Diary study analysis raised; degrading to empty analysis: %s", e)
            data = {}

        nuggets = [
            {"text": n["text"], "source": "diary-study", "tags": n.get("tags", [])}
            for n in data.get("nuggets", [])
        ]
        return SkillOutput(
            success=True,
            summary=data.get(
                "summary", f"Analyzed diary entries. {len(nuggets)} nuggets extracted."
            ),
            nuggets=nuggets,
            artifacts={"diary_analysis.json": json.dumps(data, indent=2)},
        )
