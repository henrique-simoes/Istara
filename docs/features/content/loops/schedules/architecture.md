---
stable_id: loops.schedules
title: Loop Schedules
ui_path: Loops > Schedules
audience: architecture
status: documented
related_features: ["loops.overview", "loops.history"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/SchedulesTab.tsx", "frontend/src/components/loops/CronBuilder.tsx", "backend/app/api/routes/scheduler.py", "backend/app/core/scheduler.py"]
api_references: ["backend/app/api/routes/scheduler.py", "backend/app/api/routes/loops.py"]
test_references: ["tests/test_loops.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-776
---

# Loop Schedules Architecture

## Implementation Summary

Schedules configure recurring loop timing, including cron-style recurrence controls.

## Frontend Surface

- `frontend/src/components/loops/SchedulesTab.tsx`
- `frontend/src/components/loops/CronBuilder.tsx`
- `backend/app/api/routes/scheduler.py`
- `backend/app/core/scheduler.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/scheduler.py`
- `backend/app/api/routes/loops.py`
- Schedule listing and creation operate only in the active project context; the project-facing UI does not expose a cross-project selector.
- The scheduler selects due work only for non-paused projects and treats missing project ownership as a permanent schedule error instead of executing against a dangling project id.

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/SchedulesTab.tsx` and the UI navigation path recorded in the inventory.
- Pausing a project prevents scheduled skills and reminders from mutating task state, broadcasting project suggestions, or consuming model resources for that project.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.
- Scheduled skill execution is project content processing; it must remain bound to the schedule's project id and active pause state.

## Tests And Verification

- `tests/test_loops.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [loops.overview](../../loops/overview/architecture.md)
- [loops.history](../../loops/history/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-776
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
