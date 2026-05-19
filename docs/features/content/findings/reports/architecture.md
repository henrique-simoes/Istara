---
stable_id: findings.reports
title: Project Reports
ui_path: Findings > Reports
audience: architecture
status: documented
related_features: ["findings.evidence", "tasks.send-report", "interfaces.handoff"]
related_glossary: ["minto-pyramid", "scr", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/ProjectReportsView.tsx", "backend/app/api/routes/reports.py", "backend/app/core/report_manager.py", "backend/app/core/reporting_worker.py"]
api_references: ["backend/app/api/routes/reports.py"]
test_references: ["tests/test_research_integrity_reports.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-773
---

# Project Reports Architecture

## Implementation Summary

The Reports tab lets users generate, inspect, and manage project reports produced from findings and research evidence.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `frontend/src/components/findings/ProjectReportsView.tsx`
- `backend/app/api/routes/reports.py`
- `backend/app/core/report_manager.py`
- `backend/app/core/reporting_worker.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/reports.py`
- `backend/app/core/report_manager.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- Report generation and executive-summary calls preserve the report's `project_id` through async database boundaries and pass that project id into LLM routing so summaries cannot lose their project context.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Executive-summary and report-composition LLM calls are project-contextual and must keep the report project id attached to generated content.

## Tests And Verification

- `tests/test_research_integrity_reports.py`

## Related Features

- [findings.evidence](../../findings/evidence/architecture.md)
- [tasks.send-report](../../tasks/send-report/architecture.md)
- [interfaces.handoff](../../interfaces/handoff/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)
- [scr](../../../glossary/scr.md)
- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-773
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
