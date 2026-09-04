---
stable_id: agents.registry
title: Agent Registry
ui_path: Agents > Agents
audience: architecture
status: documented
related_features: ["agents.detail", "agents.a2a", "agents.create"]
related_glossary: ["a2a", "mcp"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/stores/agentStore.ts", "backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py"]
test_references: ["tests/test_agents.py", "tests/test_agent_mutation_scope.py", "tests/test_agent_scope_contracts.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-56 / CF-698; CF-SPEC-83 / CF-1075
---

# Agent Registry Architecture

## Implementation Summary

The Agents view lists and manages available agents, including their status and project-facing roles.

## Frontend Surface

- `frontend/src/components/agents/AgentsView.tsx`
- `frontend/src/stores/agentStore.ts`
- `backend/app/api/routes/agents.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/agentStore.ts`

### API And Backend

- `backend/app/api/routes/agents.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/agents/AgentsView.tsx` and the UI navigation path recorded in the inventory.
- Shared agent project-scope policy lives in `backend/app/api/agent_project_scope.py` and is reused by registry, detail, heartbeat, recent-log, and direct A2A endpoints.
- `frontend/src/components/agents/AgentsView.tsx` passes the active project to `frontend/src/stores/agentStore.ts` so project-scoped agents are filtered by `/api/agents?project_id=...` while universal system agents remain visible.
- Agent heartbeat, recent-log, avatar, and identity requests also carry the active project id; non-admin requests without that scope are rejected instead of falling back to a global agent view.
- Project-facing by-id actions for update, delete, pause, resume, restart, avatar upload, memory update, identity update, export, and import require the active project id. The backend resolves the agent by id plus owned project and returns not found for stale ids from another project or for universal/system agents on these project-owned mutation paths.
- Universal agents remain visible in project views, but runtime memory and current-task state are redacted for non-admin users because those fields are not project-partitioned.
- The onboarding description derives its system-agent count from the registry response, so the explanatory copy cannot drift from the number of rendered system-agent cards.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.
- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_agents.py` covers the related registry, heartbeat, recent-log, detail, memory, mutation, promotion, and A2A project-scoping contracts for the Agents surface.
- `tests/test_agent_mutation_scope.py` verifies that project-facing by-id mutations reject missing, stale cross-project, and universal/system agent ids.
- `tests/test_agent_scope_contracts.py` pins the frontend API/store/view contract so by-id mutations cannot regress to projectless agent routes.

## Related Features

- [agents.detail](../../agents/detail/architecture.md)
- [agents.a2a](../../agents/a2a/architecture.md)
- [agents.create](../../agents/create/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-56 / CF-698; CF-SPEC-83 / CF-1075
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
