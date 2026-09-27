---
stable_id: findings.reports
title: Project Reports
ui_path: Findings > Reports
audience: researcher
status: documented
related_features: ["findings.evidence", "tasks.send-report", "interfaces.handoff"]
related_glossary: ["minto-pyramid", "scr", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/ProjectReportsView.tsx", "backend/app/api/routes/reports.py", "backend/app/core/report_manager.py", "backend/app/core/reporting_worker.py", "backend/app/services/report_export.py"]
api_references: ["backend/app/api/routes/reports.py"]
test_references: ["tests/test_research_integrity_reports.py", "tests/test_report_export.py"]
last_verified: 2026-09-27
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

- Open Findings > Reports. A report exists only for work that passed the Research Spine: a task's
  findings reach Reports after its codes are reconciled and the task is approved as Done.
- Open a report to read its executive summary and findings.
- Share it with **Export**: **Markdown** and **Word** give the report with every finding followed by
  its evidence trail (the quoted source text, the document and character range it comes from, and
  whether that coded evidence was accepted); **CSV** gives one row per finding and quote for your own
  analysis or an evidence appendix.

## Supported Workflows

- Hand a report to stakeholders as a Word document whose every claim can be checked against the
  source.
- Build an evidence appendix from the CSV.
- Move to related surfaces when needed: findings.evidence, tasks.send-report, interfaces.handoff.

## Inputs, Outputs, And Expected Outcomes

- Input: an approved Done task's findings, grounded in evidence units.
- Output: the report in Istara, and exports named after the report.
- Each export states how many of its findings are traced to a source span; a finding with no trail
  is marked "not traced to a source" rather than presented as evidence.

## Caveats

- Exports carry pseudonymous participant labels as they appear in the sources; remove anything
  identifying from sources before sharing.
- PDF export is not offered; print the Word document to PDF.

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
