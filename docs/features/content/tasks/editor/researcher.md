---
stable_id: tasks.editor
title: Task Editor
ui_path: Tasks > Task Editor
audience: researcher
status: documented
related_features: ["tasks.kanban", "tasks.attachments"]
related_glossary: ["scr"]
code_references: ["frontend/src/components/kanban/TaskEditor.tsx", "frontend/src/stores/taskStore.ts", "backend/app/api/routes/tasks.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-05-15
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

- Source files: `frontend/src/components/kanban/TaskEditor.tsx`, `frontend/src/stores/taskStore.ts`, `backend/app/api/routes/tasks.py`
- API references: `backend/app/api/routes/tasks.py`
- Tests: `tests/test_tasks.py`
