"""Channel Research Deployment skill — deploy interviews, surveys, and diary studies via messaging.

Deploys research studies across Telegram, Slack, WhatsApp, and Google Chat
with adaptive questioning, rate limiting, and real-time analytics.
"""

import json
import logging

from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType

logger = logging.getLogger(__name__)


DEPLOYMENT_PLAN_PROMPT = """You are an expert UX Researcher planning a research deployment via messaging channels.

## Context
{context}

## Research Goals
{research_goals}

## Deployment Type
{deployment_type}

## Instructions
Create a research deployment plan including:

1. **Study Design** — What type of study, target participants, and expected duration
2. **Question Set** — 5-10 questions appropriate for the deployment type:
   - For interviews: open-ended, probing questions
   - For surveys: mix of open and closed questions
   - For diary studies: daily/weekly prompts
3. **Adaptive Rules** — When to ask follow-up probes, skip logic, and branching
4. **Channel Strategy** — Which messaging channels to use and why
5. **Completion Criteria** — Target responses, saturation indicators
6. **Ethical Considerations** — Consent, data handling, participant well-being

For each question, include:
- The question text
- Question type (open | scale | multiple_choice | yes_no)
- Expected insight (what you hope to learn)
- Follow-up triggers (when to probe deeper)

Respond in valid JSON:
{{
    "study_design": {{
        "type": "{deployment_type}",
        "description": "...",
        "target_participants": 0,
        "estimated_duration_days": 0
    }},
    "questions": [
        {{
            "text": "...",
            "type": "open",
            "expected_insight": "...",
            "follow_up_triggers": ["..."]
        }}
    ],
    "adaptive_rules": {{
        "probe_short_answers": true,
        "min_words_for_skip_probe": 15,
        "max_probes_per_question": 2,
        "saturation_check": true
    }},
    "channel_strategy": "...",
    "completion_criteria": {{
        "target_responses": 0,
        "saturation_threshold": 0
    }},
    "ethical_notes": ["..."]
}}"""


ANALYSIS_PROMPT = """You are an expert UX Researcher analyzing responses from a channel-deployed {deployment_type}.

## Deployment Summary
Name: {deployment_name}
Type: {deployment_type}
Responses collected: {response_count}

## Response Data
{responses}

## Instructions
Analyze the collected responses and propose candidate Research Spine artifacts.
These artifacts are provisional: they are not accepted Atomic Research evidence
until raw response evidence units pass independent coding, reliability checks,
and review/reconciliation gates.

### 1. Key Themes
Identify recurring patterns across responses.

### 2. Candidate Atomic Observations
Extract 5-15 source-grounded candidate observations with source attribution.
Prefer direct quotes. If you paraphrase, mark the item as lower confidence.

### 3. Candidate Insights
Higher-level patterns and conclusions that remain provisional until accepted.

### 4. Candidate Recommendations
Actionable next steps based on candidate findings.

### 5. Data Quality Assessment
- Response quality (depth, relevance)
- Potential biases
- Gaps in coverage

Respond in valid JSON:
{{
    "themes": [{{"name": "...", "description": "...", "frequency": 0, "confidence": "high|medium|low"}}],
    "candidate_nuggets": [{{"text": "...", "source": "...", "source_location": "...", "source_quote": "...", "tags": ["..."], "confidence": "high|medium|low"}}],
    "candidate_insights": [{{"text": "...", "confidence": "high|medium|low", "impact": "low|medium|high"}}],
    "candidate_recommendations": [{{"text": "...", "priority": "low|medium|high|critical", "effort": "low|medium|high"}}],
    "data_quality": {{
        "overall_quality": "high|medium|low",
        "biases": ["..."],
        "gaps": ["..."]
    }}
}}"""


