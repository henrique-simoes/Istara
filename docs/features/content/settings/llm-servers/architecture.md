---
stable_id: settings.llm-servers
title: Legacy LLM Server Compatibility
ui_path: Settings > Pi Model Management (legacy compatibility only)
audience: architecture
status: deprecated
related_features: ["chat.model-controls", "settings.connection-strings"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/settings.py", "backend/app/core/pi_runtime/model_manager.py", "backend/app/core/pi_runtime/endpoints.py", "backend/app/core/petals_bridge.py"]
api_references: ["backend/app/api/routes/settings.py", "backend/app/api/routes/petals.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_settings_agentic_pi_endpoints.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w1_agentic_contract.py", "tests/pi_production/test_same_model_donor_isolation.py", "tests/petals_bridge/test_petals_bridge.py", "tests/pi_production/test_w8_embeddings_gateway.py"]
last_verified: 2026-08-24
compass: CF-SPEC-94 / CF-1193; CF-SPEC-8 (Pi replacement W1 model catalog; W8 projection refresh)
---

# Legacy LLM Server Compatibility Architecture

## Implementation Summary

Legacy `LLMServer` rows remain as migration input only; their classical public CRUD endpoint has been retired. Pi Model Management is the authoritative provider/model plane for both Istara and Pi Agentic Loop execution. Donated Petals capacity joins that authority only through the governed bridge and keeps its separate consent, project-scope, health, and lifecycle controls.

## Frontend Surface

- `frontend/src/components/common/SettingsView.tsx`
- `frontend/src/lib/modelProviders.ts`
- `backend/app/core/pi_runtime/model_manager.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/settings.py`
- `backend/app/api/routes/petals.py`

The retired LLM-server route is not mounted. Existing rows are projected
read-only for migration compatibility and are never mutated by Pi resolution.
Pi catalog/model/provider mutations remain global-admin surfaces in team mode;
public `/api/settings/status` is redacted and passive.

### Isolated Pi Model Catalog (Pi Replacement W1)

- `backend/app/core/pi_runtime/model_manager.py` (`PiModelManager`) is the
  provider/model authority for both supported loop modes. The Pi-runtime
  package never imports `ComputeRegistry`; the outer Petals bridge performs
  consent, health, scope, and identity projection.
- The catalog is built from four governed sources: the static
  `settings.pi_api_endpoints` entries plus the built-in
  `pi-deepseek-default`; persisted `LLMServer` rows projected read-only into
  the catalog as `openai_compat`/`anthropic_compat` endpoints carrying the
  row's encrypted key; and local serving at `settings.ollama_host + "/v1"` and
  `settings.lmstudio_host + "/v1"` marked `kind=local`; plus healthy,
  explicitly consented relay/browser nodes projected as `kind=petals` through
  an authenticated loopback shim and pinned to the active project.
- Both the legacy-row projection and the Petals projection are one-directional.
  Pi never writes back to either source. Petals endpoints are selected by exact
  identity, not capacity score, and same-model donor/endpoint replicas never
  count as independent Research Spine coders.
- Each catalog entry carries the capability set used for exact-identity or
  capability-filtered selection: `model`, `context_window`, `max_tokens`,
  `supports_tools`, `supports_vision`, `family`, `cost_per_mtok`,
  `timeout_ms`, and `max_retries`. Selection is exact-identity or
  capability-filtered only — never donor-style capacity scoring.
- `resolve(...)` raises a typed `PiEndpointResolutionError` on any miss, and
  `resolve_distinct(n, ...)` fails closed when fewer than `n` distinct
  identities exist rather than silently reusing one endpoint as two.
  `catalog()` feeds the settings model UI and benchmark comparison surfaces.

### Live Catalog Refresh And Merged Model View

- Model-management mutations refresh every live manager so both loop modes see
  the same authoritative catalog without process restart.
  `PiModelManager.reset_db_projection()` drops the `llm_server`-sourced catalog entries so the
  next `ensure_db_projection` re-reads the database, and the module-level
  `reset_live_db_projections()` applies that reset to every live manager
  through a weakref registry — the projection stays one-directional (database
  row to Pi catalog entry) and nothing Pi-side writes back to the row.
- Pi endpoint add/update/delete and model/provider setting changes invalidate
  the live catalog immediately. A stale projection is removed before the next
  resolution; the retired legacy route is not required for refresh.
- `backend/app/api/routes/settings.py` `GET /settings/models` now includes a
  `"pi_catalog"` key alongside the legacy model list in both online and
  offline responses. It is an identity/capability view only — endpoint ids,
  model names, and kinds — and never exposes endpoint URLs or API keys.
- The frontend does not render a legacy LLM Server section or expose its
  manual provider/model form in normal Settings. `PiModelManagement` owns the
  complete browseable + autocomplete catalog, API-key/OAuth choices, and
  configured-model list. Legacy rows remain available to compatibility/migration
  routes and the Pi projection; they are never silently deleted or used to
  expose donated compute as a cloud catalog.
- Chat uses the project-readable identity-only model catalog and stores an exact
  `endpoint_override` alongside `model_override`, preserving provider identity
  when two providers expose the same model id.

## Architecture Notes

- Compatibility is implemented by read-only row projection, not a public legacy route. User-facing configuration is mounted through `frontend/src/components/settings/PiModelManagement.tsx` and documented under `settings.general`.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `frontend/src/lib/modelProviders.test.ts`
- `tests/test_project_scope_contracts.py`
- `tests/pi_production/test_w1_agentic_contract.py` verifies catalog sources and prevents direct Pi-runtime registry imports.
- `tests/pi_production/test_same_model_donor_isolation.py` verifies same-model plane isolation.
- `tests/petals_bridge/test_petals_bridge.py` verifies consent, health, token, project pinning, dynamic refresh, and fail-closed behavior.
- `tests/pi_production/test_w8_embeddings_gateway.py` verifies live projection-reset hooks and the merged `pi_catalog` view.
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
