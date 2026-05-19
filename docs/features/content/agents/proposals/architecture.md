---
stable_id: agents.proposals
title: Agent Proposals
ui_path: Agents > Proposals
audience: architecture
status: needs-verification
related_features: ["agents.registry", "skills.proposals", "tasks.review"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/core/agent_factory.py", "backend/app/core/improvement_governance_evidence.py", "backend/app/core/meta_hyperagent.py", "backend/app/agents/orchestrator.py", "backend/app/api/routes/permission_requests.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/routes/permission_requests.py"]
test_references: ["tests/test_agents.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Agent Proposals Architecture

## Implementation Summary

Agent proposal workflows surface project-specific suggested agent changes or actions for review.

## Frontend Surface

- `frontend/src/components/agents/AgentsView.tsx`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/agents.py`
- `backend/app/core/agent_factory.py`
- `backend/app/core/improvement_governance_evidence.py`
- `backend/app/core/meta_hyperagent.py`
- `backend/app/agents/orchestrator.py`
- `backend/app/api/routes/permission_requests.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/agentStore.ts`

### API And Backend

- `backend/app/api/routes/agents.py`
- `backend/app/core/agent_factory.py`
- `backend/app/api/routes/permission_requests.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/agents/AgentsView.tsx` and the UI navigation path recorded in the inventory.
- Agent creation proposals created by the Memento-style factory carry the originating `project_id` from the task that exposed the capability gap.
- The meta-orchestrator considers only unassigned tasks from non-paused projects before it routes work, reads A2A collaboration responses, sends A2A collaboration requests, or opens agent-creation proposals.
- Agent-factory governance registration refuses project-owned proposals without a concrete project id, preventing global proposal records from autonomous routing work.
- The Proposals tab calls `/api/agents/creation-proposals/*` with the active project id and clears proposal state when no active project is selected.
- The route layer requires `project_id`, verifies project-admin access, and filters list/approve/reject operations through `AgentFactory` project matching.
- Governance evidence and Meta Hyperagent observations also pass project ids so autonomous improvement review does not read proposal history from unrelated projects.
- Approved proposal agents are created directly as project-scoped custom agents; proposal approval cannot create a universal custom agent.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_agents.py` covers missing project ids, cross-project proposal filtering, and reject immutability across projects.
- `tests/test_project_scope_contracts.py` pins frontend, factory, governance, orchestrator, and Meta Hyperagent project-scope contracts.

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [skills.proposals](../../skills/proposals/architecture.md)
- [tasks.review](../../tasks/review/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
