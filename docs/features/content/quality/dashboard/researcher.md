---
stable_id: quality.dashboard
title: Quality Dashboard
ui_path: Quality Dashboard
audience: researcher
status: documented
related_features: ["ensemble.health", "settings.governed-evolution"]
related_glossary: ["triangulation", "fleiss-kappa"]
code_references: ["frontend/src/components/common/QualityView.tsx", "backend/app/core/validation.py", "backend/app/core/adaptive_validation.py"]
api_references: ["backend/app/api/routes/metrics.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Quality Dashboard

## What It Does

Quality Dashboard summarizes system quality, validation, and operational signals for the running Istara installation.

## Why It Exists

Quality Dashboard exists so the work represented by Quality Dashboard has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Quality Dashboard
- Navigation group: Secondary
- Primary component: `QualityView`

## How UX Researchers Use It

- Open Quality Dashboard from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with quality dashboard in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Quality Dashboard when the current research task needs quality dashboard.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: ensemble.health, settings.governed-evolution.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with quality dashboard.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [ensemble.health](../../ensemble/health/researcher.md)
- [settings.governed-evolution](../../settings/governed-evolution/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)
- [fleiss-kappa](../../../glossary/fleiss-kappa.md)

## Evidence

- Source files: `frontend/src/components/common/QualityView.tsx`, `backend/app/core/validation.py`, `backend/app/core/adaptive_validation.py`
- API references: `backend/app/api/routes/metrics.py`
- Tests: none recorded
