---
stable_id: tasks.kanban
title: Task Kanban Board
ui_path: Tasks > Kanban
audience: researcher
status: documented
related_features: ["tasks.editor", "tasks.review", "tasks.send-report"]
related_glossary: ["scr"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/components/common/ToastNotification.tsx", "frontend/src/lib/taskProgressToast.ts", "frontend/src/lib/taskRealtime.ts", "frontend/src/stores/taskStore.ts", "backend/app/api/routes/tasks.py", "backend/app/api/websocket.py", "backend/app/core/agent_lifecycle.py"]
api_references: ["backend/app/api/routes/tasks.py", "backend/app/api/websocket.py"]
test_references: ["frontend/src/lib/taskProgressToast.test.ts", "frontend/src/lib/taskRealtime.test.ts", "frontend/src/stores/taskStore.test.ts", "tests/test_websocket.py", "tests/test_tasks.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-08-31
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
- Creating a card opens Task Editor immediately and reserves the task from agents while you configure its skill, files, context, and instructions. The agent can claim it only after Done Editing saves successfully and releases the reservation.
- Opening an existing card also reserves it. If another user already owns the edit lock, Istara warns you and leaves the editor closed.
- Agent terminal events refresh the card in place, so In Review and failure states reconcile without a manual page refresh or a blank-board flicker.
- Agent terminal updates distinguish work that is ready for human review from work that failed verification. A warning says `Task Needs Attention`; only a verified handoff says `Ready for Review`. A percentage reaching 100% alone is not presented as successful completion.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with task kanban board.
- The task list API requires the active project id; project-facing Kanban does not show cross-project task activity.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- A failed verification leaves the card outside Done and should be resolved through task details and review feedback; its warning is not evidence that research was accepted or reportable.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [tasks.editor](../../tasks/editor/researcher.md)
- [tasks.review](../../tasks/review/researcher.md)
- [tasks.send-report](../../tasks/send-report/researcher.md)

## Related Concepts

- [scr](../../../glossary/scr.md)

## Evidence

- Source files: `frontend/src/components/kanban/KanbanBoard.tsx`, `frontend/src/components/common/ToastNotification.tsx`, `frontend/src/lib/taskProgressToast.ts`, `frontend/src/lib/taskRealtime.ts`, `frontend/src/stores/taskStore.ts`, `backend/app/api/routes/tasks.py`, `backend/app/api/websocket.py`, `backend/app/core/agent_lifecycle.py`
- API references: `backend/app/api/routes/tasks.py`, `backend/app/api/websocket.py`
- Tests: `frontend/src/lib/taskProgressToast.test.ts`, `frontend/src/lib/taskRealtime.test.ts`, `frontend/src/stores/taskStore.test.ts`, `tests/test_websocket.py`, `tests/test_tasks.py`, `tests/test_project_scope_contracts.py`
