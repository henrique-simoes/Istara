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
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat Sessions Architecture

## Implementation Summary

The chat session sidebar manages project-scoped conversation history and new session creation.

## Frontend Surface

- `frontend/src/components/chat/ChatSessionsSidebar.tsx`
- `frontend/src/stores/sessionStore.ts`
- `backend/app/api/routes/sessions.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/sessionStore.ts`

### API And Backend

- `frontend/src/lib/sessionsApi.ts`
- `backend/app/api/routes/sessions.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatSessionsSidebar.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [chat.overview](../../chat/overview/architecture.md)
- [history.version](../../history/version/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
