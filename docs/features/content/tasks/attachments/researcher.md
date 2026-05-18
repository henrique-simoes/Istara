---
stable_id: tasks.attachments
title: Task Attachments
ui_path: Tasks > Attachments
audience: researcher
status: needs-verification
related_features: ["documents.upload", "tasks.editor"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/kanban/TaskEditor.tsx", "backend/app/api/routes/tasks.py", "backend/app/api/routes/files.py"]
api_references: ["backend/app/api/routes/tasks.py", "backend/app/api/routes/files.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Task Attachments

## What It Does

Tasks can reference project files or documents so research work stays connected to the evidence it depends on.

## Why It Exists

Task Attachments exists so the work represented by Tasks > Attachments has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Tasks > Attachments
- Navigation group: Tasks
- Primary component: `TaskEditor`

## How UX Researchers Use It

- Open Tasks > Attachments from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with task attachments in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Tasks > Attachments when the current research task needs task attachments.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: documents.upload, tasks.editor.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with task attachments.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [documents.upload](../../documents/upload/researcher.md)
- [tasks.editor](../../tasks/editor/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/kanban/TaskEditor.tsx`, `backend/app/api/routes/tasks.py`, `backend/app/api/routes/files.py`
- API references: `backend/app/api/routes/tasks.py`, `backend/app/api/routes/files.py`
- Tests: `tests/test_tasks.py`