# W5: schema for the AgenticDispatcher structured path of ``_analyze``
# (``skill.discover_analyze``); the dispatcher validates against it. Formalized
# from the ANALYSIS_PROMPT response shape — every key is read via ``.get``
# downstream, so nothing is required.
DEPLOYMENT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "frequency": {"type": "number"},
                    "confidence": {"type": "string"},
                },
            },
        },
        "candidate_nuggets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source": {"type": "string"},
                    "source_location": {"type": "string"},
                    "source_quote": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string"},
                },
            },
        },
        "candidate_insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "confidence": {"type": "string"},
                    "impact": {"type": "string"},
                },
            },
        },
        "candidate_recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "priority": {"type": "string"},
                    "effort": {"type": "string"},
                },
            },
        },
        "data_quality": {
            "type": "object",
            "properties": {
                "overall_quality": {"type": "string"},
                "biases": {"type": "array", "items": {"type": "string"}},
                "gaps": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "required": [],
}


class ChannelResearchDeploymentSkill(BaseSkill):
    """Skill for deploying and analyzing research via messaging channels."""

    @property
    def name(self) -> str:
        return "channel-research-deployment"

    @property
    def display_name(self) -> str:
        return "Channel Research Deployment"

    @property
    def description(self) -> str:
        return (
            "Deploy interviews, surveys, and diary studies via messaging channels "
            "(Telegram, Slack, WhatsApp, Google Chat) with adaptive questioning. "
            "Supports real-time analytics, LLM-powered probing, and provisional "
            "candidate evidence extraction for Research Spine validation."
        )

    @property
    def phase(self) -> SkillPhase:
        return SkillPhase.DISCOVER

    @property
    def skill_type(self) -> SkillType:
        return SkillType.MIXED

    @property
    def version(self) -> str:
        return "1.0.0"

    async def plan(self, skill_input: SkillInput) -> dict:
        """Generate a deployment plan with questions and adaptive rules."""
        deployment_type = skill_input.parameters.get("deployment_type", "interview")
        research_goals = skill_input.parameters.get(
            "research_goals", "Understand user experience and identify pain points"
        )

        context_parts = []
        if skill_input.company_context:
            context_parts.append(f"Company: {skill_input.company_context}")
        if skill_input.project_context:
            context_parts.append(f"Project: {skill_input.project_context}")
        if skill_input.user_context:
            context_parts.append(f"Additional context: {skill_input.user_context}")
        context = "\n".join(context_parts) if context_parts else "No additional context."

        prompt = DEPLOYMENT_PLAN_PROMPT.format(
            context=context,
            research_goals=research_goals,
            deployment_type=deployment_type,
        )

        # W5: deployment plan generation goes through the
        # AgenticDispatcher (``skill.discover_plan``) — prose/JSON text
        # with the same downstream parse-and-fallback handling.
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
        response_text = outcome.text

        # Parse JSON from response
        plan_data = {}
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                plan_data = json.loads(response_text[json_start:json_end])
        except json.JSONDecodeError:
            plan_data = {"raw_plan": response_text}

        return {
            "skill": self.name,
            "plan_type": "channel_deployment",
            "deployment_type": deployment_type,
            "research_goals": research_goals,
            **plan_data,
            "steps": [
                "Review the generated questions and adapt to your context",
                "Configure channel instances (Telegram, Slack, etc.)",
                "Create a deployment with the question set",
                "Activate the deployment to start collecting responses",
                "Monitor real-time analytics as responses come in",
                "Complete the deployment and analyze aggregated findings",
            ],
        }

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        """Execute the skill — either plan a deployment or analyze collected data."""
        mode = skill_input.parameters.get("mode", "plan")

        if mode == "plan":
            plan = await self.plan(skill_input)
            return SkillOutput(
                success=True,
                summary=f"Generated deployment plan for {plan.get('deployment_type', 'interview')}.",
                artifacts={"deployment_plan.json": json.dumps(plan, indent=2)},
                suggestions=plan.get("steps", []),
            )

        if mode == "analyze":
            return await self._analyze(skill_input)

        return SkillOutput(
            success=False,
            summary=f"Unknown mode: {mode}",
            errors=[f"Supported modes: plan, analyze. Got: {mode}"],
        )

    async def _analyze(self, skill_input: SkillInput) -> SkillOutput:
        """Analyze collected deployment responses."""
        deployment_name = skill_input.parameters.get("deployment_name", "Unnamed")
        deployment_type = skill_input.parameters.get("deployment_type", "interview")
        responses_data = skill_input.parameters.get("responses", [])
        response_count = len(responses_data)

        if not responses_data and skill_input.user_context:
            responses_text = skill_input.user_context
        else:
            responses_text = json.dumps(responses_data, indent=2)

        context_parts = []
        if skill_input.project_context:
            context_parts.append(skill_input.project_context)
        if skill_input.company_context:
            context_parts.append(skill_input.company_context)

        prompt = ANALYSIS_PROMPT.format(
            deployment_type=deployment_type,
            deployment_name=deployment_name,
            response_count=response_count,
            responses=responses_text[:8000],
        )

        # W5: deployment response analysis goes through the
        # AgenticDispatcher (``skill.discover_analyze``) with
        # DEPLOYMENT_ANALYSIS_SCHEMA driving the engine.
        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        try:
            outcome = await agentic.structured(
                purpose="skill.discover_analyze",
                project_id=skill_input.project_id,
                system=None,
                messages=[{"role": "user", "content": prompt}],
                schema=DEPLOYMENT_ANALYSIS_SCHEMA,
                params=TurnParams(temperature=0.3),
                spine_phase="synthesis",
            )
            if outcome.status == "success" and outcome.value:
                analysis = outcome.value
            else:
                analysis = {"raw_analysis": outcome.text}
        except Exception as e:
            # F-W5-2: the Pi engine raises PiRuntimeTurnError on invalid
            # structured output instead of returning status != "success";
            # degrade to the same raw-analysis fallback.
            logger.warning("Channel deployment raised; degrading to raw_analysis: %s", e)
            analysis = {"raw_analysis": ""}

        research_validity = {
            "status": "provisional",
            "artifact_state": "candidate_atom",
            "report_allowed": False,
            "reason": (
                "Channel deployment analysis is model-generated candidate research. "
                "It must be grounded in raw response evidence units and accepted by "
                "coding, reliability, reconciliation, and Done-task gates before reports."
            ),
            "policy": "channel_deployment_analysis_outputs_are_candidates_until_spine_acceptance",
        }

        # Build output. Keep SkillOutput's existing field names for framework
        # compatibility, but mark every generated research artifact as candidate.
        candidate_nuggets = analysis.get("candidate_nuggets") or analysis.get("nuggets", [])
        nuggets = [
            {
                "text": n.get("text", ""),
                "source": n.get("source", f"deployment:{deployment_name}"),
                "source_location": n.get(
                    "source_location",
                    f"deployment:{deployment_name}:response:unverified",
                ),
                "source_quote": n.get("source_quote", n.get("quote", "")),
                "tags": n.get("tags", [deployment_type, "channel-research"]),
                "confidence": n.get("confidence", "medium"),
                "artifact_state": "candidate_atom",
                "research_validity": research_validity,
            }
            for n in candidate_nuggets
        ]

        candidate_insights = analysis.get("candidate_insights") or analysis.get("insights", [])
        insights = [
            {
                "text": i.get("text", ""),
                "confidence": i.get("confidence", "medium"),
                "impact": i.get("impact", "medium"),
                "artifact_state": "candidate_insight",
                "research_validity": research_validity,
            }
            for i in candidate_insights
        ]

        candidate_recommendations = analysis.get("candidate_recommendations") or analysis.get(
            "recommendations", []
        )
        recommendations = [
            {
                "text": r.get("text", ""),
                "priority": r.get("priority", "medium"),
                "effort": r.get("effort", "medium"),
                "artifact_state": "candidate_recommendation",
                "research_validity": research_validity,
            }
            for r in candidate_recommendations
        ]

        normalized_analysis = {
            **analysis,
            "research_validity": research_validity,
            "candidate_nuggets": nuggets,
            "candidate_insights": insights,
            "candidate_recommendations": recommendations,
        }

        summary = (
            f"Analyzed {response_count} responses from {deployment_type} deployment "
            f"'{deployment_name}'. Proposed {len(nuggets)} candidate nuggets, "
            f"{len(insights)} candidate insights, and "
            f"{len(recommendations)} candidate recommendations for Research Spine review."
        )

        return SkillOutput(
            success=True,
            summary=summary,
            nuggets=nuggets,
            insights=insights,
            recommendations=recommendations,
            artifacts={"deployment_analysis.json": json.dumps(normalized_analysis, indent=2)},
            suggestions=[
                f"Review the {len(nuggets)} candidate nuggets against raw response spans",
                "Run governed coding and reliability checks before accepting any artifact",
                "Keep candidate insights and recommendations out of reports until Done gates pass",
            ],
        )
