---
stable_id: tasks.send-report
title: Send Task To Report
ui_path: Tasks > Send To Report
audience: architecture
status: needs-verification
related_features: ["findings.reports", "tasks.review"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/components/kanban/TaskEditor.tsx", "backend/app/api/routes/tasks.py"]
api_references: ["backend/app/api/routes/tasks.py", "backend/app/api/routes/reports.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941
---

# Send Task To Report Architecture

## Implementation Summary

Task surfaces can move validated task outputs toward report generation or reporting workflows.

## Frontend Surface

- `frontend/src/components/kanban/KanbanBoard.tsx`
- `frontend/src/components/kanban/TaskEditor.tsx`
- `backend/app/api/routes/tasks.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/taskStore.ts`

### API And Backend

- `backend/app/api/routes/tasks.py`
- `backend/app/api/routes/reports.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/kanban/KanbanBoard.tsx` and the UI navigation path recorded in the inventory.
- Sending a task to Reports is active-project-bound: the UI passes `activeProjectId`, and `/api/tasks/{task_id}/reports` loads the task by both task id and project id before creating a project report.
- Report creation remains limited to human-approved Done tasks in the same project; stale task ids from another project resolve as not found instead of creating cross-project report drafts.
- Done status is necessary but not sufficient. The task must also have accepted/reconciled Research Spine evidence or reportable task artifacts; task notes alone cannot be sent to Reports.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_tasks.py`

## Related Features

- [findings.reports](../../findings/reports/architecture.md)
- [tasks.review](../../tasks/review/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
