---
stable_id: autoresearch.experiments
title: Autoresearch Experiments
ui_path: Autoresearch > Experiments
audience: researcher
status: documented
related_features: ["autoresearch.dashboard", "autoresearch.config"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_engine.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Autoresearch Experiments

## What It Does

Experiments configure and inspect automated research runs across strategies or parameters.

## Why It Exists

Autoresearch Experiments exists so the work represented by Autoresearch > Experiments has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Autoresearch > Experiments
- Navigation group: Autoresearch
- Primary component: `AutoresearchView`

## How UX Researchers Use It

- Open Autoresearch > Experiments from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with autoresearch experiments in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Autoresearch > Experiments when the current research task needs autoresearch experiments.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: autoresearch.dashboard, autoresearch.config.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with autoresearch experiments.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [autoresearch.dashboard](../../autoresearch/dashboard/researcher.md)
- [autoresearch.config](../../autoresearch/config/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/autoresearch/AutoresearchView.tsx`, `backend/app/core/autoresearch_engine.py`
- API references: `backend/app/api/routes/autoresearch.py`
- Tests: none recorded
