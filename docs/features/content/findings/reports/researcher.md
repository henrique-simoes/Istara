---
stable_id: findings.reports
title: Project Reports
ui_path: Findings > Reports
audience: researcher
status: documented
related_features: ["findings.evidence", "tasks.send-report", "interfaces.handoff"]
related_glossary: ["minto-pyramid", "scr", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/ProjectReportsView.tsx", "backend/app/api/routes/reports.py", "backend/app/core/report_manager.py", "backend/app/core/reporting_worker.py"]
api_references: ["backend/app/api/routes/reports.py"]
test_references: ["tests/test_research_integrity_reports.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-773
---

# Project Reports

## What It Does

The Reports tab lets users generate, inspect, and manage project reports produced from findings and research evidence.

## Why It Exists

Project Reports exists so the work represented by Findings > Reports has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Findings > Reports
- Navigation group: Findings
- Primary component: `ProjectReportsView`

## How UX Researchers Use It

- Open Findings > Reports from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with project reports in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Findings > Reports when the current research task needs project reports.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.evidence, tasks.send-report, interfaces.handoff.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with project reports.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Generated executive summaries keep the report's project context attached during LLM routing.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.evidence](../../findings/evidence/researcher.md)
- [tasks.send-report](../../tasks/send-report/researcher.md)
- [interfaces.handoff](../../interfaces/handoff/researcher.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)
- [scr](../../../glossary/scr.md)
- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/findings/FindingsView.tsx`, `frontend/src/components/findings/ProjectReportsView.tsx`, `backend/app/api/routes/reports.py`, `backend/app/core/report_manager.py`, `backend/app/core/reporting_worker.py`
- API references: `backend/app/api/routes/reports.py`
- Tests: `tests/test_research_integrity_reports.py`
