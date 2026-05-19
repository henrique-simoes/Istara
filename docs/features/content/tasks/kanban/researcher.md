---
stable_id: tasks.kanban
title: Task Kanban Board
ui_path: Tasks > Kanban
audience: researcher
status: documented
related_features: ["tasks.editor", "tasks.review", "tasks.send-report"]
related_glossary: ["scr"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/stores/taskStore.ts", "backend/app/api/routes/tasks.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-770
---

# Task Kanban Board

## What It Does

Tasks presents project work as a Kanban board for tracking research operations, agent work, and review handoffs.

## Why It Exists

Task Kanban Board exists so the work represented by Tasks > Kanban has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Tasks > Kanban
- Navigation group: Tasks
- Primary component: `KanbanBoard`

## How UX Researchers Use It

- Open Tasks > Kanban from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with task kanban board in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Tasks > Kanban when the current research task needs task kanban board.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: tasks.editor, tasks.review, tasks.send-report.
- Task cards are loaded only for the active project. Switching projects clears the previous board state before the new project's cards are shown.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with task kanban board.
- The task list API requires the active project id; project-facing Kanban does not show cross-project task activity.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [tasks.editor](../../tasks/editor/researcher.md)
- [tasks.review](../../tasks/review/researcher.md)
- [tasks.send-report](../../tasks/send-report/researcher.md)

## Related Concepts

- [scr](../../../glossary/scr.md)

## Evidence

- Source files: `frontend/src/components/kanban/KanbanBoard.tsx`, `frontend/src/stores/taskStore.ts`, `backend/app/api/routes/tasks.py`
- API references: `backend/app/api/routes/tasks.py`
- Tests: `tests/test_tasks.py`, `tests/test_project_scope_contracts.py`
