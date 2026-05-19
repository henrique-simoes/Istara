---
stable_id: loops.agent-loops
title: Agent Loops
ui_path: Loops > Agent Loops
audience: architecture
status: documented
related_features: ["agents.registry", "loops.schedules"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/AgentLoopsTab.tsx", "backend/app/api/routes/loops.py", "backend/app/core/scheduler.py", "backend/app/main.py", "backend/app/agents/orchestrator.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: ["tests/test_loops.py", "tests/test_project_scope_contracts.py", "tests/test_simulation_project_scope_contracts.py", "tests/simulation/scenarios/49-loops-schedule.mjs"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-776; CF-SPEC-68 / CF-870; CF-SPEC-107 / CF-1351
---

# Agent Loops Architecture

## Implementation Summary

Agent Loops connects recurring work with configured agents and their automated research responsibilities.

## Frontend Surface

- `frontend/src/components/loops/AgentLoopsTab.tsx`
- `backend/app/api/routes/loops.py`
- `backend/app/core/scheduler.py`
- `backend/app/main.py`
- `backend/app/agents/orchestrator.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/loops.py`
- Agent-loop configs are visible or mutable only when the agent belongs to the active project or has an explicit loop project filter for that project.
- Resuming a paused agent loop requires the requested project to be active and unpaused; pausing remains allowed so work can be stopped without reactivating a project.
- Startup keeps project-scoped task workers available for assigned active-project work, but DevOps/UI/UX/User Simulation quality loops are disabled by default and run only when `autonomous_quality_agents_enabled` is explicitly enabled.
- Simulation scenario 49 passes the active simulation `project_id` to agent-loop listing, config, pause, resume, and restore calls rather than exercising agent-loop routes globally by omission.

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/AgentLoopsTab.tsx` and the UI navigation path recorded in the inventory.
- The meta-orchestrator selects unassigned tasks only from non-paused projects before routing, proposing agents, or sending A2A collaboration messages.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.
- Autonomous QA agents can fetch app/API state or call an LLM, so they are treated as admin/dev testing loops rather than normal project background processing.

## Tests And Verification

- `tests/test_loops.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_simulation_project_scope_contracts.py`
- `tests/simulation/scenarios/49-loops-schedule.mjs`

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [loops.schedules](../../loops/schedules/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-776; CF-SPEC-68 / CF-870; CF-SPEC-107 / CF-1351
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
