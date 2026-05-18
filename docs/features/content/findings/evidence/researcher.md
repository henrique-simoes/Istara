---
stable_id: findings.evidence
title: Findings Evidence
ui_path: Findings > Evidence
audience: researcher
status: documented
related_features: ["findings.phase-tabs", "findings.codebook", "findings.reports"]
related_glossary: ["atomic-research", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "backend/app/api/routes/findings.py"]
api_references: ["backend/app/api/routes/findings.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Findings Evidence

## What It Does

The Findings evidence tab lists research insights and recommendations for the active project and supports phase-oriented review.

## Why It Exists

Findings Evidence exists so the work represented by Findings > Evidence has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Findings > Evidence
- Navigation group: Findings
- Primary component: `FindingsView`

## How UX Researchers Use It

- Open Findings > Evidence from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with findings evidence in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Findings > Evidence when the current research task needs findings evidence.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.phase-tabs, findings.codebook, findings.reports.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with findings evidence.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.phase-tabs](../../findings/phase-tabs/researcher.md)
- [findings.codebook](../../findings/codebook/researcher.md)
- [findings.reports](../../findings/reports/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)
- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/findings/FindingsView.tsx`, `backend/app/api/routes/findings.py`
- API references: `backend/app/api/routes/findings.py`
- Tests: none recorded
