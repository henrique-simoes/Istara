# Research Deployments

Deploy interviews, surveys, and diary studies directly through messaging channels with adaptive questioning and real-time analytics.

## Deployment Types

- **Interview**: Structured or semi-structured interview with adaptive follow-ups
- **Survey**: Questionnaire delivered through chat messages
- **Diary Study**: Longitudinal data collection over time

## Deployment Lifecycle

```
Draft -> Active -> [Paused] -> Completed
          |                       |
          +-- Conversations --+   +-- Analysis triggered
              (per participant)
```

## Adaptive Questioning (AURA-Style)

When adaptive mode is enabled:
1. Participant responds to a question
2. LLM analyzes the response against research goals
3. If clarification needed, generates a follow-up question
4. If response is complete, moves to next scheduled question
5. Respects max follow-up limit to avoid endless loops

### Configuration Options
- `adaptive: true/false` — Enable adaptive follow-ups
- `max_followups: 3` — Maximum follow-up questions per scheduled question
- `research_goals: "..."` — Context for the LLM to generate relevant follow-ups
- `intro_message: "..."` — Custom introduction message
- `thank_you_message: "..."` — Custom completion message
- `rate_limit_seconds: 30` — Minimum delay between questions

## Conversation States

| State | Description |
|-------|-------------|
| active | Participant is responding to questions |
| completed | All questions answered, thank-you sent |
| paused | Deployment paused, no new questions sent |
| expired | No response within timeout period |

## Analytics Dashboard

### Overview (24h)
- Conversations started/completed counts
- Findings created (nuggets/facts/insights/recommendations)
- Active deployments with progress

### Per-Deployment Analytics
- **Question Analytics**: Response count, skip count, avg word count per question
- **Participant Tracker**: Status, current question, last active time
- **Findings Pipeline**: Real-time view of responses becoming findings
- **Channel Performance**: Compare response rates across platforms
- **Timeline**: Projected vs actual completion, on-track indicator

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/deployments | Create deployment |
| GET | /api/deployments | List deployments |
| GET | /api/deployments/overview | 24h summary |
| GET | /api/deployments/{id} | Details |
| GET | /api/deployments/{id}/analytics | Full analytics |
| POST | /api/deployments/{id}/activate | Start |
| POST | /api/deployments/{id}/pause | Pause |
| POST | /api/deployments/{id}/complete | End + analyze |
| GET | /api/deployments/{id}/conversations | Participants |
| GET | /api/deployments/{id}/conversations/{cid}/transcript | Full transcript |
