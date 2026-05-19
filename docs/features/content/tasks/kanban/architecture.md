---
stable_id: tasks.kanban
title: Task Kanban Board
ui_path: Tasks > Kanban
audience: architecture
status: documented
related_features: ["tasks.editor", "tasks.review", "tasks.send-report"]
related_glossary: ["scr"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/stores/taskStore.ts", "backend/app/api/routes/tasks.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-770
---

# Task Kanban Board Architecture

## Implementation Summary

Tasks presents project work as a Kanban board for tracking research operations, agent work, and review handoffs.

## Frontend Surface

- `frontend/src/components/kanban/KanbanBoard.tsx`
- `frontend/src/stores/taskStore.ts`
- `backend/app/api/routes/tasks.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/taskStore.ts`

### API And Backend

- `backend/app/api/routes/tasks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/kanban/KanbanBoard.tsx` and the UI navigation path recorded in the inventory.
- Task list reads are active-project scoped: `/api/tasks` requires `project_id` for every role, including global admins, and verifies project visibility before returning cards.
- `frontend/src/stores/taskStore.ts` clears stale cards when there is no active project or when a scoped fetch fails, then filters returned rows back to the active project id as a frontend defense-in-depth check.
- Cross-project task aggregation belongs on explicit admin reporting surfaces, not on the project-facing Kanban route or store.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_tasks.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [tasks.editor](../../tasks/editor/architecture.md)
- [tasks.review](../../tasks/review/architecture.md)
- [tasks.send-report](../../tasks/send-report/architecture.md)

## Related Concepts

- [scr](../../../glossary/scr.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-770
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
