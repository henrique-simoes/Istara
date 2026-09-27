"""User Interviews skill — the reference implementation for Istara skills.

Capabilities:
- Generate interview guides based on research questions
- Process interview transcripts (extract nuggets, themes, patterns)
- Identify follow-up questions and research gaps
- Synthesize findings across multiple interviews
"""

import json
import logging
from pathlib import Path

from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType

logger = logging.getLogger(__name__)


INTERVIEW_GUIDE_PROMPT = """You are an expert UX Researcher creating an interview guide.

## Context
{context}

## Research Questions
{research_questions}

## Instructions
Create a semi-structured interview guide with:
1. **Introduction script** (2-3 sentences to put the participant at ease)
2. **Warm-up questions** (2-3 easy questions to build rapport)
3. **Core questions** (8-12 questions organized by theme, each with 2-3 probing follow-ups)
4. **Closing questions** (2-3 wrap-up questions including "Is there anything else?")
5. **Debrief script** (thank them, explain next steps)

For each core question, include:
- The main question
- Why you're asking it (research goal)
- 2-3 follow-up probes
- Things to watch for (body language, hesitation, emotion)

Format as clean Markdown."""


TRANSCRIPT_ANALYSIS_PROMPT = """You are an expert UX Researcher analyzing an interview transcript.

## Project Context
{context}

## Interview Transcript
{transcript}

## Instructions
Analyze this interview transcript and extract:

### 1. Nuggets (Direct Evidence)
Extract 5-15 key quotes or observations. For each:
- The exact quote or paraphrased observation
- Timestamp or location in the transcript (if available)
- Relevant tags (themes it relates to)
- Emotional tone (neutral, positive, negative, frustrated, excited, etc.)

### 2. Key Themes
Identify 3-7 recurring themes with:
- Theme name
- Brief description
- Supporting nugget references
- Strength (how many data points support it)

### 3. Pain Points
List specific pain points mentioned or implied:
- Description
- Severity (1-5)
- Frequency indicator (mentioned once vs. recurring)

### 4. Opportunities
Positive signals or unmet needs that suggest opportunities:
- Description
- Potential impact

### 5. Follow-up Questions
3-5 questions you'd want to explore in the next interview based on what you learned.

### 6. Participant Summary
A 2-3 sentence summary of this participant's experience and perspective.

Respond in valid JSON with this structure:
{{
    "nuggets": [{{"text": "...", "location": "...", "tags": ["..."], "tone": "..."}}],
    "themes": [{{"name": "...", "description": "...", "strength": 1-5}}],
    "pain_points": [{{"description": "...", "severity": 1-5, "frequency": "once|recurring"}}],
    "opportunities": [{{"description": "...", "impact": "low|medium|high"}}],
    "follow_up_questions": ["..."],
    "participant_summary": "..."
}}"""


SYNTHESIS_PROMPT = (
    """You are an expert UX Researcher synthesizing findings """
    """across multiple interviews.

## Project Context
{context}

## Individual Interview Analyses
{analyses}

## Instructions
Synthesize the findings across all interviews:

### 1. Cross-cutting Themes
Identify themes that appear across multiple interviews:
- Theme name and description
- How many participants mentioned it
- Key supporting quotes
- Confidence level (high/medium/low based on evidence strength)

### 2. Facts (Verified Claims)
Statements that are supported by multiple data points:
- The fact statement
- Number of supporting data points
- Sources

### 3. Insights (Patterns & Conclusions)
Higher-level patterns you see across the data:
- The insight
- Supporting facts
- Confidence level
- Potential impact on the project

### 4. Recommendations
What should the team do based on these findings:
- Recommendation
- Supporting insights
- Priority (low/medium/high/critical)
- Effort estimate (low/medium/high)

### 5. Research Gaps
What questions remain unanswered:
- Gap description
- Suggested method to fill it
- Priority

Respond in valid JSON with this structure:
{{
    "themes": [{{"name": "...", "description": "...", "participant_count": 0, \
"quotes": ["..."], "confidence": "high|medium|low"}}],
    "facts": [{{"text": "...", "evidence_count": 0, "sources": ["..."]}}],
    "insights": [{{"text": "...", "supporting_facts": ["..."], \
"confidence": "high|medium|low", "impact": "low|medium|high"}}],
    "recommendations": [{{"text": "...", "supporting_insights": ["..."], \
"priority": "low|medium|high|critical", "effort": "low|medium|high"}}],
    "research_gaps": [{{"description": "...", "suggested_method": "...", \
"priority": "low|medium|high"}}]
}}"""
)


