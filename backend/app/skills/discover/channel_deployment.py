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
Analyze the collected responses and extract:

### 1. Key Themes
Identify recurring patterns across responses.

### 2. Nuggets (Evidence)
Extract 5-15 direct quotes or paraphrased observations with source attribution.

### 3. Insights
Higher-level patterns and conclusions from the data.

### 4. Recommendations
Actionable next steps based on findings.

### 5. Data Quality Assessment
- Response quality (depth, relevance)
- Potential biases
- Gaps in coverage

Respond in valid JSON:
{{
    "themes": [{{"name": "...", "description": "...", "frequency": 0, "confidence": "high|medium|low"}}],
    "nuggets": [{{"text": "...", "source": "...", "tags": ["..."]}}],
    "insights": [{{"text": "...", "confidence": "high|medium|low", "impact": "low|medium|high"}}],
    "recommendations": [{{"text": "...", "priority": "low|medium|high|critical", "effort": "low|medium|high"}}],
    "data_quality": {{
        "overall_quality": "high|medium|low",
        "biases": ["..."],
        "gaps": ["..."]
    }}
}}"""


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
            "Supports real-time analytics, LLM-powered probing, and automatic "
            "evidence extraction into the Atomic Research chain."
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
        from app.core.ollama import ollama

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

        response = await ollama.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        response_text = response.get("message", {}).get("content", "")

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
        from app.core.ollama import ollama

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

        response = await ollama.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        response_text = response.get("message", {}).get("content", "")

        # Parse JSON
        analysis = {}
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response_text[json_start:json_end])
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response_text}

        # Build output
        nuggets = [
            {
                "text": n.get("text", ""),
                "source": n.get("source", f"deployment:{deployment_name}"),
                "tags": n.get("tags", [deployment_type, "channel-research"]),
            }
            for n in analysis.get("nuggets", [])
        ]

        insights = [
            {
                "text": i["text"],
                "confidence": i.get("confidence", "medium"),
            }
            for i in analysis.get("insights", [])
        ]

        recommendations = [
            {
                "text": r["text"],
                "priority": r.get("priority", "medium"),
                "effort": r.get("effort", "medium"),
            }
            for r in analysis.get("recommendations", [])
        ]

        summary = (
            f"Analyzed {response_count} responses from {deployment_type} deployment "
            f"'{deployment_name}'. Extracted {len(nuggets)} nuggets, "
            f"{len(insights)} insights, {len(recommendations)} recommendations."
        )

        return SkillOutput(
            success=True,
            summary=summary,
            nuggets=nuggets,
            insights=insights,
            recommendations=recommendations,
            artifacts={"deployment_analysis.json": json.dumps(analysis, indent=2)},
            suggestions=[
                f"Review the {len(nuggets)} extracted nuggets for accuracy",
                "Link nuggets to facts to build the evidence chain",
                "Consider follow-up studies to address identified gaps",
            ],
        )
