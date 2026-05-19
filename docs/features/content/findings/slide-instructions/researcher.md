---
stable_id: findings.slide-instructions
title: Report Slide Instructions
ui_path: Findings > Reports > Slide Instructions
audience: researcher
status: needs-verification
related_features: ["findings.reports", "interfaces.handoff"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/findings/ProjectReportsView.tsx", "backend/app/api/routes/presentation.py"]
api_references: ["backend/app/api/routes/presentation.py", "backend/app/api/routes/reports.py"]
test_references: ["tests/test_reports.py"]
last_verified: 2026-05-19
compass: CF-SPEC-94 / CF-1205
---

# Report Slide Instructions

## What It Does

Report-related surfaces support presentation or slide guidance that can carry research findings into communicable report artifacts. The slide-instruction action only works for reports that belong to the currently active project.

## Why It Exists

Report Slide Instructions exists so the work represented by Findings > Reports > Slide Instructions has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Findings > Reports > Slide Instructions
- Navigation group: Findings
- Primary component: `ProjectReportsView`

## How UX Researchers Use It

- Open Findings > Reports > Slide Instructions from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with report slide instructions in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Findings > Reports > Slide Instructions when the current research task needs report slide instructions.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.reports, interfaces.handoff.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with report slide instructions.
- Slide instructions generated from the selected active-project report; stale report ids from another project are rejected.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.reports](../../findings/reports/researcher.md)
- [interfaces.handoff](../../interfaces/handoff/researcher.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Evidence

- Source files: `frontend/src/components/findings/ProjectReportsView.tsx`, `backend/app/api/routes/presentation.py`
- API references: `backend/app/api/routes/presentation.py`, `backend/app/api/routes/reports.py`
- Tests: `tests/test_reports.py`
