---
stable_id: chat.files
title: Chat File Attachments
ui_path: Chat > File Attachments
audience: architecture
status: documented
related_features: ["documents.upload", "documents.library", "chat.overview"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "backend/app/api/routes/files.py", "backend/app/core/file_processor.py"]
api_references: ["backend/app/api/routes/files.py", "backend/app/api/routes/documents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat File Attachments Architecture

## Implementation Summary

Chat can attach uploaded project files and documents so the conversation can use project evidence and user-provided material.

## Frontend Surface

- `frontend/src/components/chat/ChatView.tsx`
- `backend/app/api/routes/files.py`
- `backend/app/core/file_processor.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/chatStore.ts`

### API And Backend

- `backend/app/api/routes/files.py`
- `backend/app/api/routes/documents.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [documents.upload](../../documents/upload/architecture.md)
- [documents.library](../../documents/library/architecture.md)
- [chat.overview](../../chat/overview/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
