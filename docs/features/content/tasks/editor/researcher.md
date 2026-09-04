---
stable_id: tasks.editor
title: Task Editor
ui_path: Tasks > Task Editor
audience: researcher
status: documented
related_features: ["tasks.kanban", "tasks.attachments"]
related_glossary: ["scr"]
code_references: ["frontend/src/components/kanban/TaskEditor.tsx", "frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/lib/api.ts", "frontend/src/stores/taskStore.ts", "backend/app/api/routes/tasks.py", "backend/app/core/agent_lifecycle.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["frontend/src/stores/taskStore.test.ts", "tests/test_tasks.py"]
last_verified: 2026-08-31
compass: CF-SPEC-53 / CF-657
---

# Task Editor

## What It Does

The task editor creates and updates task details, assignments, status, and task-linked research context.

## Why It Exists

Task Editor exists so the work represented by Tasks > Task Editor has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Tasks > Task Editor
- Navigation group: Tasks
- Primary component: `TaskEditor`

## How UX Researchers Use It

- Open Tasks > Task Editor from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with task editor in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Tasks > Task Editor when the current research task needs task editor.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: tasks.kanban, tasks.attachments.
- A newly created task opens here before any agent can claim it. Add the intended skill, files, context, instructions, links, and labels while the header says the task is locked for editing.
- Save records changes but keeps the reservation. Done Editing saves, releases the reservation, and only then makes Backlog or In Progress work available to the assigned agent.
- If saving or releasing the reservation fails, the editor stays open and shows the error; your task is not silently handed to an agent with partial configuration.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with task editor.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [tasks.kanban](../../tasks/kanban/researcher.md)
- [tasks.attachments](../../tasks/attachments/researcher.md)

## Related Concepts

- [scr](../../../glossary/scr.md)

## Evidence

- Source files: `frontend/src/components/kanban/TaskEditor.tsx`, `frontend/src/components/kanban/KanbanBoard.tsx`, `frontend/src/lib/api.ts`, `frontend/src/stores/taskStore.ts`, `backend/app/api/routes/tasks.py`, `backend/app/core/agent_lifecycle.py`
- API references: `backend/app/api/routes/tasks.py`
- Tests: `frontend/src/stores/taskStore.test.ts`, `tests/test_tasks.py`
