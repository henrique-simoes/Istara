---
stable_id: agents.registry
title: Agent Registry
ui_path: Agents > Agents
audience: architecture
status: documented
related_features: ["agents.detail", "agents.a2a", "agents.create"]
related_glossary: ["a2a", "mcp"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/stores/agentStore.ts", "backend/app/api/routes/agents.py"]
api_references: ["backend/app/api/routes/agents.py"]
test_references: ["tests/test_agents.py"]
last_verified: 2026-05-18
compass: CF-SPEC-56 / CF-698
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
- `frontend/src/components/agents/AgentsView.tsx` passes the active project to `frontend/src/stores/agentStore.ts` so project-scoped agents are filtered by `/api/agents?project_id=...` while universal system agents remain visible.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.
- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_agents.py` covers the related A2A project-scoping contract for the Agents surface.

## Related Features

- [agents.detail](../../agents/detail/architecture.md)
- [agents.a2a](../../agents/a2a/architecture.md)
- [agents.create](../../agents/create/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-56 / CF-698
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
