---
stable_id: autoresearch.leaderboard
title: Autoresearch Leaderboard
ui_path: Autoresearch > Leaderboard
audience: architecture
status: documented
related_features: ["autoresearch.experiments", "quality.dashboard"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/api/routes/autoresearch.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
---

# Autoresearch Leaderboard Architecture

## Implementation Summary

The leaderboard ranks automated research experiment outcomes for comparison.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `backend/app/api/routes/autoresearch.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`
- Leaderboard requests use the active project id and clear leaderboard state when no project is active.

### API And Backend

- `backend/app/api/routes/autoresearch.py`
- `/api/autoresearch/leaderboard` requires `project_id`, enforces project visibility, and derives model/temperature rankings from project-scoped telemetry rather than global model statistics.

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Leaderboard entries influence model/temperature choices, so they must be computed from telemetry the active project is authorized to expose.

## Tests And Verification

- `tests/test_autoresearch.py` verifies the leaderboard endpoint requires project-scoped access.
- `tests/test_project_scope_contracts.py` verifies the frontend and backend do not use unscoped leaderboard calls.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/architecture.md)
- [quality.dashboard](../../quality/dashboard/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
