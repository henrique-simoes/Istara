"""LEGACY BOOTSTRAP REFERENCE ONLY.

Canonical skill definitions live in backend/app/skills/definitions/*.json.
Those JSON files are loaded by the runtime skill registry, used by dataset
generation, and may contain richer prompts, schemas, references, and metadata
than this file.

Do not treat this module as the source of truth and do not regenerate existing
definition files from it. Use generate_definitions.py only to scaffold missing
JSON definitions for newly introduced legacy skills.

All 40+ Istara UXR skills — defined using the skill factory.

Hand-written skills (more complex logic):
- user_interviews (discover)
- contextual_inquiry (discover)
- diary_studies (discover)

Factory-generated skills (standard plan/execute pattern):
- Everything else (37+ skills)

Plus specialized skills:
- survey_ai_detection
- kappa_thematic_analysis
- survey_generator
- interview_question_generator
- taxonomy_generator
"""

from app.skills.base import SkillPhase, SkillType
from app.skills.skill_factory import create_skill
from app.skills.browser_skills import (
    CompetitiveAnalysisSkill as BrowserCompetitiveAnalysisSkill,
    AccessibilityAuditSkill as BrowserAccessibilityAuditSkill,
    HeuristicEvaluationSkill as BrowserHeuristicEvaluationSkill
)
from app.skills.evaluation_skill import EvaluationSkill as FormalEvaluationSkill
from app.skills.simulation_skill import SimulationSkill as ParticipantSimulationSkill

# =====================================================================
# DISCOVER PHASE (10 core + extras)
# =====================================================================

CompetitiveAnalysisSkill = BrowserCompetitiveAnalysisSkill

