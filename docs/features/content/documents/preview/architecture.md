---
stable_id: documents.preview
title: Document Preview
ui_path: Documents > Preview
audience: architecture
status: needs-verification
related_features: ["documents.library", "documents.suggestions"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/documents/DocumentsView.tsx", "frontend/src/components/common/ContextPreview.tsx"]
api_references: ["backend/app/api/routes/documents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Document Preview Architecture

## Implementation Summary

Document preview lets users inspect uploaded project material before using it in chat, interviews, or findings workflows.

## Frontend Surface

- `frontend/src/components/documents/DocumentsView.tsx`
- `frontend/src/components/common/ContextPreview.tsx`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/documentStore.ts`

### API And Backend

- `backend/app/api/routes/documents.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/documents/DocumentsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [documents.library](../../documents/library/architecture.md)
- [documents.suggestions](../../documents/suggestions/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
