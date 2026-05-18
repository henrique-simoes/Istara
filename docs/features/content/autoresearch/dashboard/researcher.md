---
stable_id: autoresearch.dashboard
title: Autoresearch Dashboard
ui_path: Autoresearch > Dashboard
audience: researcher
status: documented
related_features: ["autoresearch.experiments", "autoresearch.leaderboard"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "frontend/src/stores/autoresearchStore.ts", "backend/app/api/routes/autoresearch.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
---

# Autoresearch Dashboard

## What It Does

The Autoresearch dashboard summarizes automated research experiment status and recent results.

## Why It Exists

Autoresearch Dashboard exists so the work represented by Autoresearch > Dashboard has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Autoresearch > Dashboard
- Navigation group: Autoresearch
- Primary component: `AutoresearchView`

## How UX Researchers Use It

- Open Autoresearch > Dashboard from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work only with autoresearch dashboard data from the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Autoresearch > Dashboard when the current research task needs autoresearch dashboard.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: autoresearch.experiments, autoresearch.leaderboard.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped status and operational metrics associated with the active project.
- Visible task, agent, document, finding, deployment, telemetry, schedule, and experiment counts filtered to the project the current user is authorized to access.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/researcher.md)
- [autoresearch.leaderboard](../../autoresearch/leaderboard/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/autoresearch/AutoresearchView.tsx`, `frontend/src/stores/autoresearchStore.ts`, `backend/app/api/routes/autoresearch.py`
- API references: `backend/app/api/routes/autoresearch.py`
- Tests: `tests/test_autoresearch.py`, `tests/test_project_scope_contracts.py`