StakeholderInterviewsSkill = create_skill(
    skill_name="stakeholder-interviews",
    display="Stakeholder Interviews",
    desc="Generate stakeholder interview guides, synthesize business goals, map assumptions vs evidence.",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Create a stakeholder interview plan for UX research.
Context: {context}
Include: stakeholder mapping (who to interview and why), interview guide with questions about business goals,
success metrics, constraints, assumptions, timeline, and priorities. Format as Markdown.""",
    execute_prompt="""Analyze stakeholder interview data.
Context: {context}

Interview data:
{content}

Extract: business goals, success metrics, assumptions (validated vs unvalidated), constraints,
organizational politics/dynamics, alignment/misalignment between stakeholders, priorities, risks.""",
    output_schema="""{{"business_goals": [{{"goal": "...", "stakeholder": "...", "priority": "..."}}],
"assumptions": [{{"assumption": "...", "validated": false, "evidence": "..."}}],
"constraints": [{{"constraint": "...", "type": "technical|business|legal|timeline"}}],
"alignment": [{{"topic": "...", "aligned": true, "stakeholders": ["..."]}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

SurveyDesignSkill = create_skill(
    skill_name="survey-design",
    display="Survey Design & Analysis",
    desc="Design surveys with bias checking, analyze responses with statistical summaries and cross-tabs.",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Design a UX research survey.
Context: {context}
Include: research questions to answer, question types (Likert, multiple choice, open-ended, ranking),
question wording (check for leading/double-barreled/loaded questions), response options,
survey flow and logic, estimated completion time, sample size calculation, distribution strategy.
Format as Markdown.""",
    execute_prompt="""Analyze survey response data.
Context: {context}

Survey data:
{content}

Perform:
1. Response summary statistics (counts, percentages, means)
2. Cross-tabulation by demographics/segments
3. Open-ended response thematic analysis
4. Statistical significance tests where applicable
5. Key findings and patterns
6. Data quality assessment (completion rate, straightlining, attention checks)""",
    output_schema="""{{"response_summary": [{{"question": "...", "type": "...", "results": {{}}}}],
"cross_tabs": [{{"dimension": "...", "findings": "..."}}],
"themes": [{{"theme": "...", "frequency": 0, "example_responses": ["..."]}}],
"data_quality": {{"completion_rate": 0, "straightlining_pct": 0, "flagged_responses": 0}},
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"facts": [{{"text": "...", "evidence_count": 0}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

AnalyticsReviewSkill = create_skill(
    skill_name="analytics-review",
    display="Analytics Review",
    desc="Interpret analytics exports — funnels, drop-offs, segments, anomalies, conversion paths.",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Create an analytics review plan for UX research.
Context: {context}
Include: key metrics to examine, funnel stages, segments to compare, time periods,
tools/exports needed, analysis approach. Format as Markdown.""",
    execute_prompt="""Analyze this product analytics data for UX insights.
Context: {context}

Analytics data:
{content}

Analyze: conversion funnels, drop-off points, user segments, behavioral patterns,
time-on-task, error rates, feature usage, engagement trends, anomalies.""",
    output_schema="""{{"funnels": [{{"name": "...", "stages": [{{"stage": "...", "users": 0, "drop_off_pct": 0}}]}}],
"segments": [{{"segment": "...", "key_metrics": {{}}, "notable_differences": "..."}}],
"anomalies": [{{"metric": "...", "expected": "...", "actual": "...", "possible_cause": "..."}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"facts": [{{"text": "...", "evidence_count": 0}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

DeskResearchSkill = create_skill(
    skill_name="desk-research",
    display="Literature / Desk Research",
    desc="Summarize academic papers, industry reports, best practices relevant to the research domain.",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.MIXED,
    plan_prompt="""Create a desk research plan.
Context: {context}
Include: research questions, search strategy (databases, keywords), inclusion/exclusion criteria,
synthesis approach, expected outputs. Format as Markdown.""",
    execute_prompt="""Analyze and synthesize this desk research / literature.
Context: {context}

Content:
{content}

Extract: key findings from each source, common themes across sources, contradictions,
best practices, frameworks, gaps in existing knowledge, relevance to the project.""",
    output_schema="""{{"sources": [{{"title": "...", "key_findings": ["..."], "relevance": "high|medium|low"}}],
"themes": [{{"theme": "...", "sources_count": 0, "description": "..."}}],
"best_practices": [{{"practice": "...", "evidence_strength": "strong|moderate|weak"}}],
"gaps": [{{"gap": "...", "importance": "high|medium|low"}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

FieldStudiesSkill = create_skill(
    skill_name="field-studies",
    display="Field Studies / Ethnography",
    desc="Structure field notes, code observations, identify cultural and environmental patterns.",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Design a field study / ethnographic research plan.
Context: {context}
Include: research questions, site selection, observation protocol, recording methods,
ethical considerations, analysis approach (coding framework). Format as Markdown.""",
    execute_prompt="""Analyze field study / ethnographic observation data.
Context: {context}

Field notes:
{content}

Extract: behavioral patterns, cultural norms, environmental influences, social dynamics,
artifacts and tools used, rituals and routines, unexpected discoveries.""",
    output_schema="""{{"behavioral_patterns": [{{"pattern": "...", "frequency": "common|occasional|rare"}}],
"cultural_norms": [{{"norm": "...", "impact_on_ux": "..."}}],
"environmental_factors": [{{"factor": "...", "influence": "positive|negative|neutral"}}],
"artifacts": [{{"artifact": "...", "usage": "...", "significance": "..."}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

AccessibilityAuditSkill = BrowserAccessibilityAuditSkill

# =====================================================================
# DEFINE PHASE (10 skills)
# =====================================================================

AffinityMappingSkill = create_skill(
    skill_name="affinity-mapping",
    display="Affinity Mapping",
    desc="Auto-cluster research nuggets and notes into themes. Users can refine groupings interactively.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Create an affinity mapping plan for synthesizing research data.
Context: {context}
Include: data preparation steps, clustering approach, theme naming conventions,
hierarchy levels, validation process. Format as Markdown.""",
    execute_prompt="""Perform affinity mapping on this research data.
Context: {context}

Data to cluster:
{content}

Cluster the data into themes:
1. Group related items together
2. Name each group with a descriptive theme
3. Create hierarchy (sub-themes under main themes)
4. Identify outliers that don't fit
5. Note the strength of each theme (number of supporting items)""",
    output_schema="""{{"themes": [{{"name": "...", "description": "...", "items": ["..."],
"sub_themes": [{{"name": "...", "items": ["..."]}}], "strength": 0}}],
"outliers": [{{"item": "...", "possible_home": "..."}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

PersonaCreationSkill = create_skill(
    skill_name="persona-creation",
    display="Persona Creation",
    desc="Synthesize evidence-based personas from research data. Every claim linked to sources.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan evidence-based persona creation.
Context: {context}
Include: data sources to use, persona dimensions (goals, behaviors, pain points, context),
segmentation approach, validation plan. Format as Markdown.""",
    execute_prompt="""Create evidence-based personas from this research data.
Context: {context}

Research data:
{content}

Create personas with: name, photo description, demographics, goals (functional/emotional/social),
behaviors, pain points, motivations, technology comfort, quote, scenario of use.
Every attribute must link to evidence.""",
    output_schema="""{{"personas": [{{"name": "...", "archetype": "...", "demographics": {{}},
"goals": [{{"goal": "...", "type": "functional|emotional|social", "evidence": "..."}}],
"behaviors": [{{"behavior": "...", "evidence": "..."}}],
"pain_points": [{{"pain": "...", "severity": 1-5, "evidence": "..."}}],
"motivations": ["..."], "quote": "...", "scenario": "..."}}],
"segmentation_rationale": "...",
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

JourneyMappingSkill = create_skill(
    skill_name="journey-mapping",
    display="Journey Mapping",
    desc="Build end-to-end journey maps with stages, actions, emotions, pain points, opportunities — all linked to evidence.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan a journey mapping exercise.
Context: {context}
Include: journey scope (start/end points), stages to map, data sources, persona to use,
channels/touchpoints to include, emotional mapping approach. Format as Markdown.""",
    execute_prompt="""Create a user journey map from this research data.
Context: {context}

Research data:
{content}

Map the journey with: stages, user actions, touchpoints, thoughts, emotions (positive/neutral/negative),
pain points, opportunities, moments of truth, and backstage processes.""",
    output_schema="""{{"journey_name": "...", "persona": "...",
"stages": [{{"name": "...", "actions": ["..."], "touchpoints": ["..."],
"thoughts": ["..."], "emotion": "positive|neutral|negative", "emotion_score": -2,
"pain_points": ["..."], "opportunities": ["..."], "evidence": ["..."]}}],
"moments_of_truth": [{{"stage": "...", "description": "...", "importance": "high|medium|low"}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "low|medium|high"}}],
"summary": "..."}}""",
)

EmpathyMappingSkill = create_skill(
    skill_name="empathy-mapping",
    display="Empathy Mapping",
    desc="Create Says/Thinks/Does/Feels quadrants from interview data, identify contradictions.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan empathy mapping from research data. Context: {context}
Include approach, data sources, quadrant definitions, contradiction analysis method. Markdown.""",
    execute_prompt="""Create empathy maps from research data. Context: {context}
Data: {content}
Map: Says (direct quotes), Thinks (inferred beliefs), Does (observed behaviors),
Feels (emotional states). Highlight contradictions between quadrants.""",
    output_schema="""{{"empathy_maps": [{{"persona": "...",
"says": [{{"quote": "...", "source": "..."}}],
"thinks": [{{"thought": "...", "evidence": "..."}}],
"does": [{{"action": "...", "context": "..."}}],
"feels": [{{"emotion": "...", "trigger": "..."}}],
"contradictions": [{{"between": "says_vs_does", "description": "..."}}]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

JTBDAnalysisSkill = create_skill(
    skill_name="jtbd-analysis",
    display="Jobs-to-be-Done Analysis",
    desc="Extract JTBD statements from research, identify functional/emotional/social jobs.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan a Jobs-to-be-Done analysis. Context: {context}
Include: JTBD framework, interview questions for job extraction, outcome expectations analysis. Markdown.""",
    execute_prompt="""Extract Jobs-to-be-Done from research data. Context: {context}
Data: {content}
Use the format: "When [situation], I want to [motivation], so I can [expected outcome]."
Categorize as functional, emotional, or social jobs. Identify hiring/firing criteria.""",
    output_schema="""{{"jobs": [{{"statement": "When..., I want to..., so I can...",
"type": "functional|emotional|social", "importance": "high|medium|low",
"satisfaction": "over-served|served|under-served|unserved", "evidence": ["..."]}}],
"hiring_criteria": [{{"criterion": "...", "job": "..."}}],
"firing_criteria": [{{"criterion": "...", "job": "..."}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

HMWStatementsSkill = create_skill(
    skill_name="hmw-statements",
    display="Problem Statements / HMW",
    desc="Generate 'How Might We' statements from insights, score by impact/feasibility.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan HMW statement generation. Context: {context}
Include: insight sources, HMW formulation rules, prioritization criteria. Markdown.""",
    execute_prompt="""Generate How Might We statements from these research insights. Context: {context}
Data: {content}
For each insight, create 2-3 HMW statements at different scopes (broad, narrow, lateral).
Score each by impact and feasibility.""",
    output_schema="""{{"hmw_statements": [{{"statement": "How might we...",
"source_insight": "...", "scope": "broad|narrow|lateral",
"impact": "high|medium|low", "feasibility": "high|medium|low", "score": 0}}],
"prioritized_top_5": ["..."],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

UserFlowMappingSkill = create_skill(
    skill_name="user-flow-mapping",
    display="User Flow Mapping",
    desc="Document current-state user flows, identify friction points, map to research findings.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan user flow documentation. Context: {context}
Include: flows to map, entry/exit points, decision points, error states. Markdown.""",
    execute_prompt="""Document and analyze user flows. Context: {context}
Data: {content}
Map: steps, decisions, branches, error states, friction points, drop-off risks.
Link each friction point to research evidence.""",
    output_schema="""{{"flows": [{{"name": "...", "entry_point": "...",
"steps": [{{"step": "...", "type": "action|decision|wait|error",
"friction": "none|low|medium|high", "evidence": "..."}}],
"branches": [{{"condition": "...", "path_a": "...", "path_b": "..."}}],
"drop_off_risks": [{{"step": "...", "risk_level": "high|medium|low", "evidence": "..."}}]}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

ThematicAnalysisSkill = create_skill(
    skill_name="thematic-analysis",
    display="Thematic Analysis",
    desc="Rigorous coding (open → axial → selective), codebook management, inter-rater reliability.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan a thematic analysis. Context: {context}
Include: Braun & Clarke 6-phase approach, coding strategy, codebook structure,
reliability measures, reflexivity considerations. Markdown.""",
    execute_prompt="""Perform thematic analysis on this qualitative data. Context: {context}
Data: {content}
Follow Braun & Clarke phases: familiarization, initial coding, theme searching,
theme reviewing, theme defining, report production.
Generate initial codes, then organize into themes and sub-themes.""",
    output_schema="""{{"codebook": [{{"code": "...", "definition": "...", "example": "...", "frequency": 0}}],
"themes": [{{"name": "...", "definition": "...", "codes": ["..."],
"sub_themes": [{{"name": "...", "codes": ["..."]}}],
"prevalence": "dominant|common|minor"}}],
"theme_map": "...",
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"facts": [{{"text": "..."}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

ResearchSynthesisSkill = create_skill(
    skill_name="research-synthesis",
    display="Research Synthesis Report",
    desc="Generate structured research reports: executive summary, methodology, findings, recommendations.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan a research synthesis report. Context: {context}
Include: report structure, audience, key sections, data sources to synthesize. Markdown.""",
    execute_prompt="""Synthesize all research data into a structured report. Context: {context}
Data: {content}
Generate: executive summary, methodology overview, key findings (organized by theme),
supporting evidence, implications, recommendations, limitations, next steps.""",
    output_schema="""{{"executive_summary": "...",
"methodology": "...",
"findings": [{{"theme": "...", "description": "...", "evidence": ["..."], "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low", "effort": "low|medium|high"}}],
"limitations": ["..."],
"next_steps": ["..."],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

PrioritizationMatrixSkill = create_skill(
    skill_name="prioritization-matrix",
    display="Prioritization Matrix",
    desc="Impact vs Effort scoring, MoSCoW prioritization, stakeholder alignment.",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan a prioritization exercise. Context: {context}
Include: items to prioritize, scoring dimensions, stakeholder input process. Markdown.""",
    execute_prompt="""Prioritize these research findings/opportunities. Context: {context}
Data: {content}
Score each item on: impact (1-5), effort (1-5), confidence (1-5), urgency (1-5).
Apply MoSCoW categorization. Generate a prioritized roadmap.""",
    output_schema="""{{"items": [{{"item": "...", "impact": 1, "effort": 1, "confidence": 1, "urgency": 1,
"score": 0, "moscow": "must|should|could|wont", "rationale": "..."}}],
"quadrants": {{"quick_wins": ["..."], "big_bets": ["..."], "fill_ins": ["..."], "avoid": ["..."]}},
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low"}}],
"summary": "..."}}""",
)

# =====================================================================
# DEVELOP PHASE (10 skills)
# =====================================================================

UsabilityTestingSkill = create_skill(
    skill_name="usability-testing",
    display="Usability Testing",
    desc="Create test scripts, process session data, calculate task success/time/errors, identify patterns.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.MIXED,
    plan_prompt="""Create a usability test plan. Context: {context}
Include: test objectives, tasks to test (with success criteria), participant profile,
test script, moderator guide, metrics to capture, environment setup. Markdown.""",
    execute_prompt="""Analyze usability test results. Context: {context}
Data: {content}
Calculate: task completion rates, time on task, error rates, satisfaction scores.
Identify: usability issues (severity rated), patterns across participants, design recommendations.""",
    output_schema="""{{"tasks": [{{"task": "...", "completion_rate": 0, "avg_time_seconds": 0,
"error_rate": 0, "satisfaction": 0, "issues": [{{"issue": "...", "severity": 1-4,
"frequency": 0, "recommendation": "..."}}]}}],
"overall_metrics": {{"sus_score": 0, "task_success_avg": 0}},
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low", "effort": "low|medium|high"}}],
"summary": "..."}}""",
)

HeuristicEvaluationSkill = BrowserHeuristicEvaluationSkill

ABTestAnalysisSkill = create_skill(
    skill_name="ab-test-analysis",
    display="A/B Test Analysis",
    desc="Analyze A/B test results — statistical significance, confidence intervals, segment breakdowns.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan an A/B test analysis. Context: {context}
Include: hypothesis, metrics, sample size requirements, test duration, segmentation plan. Markdown.""",
    execute_prompt="""Analyze A/B test results. Context: {context}
Data: {content}
Calculate: conversion rates per variant, statistical significance (p-value), confidence intervals,
effect size, segment breakdowns, practical significance assessment.""",
    output_schema="""{{"variants": [{{"name": "...", "sample_size": 0, "conversions": 0, "rate": 0}}],
"statistical_test": {{"p_value": 0, "significant": false, "confidence_level": 0.95}},
"effect_size": 0, "confidence_interval": [0, 0],
"segments": [{{"segment": "...", "winner": "...", "difference": 0}}],
"facts": [{{"text": "..."}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "low|medium|high"}}],
"summary": "..."}}""",
)

CardSortingSkill = create_skill(
    skill_name="card-sorting",
    display="Card Sorting Analysis",
    desc="Analyze open/closed/hybrid card sorts — dendrograms, similarity matrices, IA recommendations.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan card sorting research. Context: {context}
Include: sort type, cards/items, participant count, analysis approach. Markdown.""",
    execute_prompt="""Analyze card sorting results. Context: {context}
Data: {content}
Generate: similarity matrix, category clusters, agreement rates, outlier items,
IA recommendations, labeling suggestions.""",
    output_schema="""{{"categories": [{{"name": "...", "items": ["..."], "agreement_pct": 0}}],
"similarity_pairs": [{{"item_a": "...", "item_b": "...", "similarity": 0}}],
"outliers": [{{"item": "...", "reason": "..."}}],
"ia_recommendations": [{{"recommendation": "...", "confidence": "high|medium|low"}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

TreeTestingSkill = create_skill(
    skill_name="tree-testing",
    display="Tree Testing Analysis",
    desc="Process tree test results — findability, success/directness scores, path analysis.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan tree testing. Context: {context}
Include: tasks, tree structure, success criteria, metrics. Markdown.""",
    execute_prompt="""Analyze tree test results. Context: {context}
Data: {content}
Calculate: task success rates, directness scores, first-click accuracy,
path analysis, problem areas in IA.""",
    output_schema="""{{"tasks": [{{"task": "...", "success_rate": 0, "directness": 0,
"first_click_accuracy": 0, "common_paths": ["..."], "problem_nodes": ["..."]}}],
"overall_findability": 0,
"problem_areas": [{{"node": "...", "issue": "...", "severity": "high|medium|low"}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "low|medium|high"}}],
"summary": "..."}}""",
)

ConceptTestingSkill = create_skill(
    skill_name="concept-testing",
    display="Concept Testing",
    desc="Structure concept test protocols, analyze reactions, preference rankings.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan concept testing. Context: {context}
Include: concepts to test, evaluation criteria, testing method, feedback structure. Markdown.""",
    execute_prompt="""Analyze concept testing feedback. Context: {context}
Data: {content}
Evaluate: desirability, clarity, uniqueness, feasibility perception.
Rank concepts by preference. Identify strengths/weaknesses per concept.""",
    output_schema="""{{"concepts": [{{"name": "...", "desirability": 0, "clarity": 0, "uniqueness": 0,
"strengths": ["..."], "weaknesses": ["..."], "participant_quotes": ["..."]}}],
"ranking": ["..."],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "low|medium|high"}}],
"summary": "..."}}""",
)

CognitiveWalkthroughSkill = create_skill(
    skill_name="cognitive-walkthrough",
    display="Cognitive Walkthrough",
    desc="Systematic task analysis: will user notice, understand, associate, interpret feedback?",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan a cognitive walkthrough. Context: {context}
Include: tasks, user profile, success criteria, walkthrough questions. Markdown.""",
    execute_prompt="""Perform cognitive walkthrough analysis. Context: {context}
Data: {content}
For each step: Will the user try? Will they notice the correct action?
Will they associate it with their goal? Will they interpret feedback correctly?""",
    output_schema="""{{"tasks": [{{"task": "...",
"steps": [{{"step": "...", "will_try": true, "will_notice": true,
"will_associate": true, "will_interpret": true, "issues": ["..."]}}]}}],
"critical_failures": [{{"task": "...", "step": "...", "failure_type": "..."}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low"}}],
"summary": "..."}}""",
)

DesignCritiqueSkill = create_skill(
    skill_name="design-critique",
    display="Design Critique / Expert Review",
    desc="Structured critique using UX principles — Gestalt, visual hierarchy, cognitive load, etc.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan a design critique. Context: {context}
Include: evaluation framework, design principles to apply, critique structure. Markdown.""",
    execute_prompt="""Perform a structured design critique. Context: {context}
Data: {content}
Evaluate: visual hierarchy, consistency, cognitive load, affordances, error prevention,
feedback, Gestalt principles, typography, color, spacing, responsive behavior.""",
    output_schema="""{{"evaluations": [{{"principle": "...", "score": 0,
"findings": [{{"issue": "...", "severity": "critical|major|minor", "location": "...",
"recommendation": "..."}}]}}],
"strengths": ["..."],
"overall_score": 0,
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low"}}],
"summary": "..."}}""",
)

PrototypeFeedbackSkill = create_skill(
    skill_name="prototype-feedback",
    display="Prototype Feedback Analysis",
    desc="Process feedback on prototypes, categorize by theme/severity/screen, track across iterations.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan prototype feedback collection. Context: {context}
Include: feedback dimensions, collection method, categorization scheme, iteration tracking. Markdown.""",
    execute_prompt="""Analyze prototype feedback. Context: {context}
Data: {content}
Categorize feedback by: screen/component, theme, severity, type (bug/ux/visual/content).
Track patterns across iterations if multiple rounds provided.""",
    output_schema="""{{"feedback_items": [{{"item": "...", "screen": "...", "theme": "...",
"severity": "critical|major|minor", "type": "bug|ux|visual|content",
"iteration": 1, "status": "new|recurring|resolved"}}],
"themes": [{{"theme": "...", "count": 0, "severity_avg": "..."}}],
"iteration_comparison": {{"improved": ["..."], "regressed": ["..."], "new": ["..."]}},
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low"}}],
"summary": "..."}}""",
)

WorkshopFacilitationSkill = create_skill(
    skill_name="workshop-facilitation",
    display="Workshop Facilitation",
    desc="Generate workshop agendas, activities, templates. Process workshop outputs into findings.",
    phase=SkillPhase.DEVELOP,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Design a UX research workshop. Context: {context}
Include: objectives, participants, agenda, activities (design studio, crazy 8s, dot voting, etc.),
materials needed, facilitation guide, time allocation. Markdown.""",
    execute_prompt="""Analyze workshop outputs and synthesize findings. Context: {context}
Data: {content}
Extract: ideas generated, votes/priorities, themes, decisions made,
action items, areas of agreement/disagreement.""",
    output_schema="""{{"ideas": [{{"idea": "...", "votes": 0, "category": "..."}}],
"themes": [{{"theme": "...", "ideas_count": 0}}],
"decisions": [{{"decision": "...", "rationale": "...", "stakeholders": ["..."]}}],
"action_items": [{{"action": "...", "owner": "...", "deadline": "..."}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

# =====================================================================
# DELIVER PHASE (10 skills)
# =====================================================================

SUSUMUXScoringSkill = create_skill(
    skill_name="sus-umux-scoring",
    display="SUS / UMUX Scoring",
    desc="Calculate SUS/UMUX scores, percentile rankings, benchmark against industry, track over time.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan SUS/UMUX measurement. Context: {context}
Include: questionnaire selection, administration timing, benchmark sources, tracking plan. Markdown.""",
    execute_prompt="""Calculate and analyze SUS/UMUX scores. Context: {context}
Data: {content}
Calculate: individual scores, mean score, standard deviation, percentile ranking,
adjective rating (Bangor scale), NPS-style grade, comparison to industry benchmarks.
Track changes over time if historical data provided.""",
    output_schema="""{{"scores": {{"mean": 0, "median": 0, "std_dev": 0, "min": 0, "max": 0,
"percentile": 0, "adjective": "...", "grade": "A|B|C|D|F"}},
"individual_scores": [0],
"benchmark_comparison": {{"industry_avg": 68, "difference": 0, "assessment": "above|at|below"}},
"trend": [{{"date": "...", "score": 0}}],
"facts": [{{"text": "..."}}],
"recommendations": [{{"text": "...", "priority": "low|medium|high"}}],
"summary": "..."}}""",
)

NPSAnalysisSkill = create_skill(
    skill_name="nps-analysis",
    display="NPS Analysis",
    desc="Calculate NPS, segment analysis, open-ended response analysis, trend tracking.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan NPS measurement. Context: {context}
Include: survey design, segmentation plan, follow-up questions, tracking cadence. Markdown.""",
    execute_prompt="""Analyze NPS data. Context: {context}
Data: {content}
Calculate: NPS score, promoter/passive/detractor distribution, segment breakdowns,
open-ended response themes, trend over time, driver analysis.""",
    output_schema="""{{"nps": {{"score": 0, "promoters_pct": 0, "passives_pct": 0, "detractors_pct": 0,
"total_responses": 0}},
"segments": [{{"segment": "...", "nps": 0, "n": 0}}],
"themes": [{{"theme": "...", "sentiment": "positive|negative", "frequency": 0, "examples": ["..."]}}],
"drivers": [{{"driver": "...", "impact": "high|medium|low", "sentiment": "..."}}],
"trend": [{{"period": "...", "nps": 0}}],
"facts": [{{"text": "..."}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

TaskAnalysisQuantSkill = create_skill(
    skill_name="task-analysis-quant",
    display="Task Analysis (Quantitative)",
    desc="Task completion rates, time-on-task, error rates, efficiency metrics, benchmarks.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan quantitative task analysis. Context: {context}
Include: tasks to measure, metrics, benchmarks, data collection method. Markdown.""",
    execute_prompt="""Analyze quantitative task performance data. Context: {context}
Data: {content}
Calculate: completion rates, time-on-task (mean, median, 95th percentile), error rates,
efficiency (lostness, deviations), learnability (improvement over attempts).""",
    output_schema="""{{"tasks": [{{"task": "...", "completion_rate": 0, "time_mean": 0, "time_median": 0,
"time_p95": 0, "error_rate": 0, "efficiency": 0, "benchmark": 0, "vs_benchmark": "above|at|below"}}],
"overall": {{"avg_completion": 0, "avg_time": 0, "avg_errors": 0}},
"facts": [{{"text": "..."}}],
"recommendations": [{{"text": "...", "priority": "low|medium|high"}}],
"summary": "..."}}""",
)

RegressionImpactSkill = create_skill(
    skill_name="regression-impact",
    display="Regression / Impact Analysis",
    desc="Before/after comparisons, measure impact of changes, statistical significance.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Plan regression/impact analysis. Context: {context}
Include: baseline metrics, intervention, measurement timeline, statistical approach. Markdown.""",
    execute_prompt="""Perform before/after impact analysis. Context: {context}
Data: {content}
Compare: baseline vs post-change metrics, calculate improvement/regression percentages,
statistical significance, practical significance, confounding factors.""",
    output_schema="""{{"metrics": [{{"metric": "...", "baseline": 0, "post_change": 0,
"change_pct": 0, "significant": false, "p_value": 0}}],
"overall_impact": "positive|neutral|negative",
"confounders": ["..."],
"facts": [{{"text": "..."}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "low|medium|high"}}],
"summary": "..."}}""",
)

DesignSystemAuditSkill = create_skill(
    skill_name="design-system-audit",
    display="Design System Audit",
    desc="Evaluate consistency against design system, identify deviations, accessibility compliance.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan a design system audit. Context: {context}
Include: components to audit, consistency checks, accessibility requirements, scoring criteria. Markdown.""",
    execute_prompt="""Audit design system compliance. Context: {context}
Data: {content}
Check: component consistency, naming conventions, spacing/typography adherence,
color usage, accessibility compliance, documentation completeness.""",
    output_schema="""{{"components": [{{"component": "...", "consistent": true,
"deviations": [{{"deviation": "...", "severity": "critical|major|minor"}}],
"accessibility": "pass|fail|partial"}}],
"overall_consistency": 0,
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low"}}],
"summary": "..."}}""",
)

HandoffDocumentationSkill = create_skill(
    skill_name="handoff-documentation",
    display="Handoff Documentation",
    desc="Generate developer handoff docs: specs, annotations, edge cases, accessibility requirements.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan handoff documentation. Context: {context}
Include: deliverables, specification format, edge cases to document, review process. Markdown.""",
    execute_prompt="""Generate handoff documentation from research/design data. Context: {context}
Data: {content}
Create: component specs, interaction specifications, edge cases and error states,
accessibility requirements, content guidelines, QA checklist.""",
    output_schema="""{{"specs": [{{"component": "...", "behavior": "...", "states": ["..."],
"edge_cases": ["..."], "accessibility": ["..."], "content": "..."}}],
"qa_checklist": [{{"check": "...", "priority": "must|should|nice"}}],
"summary": "..."}}""",
)

RepositoryCurationSkill = create_skill(
    skill_name="repository-curation",
    display="Research Repository Curation",
    desc="Organize all research into searchable, tagged repository with atomic research principles.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan research repository curation. Context: {context}
Include: taxonomy, tagging scheme, linking strategy, search optimization. Markdown.""",
    execute_prompt="""Curate and organize research findings into a structured repository. Context: {context}
Data: {content}
Organize: tag all findings, link nuggets→facts→insights→recommendations,
identify gaps, suggest taxonomy improvements, create search-optimized summaries.""",
    output_schema="""{{"repository": [{{"finding": "...", "type": "nugget|fact|insight|recommendation",
"tags": ["..."], "linked_to": ["..."], "project": "...", "phase": "..."}}],
"taxonomy": [{{"category": "...", "tags": ["..."]}}],
"gaps": [{{"area": "...", "missing": "..."}}],
"summary": "..."}}""",
)

StakeholderPresentationSkill = create_skill(
    skill_name="stakeholder-presentation",
    display="Stakeholder Presentation",
    desc="Generate presentation content from findings, tailored to audience (exec/design/eng).",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan a stakeholder research presentation. Context: {context}
Include: audience analysis, key messages, narrative arc, supporting evidence selection. Markdown.""",
    execute_prompt="""Generate a research presentation from findings. Context: {context}
Data: {content}
Create slides for: executive summary, methodology, key findings (with evidence),
impact assessment, recommendations (prioritized), next steps.
Tailor language and depth to the audience.""",
    output_schema="""{{"slides": [{{"title": "...", "content": "...", "speaker_notes": "...",
"visuals": "..."}}],
"key_messages": ["..."],
"appendix": [{{"topic": "...", "detail": "..."}}],
"summary": "..."}}""",
)

ResearchRetroSkill = create_skill(
    skill_name="research-retro",
    display="Research Ops Retrospective",
    desc="Analyze research process effectiveness, identify improvements, update team practices.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan a research ops retrospective. Context: {context}
Include: process steps to review, metrics, team feedback collection, improvement framework. Markdown.""",
    execute_prompt="""Conduct a research ops retrospective. Context: {context}
Data: {content}
Analyze: what worked, what didn't, process bottlenecks, tool effectiveness,
timeline adherence, quality of outputs, team satisfaction, improvement opportunities.""",
    output_schema="""{{"went_well": [{{"item": "...", "impact": "high|medium|low"}}],
"improvements_needed": [{{"item": "...", "severity": "critical|major|minor", "suggestion": "..."}}],
"process_metrics": {{"timeline_adherence": 0, "quality_score": 0, "team_satisfaction": 0}},
"action_items": [{{"action": "...", "owner": "...", "priority": "high|medium|low"}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

LongitudinalTrackingSkill = create_skill(
    skill_name="longitudinal-tracking",
    display="Longitudinal Study Tracking",
    desc="Track metrics and findings over time, identify trends, seasonal patterns, regression detection.",
    phase=SkillPhase.DELIVER,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan longitudinal study tracking. Context: {context}
Include: metrics to track, measurement cadence, trend analysis approach, regression alerts. Markdown.""",
    execute_prompt="""Analyze longitudinal research/metric data. Context: {context}
Data: {content}
Identify: trends (improving/declining/stable), seasonal patterns, inflection points,
regressions, correlations between metrics, anomalies, forecasts.""",
    output_schema="""{{"metrics": [{{"metric": "...",
"data_points": [{{"date": "...", "value": 0}}],
"trend": "improving|declining|stable",
"change_pct": 0, "anomalies": [{{"date": "...", "description": "..."}}]}}],
"correlations": [{{"metric_a": "...", "metric_b": "...", "correlation": 0}}],
"regressions": [{{"metric": "...", "date": "...", "severity": "critical|major|minor"}}],
"forecasts": [{{"metric": "...", "forecast": 0, "confidence": 0}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

EvaluateResearchQualitySkill = FormalEvaluationSkill

# =====================================================================
# SPECIALIZED SKILLS (new additions)
# =====================================================================

SurveyAIDetectionSkill = create_skill(
    skill_name="survey-ai-detection",
    display="Survey AI Response Detection",
    desc="""Detect AI-generated survey responses using multiple heuristic and statistical methods.

Based on academic research (Wu et al. 2025, Yang et al. 2024):
- Linguistic analysis: perplexity scoring, burstiness, vocabulary diversity
- Response pattern analysis: timing, straightlining, semantic similarity between responses
- Statistical methods: response length distribution, lexical richness (TTR), coherence scores
- Behavioral signals: completion time vs expected, copy-paste indicators, IP/device clustering""",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.QUANTITATIVE,
    plan_prompt="""Design an AI response detection protocol for survey data.
Context: {context}
Include:
1. Detection methods hierarchy (linguistic, behavioral, statistical)
2. Perplexity and burstiness analysis approach
3. Response timing analysis (too fast = suspicious)
4. Semantic similarity clustering (AI responses tend to be similar)
5. Vocabulary diversity metrics (Type-Token Ratio)
6. Attention check / trap question design
7. Threshold calibration (sensitivity vs specificity trade-off)
8. False positive mitigation strategies
9. Reporting format for flagged responses
Format as Markdown with academic references.""",
    execute_prompt="""Analyze survey responses for AI-generated content.
Context: {context}

Survey response data:
{content}

Apply these detection methods:
1. **Linguistic Analysis**: Calculate vocabulary diversity (TTR), average sentence length, 
   use of hedging language, formality consistency, repetitive phrasing patterns
2. **Response Pattern Analysis**: Check for suspiciously uniform response lengths, 
   semantic similarity clusters (responses that are too similar to each other), 
   unnatural coherence across unrelated questions
3. **Behavioral Signals**: Response completion time analysis, sequential response patterns,
   copy-paste indicators, device/browser fingerprint analysis
4. **Content Quality**: Check for generic/surface-level answers, absence of personal anecdotes,
   overly structured responses, unusually comprehensive coverage
5. **Statistical Outliers**: Identify responses that deviate from expected distributions

For each flagged response, provide: detection method, confidence score, evidence, 
and recommendation (remove/review/keep).""",
    output_schema="""{{"total_responses": 0, "flagged_count": 0, "flag_rate": 0,
"detection_results": [{{"response_id": "...", "flag_level": "high|medium|low",
"detection_methods": [{{"method": "...", "score": 0, "evidence": "..."}}],
"overall_confidence": 0, "recommendation": "remove|review|keep"}}],
"aggregate_analysis": {{
"avg_response_length": 0, "length_std_dev": 0,
"avg_vocabulary_diversity": 0, "semantic_similarity_clusters": 0,
"suspicious_timing_count": 0, "straightlining_count": 0}},
"clean_dataset_size": 0,
"methodology_notes": "...",
"facts": [{{"text": "..."}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "priority": "critical|high|medium|low"}}],
"summary": "..."}}""",
)

KappaThematicAnalysisSkill = create_skill(
    skill_name="kappa-thematic-analysis",
    display="Kappa Intercoder Thematic Analysis",
    desc="""Thematic analysis with Cohen's/Fleiss' Kappa intercoder reliability.
Supports agent-only, human-only, or agent+human coding with reliability measurement.""",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Design a Kappa-validated thematic analysis process.
Context: {context}
Include:
1. Codebook development process (inductive/deductive/hybrid)
2. Coder training protocol
3. Pilot coding round with Kappa measurement
4. Kappa interpretation scale (Landis & Koch: slight/fair/moderate/substantial/almost perfect)
5. Disagreement resolution process
6. Iterative refinement until acceptable Kappa (≥0.6 moderate, ≥0.8 excellent)
7. Agent-as-coder protocol: how the AI acts as a second coder
8. Final coding with reliability reporting
Format as Markdown.""",
    execute_prompt="""Perform thematic analysis with intercoder reliability measurement.
Context: {context}

Data to code:
{content}

Process:
1. Generate initial codebook from data (open coding)
2. Code all items using the codebook
3. Generate a SECOND independent coding (as a reliability coder)
4. Calculate Cohen's Kappa between the two codings
5. Report agreement/disagreement per code
6. Identify codes needing refinement (low agreement)
7. Provide final consolidated coding with reliability metrics
8. Group codes into themes with prevalence data""",
    output_schema="""{{"codebook": [{{"code": "...", "definition": "...", "examples": ["..."],
"frequency": 0}}],
"reliability": {{
"kappa": 0, "interpretation": "slight|fair|moderate|substantial|almost_perfect",
"agreement_pct": 0, "n_items": 0, "n_codes": 0,
"per_code_agreement": [{{"code": "...", "agreement": 0, "kappa": 0}}]}},
"coding_results": [{{"item_id": "...", "text": "...",
"coder_1": ["..."], "coder_2": ["..."], "agreed": ["..."], "disagreed": ["..."]}}],
"themes": [{{"name": "...", "codes": ["..."], "prevalence": "dominant|common|minor",
"description": "..."}}],
"refinement_needed": [{{"code": "...", "kappa": 0, "issue": "..."}}],
"nuggets": [{{"text": "...", "tags": ["..."]}}],
"insights": [{{"text": "...", "confidence": "high|medium|low"}}],
"summary": "..."}}""",
)

SurveyGeneratorSkill = create_skill(
    skill_name="survey-generator",
    display="Survey Generator",
    desc="Generate context-aware surveys from project knowledge — research questions, context layers, existing findings.",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan survey generation from project context.
Context: {context}
Include: research goals driving the survey, target audience, question types,
length constraints, distribution method, analysis plan. Markdown.""",
    execute_prompt="""Generate a complete survey based on project context and research needs.
Context: {context}

Existing knowledge / gaps to fill:
{content}

Create a survey with:
1. Clear introduction and consent language
2. Screener questions (if needed)
3. Demographic questions (minimal, relevant only)
4. Core questions organized by research theme
5. Mix of question types (Likert, MC, ranking, open-ended)
6. Attention check questions embedded naturally
7. Anti-AI-response trap questions (subtle)
8. Logical flow and skip logic recommendations
9. Estimated completion time
10. Quality: no leading, double-barreled, or loaded questions""",
    output_schema="""{{"survey": {{
"title": "...", "introduction": "...", "estimated_time_minutes": 0,
"sections": [{{"section_name": "...", "questions": [{{
"id": "...", "text": "...", "type": "likert|multiple_choice|ranking|open_ended|matrix|slider",
"options": ["..."], "required": true, "skip_logic": "...",
"purpose": "...", "research_question": "..."}}]}}],
"screener": [{{"question": "...", "qualifying_answer": "..."}}],
"attention_checks": [{{"question": "...", "correct_answer": "..."}}]}},
"quality_review": [{{"issue": "...", "question_id": "...", "suggestion": "..."}}],
"analysis_plan": [{{"question_id": "...", "analysis_method": "..."}}],
"summary": "..."}}""",
)

InterviewQuestionGeneratorSkill = create_skill(
    skill_name="interview-question-generator",
    display="Interview Question Generator",
    desc="Generate interview questions from project context, research goals, and existing findings.",
    phase=SkillPhase.DISCOVER,
    skill_type=SkillType.QUALITATIVE,
    plan_prompt="""Plan interview question generation from project context.
Context: {context}
Include: research objectives, target participants, question categories, probing strategy. Markdown.""",
    execute_prompt="""Generate interview questions based on project context and research needs.
Context: {context}

Existing knowledge / gaps to fill:
{content}

Create:
1. Opening/warm-up questions (2-3)
2. Core questions organized by research theme (8-12)
3. Each core question with 2-3 probing follow-ups
4. Scenario-based questions where appropriate
5. Critical incident questions ("Tell me about a time when...")
6. Closing questions
7. Question quality check (no leading, double-barreled, or yes/no questions)
8. Annotations: WHY each question is asked and what it maps to""",
    output_schema="""{{"interview_guide": {{
"warm_up": [{{"question": "...", "purpose": "..."}}],
"core_themes": [{{"theme": "...", "research_question": "...",
"questions": [{{"question": "...", "type": "open|scenario|critical_incident",
"probes": ["..."], "purpose": "...", "maps_to": "..."}}]}}],
"closing": [{{"question": "...", "purpose": "..."}}]}},
"quality_check": [{{"issue": "...", "question": "...", "suggestion": "..."}}],
"estimated_duration_minutes": 0,
"summary": "..."}}""",
)

TaxonomyGeneratorSkill = create_skill(
    skill_name="taxonomy-generator",
    display="Taxonomy Generator",
    desc="""Generate multi-level taxonomies for projects, tasks, features, and companies.
Supports fine-tuning depth by context level (company-wide, product, feature, task).""",
    phase=SkillPhase.DEFINE,
    skill_type=SkillType.MIXED,
    plan_prompt="""Plan taxonomy development.
Context: {context}
Include: scope (what to taxonomize), hierarchy depth, naming conventions,
mutual exclusivity rules, governance process. Markdown.""",
    execute_prompt="""Generate a multi-level taxonomy from project/company context.
Context: {context}

Content to taxonomize:
{content}

Create taxonomy at multiple levels:
1. **Company level**: Product areas, user segments, business domains
2. **Product level**: Features, user flows, content types
3. **Project level**: Research themes, methods used, finding categories
4. **Task level**: Task types, priorities, skill categories
5. **Feature level**: Component types, interaction patterns, states

For each level:
- Hierarchical categories with clear definitions
- Mutually exclusive, collectively exhaustive (MECE) where possible
- Tagging recommendations
- Cross-references between levels""",
    output_schema="""{{"taxonomies": {{
"company": [{{"category": "...", "definition": "...",
"subcategories": [{{"name": "...", "definition": "..."}}]}}],
"product": [{{"category": "...", "definition": "...", "subcategories": [{{}}]}}],
"project": [{{"category": "...", "definition": "...", "subcategories": [{{}}]}}],
"task": [{{"category": "...", "definition": "...", "subcategories": [{{}}]}}],
"feature": [{{"category": "...", "definition": "...", "subcategories": [{{}}]}}}},
"cross_references": [{{"from_level": "...", "from_category": "...",
"to_level": "...", "to_category": "...", "relationship": "..."}}],
"governance": {{"owner": "...", "review_cadence": "...", "change_process": "..."}},
"summary": "..."}}""",
)

SimulateParticipantSkill = ParticipantSimulationSkill


# =====================================================================# REGISTRATION
# =====================================================================

ALL_FACTORY_SKILLS = [
    # Discover
    CompetitiveAnalysisSkill,
    StakeholderInterviewsSkill,
    SurveyDesignSkill,
    AnalyticsReviewSkill,
    DeskResearchSkill,
    FieldStudiesSkill,
    AccessibilityAuditSkill,
    SurveyAIDetectionSkill,
    SurveyGeneratorSkill,
    InterviewQuestionGeneratorSkill,
    # Define
    AffinityMappingSkill,
    PersonaCreationSkill,
    JourneyMappingSkill,
    EmpathyMappingSkill,
    JTBDAnalysisSkill,
    HMWStatementsSkill,
    UserFlowMappingSkill,
    ThematicAnalysisSkill,
    ResearchSynthesisSkill,
    PrioritizationMatrixSkill,
    KappaThematicAnalysisSkill,
    TaxonomyGeneratorSkill,
    SimulateParticipantSkill,
    # Develop
    UsabilityTestingSkill,
    HeuristicEvaluationSkill,
    ABTestAnalysisSkill,
    CardSortingSkill,
    TreeTestingSkill,
    ConceptTestingSkill,
    CognitiveWalkthroughSkill,
    DesignCritiqueSkill,
    PrototypeFeedbackSkill,
    WorkshopFacilitationSkill,
    # Deliver
    SUSUMUXScoringSkill,
    NPSAnalysisSkill,
    TaskAnalysisQuantSkill,
    RegressionImpactSkill,
    DesignSystemAuditSkill,
    HandoffDocumentationSkill,
    RepositoryCurationSkill,
    StakeholderPresentationSkill,
    ResearchRetroSkill,
    LongitudinalTrackingSkill,
    EvaluateResearchQualitySkill,
]
