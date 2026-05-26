---
stable_id: documents.library
title: Document Library
ui_path: Documents > Library
audience: architecture
status: documented
related_features: ["documents.upload", "documents.preview", "chat.files"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/documents/DocumentsView.tsx", "frontend/src/stores/documentStore.ts", "backend/app/api/routes/documents.py"]
api_references: ["backend/app/api/routes/documents.py"]
test_references: ["tests/test_documents.py", "tests/test_project_rbac.py"]
last_verified: 2026-05-22
compass: CF-SPEC-53 / CF-657; CF-SPEC-131
---

# Document Library Architecture

## Implementation Summary

Documents centralizes project documents and makes source material available for preview, chat, and analysis workflows.
Library payloads expose each document's Research Spine state. Documents remain raw sources: their source evidence units can feed governed coding, but the library must not label a document or its text as accepted research, report evidence, or a trusted Atomic artifact.

## Frontend Surface

- `frontend/src/components/documents/DocumentsView.tsx`
- `frontend/src/stores/documentStore.ts`
- `backend/app/api/routes/documents.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/documentStore.ts`
- The document store is keyed by the active project id. Project changes clear documents, tags, stats, pagination, and the selected preview id before loading the next project's material.

### API And Backend

- `backend/app/api/routes/documents.py`
- Document listing requires an explicit `project_id`; project-facing document library views do not fall back to a global document list.
- ID-based document operations require the same active `project_id` used by the UI and load records by `(document_id, project_id)` so stale IDs from another authorized project resolve as not found.
- List, get, create, and update responses include `research_spine` with `artifact_state=raw_source`, source evidence-unit counts, and a report-blocking policy.
- Text document creation and content updates register versioned raw source evidence units. Content updates create a new document evidence source version instead of treating old source spans as silently current.

## Architecture Notes

- The feature is mounted through `frontend/src/components/documents/DocumentsView.tsx` and the UI navigation path recorded in the inventory.
- Folder sync and file-watch registration must create `source_span` evidence units from raw file text before any later skill, agent, or report can use the material as accepted research.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_documents.py`
- `tests/test_documents.py::test_document_create_registers_raw_source_evidence_units`
- `tests/test_documents.py::test_documents_sync_registers_raw_source_evidence_units`
- `tests/test_project_rbac.py`

## Related Features

- [documents.upload](../../documents/upload/architecture.md)
- [documents.preview](../../documents/preview/architecture.md)
- [chat.files](../../chat/files/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-131
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
