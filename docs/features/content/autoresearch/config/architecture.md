---
stable_id: autoresearch.config
title: Autoresearch Configuration
ui_path: Autoresearch > Config
audience: architecture
status: documented
related_features: ["autoresearch.experiments", "chat.model-controls"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_runners/rag_params.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Autoresearch Configuration Architecture

## Implementation Summary

Autoresearch configuration sets parameters for automated research strategies and runs.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `backend/app/core/autoresearch_runners/rag_params.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`

### API And Backend

- `backend/app/api/routes/autoresearch.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/architecture.md)
- [chat.model-controls](../../chat/model-controls/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
