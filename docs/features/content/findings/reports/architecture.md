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
test_references: ["tests/test_research_integrity_reports.py", "tests/real_user_benchmark/run.mjs"]
last_verified: 2026-05-21
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-773; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581
---

# Project Reports Architecture

## Implementation Summary

The Reports tab lets users generate, inspect, and manage project reports produced from findings and research evidence. In the real-user benchmark, report evidence is strongest when the Findings chain is created from approved task outputs rather than synthetic notes created before review.

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
- Task-produced findings carry `task_id` provenance. Reports consume those findings only after the associated task is Done and `review_state=approved`; In Review work can create findings for researcher review, but it is not report evidence at any reporting layer.
- The real-user benchmark records approved task ids before creating task-backed nuggets, facts, insights, and recommendations, then requests report/brief generation after that chain exists. This keeps Findings/reporting aligned with Istara's human-in-the-loop review process.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Executive-summary and report-composition LLM calls are project-contextual and must keep the report project id attached to generated content.
- Agentic reporting is based on reviewed project evidence. Benchmark artifacts must distinguish approved-task-backed report generation from fallback baseline report checks, and must not count In Review findings as approved report material.

## Tests And Verification

- `tests/test_research_integrity_reports.py`
- `tests/real_user_benchmark/run.mjs`

## Related Features

- [findings.evidence](../../findings/evidence/architecture.md)
- [tasks.send-report](../../tasks/send-report/architecture.md)
- [interfaces.handoff](../../interfaces/handoff/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)
- [scr](../../../glossary/scr.md)
- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-773; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
