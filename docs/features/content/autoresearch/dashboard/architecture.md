---
stable_id: autoresearch.dashboard
title: Autoresearch Dashboard
ui_path: Autoresearch > Dashboard
audience: architecture
status: documented
related_features: ["autoresearch.experiments", "autoresearch.leaderboard"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "frontend/src/stores/autoresearchStore.ts", "backend/app/api/routes/autoresearch.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
---

# Autoresearch Dashboard Architecture

## Implementation Summary

The Autoresearch dashboard summarizes automated research experiment status and recent results.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `frontend/src/stores/autoresearchStore.ts`
- `backend/app/api/routes/autoresearch.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`
- Dashboard status requests use the active project id from `frontend/src/stores/projectStore.ts`; missing project context clears status instead of querying global metrics.

### API And Backend

- `backend/app/api/routes/autoresearch.py`
- `/api/autoresearch/status` requires `project_id`, enforces project access, and returns task, agent, document, finding, telemetry, schedule, and deployment metrics filtered to that project.

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Autoresearch status can inform automated experiment loops, so every operational signal in the dashboard must be scoped to the active project before it can influence agents, skills, LLM routing, or improvement proposals.

## Tests And Verification

- `tests/test_autoresearch.py` verifies project-scoped status metrics.
- `tests/test_project_scope_contracts.py` verifies frontend status calls carry the active project id and backend status uses project-filtered queries.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/architecture.md)
- [autoresearch.leaderboard](../../autoresearch/leaderboard/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
