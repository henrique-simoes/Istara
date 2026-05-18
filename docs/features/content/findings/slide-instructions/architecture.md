---
stable_id: findings.slide-instructions
title: Report Slide Instructions
ui_path: Findings > Reports > Slide Instructions
audience: architecture
status: needs-verification
related_features: ["findings.reports", "interfaces.handoff"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/findings/ProjectReportsView.tsx", "backend/app/api/routes/presentation.py"]
api_references: ["backend/app/api/routes/presentation.py", "backend/app/api/routes/reports.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Report Slide Instructions Architecture

## Implementation Summary

Report-related surfaces support presentation or slide guidance that can carry research findings into communicable report artifacts.

## Frontend Surface

- `frontend/src/components/findings/ProjectReportsView.tsx`
- `backend/app/api/routes/presentation.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/presentation.py`
- `backend/app/api/routes/reports.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/ProjectReportsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [findings.reports](../../findings/reports/architecture.md)
- [interfaces.handoff](../../interfaces/handoff/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
