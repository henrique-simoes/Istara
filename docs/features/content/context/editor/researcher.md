---
stable_id: context.editor
title: Project Context Editor
ui_path: Context > Editor
audience: researcher
status: documented
related_features: ["chat.steering", "memory.context-dag"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/projects/ContextEditor.tsx", "backend/app/api/routes/projects.py"]
api_references: ["backend/app/api/routes/projects.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Project Context Editor

## What It Does

The Context view edits project background, goals, assumptions, and other structured context used by Istara workflows.

## Why It Exists

Project Context Editor exists so the work represented by Context > Editor has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Context > Editor
- Navigation group: Context
- Primary component: `ContextEditor`

## How UX Researchers Use It

- Open Context > Editor from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with project context editor in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Context > Editor when the current research task needs project context editor.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: chat.steering, memory.context-dag.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with project context editor.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.steering](../../chat/steering/researcher.md)
- [memory.context-dag](../../memory/context-dag/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/projects/ContextEditor.tsx`, `backend/app/api/routes/projects.py`
- API references: `backend/app/api/routes/projects.py`
- Tests: none recorded
