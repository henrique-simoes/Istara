---
stable_id: agents.create
title: Create Agent
ui_path: Agents > Create
audience: architecture
status: documented
related_features: ["agents.registry", "skills.catalog"]
related_glossary: ["a2a", "mcp"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/components/agents/CreateAgentWizard.tsx", "frontend/src/stores/agentStore.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/services/agent_service.py", "backend/app/core/agent_factory.py"]
api_references: ["backend/app/api/routes/agents.py"]
test_references: ["tests/test_agents.py", "tests/test_agent_mutation_scope.py", "tests/test_agent_scope_contracts.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757; CF-SPEC-83 / CF-1075
---

# Create Agent Architecture

## Implementation Summary

Create Agent supports configuring new agents and their role-facing metadata inside the active project.

## Frontend Surface

- `frontend/src/components/agents/AgentsView.tsx`
- `frontend/src/components/agents/CreateAgentWizard.tsx`
- `frontend/src/stores/agentStore.ts`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/agents.py`
- `backend/app/services/agent_service.py`
- `backend/app/core/agent_factory.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/agentStore.ts`

### API And Backend

- `backend/app/api/routes/agents.py`
- `backend/app/services/agent_service.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/agents/AgentsView.tsx` and the UI navigation path recorded in the inventory.
- Manual custom-agent creation requires the active project id in the frontend store/API call. The route rejects missing `project_id` before creating any agent record.
- The backend requires project-admin access for the supplied project id and creates custom agents with `scope="project"` and the matching `project_id` in the first database write.
- Imported agent configs follow the same active-project rule: the frontend attaches the active project id, the backend rejects missing `project_id`, and the imported agent is created as project-scoped instead of becoming a universal/global custom agent.
- Proposal-approved agents use the same scoped creation path so generated agents do not transiently exist as universal agents before metadata is patched.
- The create request validates `role` against the shared `AgentRole` enum (`task_executor`, `devops_audit`, `ui_audit`, `ux_evaluation`, `user_simulation`, `design_lead`, or `custom`) at the API boundary. Unsupported values return a 422 validation response instead of leaking an enum conversion error as HTTP 500.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.
- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_agents.py` covers missing project ids, rejects unsupported roles with a 422 validation response, and verifies created custom agents are project-scoped.
- `tests/test_agent_mutation_scope.py` verifies imported agent configs require and preserve the active project id.
- `tests/test_agent_scope_contracts.py` pins the frontend/store/API/backend project-scope contract, including imported agent configs.

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [skills.catalog](../../skills/catalog/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757; CF-SPEC-83 / CF-1075
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
