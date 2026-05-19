---
stable_id: chat.steering
title: Chat Steering
ui_path: Chat > Steering
audience: architecture
status: documented
related_features: ["chat.overview", "context.editor"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SteeringInput.tsx", "backend/app/api/routes/steering.py"]
api_references: ["backend/app/api/routes/steering.py"]
test_references: ["tests/test_steering_api.py", "tests/test_steering_manager.py", "tests/test_steering_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-87 / CF-1117
---

# Chat Steering Architecture

## Implementation Summary

Steering controls collect lightweight user guidance that can shape downstream assistant behavior inside the active project only. Every steering message, follow-up, queue read, queue clear, abort, and status request carries an explicit `project_id`, verifies that the project exists, and enforces project access before it touches the in-memory agent queue.

## Frontend Surface

- `frontend/src/components/common/SteeringInput.tsx`
- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/components/agents/AgentsView.tsx`
- `frontend/src/lib/researchIntegrityApi.ts`
- `backend/app/api/routes/steering.py`
- `backend/app/core/steering.py`
- `backend/app/core/agent_lifecycle.py`

## State, API, And Backend Contracts

### Stores

- `SteeringInput` receives `projectId` from the active project store and does not render or send when there is no active project.
- `ChatView` requests all queue status for the active project only.

### API And Backend

- `POST /api/steering/{agent_id}` and `POST /api/steering/{agent_id}/follow-up` require `project_id` in the body.
- `GET /api/steering/{agent_id}/status`, `GET /api/steering/{agent_id}/queues`, `DELETE /api/steering/{agent_id}/queues`, `POST /api/steering/{agent_id}/abort`, `GET /api/steering/{agent_id}/idle`, and `GET /api/steering` require `project_id` in the query string.
- The route loads the project, keeps the existing admin gate, and then calls `require_project_access`.
- Project-owned agents can only be steered for their own project. System agents remain universal identities, but their steering messages are still queued and drained by project.

## Architecture Notes

- `backend/app/core/steering.py` stores queue metadata per message and filters by `metadata.project_id` for status, read, clear, abort, and drain operations.
- A drain call without a project only sees legacy unscoped messages. Project-bound messages are never drained by a global `agent_id` call.
- `backend/app/core/agent_lifecycle.py` discovers queued project ids, loads the matching project, skips paused or missing projects, and executes steering with `SkillInput.project_id`, project context, company context, and project-scoped websocket broadcasts.

## Agents, Skills, LLM, MCP, And Permissions

- Steering is security-sensitive because a message can contain project research context and can trigger skill or LLM execution.
- The API requires admin access plus project authorization, and queue contents are filtered by active project before being returned to the browser.
- Project-scoped database agents reject steering requests for any other project.
- Universal/system agents can be steered only through project-bound queue messages, so one project cannot see or drain another project's pending guidance.

## Tests And Verification

- `tests/test_steering_api.py`
- `tests/test_steering_manager.py`
- `tests/test_steering_project_scope_contracts.py`

## Related Features

- [chat.overview](../../chat/overview/architecture.md)
- [context.editor](../../context/editor/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-87 / CF-1117
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
