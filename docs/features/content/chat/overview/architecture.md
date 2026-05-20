---
stable_id: chat.overview
title: Chat Workspace
ui_path: Chat
audience: architecture
status: documented
related_features: ["chat.sessions", "chat.model-controls", "chat.files", "chat.audio", "chat.steering"]
related_glossary: ["rag", "mcp"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/stores/chatStore.ts", "frontend/src/stores/sessionStore.ts", "backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py"]
api_references: ["backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py", "frontend/src/lib/chatApi.ts", "frontend/src/lib/sessionsApi.ts"]
test_references: ["tests/test_chat.py", "tests/test_sessions.py", "tests/test_project_rbac.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-102 / CF-1295
---

# Chat Workspace Architecture

## Implementation Summary

Chat is the project-scoped conversational workspace for working with Istara agents, context, files, and model settings.

## Frontend Surface

- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/stores/chatStore.ts`
- `frontend/src/stores/sessionStore.ts`
- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/sessions.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/chatStore.ts`
- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/sessions.py`
- `frontend/src/lib/chatApi.ts`
- `frontend/src/lib/sessionsApi.ts`

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatView.tsx` and the UI navigation path recorded in the inventory.
- Chat history fetches clear previous messages before loading the active project's session history; errors also clear messages so stale conversations cannot remain visible.
- Session detail fetches include the active project id and the backend authorizes that project before loading the session and its messages.
- Toolbar session updates carry the active project id so model, agent, preset, and thinking-mode changes cannot mutate a stale session from another project.
- Chat session agent assignment is server-validated before create, update, or LLM prompt composition: project-owned agents must belong to the active project, inactive or foreign agents return 404, and universal system agents remain usable.
- Native tool calling falls back to text-based tool prompting when the selected project-scoped compute path has no tool-capable streaming node, allowing smaller donated relay models to answer instead of failing before the fallback path can run.
- Steering status/input is a global-admin capability in the current backend contract. Researcher chat sessions must not mount steering polling or steering mutation controls during normal chat journeys; negative authorization tests may still assert that researcher calls are rejected.
- Voice transcription uploads must carry the active project id and pass project researcher authorization before Istara reads audio bytes or invokes transcription. Missing, blank, hidden, or viewer-only project claims fail before audio processing.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.
- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.
- Agent persona and system-prompt loading only occurs after the stored `agent_id` is proven assignable to the active project session.

## Tests And Verification

- `tests/test_chat.py`
- `tests/test_sessions.py`
- `tests/test_project_rbac.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [chat.sessions](../../chat/sessions/architecture.md)
- [chat.model-controls](../../chat/model-controls/architecture.md)
- [chat.files](../../chat/files/architecture.md)
- [chat.audio](../../chat/audio/architecture.md)
- [chat.steering](../../chat/steering/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)
- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-102 / CF-1295
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
