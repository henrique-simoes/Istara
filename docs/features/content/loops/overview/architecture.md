---
stable_id: loops.overview
title: Loops Overview
ui_path: Loops > Overview
audience: architecture
status: documented
related_features: ["loops.schedules", "loops.agent-loops"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/LoopsView.tsx", "frontend/src/components/loops/LoopOverviewTab.tsx", "frontend/src/stores/loopsStore.ts", "backend/app/api/routes/loops.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: ["tests/test_loops.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870
---

# Loops Overview Architecture

## Implementation Summary

Loops overview summarizes automated and scheduled research loop health.

## Frontend Surface

- `frontend/src/components/loops/LoopsView.tsx`
- `frontend/src/components/loops/LoopOverviewTab.tsx`
- `frontend/src/stores/loopsStore.ts`
- `backend/app/api/routes/loops.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/loops.py`
- Project-facing requests to overview, health, agent-loop, schedule, and execution endpoints must include the active `project_id` and pass `require_project_access`; global admins do not get a projectless fallback on these feature surfaces.
- `frontend/src/stores/loopsStore.ts` clears loop state when there is no active project instead of falling back to global automation data.

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/LoopsView.tsx` and the UI navigation path recorded in the inventory.
- Loop summaries and execution counts are derived from sources attached to the requested project, so A2A or schedule activity from another project cannot appear as "recent activity" in the active project view.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_loops.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [loops.schedules](../../loops/schedules/architecture.md)
- [loops.agent-loops](../../loops/agent-loops/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