# W5: schemas for the AgenticDispatcher structured paths of ``execute``
# (``skill.discover_analyze``); the dispatcher validates against them.
# Formalized from the TRANSCRIPT_ANALYSIS_PROMPT / SYNTHESIS_PROMPT response
# shapes — every key is read via ``.get`` downstream, so nothing is required.
TRANSCRIPT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "nuggets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "location": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "tone": {"type": "string"},
                },
            },
        },
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "strength": {"type": "number"},
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
                    "frequency": {"type": "string"},
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
        "follow_up_questions": {"type": "array", "items": {"type": "string"}},
        "participant_summary": {"type": "string"},
    },
    "required": [],
}


SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "participant_count": {"type": "number"},
                    "quotes": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string"},
                },
            },
        },
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "evidence_count": {"type": "number"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "supporting_facts": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string"},
                    "impact": {"type": "string"},
                },
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "supporting_insights": {"type": "array", "items": {"type": "string"}},
                    "priority": {"type": "string"},
                    "effort": {"type": "string"},
                },
            },
        },
        "research_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "suggested_method": {"type": "string"},
                    "priority": {"type": "string"},
                },
            },
        },
    },
    "required": [],
}


class UserInterviewsSkill(BaseSkill):
    """Skill for planning, conducting, and analyzing user interviews."""

    @property
    def name(self) -> str:
        return "user-interviews"

    @property
    def display_name(self) -> str:
        return "User Interviews"

    @property
    def description(self) -> str:
        return (
            "Plan, conduct, and analyze user interviews. "
            "Generate interview guides, process transcripts, extract nuggets and themes, "
            "and synthesize findings across multiple interviews."
        )

    @property
    def phase(self) -> SkillPhase:
        return SkillPhase.DISCOVER

    @property
    def skill_type(self) -> SkillType:
        return SkillType.QUALITATIVE

    async def plan(self, skill_input: SkillInput) -> dict:
        """Generate an interview research plan."""
        research_questions = skill_input.parameters.get(
            "research_questions", "Understand user experience and pain points"
        )
        num_participants = skill_input.parameters.get("num_participants", 5)

        context_parts = []
        if skill_input.company_context:
            context_parts.append(f"Company: {skill_input.company_context}")
        if skill_input.project_context:
            context_parts.append(f"Project: {skill_input.project_context}")
        if skill_input.user_context:
            context_parts.append(f"Additional context: {skill_input.user_context}")

        context = "\n".join(context_parts) if context_parts else "No additional context provided."

        # Generate interview guide
        prompt = INTERVIEW_GUIDE_PROMPT.format(
            context=context,
            research_questions=research_questions,
        )

        # W5: interview guide generation goes through the
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
        guide_content = outcome.text

        return {
            "skill": self.name,
            "plan_type": "interview_guide",
            "research_questions": research_questions,
            "recommended_participants": num_participants,
            "estimated_time_per_interview": "45-60 minutes",
            "guide": guide_content,
            "steps": [
                f"Recruit {num_participants} participants matching your target audience",
                "Review and customize the interview guide below",
                "Conduct interviews (record with consent)",
                "Upload transcripts to Istara for analysis",
                "Review extracted nuggets and themes",
                "Synthesize findings across all interviews",
            ],
        }

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        """Process interview transcripts and extract findings."""
        mode = skill_input.parameters.get("mode", "analyze")

        if mode == "plan":
            plan = await self.plan(skill_input)
            return SkillOutput(
                success=True,
                summary="Interview guide generated.",
                artifacts={"interview_guide.md": plan["guide"]},
                suggestions=plan["steps"],
            )

        # Analyze mode — process transcript files or inline context
        context_parts = []
        if skill_input.project_context:
            context_parts.append(skill_input.project_context)
        if skill_input.company_context:
            context_parts.append(skill_input.company_context)
        if skill_input.user_context:
            context_parts.append(skill_input.user_context)
        context = "\n".join(context_parts) if context_parts else "No context."

        if not skill_input.files and not skill_input.user_context:
            return SkillOutput(
                success=False,
                summary="No files provided for analysis.",
                errors=["Please provide interview transcript files."],
            )

        # Process each transcript
        all_analyses = []
        all_nuggets = []
        all_errors = []

        # D-14/D-15: read every transcript in full, with its own file name, in windows sized to
        # the model that serves the skill. Nothing is cut at a fixed character count.
        from app.skills.skill_windows import (
            extraction_char_budget,
            plan_windows,
            read_sources,
            resolve_call_budget,
            window_char_budget,
        )

        sources = read_sources(skill_input.files) if skill_input.files else []
        for file_path_str in skill_input.files or []:
            if Path(file_path_str).name not in {name for name, _ in sources}:
                all_errors.append(f"Could not read {Path(file_path_str).name}")
        if not sources and skill_input.user_context:
            sources = [("inline-context", skill_input.user_context)]
        budget = resolve_call_budget(skill_input.project_id)
        window_chars = extraction_char_budget(budget, 1500)
        # Synthesis reads the analyses, not the transcripts: it may use the whole context.
        synthesis_chars = window_char_budget(budget, 1500)
        passages = [
            (name, window.text)
            for name, text in sources
            for window in plan_windows([(name, text)], window_chars)
        ]
        coverage = {
            "source_files": len(sources),
            "source_chars": sum(len(text) for _, text in sources),
            "passages": len(passages),
            "context_tokens": budget.context_tokens,
            "budget_basis": budget.basis,
        }

        for source_name, transcript in passages:
            # Analyze the transcript
            prompt = TRANSCRIPT_ANALYSIS_PROMPT.format(
                context=context,
                transcript=transcript,
            )

            # W5: transcript analysis goes through the AgenticDispatcher
            # (``skill.discover_analyze``) with TRANSCRIPT_ANALYSIS_SCHEMA
            # driving the engine.
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            try:
                outcome = await agentic.structured(
                    purpose="skill.discover_analyze",
                    project_id=skill_input.project_id,
                    system=None,
                    messages=[{"role": "user", "content": prompt}],
                    schema=TRANSCRIPT_ANALYSIS_SCHEMA,
                    params=TurnParams(temperature=0.3),
                    spine_phase="synthesis",
                )
                if outcome.status == "success" and outcome.value:
                    analysis = outcome.value
                else:
                    analysis = {"raw_analysis": outcome.text}
            except Exception as e:
                # F-W5-2: the Pi engine raises PiRuntimeTurnError on
                # invalid structured output instead of returning
                # status != "success"; degrade to raw_analysis fallback.
                logger.warning("Transcript analysis raised; degrading to raw_analysis: %s", e)
                analysis = {"raw_analysis": ""}

            analysis["source_file"] = source_name
            all_analyses.append(analysis)

            # Extract nuggets
            for nugget_data in analysis.get("nuggets", []):
                all_nuggets.append(
                    {
                        "text": nugget_data.get("text", ""),
                        "source": source_name,
                        "source_location": nugget_data.get("location", ""),
                        "tags": nugget_data.get("tags", []),
                    }
                )

        # Synthesize facts, insights and recommendations across every analysed passage, also for a
        # single transcript (SK1): the analyses go in whole when they fit, otherwise the passage
        # themes and nuggets that fit.
        synthesis = None
        # Nothing to synthesise when no passage yielded a nugget (a failed analysis, SK4).
        if all_analyses and any(a.get("nuggets") for a in all_analyses):
            analyses_text = json.dumps(all_analyses, indent=2)
            if len(analyses_text) > synthesis_chars:
                compact = [
                    {
                        "source_file": a.get("source_file"),
                        "themes": a.get("themes", []),
                        "nuggets": [n.get("text", "") for n in a.get("nuggets", [])],
                    }
                    for a in all_analyses
                ]
                analyses_text = json.dumps(compact, indent=1)[:synthesis_chars]
            synthesis_prompt = SYNTHESIS_PROMPT.format(
                context=context,
                analyses=analyses_text,
            )

            # W5: cross-interview synthesis goes through the
            # AgenticDispatcher (``skill.discover_analyze``) — the result
            # is JSON-parsed below, so it uses the structured verb with
            # SYNTHESIS_SCHEMA driving the engine.
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            try:
                outcome = await agentic.structured(
                    purpose="skill.discover_analyze",
                    project_id=skill_input.project_id,
                    system=None,
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    schema=SYNTHESIS_SCHEMA,
                    params=TurnParams(temperature=0.3),
                    spine_phase="synthesis",
                )
                if outcome.status == "success" and outcome.value:
                    synthesis = outcome.value
                else:
                    synthesis = {"raw_synthesis": outcome.text}
            except Exception as e:
                # F-W5-2: the Pi engine raises PiRuntimeTurnError on
                # invalid structured output instead of returning
                # status != "success"; degrade to raw_synthesis fallback.
                logger.warning("Interview synthesis raised; degrading to raw_synthesis: %s", e)
                synthesis = {"raw_synthesis": ""}

        # Build output
        facts = []
        insights = []
        recommendations = []
        suggestions = []

        if synthesis:
            facts = [{"text": f["text"]} for f in synthesis.get("facts", [])]
            # The support each insight and recommendation names travels with it, so storage links
            # it to the findings it cites (finding_links), not to whichever came last.
            insights = [
                {
                    "text": i["text"],
                    "confidence": i.get("confidence", "medium"),
                    "supporting_facts": i.get("supporting_facts", []),
                }
                for i in synthesis.get("insights", [])
            ]
            recommendations = [
                {
                    "text": r["text"],
                    "priority": r.get("priority", "medium"),
                    "effort": r.get("effort", "medium"),
                    "supporting_insights": r.get("supporting_insights", []),
                }
                for r in synthesis.get("recommendations", [])
            ]
            for gap in synthesis.get("research_gaps", []):
                suggestions.append(
                    f"Research gap: {gap['description']} — "
                    f"Consider: {gap.get('suggested_method', 'further investigation')}"
                )

        # Generate summary
        summary = (
            f"Analyzed {len(sources)} transcript(s) in full ({len(passages)} passage(s), "
            f"{len(all_analyses)} analysed). "
            f"Extracted {len(all_nuggets)} nuggets, {len(facts)} facts, "
            f"{len(insights)} insights, {len(recommendations)} recommendations."
        )

        return SkillOutput(
            success=len(all_errors) == 0 or len(all_analyses) > 0,
            summary=summary,
            nuggets=all_nuggets,
            facts=facts,
            insights=insights,
            recommendations=recommendations,
            artifacts={
                "analysis.json": json.dumps(all_analyses, indent=2),
                "input_coverage.json": json.dumps(
                    {**coverage, "delivered_chars": coverage["source_chars"], "coverage": 1.0}
                    if coverage["source_chars"]
                    else coverage,
                    indent=2,
                ),
                **({"synthesis.json": json.dumps(synthesis, indent=2)} if synthesis else {}),
            },
            suggestions=suggestions,
            errors=all_errors,
        )
