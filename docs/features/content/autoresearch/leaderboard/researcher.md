---
stable_id: autoresearch.leaderboard
title: Autoresearch Leaderboard
ui_path: Autoresearch > Leaderboard
audience: researcher
status: documented
related_features: ["autoresearch.experiments", "quality.dashboard"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/api/routes/autoresearch.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
---

# Autoresearch Leaderboard

## What It Does

The leaderboard ranks automated research experiment outcomes for comparison.

## Why It Exists

Autoresearch Leaderboard exists so the work represented by Autoresearch > Leaderboard has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Autoresearch > Leaderboard
- Navigation group: Autoresearch
- Primary component: `AutoresearchView`

## How UX Researchers Use It

- Open Autoresearch > Leaderboard from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with model and temperature rankings derived from the active project's telemetry.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Autoresearch > Leaderboard when the current research task needs autoresearch leaderboard.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: autoresearch.experiments, quality.dashboard.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped model and temperature rankings associated with the active project's experiment telemetry.
- Empty leaderboard state when the active project has no qualifying telemetry, rather than falling back to global model statistics.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/researcher.md)
- [quality.dashboard](../../quality/dashboard/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/autoresearch/AutoresearchView.tsx`, `backend/app/api/routes/autoresearch.py`
- API references: `backend/app/api/routes/autoresearch.py`
- Tests: `tests/test_autoresearch.py`, `tests/test_project_scope_contracts.py`
