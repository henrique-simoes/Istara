---
stable_id: tasks.review
title: Human Task Review
ui_path: Tasks > Review
audience: researcher
status: documented
related_features: ["findings.review", "agents.proposals"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/kanban/KanbanBoard.tsx", "frontend/src/components/kanban/TaskEditor.tsx", "backend/app/core/task_review.py"]
api_references: ["backend/app/api/routes/tasks.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-08-31
compass: CF-SPEC-53 / CF-657
---

# Human Task Review

## What It Does

Review actions support approving, requesting revision, or otherwise resolving human-in-the-loop task work.

## Why It Exists

Human Task Review exists so the work represented by Tasks > Review has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Tasks > Review
- Navigation group: Tasks
- Primary component: `KanbanBoard / TaskEditor`

## How UX Researchers Use It

- Open Tasks > Review from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with human task review in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Tasks > Review when the current research task needs human task review.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.review, agents.proposals.
- To send unsuccessful work back, write concrete review instructions, choose `Return to Backlog` or `Resume In Progress`, then press `Request Revision`. The destination buttons only select where the work should return; they do not move the task by themselves.
- Istara saves the review details before releasing the editing reservation, so an agent cannot restart with stale feedback or attachments.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with human task review.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.review](../../findings/review/researcher.md)
- [agents.proposals](../../agents/proposals/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/kanban/KanbanBoard.tsx`, `frontend/src/components/kanban/TaskEditor.tsx`, `backend/app/core/task_review.py`
- API references: `backend/app/api/routes/tasks.py`
- Tests: `tests/test_tasks.py`
