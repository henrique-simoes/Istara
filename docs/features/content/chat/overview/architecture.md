---
stable_id: chat.overview
title: Chat Workspace
ui_path: Chat
audience: architecture
status: documented
related_features: ["chat.sessions", "chat.model-controls", "chat.files", "chat.audio", "chat.steering"]
related_glossary: ["rag", "mcp"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/stores/chatStore.ts", "backend/app/api/routes/chat.py"]
api_references: ["backend/app/api/routes/chat.py", "frontend/src/lib/chatApi.ts"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat Workspace Architecture

## Implementation Summary

Chat is the project-scoped conversational workspace for working with Istara agents, context, files, and model settings.

## Frontend Surface

- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/stores/chatStore.ts`
- `backend/app/api/routes/chat.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/chatStore.ts`
- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/chat.py`
- `frontend/src/lib/chatApi.ts`

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.
- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

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

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
