---
stable_id: memory.health
title: Memory Health
ui_path: Memory > Health
audience: architecture
status: needs-verification
related_features: ["memory.knowledge", "quality.dashboard"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "backend/app/core/vector_health.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Memory Health Architecture

## Implementation Summary

Memory health surfaces status and quality signals for memory or retrieval infrastructure in the active project.

## Frontend Surface

- `frontend/src/components/memory/MemoryView.tsx`
- `backend/app/core/vector_health.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/memory.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/memory/MemoryView.tsx` and the UI navigation path recorded in the inventory.
- Health statistics are read through the project-scoped memory route after project visibility is verified.
- `MemoryView` remounts the Health tab on active-project changes so one project's memory statistics do not linger in another project view.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_memory.py`

## Related Features

- [memory.knowledge](../../memory/knowledge/architecture.md)
- [quality.dashboard](../../quality/dashboard/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
