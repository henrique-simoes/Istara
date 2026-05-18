---
stable_id: loops.history
title: Loop Execution History
ui_path: Loops > History
audience: architecture
status: documented
related_features: ["loops.overview", "history.version"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/ExecutionHistoryTab.tsx", "backend/app/api/routes/loops.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Loop Execution History Architecture

## Implementation Summary

Execution History records loop runs, outcomes, and recent automation activity.

## Frontend Surface

- `frontend/src/components/loops/ExecutionHistoryTab.tsx`
- `backend/app/api/routes/loops.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/loops.py`
- Execution history is project content: non-admin requests must include an authorized active `project_id`, and execution rows are filtered to source IDs owned by that project.

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/ExecutionHistoryTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_loops.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [loops.overview](../../loops/overview/architecture.md)
- [history.version](../../history/version/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
