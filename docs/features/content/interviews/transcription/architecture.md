---
stable_id: interviews.transcription
title: Interview Transcription
ui_path: Interviews > Transcription
audience: architecture
status: needs-verification
related_features: ["interviews.files", "findings.evidence"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interviews/InterviewView.tsx", "frontend/src/components/interviews/AudioPlayer.tsx", "backend/app/core/transcription.py"]
api_references: ["backend/app/api/routes/files.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Interview Transcription Architecture

## Implementation Summary

Interview audio processing uses backend transcription capabilities to turn recordings into usable research text.

## Frontend Surface

- `frontend/src/components/interviews/InterviewView.tsx`
- `frontend/src/components/interviews/AudioPlayer.tsx`
- `backend/app/core/transcription.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/files.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interviews/InterviewView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [interviews.files](../../interviews/files/architecture.md)
- [findings.evidence](../../findings/evidence/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
