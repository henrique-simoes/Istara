---
stable_id: tasks.review
title: Human Task Review
ui_path: Tasks > Review
audience: architecture
status: documented
related_features: ["findings.review", "agents.proposals"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/components/kanban/TaskEditor.tsx", "backend/app/core/task_review.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Human Task Review Architecture

## Implementation Summary

Review actions support approving, requesting revision, or otherwise resolving human-in-the-loop task work.

## Frontend Surface

- `frontend/src/components/kanban/KanbanBoard.tsx`
- `frontend/src/components/kanban/TaskEditor.tsx`
- `backend/app/core/task_review.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/taskStore.ts`

### API And Backend

- `backend/app/api/routes/tasks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/kanban/KanbanBoard.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_tasks.py`

## Related Features

- [findings.review](../../findings/review/architecture.md)
- [agents.proposals](../../agents/proposals/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
