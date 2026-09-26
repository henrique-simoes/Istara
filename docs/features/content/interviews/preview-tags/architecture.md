---
stable_id: interviews.preview-tags
title: Interview Preview And Tags
ui_path: Interviews > Preview And Tags
audience: architecture
status: documented
related_features: ["agents.registry", "interviews.files"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interviews/interviewPreviewParts.tsx", "frontend/src/components/interviews/InterviewView.tsx"]
api_references: ["backend/app/api/routes/files.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Interview Preview And Tags Architecture

## Implementation Summary

Interview preview parts display file previews, send-to-agent actions, and tag creation controls.

## Frontend Surface

- `frontend/src/components/interviews/interviewPreviewParts.tsx`
- `frontend/src/components/interviews/InterviewView.tsx`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/files.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interviews/interviewPreviewParts.tsx` and the UI navigation path recorded in the inventory.
- On a phone (below the md breakpoint) the three columns take turns (2026-09-26,
  `interviewLayout.ts`): the open interview fills the screen, "All interviews" returns to the list,
  picking an interview opens it again, and the tags panel starts collapsed and opens over the
  interview. The fixed list (320 px) and tags panel (288 px) had left the interview no room at
  375 px. Desktop is unchanged. Journey: scenario 88.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [interviews.files](../../interviews/files/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
