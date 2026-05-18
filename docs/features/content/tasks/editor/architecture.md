---
stable_id: tasks.editor
title: Task Editor
ui_path: Tasks > Task Editor
audience: architecture
status: documented
related_features: ["tasks.kanban", "tasks.attachments"]
related_glossary: ["scr"]
code_references: ["frontend/src/components/kanban/TaskEditor.tsx", "frontend/src/stores/taskStore.ts", "backend/app/api/routes/tasks.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Task Editor Architecture

## Implementation Summary

The task editor creates and updates task details, assignments, status, and task-linked research context.

## Frontend Surface

- `frontend/src/components/kanban/TaskEditor.tsx`
- `frontend/src/stores/taskStore.ts`
- `backend/app/api/routes/tasks.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/taskStore.ts`

### API And Backend

- `backend/app/api/routes/tasks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/kanban/TaskEditor.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_tasks.py`

## Related Features

- [tasks.kanban](../../tasks/kanban/architecture.md)
- [tasks.attachments](../../tasks/attachments/architecture.md)

## Related Concepts

- [scr](../../../glossary/scr.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
