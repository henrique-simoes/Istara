---
stable_id: agents.detail
title: Agent Detail Panels
ui_path: Agents > Agents > Detail
audience: architecture
status: documented
related_features: ["agents.registry", "memory.agent"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py", "backend/app/agents/custom_worker.py", "backend/app/core/agent_identity.py", "backend/app/core/agent_learning.py", "backend/app/core/self_evolution.py", "backend/app/core/agent_memory.py", "backend/app/core/permissions.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py"]
test_references: ["tests/test_agents.py", "tests/test_agent_mutation_scope.py", "tests/test_agent_scope_contracts.py", "tests/test_agent_learning_scope.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-09-01
compass: CF-SPEC-60 / CF-776; CF-SPEC-68 / CF-870; CF-SPEC-83 / CF-1075; CF-SPEC-89 / CF-1125; CF-SPEC-129
---

# Agent Detail Panels Architecture

## Implementation Summary

Selected agent details expose overview, identity, memory, and permission information for that agent.

## Frontend Surface

- `frontend/src/components/agents/AgentsView.tsx`
- `backend/app/core/agent_identity.py`
- `backend/app/core/agent_learning.py`
- `backend/app/core/agent_memory.py`
- `backend/app/core/permissions.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/agentStore.ts`

### API And Backend

- `backend/app/api/routes/agents.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/agents/AgentsView.tsx` and the UI navigation path recorded in the inventory.
- Shared detail access policy lives in `backend/app/api/agent_project_scope.py`, with the route layer passing active project ids from `frontend/src/lib/api.ts`.
- Detail, identity, prompt diagnostic, learning, and memory reads must include the active project for non-admin users. The backend verifies that project-scoped agents belong to that project before returning agent data.
- Detail panel mutations are project-owned operations. The UI only exposes pause/resume, delete, identity-save, permissions toggles, export, and import for agents whose `project_id` matches the active project when the shared role-capability contract says the user is a global admin or active-project admin. Every corresponding API call includes that active project id.
- The embedded steering input follows the current backend steering contract and is mounted only for global-admin-capable sessions.
- The backend rejects project-facing detail mutations when `project_id` is missing, when the id belongs to another project, or when the target is a universal/system agent whose mutable state is shared outside the current project.
- Structured agent learnings are stored and retrieved only with an explicit project id. Project task failures or review feedback must not append private project content into universal persona MEMORY overlays.
- Agent-run and manually-run skill outputs are stored as candidate/provisional Research Spine artifacts unless exact source spans are available for governed coding and later reliability/reconciliation gates accept them. Agent detail and work history must not imply those artifacts are reportable before Done-task approval.
- Custom workers never write `TaskStatus.DONE`. Successful agent execution ends in the normal In Review flow, while a task whose project cannot be resolved is marked `IN_REVIEW` with `needs_revision` and an explicit human-facing failure reason. Only the human approval route may create approved Done state.
- Custom-worker execution failures persist `retry_count` and `last_retry_at`, respect bounded exponential backoff before another pickup, and return retryable failures to Backlog with a terminal realtime `retry_scheduled` outcome. Once `max_retries` is reached, the worker creates a `system_failed` review event, moves the task to `IN_REVIEW`, preserves any existing human `what_to_review` instruction, and emits an explicit terminal error outcome for the live Kanban/status UI.
- Self-evolution candidate scans, auto-evolution, and promotion mutations require an explicit active project id. The route and engine reject paused or missing projects before returning candidates or writing persona-file promotions, so one project's evidence cannot mature or mutate another project's agent behavior.
- Agent promotion review notifications are persisted with the selected agent's owning project id and project metadata. Review queues must not create global notification records from project-owned agent improvement activity.
- Universal agent runtime memory is not exposed in project detail panels for non-admin users; project-specific notes should be read through the project-scoped memory APIs.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_agents.py` verifies active-project guards for detail, identity, memory, recent logs, promotion requests, A2A messages, and that custom-worker orphan failures cannot bypass human-only Done.
- `tests/test_task_review_history.py` verifies timezone-safe custom-worker retry backoff, bounded retry escalation, preserved human review context, and terminal realtime failure events.
- `tests/test_agent_mutation_scope.py` verifies detail-panel mutation routes reject missing, stale cross-project, and universal/system agent ids.
- `tests/test_agent_scope_contracts.py` verifies that detail-panel mutation calls keep active-project scope in the frontend API, store, view, and backend route layer.
- `tests/test_agent_learning_scope.py` verifies that structured learnings, resolution lookup, self-evolution promotion candidates, and paused-project self-evolution guards do not cross project boundaries.
- `tests/test_project_scope_contracts.py` verifies the notification write contract for promotion requests and the shared category surfaces.

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [memory.agent](../../memory/agent/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-776; CF-SPEC-68 / CF-870; CF-SPEC-83 / CF-1075; CF-SPEC-89 / CF-1125; CF-SPEC-129
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
