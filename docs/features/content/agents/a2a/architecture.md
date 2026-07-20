---
stable_id: agents.a2a
title: Agent-To-Agent Log
ui_path: Agents > A2A
audience: architecture
status: documented
related_features: ["agents.registry", "loops.agent-loops"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/stores/agentStore.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py", "backend/app/api/routes/a2a.py", "backend/app/api/websocket.py", "backend/app/services/a2a.py", "backend/app/models/agent.py", "backend/alembic/versions/019_a2a_message_project_scope.py", "backend/app/core/agent_lifecycle.py", "backend/app/core/sub_agent_worker.py", "backend/app/skills/system_actions.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/agent_project_scope.py", "backend/app/api/routes/a2a.py", "backend/app/api/websocket.py"]
test_references: ["tests/test_agents.py", "tests/test_a2a_project_claims.py", "tests/test_a2a_service_scope.py", "tests/test_a2a_security.py", "tests/test_websocket.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-56 / CF-698; CF-SPEC-60 / CF-776; CF-SPEC-64 / CF-828; CF-SPEC-74 / CF-949; CF-SPEC-99 / CF-1244
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
- Project views pass the active `project_id` into `/api/agents/a2a/log`; the backend requires that scope and only returns messages persisted with that project or messages that can be traced to a task in that project.
- Direct `/api/agents/{agent_id}/messages` reads and writes also validate that the source and destination agents are visible in the supplied project before returning or persisting A2A records; service writes fail closed without an explicit project id and store it on the message row.
- Public A2A JSON-RPC `tasks/send`, `tasks/get`, `tasks/list`, and `agent/discover` also require `project_id` and enforce project authorization before project-content messages or agent catalogs are persisted, listed, or disclosed.
- The Pi replacement candidate records observability only after `tasks/send` has passed JSON-RPC auth, body-size, rate-limit, replay, and project authorization gates. The route response contract is unchanged; the candidate hook adds project-scoped, content-free telemetry when the Pi header or metadata explicitly selects it; a project-scope denial returns the JSON-RPC authorization error and creates neither Pi work nor a Pi span.
- New A2A messages persist a first-class `project_id` in `backend/app/models/agent.py`; service writes reject missing active project scope and conflicting `project_id`/`projectId` metadata aliases before persistence or realtime broadcast.
- `backend/app/services/a2a.py` resolves each message's project from the row project id first, then explicit metadata or `task_id` ownership only when those claims agree with any project-scoped sender/recipient agent claims; conflicting claims are treated as unresolved and excluded from project logs, inboxes, and thread context.
- Conversation and debate thread reconstruction requires the task's project id, so two projects that accidentally share a `context_id` cannot contribute messages to the same LLM prompt.
- Project-scoped sub-agents only receive inbox messages for their own project; universal system agents may process multiple projects only as separate project-resolved messages with `project_id` attached.
- LLM-callable system actions that assign agents, move/update tasks, attach/read documents, or send A2A messages look up tasks, documents, and target agents inside the active project before mutating or persisting coordination records.
- The frontend A2A store clears stale rows before each project fetch and on errors, then defensively keeps only messages whose payload or metadata project id matches the active project.
- Project A2A messages are broadcast with project metadata so realtime clients connected to another active project do not receive them.
- Agent realtime events resolve project scope from explicit metadata, task/deployment/channel ownership, and project-scoped agent ids only when those claims are consistent; malformed or conflicting project-bound events are dropped instead of falling back to global delivery.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_agents.py`, `tests/test_a2a_project_claims.py`, `tests/test_a2a_service_scope.py`, `tests/test_a2a_security.py`, `tests/test_websocket.py`, `tests/test_project_scope_contracts.py`, and `tests/test_pi_replacement_candidate.py` verify that project-scoped A2A logs exclude unrelated project/global messages, service writes and mark-read mutations require project scope, conflicting metadata/task/row/agent project claims are dropped, JSON-RPC task writes and discovery cannot proceed without project scope, background inbox/thread helpers do not mix projects, realtime delivery resolves only consistent project claims, and the Pi candidate hook remains downstream of those gates.

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [loops.agent-loops](../../loops/agent-loops/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-56 / CF-698; CF-SPEC-60 / CF-776; CF-SPEC-64 / CF-828; CF-SPEC-74 / CF-949; CF-SPEC-99 / CF-1244; CF-SPEC-3 / CF-38
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
