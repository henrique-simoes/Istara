---
stable_id: settings.general
title: System Status And Models
ui_path: Settings > System Status And Models
audience: architecture
status: documented
related_features: ["settings.llm-servers", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/components/layout/StatusBar.tsx", "backend/app/api/routes/settings.py"]
api_references: ["backend/app/api/routes/settings.py"]
test_references: ["tests/test_settings.py"]
last_verified: 2026-05-18
compass: CF-SPEC-55 / CF-684
---

# System Status And Models Architecture

## Implementation Summary

Settings shows backend, LLM, hardware, model recommendation, and available model status for the local installation. LLM service connectivity is based on passive server reachability; chat readiness is exposed separately so the status bar does not call a reachable provider "disconnected" just because no chat-ready model has been confirmed.

## Frontend Surface

- `frontend/src/components/common/SettingsView.tsx`
- `backend/app/api/routes/settings.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/settings.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/SettingsView.tsx` and the UI navigation path recorded in the inventory.
- `frontend/src/components/layout/StatusBar.tsx` reconciles WebSocket LLM events with passive `/api/settings/status` polling.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_settings.py`

## Related Features

- [settings.llm-servers](../../settings/llm-servers/architecture.md)
- [compute.pool](../../compute/pool/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-55 / CF-684
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
