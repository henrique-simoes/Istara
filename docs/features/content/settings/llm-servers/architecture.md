---
stable_id: settings.llm-servers
title: LLM Server Settings
ui_path: Settings > LLM Servers
audience: architecture
status: documented
related_features: ["chat.model-controls", "settings.connection-strings"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py"]
api_references: ["backend/app/api/routes/llm_servers.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_llm_servers.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-94 / CF-1193
---

# LLM Server Settings Architecture

## Implementation Summary

Settings manages configured LLM providers, server endpoints, provider labels, and active model switching.

## Frontend Surface

- `frontend/src/components/common/SettingsView.tsx`
- `frontend/src/lib/modelProviders.ts`
- `backend/app/api/routes/llm_servers.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/llm_servers.py`

The LLM server inventory, registration, deletion, discovery, and manual
health-check endpoints are global infrastructure surfaces rather than
project-content lists. They require a global admin in team mode before exposing
provider endpoint status, router health, capability metadata, or running
explicit health/discovery probes. The legacy settings model inventory and
model/provider switch routes follow the same global-admin boundary in team
mode; public `/api/settings/status` is redacted and passive, so it does not
leak provider or model identifiers. Local mode keeps the same developer
behavior through the shared permission helper.

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/SettingsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `frontend/src/lib/modelProviders.test.ts`
- `tests/test_llm_servers.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [chat.model-controls](../../chat/model-controls/architecture.md)
- [settings.connection-strings](../../settings/connection-strings/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-94 / CF-1193
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
