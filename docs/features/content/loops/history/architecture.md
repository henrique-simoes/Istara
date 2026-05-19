---
stable_id: loops.history
title: Loop Execution History
ui_path: Loops > History
audience: architecture
status: documented
related_features: ["loops.overview", "history.version"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/ExecutionHistoryTab.tsx", "backend/app/api/routes/loops.py", "backend/app/services/loop_execution_service.py", "backend/app/models/loop_execution.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: ["tests/test_loops.py", "tests/test_project_scope_contracts.py", "tests/test_simulation_project_scope_contracts.py", "tests/simulation/scenarios/49-loops-schedule.mjs"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-97 / CF-1237; CF-SPEC-107 / CF-1351
---

# Loop Execution History Architecture

## Implementation Summary

Execution History records loop runs, outcomes, and recent automation activity.

## Frontend Surface

- `frontend/src/components/loops/ExecutionHistoryTab.tsx`
- `backend/app/api/routes/loops.py`
- `backend/app/services/loop_execution_service.py`
- `backend/app/models/loop_execution.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/loops.py`
- `backend/app/services/loop_execution_service.py`
- Execution history is project content: requests must include an authorized active `project_id`, and execution rows are filtered by persisted row `project_id` plus scoped legacy fallback for older metadata/source-id-only rows.
- New loop execution records must persist `project_id`; background schedule writes pass the schedule's project id and fail closed if no project scope is available.
- Simulation scenario 49 exercises history and statistics with the active simulation `project_id`, so the harness cannot accidentally validate a projectless aggregate.

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/ExecutionHistoryTab.tsx` and the UI navigation path recorded in the inventory.
- Loop execution statistics use the same active-project scoping rules as paginated history, so aggregate counts cannot include another project's background activity.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_loops.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_simulation_project_scope_contracts.py`
- `tests/simulation/scenarios/49-loops-schedule.mjs`

## Related Features

- [loops.overview](../../loops/overview/architecture.md)
- [history.version](../../history/version/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-97 / CF-1237; CF-SPEC-107 / CF-1351
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
