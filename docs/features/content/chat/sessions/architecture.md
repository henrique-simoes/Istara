---
stable_id: chat.sessions
title: Chat Sessions
ui_path: Chat > Sessions
audience: architecture
status: documented
related_features: ["chat.overview", "history.version"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatSessionsSidebar.tsx", "frontend/src/stores/sessionStore.ts", "backend/app/api/routes/sessions.py"]
api_references: ["frontend/src/lib/sessionsApi.ts", "backend/app/api/routes/sessions.py"]
test_references: ["tests/test_sessions.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-84 / CF-1089
---

# Chat Sessions Architecture

## Implementation Summary

The chat session sidebar manages project-scoped conversation history and new session creation. Session-by-id reads and mutations require the active project id so stale session state from another authorized project cannot render or change the current project's chat.

## Frontend Surface

- `frontend/src/components/chat/ChatSessionsSidebar.tsx`
- `frontend/src/stores/sessionStore.ts`
- `frontend/src/stores/chatStore.ts`
- `frontend/src/lib/sessionsApi.ts`
- `backend/app/api/routes/sessions.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/sessionStore.ts`
- `frontend/src/stores/chatStore.ts`

### API And Backend

- `frontend/src/lib/sessionsApi.ts`
- `backend/app/api/routes/sessions.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatSessionsSidebar.tsx` and the UI navigation path recorded in the inventory.
- `sessionStore` persists active session ids under per-project keys, clears session state on project switches, and only restores a saved id if that id exists in the active project's fetched sessions.
- `sessionsApi.get`, `update`, `delete`, and `star` all include `project_id`; the backend verifies access to that active project and then looks up the chat session with both `ChatSession.id` and `ChatSession.project_id`.
- Session detail responses load messages with both `Message.session_id` and `Message.project_id`, and a cross-project active scope returns 404 instead of revealing that another project's session exists.
- Session create and update validate `agent_id` against the same active project before storing it. Universal system agents are allowed; project-owned agents from another project, inactive agents, and orphaned project-scoped agents are rejected.
- Session create and update also reject embedding-only model names at the persistence boundary, so a stale or direct API override cannot route an embedding transport through chat.
- The sidebar derives `scopedSessions` from the active project before rendering rows, counts, and actions.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.
- Agent-specific chat personas are only valid when the selected session agent is universal or belongs to the active project.

## Tests And Verification

- `tests/test_sessions.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [chat.overview](../../chat/overview/architecture.md)
- [history.version](../../history/version/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-84 / CF-1089
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
