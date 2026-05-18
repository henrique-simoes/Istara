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
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
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
- Configuration reads are global runtime settings, but status refreshes shown in this tab still use the active project id.

### API And Backend

- `backend/app/api/routes/autoresearch.py`
- Autoresearch configuration mutations and global enable/disable toggles require global admin access because they affect every project. Project-facing status, experiments, and leaderboard routes remain project-scoped.

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes. Global config changes must not expose or process project content; runtime experiment execution still requires project authorization.

## Tests And Verification

- `tests/test_autoresearch.py` verifies non-admin researchers cannot mutate global autoresearch config and admins can.
- `tests/test_project_scope_contracts.py` verifies project-facing autoresearch calls carry project ids.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/architecture.md)
- [chat.model-controls](../../chat/model-controls/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
