---
stable_id: interfaces.handoff
title: Interface Handoff
ui_path: Interfaces > Handoff
audience: researcher
status: needs-verification
related_features: ["interfaces.screens", "findings.reports"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/interfaces/HandoffTab.tsx", "backend/app/api/routes/interfaces.py"]
api_references: ["backend/app/api/routes/interfaces.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Interface Handoff

## What It Does

Handoff packages interface outputs into developer-facing specifications or exportable artifacts.

## Why It Exists

Interface Handoff exists so the work represented by Interfaces > Handoff has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interfaces > Handoff
- Navigation group: Interfaces
- Primary component: `HandoffTab`

## How UX Researchers Use It

- Open Interfaces > Handoff from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with interface handoff in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interfaces > Handoff when the current research task needs interface handoff.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: interfaces.screens, findings.reports.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with interface handoff.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [interfaces.screens](../../interfaces/screens/researcher.md)
- [findings.reports](../../findings/reports/researcher.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Evidence

- Source files: `frontend/src/components/interfaces/HandoffTab.tsx`, `backend/app/api/routes/interfaces.py`
- API references: `backend/app/api/routes/interfaces.py`
- Tests: none recorded
