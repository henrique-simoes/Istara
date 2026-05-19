---
stable_id: chat.steering
title: Chat Steering
ui_path: Chat > Steering
audience: researcher
status: documented
related_features: ["chat.overview", "context.editor"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SteeringInput.tsx", "backend/app/api/routes/steering.py"]
api_references: ["backend/app/api/routes/steering.py"]
test_references: ["tests/test_steering_api.py", "tests/test_steering_manager.py", "tests/test_steering_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-87 / CF-1117
---

# Chat Steering

## What It Does

Steering controls collect lightweight user guidance that can shape downstream assistant behavior for the active project.

## Why It Exists

Chat Steering exists so the work represented by Chat > Steering has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools or other projects.

## Where It Lives

- UI path: Chat > Steering
- Navigation group: Chat
- Primary component: `SteeringInput`

## How UX Researchers Use It

- Open Chat > Steering from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with chat steering in the active project context.
- Queue status, queued message recovery, abort, and follow-up controls show only messages for the current project.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Chat > Steering when the current research task needs chat steering.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: chat.overview, context.editor.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped steering and follow-up messages associated with the current project.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Steering controls are hidden when there is no active project because unscoped steering is not allowed.
- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.overview](../../chat/overview/researcher.md)
- [context.editor](../../context/editor/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/SteeringInput.tsx`, `backend/app/api/routes/steering.py`
- API references: `backend/app/api/routes/steering.py`
- Tests: `tests/test_steering_api.py`, `tests/test_steering_manager.py`, `tests/test_steering_project_scope_contracts.py`
