---
stable_id: findings.phase-tabs
title: Findings Phase Tabs
ui_path: Findings > Evidence > Phase Tabs
audience: researcher
status: documented
related_features: ["findings.evidence"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/findings/FindingsView.tsx"]
api_references: ["backend/app/api/routes/findings.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Findings Phase Tabs

## What It Does

The Evidence view segments findings by Discover, Define, Develop, and Deliver project phases.

## Why It Exists

Findings Phase Tabs exists so the work represented by Findings > Evidence > Phase Tabs has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Findings > Evidence > Phase Tabs
- Navigation group: Findings
- Primary component: `FindingsView`

## How UX Researchers Use It

- Open Findings > Evidence > Phase Tabs from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with findings phase tabs in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Findings > Evidence > Phase Tabs when the current research task needs findings phase tabs.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.evidence.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with findings phase tabs.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.evidence](../../findings/evidence/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Evidence

- Source files: `frontend/src/components/findings/FindingsView.tsx`
- API references: `backend/app/api/routes/findings.py`
- Tests: none recorded
