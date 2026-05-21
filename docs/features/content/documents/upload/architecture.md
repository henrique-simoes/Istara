---
stable_id: documents.upload
title: Document Upload
ui_path: Documents > Upload
audience: architecture
status: documented
related_features: ["documents.library", "chat.files", "tasks.attachments"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/documents/DocumentsView.tsx", "backend/app/api/routes/files.py", "backend/app/core/upload_security.py"]
api_references: ["backend/app/api/routes/files.py", "backend/app/api/routes/documents.py"]
test_references: ["tests/document_corpus/shared-corpus.mjs", "tests/real_user_benchmark/run.mjs"]
last_verified: 2026-05-21
compass: CF-SPEC-53 / CF-657; CF-SPEC-122
---

# Document Upload Architecture

## Implementation Summary

Upload controls import project files and documents into Istara for downstream reading, chat, and evidence workflows.

## Frontend Surface

- `frontend/src/components/documents/DocumentsView.tsx`
- `backend/app/api/routes/files.py`
- `backend/app/core/upload_security.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/documentStore.ts`

### API And Backend

- `backend/app/api/routes/files.py`
- `backend/app/api/routes/documents.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/documents/DocumentsView.tsx` and the UI navigation path recorded in the inventory.
- Document-heavy benchmarks and simulations use `tests/document_corpus/shared-corpus.mjs` as their corpus contract. Agentic research, task execution, Findings, and Reports tests should use at least 120 long-form sources unless they are explicitly narrow parser/unit checks.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/document_corpus/shared-corpus.mjs`
- `tests/real_user_benchmark/run.mjs`

## Related Features

- [documents.library](../../documents/library/architecture.md)
- [chat.files](../../chat/files/architecture.md)
- [tasks.attachments](../../tasks/attachments/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-122
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
