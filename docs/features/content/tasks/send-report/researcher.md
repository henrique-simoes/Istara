---
stable_id: tasks.send-report
title: Send Task To Report
ui_path: Tasks > Send To Report
audience: researcher
status: needs-verification
related_features: ["findings.reports", "tasks.review"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/components/kanban/TaskEditor.tsx", "backend/app/api/routes/tasks.py"]
api_references: ["backend/app/api/routes/tasks.py", "backend/app/api/routes/reports.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Send Task To Report

## What It Does

Task surfaces can move validated task outputs toward report generation or reporting workflows.

## Why It Exists

Send Task To Report exists so the work represented by Tasks > Send To Report has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Tasks > Send To Report
- Navigation group: Tasks
- Primary component: `KanbanBoard / TaskEditor`

## How UX Researchers Use It

- Open Tasks > Send To Report from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with send task to report in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Tasks > Send To Report when the current research task needs send task to report.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.reports, tasks.review.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with send task to report.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.reports](../../findings/reports/researcher.md)
- [tasks.review](../../tasks/review/researcher.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Evidence

- Source files: `frontend/src/components/kanban/KanbanBoard.tsx`, `frontend/src/components/kanban/TaskEditor.tsx`, `backend/app/api/routes/tasks.py`
- API references: `backend/app/api/routes/tasks.py`, `backend/app/api/routes/reports.py`
- Tests: `tests/test_tasks.py`
