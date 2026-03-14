# User Interviews Skill

> Plan, conduct, and analyze user interviews for UX Research projects.

## Overview

User interviews are the cornerstone of qualitative UX research. This skill helps researchers through the entire interview lifecycle:

1. **Planning** — Generate semi-structured interview guides
2. **Conducting** — Provide best practices and facilitation tips
3. **Analyzing** — Process transcripts, extract nuggets, identify themes
4. **Synthesizing** — Cross-reference findings across multiple interviews

## Modes

### `plan` — Generate Interview Guide

**Input:**
- Research questions (what you want to learn)
- Project context (product, users, goals)
- Number of participants (default: 5)

**Output:**
- Semi-structured interview guide with:
  - Introduction script
  - Warm-up questions (2-3)
  - Core questions organized by theme (8-12), each with follow-up probes
  - Closing questions
  - Debrief script

### `analyze` — Process Transcripts

**Input:**
- One or more transcript files (TXT, PDF, DOCX)
- Project context

**Output:**
- **Nuggets** — Direct quotes and observations with timestamps, tags, and emotional tone
- **Themes** — Recurring patterns across the transcript
- **Pain Points** — Issues identified with severity ratings
- **Opportunities** — Unmet needs and positive signals
- **Follow-up Questions** — Areas to explore in future interviews
- **Participant Summary** — Quick overview of this participant

### `synthesize` — Cross-Interview Analysis (automatic when >1 transcript)

**Output:**
- Cross-cutting themes with participant counts
- Verified facts with evidence chains
- Research insights with confidence levels
- Actionable recommendations with priority/effort ratings
- Research gaps and suggested methods to fill them

## Best Practices

- **Sample size:** 5-8 participants per user segment for saturation
- **Duration:** 45-60 minutes per session
- **Recording:** Always record (with consent) for accurate analysis
- **Probing:** "Tell me more about that" > "Did you like it?"
- **Neutrality:** Don't lead the participant toward desired answers
- **Follow-ups:** The best insights come from follow-up probes, not scripted questions

## Atomic Research Mapping

```
Interview Recording → Transcript → Nuggets → Facts → Insights → Recommendations
                                    (quotes)   (verified)  (patterns)   (actions)
```

Every nugget includes:
- Source file and timestamp
- Relevant tags for cross-referencing
- Emotional tone indicator
- Confidence score
