---
stable_id: loops.schedules
title: Loop Schedules
ui_path: Loops > Schedules
audience: architecture
status: documented
related_features: ["loops.overview", "loops.history"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/SchedulesTab.tsx", "frontend/src/components/loops/CronBuilder.tsx", "backend/app/api/routes/scheduler.py"]
api_references: ["backend/app/api/routes/scheduler.py", "backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Loop Schedules Architecture

## Implementation Summary

Schedules configure recurring loop timing, including cron-style recurrence controls.

## Frontend Surface

- `frontend/src/components/loops/SchedulesTab.tsx`
- `frontend/src/components/loops/CronBuilder.tsx`
- `backend/app/api/routes/scheduler.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/scheduler.py`
- `backend/app/api/routes/loops.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/SchedulesTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [loops.overview](../../loops/overview/architecture.md)
- [loops.history](../../loops/history/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
