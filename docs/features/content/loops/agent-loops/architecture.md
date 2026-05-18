---
stable_id: loops.agent-loops
title: Agent Loops
ui_path: Loops > Agent Loops
audience: architecture
status: documented
related_features: ["agents.registry", "loops.schedules"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/AgentLoopsTab.tsx", "backend/app/api/routes/loops.py", "backend/app/core/scheduler.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Agent Loops Architecture

## Implementation Summary

Agent Loops connects recurring work with configured agents and their automated research responsibilities.

## Frontend Surface

- `frontend/src/components/loops/AgentLoopsTab.tsx`
- `backend/app/api/routes/loops.py`
- `backend/app/core/scheduler.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/loops.py`
- Agent-loop configs are visible or mutable only when the agent belongs to the active project or has an explicit loop project filter for that project.

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/AgentLoopsTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_loops.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [loops.schedules](../../loops/schedules/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
