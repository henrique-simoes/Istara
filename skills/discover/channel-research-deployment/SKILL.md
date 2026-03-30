---
name: channel-research-deployment
description: "Deploy interviews, surveys, and diary studies via messaging channels (Telegram, Slack, WhatsApp, Google Chat) with adaptive questioning and real-time analytics."
metadata:
  istara:
    phase: discover
    type: mixed
    version: "1.0.0"
---

# Channel Research Deployment

## Capabilities

- Deploy research studies across Telegram, Slack, WhatsApp, and Google Chat
- Adaptive questioning with LLM-powered follow-up probes
- Real-time analytics dashboard (response rate, completion rate, per-question stats)
- Automatic nugget extraction from participant responses into the Atomic Research chain
- Conversation state machine: intro, questions, probing, wrap-up
- Configurable rate limiting between questions
- LLM-judged saturation detection to avoid over-probing
- Cross-deployment overview with progress tracking

## Workflow

1. **Plan** -- Define research goals, generate question set with adaptive rules
2. **Configure** -- Set up channel instances and link to a project
3. **Deploy** -- Create and activate a deployment across selected channels
4. **Collect** -- Participants respond via messaging; adaptive probing deepens insights
5. **Monitor** -- Real-time analytics show progress, response rates, and per-question stats
6. **Analyze** -- Complete the deployment; synthesize findings into nuggets, insights, recommendations

## Input

- Research goals and questions (text or generated via plan)
- Channel instance IDs (configured Telegram/Slack/WhatsApp/Google Chat connections)
- Deployment configuration (adaptive rules, rate limits, intro/outro messages)
- Project context (auto-loaded from context layers)

## Output

- Deployment plan with question set and adaptive rules (JSON)
- Real-time analytics (response rate, completion rate, per-question breakdown)
- Nuggets with source attribution (participant, channel, deployment)
- Insights and recommendations synthesized from responses
- Full conversation transcripts per participant

## Deployment Types

- **Interview** -- Semi-structured conversational interview via messaging
- **Survey** -- Structured question set with optional branching
- **Diary Study** -- Longitudinal prompts sent on a schedule over days/weeks

## Best Practices

- 5-15 questions per interview deployment; 3-5 for diary studies
- Enable adaptive probing for interviews to capture deeper insights
- Set rate limits (30-60s between questions) to avoid overwhelming participants
- Use the intro message to set expectations and build trust
- Monitor per-question skip rates to identify confusing questions
- Complete deployments promptly to avoid participant fatigue
