---
stable_id: chat.model-controls
title: Chat Model Controls
ui_path: Chat > Model Controls
audience: architecture
status: documented
related_features: ["settings.llm-servers", "settings.general", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/components/chat/chatViewParts.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py"]
api_references: ["backend/app/api/routes/llm_servers.py", "backend/app/core/llm_router.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat Model Controls Architecture

## Implementation Summary

Chat exposes model, thinking, and reasoning controls so users can tune how the assistant responds within the configured local or server-backed model environment.

## Frontend Surface

- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/components/chat/chatViewParts.tsx`
- `frontend/src/lib/modelProviders.ts`
- `backend/app/api/routes/llm_servers.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/chatStore.ts`

### API And Backend

- `backend/app/api/routes/llm_servers.py`
- `backend/app/core/llm_router.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `frontend/src/lib/modelProviders.test.ts`

## Related Features

- [settings.llm-servers](../../settings/llm-servers/architecture.md)
- [settings.general](../../settings/general/architecture.md)
- [compute.pool](../../compute/pool/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
