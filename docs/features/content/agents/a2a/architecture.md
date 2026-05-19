---
stable_id: agents.a2a
title: Agent-To-Agent Log
ui_path: Agents > A2A
audience: architecture
status: documented
related_features: ["agents.registry", "loops.agent-loops"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/stores/agentStore.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py", "backend/app/api/routes/a2a.py", "backend/app/api/websocket.py", "backend/app/services/a2a.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py", "backend/app/api/routes/a2a.py", "backend/app/api/websocket.py"]
test_references: ["tests/test_agents.py", "tests/test_a2a_security.py", "tests/test_websocket.py"]
last_verified: 2026-05-19
compass: CF-SPEC-56 / CF-698; CF-SPEC-60 / CF-776
---

# Agent-To-Agent Log Architecture

## Implementation Summary

The A2A tab displays agent-to-agent communication or coordination events for operational visibility within the active project.

## Frontend Surface

- `frontend/src/components/agents/AgentsView.tsx`
- `frontend/src/stores/agentStore.ts`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/agents.py`
- `backend/app/api/routes/a2a.py`
- `backend/app/api/websocket.py`
- `backend/app/services/a2a.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/agentStore.ts`

### API And Backend

- `frontend/src/lib/api.ts`
- `backend/app/api/routes/agents.py`
- `backend/app/api/routes/a2a.py`
- `backend/app/api/websocket.py`
- `backend/app/services/a2a.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/agents/AgentsView.tsx` and the UI navigation path recorded in the inventory.
- Project views pass the active `project_id` into `/api/agents/a2a/log`; the backend requires that scope and only returns messages tagged with that project or messages that can be traced to a task in that project.
- Direct `/api/agents/{agent_id}/messages` reads and writes also validate that the source and destination agents are visible in the supplied project before returning or persisting A2A records.
- Public A2A JSON-RPC `tasks/send`, `tasks/get`, `tasks/list`, and `agent/discover` also require `project_id` and enforce project authorization before project-content messages or agent catalogs are persisted, listed, or disclosed.
- Project A2A messages are broadcast with project metadata so realtime clients connected to another active project do not receive them.
- Agent realtime events resolve project scope from agent ids before delivery, and malformed project-bound events are dropped instead of falling back to global delivery.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_agents.py`, `tests/test_a2a_security.py`, and `tests/test_websocket.py` verify that project-scoped A2A logs exclude unrelated project/global messages, JSON-RPC task writes and discovery cannot proceed without project scope, and realtime delivery resolves agent-owned project ids.

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [loops.agent-loops](../../loops/agent-loops/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-56 / CF-698; CF-SPEC-60 / CF-776
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
