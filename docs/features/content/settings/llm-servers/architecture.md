---
stable_id: settings.llm-servers
title: LLM Server Settings
ui_path: Settings > LLM Servers
audience: architecture
status: documented
related_features: ["chat.model-controls", "settings.connection-strings"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py", "backend/app/api/routes/settings.py", "backend/app/core/network_discovery.py", "backend/app/core/pi_runtime/model_manager.py", "backend/app/core/pi_runtime/endpoints.py"]
api_references: ["backend/app/api/routes/llm_servers.py", "backend/app/api/routes/settings.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_llm_servers.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w1_agentic_contract.py", "tests/pi_production/test_same_model_donor_isolation.py", "tests/pi_production/test_w8_embeddings_gateway.py"]
last_verified: 2026-07-22
compass: CF-SPEC-94 / CF-1193; CF-SPEC-8 (Pi replacement W1 model catalog; W8 projection refresh)
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

### Isolated Pi Model Catalog (Pi Replacement W1)

- `backend/app/core/pi_runtime/model_manager.py` (`PiModelManager`) is the
  Pi-side model authority for agentic traffic. It never consults
  `ComputeRegistry`, and `ComputeRegistry` never consults it; persisted
  `LLMServer` rows keep registering into the live registry for the legacy
  engine exactly as before.
- The Pi catalog is built from exactly three sources: the static
  `settings.pi_api_endpoints` entries plus the built-in
  `pi-deepseek-default`; persisted `LLMServer` rows projected read-only into
  the catalog as `openai_compat`/`anthropic_compat` endpoints carrying the
  row's encrypted key; and local serving at `settings.ollama_host + "/v1"` and
  `settings.lmstudio_host + "/v1"` marked `kind=local`. Relay/browser donor
  capacity is never a catalog source.
- The `LLMServer`-row projection is one-directional (database row to Pi
  catalog entry): nothing Pi-side writes back to the row or registers the
  endpoint into the donor-schedulable registry, so a same-model donor can
  never be selected for Pi traffic.
- Each catalog entry carries the capability set used for exact-identity or
  capability-filtered selection: `model`, `context_window`, `max_tokens`,
  `supports_tools`, `supports_vision`, `family`, `cost_per_mtok`,
  `timeout_ms`, and `max_retries`. Selection is exact-identity or
  capability-filtered only — never donor-style capacity scoring.
- `resolve(...)` raises a typed `PiEndpointResolutionError` on any miss, and
  `resolve_distinct(n, ...)` fails closed when fewer than `n` distinct
  identities exist rather than silently reusing one endpoint as two.
  `catalog()` feeds the settings model UI and benchmark comparison surfaces.

### Catalog Projection Refresh And Merged Model View (Pi Replacement W8)

- W8 keeps the Pi catalog projection in sync with LLM server changes so both
  engine planes see the same registered servers.
  `PiModelManager.reset_db_projection()` drops the `llm_server`-sourced catalog entries so the
  next `ensure_db_projection` re-reads the database, and the module-level
  `reset_live_db_projections()` applies that reset to every live manager
  through a weakref registry — the projection stays one-directional (database
  row to Pi catalog entry) and nothing Pi-side writes back to the row.
- `backend/app/api/routes/llm_servers.py` calls
  `_refresh_pi_catalog_projection()` after add, update, and delete commits, so
  a server registered, edited, or removed in Settings is reflected in the Pi
  catalog on the next resolution. Legacy CRUD behavior is unchanged: rows
  still register into the live `llm_router` exactly as before, and relay rows
  are still never projected.
- `backend/app/core/network_discovery.py` `discover_and_register` runs the same
  refresh after persisting discovered rows, so a discovered server becomes an
  `LLMServer` row and then a Pi catalog entry without a restart.
- `backend/app/api/routes/settings.py` `GET /settings/models` now includes a
  `"pi_catalog"` key alongside the legacy model list in both online and
  offline responses. It is an identity/capability view only — endpoint ids,
  model names, and kinds — and never exposes endpoint URLs or API keys.
- The frontend consumes that side field through `mergeModelCatalogs()` so Pi
  identities are visible in the existing Available Models inventory without
  passing a Pi endpoint through the legacy provider-switch action. Duplicate
  Pi endpoint identities are collapsed, while distinct endpoint ids remain
  distinct for routing and auditability.

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
- `tests/pi_production/test_w8_embeddings_gateway.py` verifies the W8 projection-reset hooks and the merged `pi_catalog` view in `GET /settings/models`.
- Regenerate and validate the machine manifests and static site with `python scripts/feature_docs.py --seed-missing --generate-site --check`.

## Related Features

- [chat.model-controls](../../chat/model-controls/architecture.md)
- [settings.connection-strings](../../settings/connection-strings/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-94 / CF-1193; CF-SPEC-8 (Pi replacement W1 model catalog; W8 projection refresh and merged settings catalog)
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
