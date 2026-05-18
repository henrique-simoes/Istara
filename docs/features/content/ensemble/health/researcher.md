---
stable_id: ensemble.health
title: Ensemble Health
ui_path: Ensemble Health
audience: researcher
status: needs-verification
related_features: ["quality.dashboard", "compute.pool"]
related_glossary: ["fleiss-kappa"]
code_references: ["frontend/src/components/common/EnsembleHealthView.tsx", "backend/app/core/consensus.py"]
api_references: ["backend/app/api/routes/metrics.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Ensemble Health

## What It Does

Ensemble Health surfaces health and consensus signals for Istara's multi-model or multi-agent ensemble behavior.

## Why It Exists

Ensemble Health exists so the work represented by Ensemble Health has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Ensemble Health
- Navigation group: Secondary
- Primary component: `EnsembleHealthView`

## How UX Researchers Use It

- Open Ensemble Health from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with ensemble health in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Ensemble Health when the current research task needs ensemble health.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: quality.dashboard, compute.pool.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with ensemble health.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [quality.dashboard](../../quality/dashboard/researcher.md)
- [compute.pool](../../compute/pool/researcher.md)

## Related Concepts

- [fleiss-kappa](../../../glossary/fleiss-kappa.md)

## Evidence

- Source files: `frontend/src/components/common/EnsembleHealthView.tsx`, `backend/app/core/consensus.py`
- API references: `backend/app/api/routes/metrics.py`
- Tests: none recorded
