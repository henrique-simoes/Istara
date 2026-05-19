---
stable_id: shell.projects
title: Project Switcher
ui_path: Shell > Projects
audience: researcher
status: documented
related_features: ["shell.navigation", "chat.overview", "tasks.kanban"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/layout/Sidebar.tsx", "frontend/src/stores/projectStore.ts", "backend/app/api/routes/projects.py"]
api_references: ["backend/app/api/routes/projects.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Project Switcher

## What It Does

The sidebar project control lists available projects and lets users create, select, pause, resume, or delete the active project context used by most Istara views.

## Why It Exists

Project Switcher exists so the work represented by Shell > Projects has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Projects
- Navigation group: Shell
- Primary component: `Sidebar`

## How UX Researchers Use It

- Open Shell > Projects from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with project switcher in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Projects when the current research task needs project switcher.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.navigation, chat.overview, tasks.kanban.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with project switcher.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.navigation](../../shell/navigation/researcher.md)
- [chat.overview](../../chat/overview/researcher.md)
- [tasks.kanban](../../tasks/kanban/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/stores/projectStore.ts`, `backend/app/api/routes/projects.py`
- API references: `backend/app/api/routes/projects.py`
- Tests: none recorded
