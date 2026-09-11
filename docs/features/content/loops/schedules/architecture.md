---
stable_id: loops.schedules
title: Loop Schedules
ui_path: Loops > Schedules
audience: architecture
status: documented
related_features: ["loops.overview", "loops.history"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/SchedulesTab.tsx", "frontend/src/components/loops/CronBuilder.tsx", "backend/app/api/routes/scheduler.py", "backend/app/core/scheduler.py", "backend/app/services/loop_execution_service.py", "backend/app/models/loop_execution.py"]
api_references: ["backend/app/api/routes/scheduler.py", "backend/app/api/routes/loops.py"]
test_references: ["tests/test_loops.py", "tests/test_project_scope_contracts.py", "tests/test_simulation_project_scope_contracts.py", "tests/simulation/scenarios/01-health-check.mjs", "tests/simulation/scenarios/22-architecture-evaluation.mjs", "tests/simulation/scenarios/30-event-wiring-audit.mjs", "tests/simulation/scenarios/49-loops-schedule.mjs"]
last_verified: 2026-05-19
compass: CF-SPEC-61 / CF-779; CF-SPEC-68 / CF-870; CF-SPEC-97 / CF-1237; CF-SPEC-107 / CF-1351; CF-SPEC-108 / CF-1365
---

# Loop Schedules Architecture

## Implementation Summary

Schedules configure recurring loop timing, including cron-style recurrence controls.

## Frontend Surface

- `frontend/src/components/loops/SchedulesTab.tsx`
- `frontend/src/components/loops/CronBuilder.tsx`
- `backend/app/api/routes/scheduler.py`
- `backend/app/core/scheduler.py`
- `backend/app/services/loop_execution_service.py`
- `backend/app/models/loop_execution.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/scheduler.py`
- `backend/app/api/routes/loops.py`
- Schedule listing and creation operate only in the active project context; the project-facing UI does not expose a cross-project selector.
- Schedule detail, enable/disable, cron edits, and deletion require the active `project_id`; missing project scope returns 400, and a schedule id from another project returns 404 rather than falling back to the schedule's owning project.
- Creating a schedule, re-enabling a schedule, or editing a schedule that remains enabled requires an unpaused project. Disabling a schedule in a paused project remains allowed so teams can stop queued work.
- The scheduler selects due work only for non-paused projects and treats missing project ownership as a permanent schedule error instead of executing against a dangling project id.
- Scheduler execution records persist the schedule's project id before they appear in loop history or loop statistics.
- Simulation scenario 49 creates, lists, verifies, and deletes test schedules with the active simulation `project_id`; when no active project id exists, it records scoped skips instead of hitting schedule endpoints globally.
- Simulation scheduler smoke and architecture/event-wiring audit probes in scenarios 01, 22, and 30 also pass the active simulation `project_id`; when no active project id exists, they record scoped skips instead of probing `/api/schedules` globally.

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/SchedulesTab.tsx` and the UI navigation path recorded in the inventory.
- `CronBuilder` previews five future occurrences for sparse daily, weekly, and monthly expressions with a bounded multi-year search guard; impossible expressions resolve to an explicit unavailable state instead of a partial "Next 5 runs" list.
- Pausing a project prevents scheduled skills and reminders from mutating task state, broadcasting project suggestions, or consuming model resources for that project.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.
- Scheduled skill execution is project content processing; it must remain bound to the schedule's project id and active pause state.

## Tests And Verification

- `tests/test_loops.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_simulation_project_scope_contracts.py`
- `tests/simulation/scenarios/01-health-check.mjs`
- `tests/simulation/scenarios/22-architecture-evaluation.mjs`
- `tests/simulation/scenarios/30-event-wiring-audit.mjs`
- `tests/simulation/scenarios/49-loops-schedule.mjs`

## Related Features

- [loops.overview](../../loops/overview/architecture.md)
- [loops.history](../../loops/history/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-61 / CF-779; CF-SPEC-68 / CF-870; CF-SPEC-97 / CF-1237; CF-SPEC-107 / CF-1351; CF-SPEC-108 / CF-1365
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
