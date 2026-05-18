---
stable_id: autoresearch.leaderboard
title: Autoresearch Leaderboard
ui_path: Autoresearch > Leaderboard
audience: researcher
status: needs-verification
related_features: ["autoresearch.experiments", "quality.dashboard"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/api/routes/autoresearch.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
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
- Use the visible controls in this surface to work with autoresearch leaderboard in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Autoresearch > Leaderboard when the current research task needs autoresearch leaderboard.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: autoresearch.experiments, quality.dashboard.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with autoresearch leaderboard.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

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
- Tests: none recorded
