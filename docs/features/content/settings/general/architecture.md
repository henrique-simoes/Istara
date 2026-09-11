---
stable_id: settings.general
title: System Status, Agentic Core, And Pi Models
ui_path: Settings > System Status, Agentic Core, And Pi Models
audience: architecture
status: documented
related_features: ["settings.llm-servers", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/components/settings/AgenticCoreSection.tsx", "frontend/src/components/settings/PiModelManagement.tsx", "frontend/src/app/globals.css", "frontend/src/components/layout/StatusBar.tsx", "backend/app/api/routes/settings.py", "backend/app/core/pi_runtime/endpoint_policy.py", "backend/app/core/pi_runtime/catalog.py", "backend/app/core/pi_runtime/oauth.py", "backend/app/core/runtime_freshness.py"]
api_references: ["backend/app/api/routes/settings.py"]
test_references: ["tests/test_settings.py", "tests/test_settings_agentic_pi_endpoints.py", "frontend/src/lib/modelCatalog.test.ts"]
last_verified: 2026-08-30
compass: CF-SPEC-55 / CF-684; CF-SPEC-66 / CF-856; CF-SPEC-91 / CF-1156
---

# System Status And Models Architecture

## Implementation Summary

Settings shows backend and LLM health, a first-class Agentic Core comparison and choice, hardware/model guidance, and the Pi provider/model management workbench. Pi Model Management offers a complete browseable catalog plus autocomplete, provider-native authentication choices, server-side credential custody, and a global default chat-model selector. The former compact Agentic Core selector is no longer inside System Status; the legacy LLM Servers catalog is not rendered in normal Settings UX while compatibility routes/data remain preserved. Public status is intentionally minimal: `/api/settings/status` exposes backend health, team mode, cached LLM reachability/readiness, and frontend freshness only. Provider, model, hardware, integration, vector-health, maintenance, and data-integrity details are shared infrastructure metadata and require global admin access in team mode.

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
- `/api/settings/status` reports `services.llm` from cached provider reachability and `llm_readiness.chat_ready` separately, so status bars and guided checks can distinguish connected-but-not-ready from disconnected without running provider probes. The deterministic contract transport may contribute reachability but is always forced to `chat_ready=false`, matching the model-source boundary that forbids using it for chat. The Settings status card preserves the same three states (`Disconnected`, `Reachable, chat unavailable`, and `Chat ready`) rather than labeling a reachable transport as a working chat model.
- `/api/settings/status` does not expose provider names, active model identifiers, embedding model identifiers, RAG configuration, or loaded-model discovery results. Admin-only settings views read model/provider details from `/api/settings/models`.
- `/api/settings/hardware`, `/api/settings/models`, `/api/settings/maintenance`, `/api/settings/integrations-status`, `/api/settings/vector-health`, `/api/settings/data-integrity`, `/api/settings/model`, and `/api/settings/provider` require global admin access in team mode.
- `GET /api/settings/models` returns the normalized `agentic_engine_default` (`pi` or `legacy`) alongside the provider inventory, the effective `default_endpoint_id`/`default_model` for chat generation, and identity-only Pi projections. A Pi identity is reported as the default only when its passive credential state is `ready` or `stored`; an uncredentialed built-in catalog row is inventory, not availability. `AgenticCoreSection` renders the global choice as a dedicated, plain-language comparison with the shared embedding invariant and source-linked provisional benchmark rows. The Settings status card labels the effective generation choice as `Default Chat Model`; when Pi is selected it never substitutes the local transport's `active_model`, and shows `Not configured` until a credential-ready Pi default exists. When Istara is selected, the local `active_model` is shown only while cached local chat readiness is true, so a contract or otherwise non-ready transport cannot be presented as the effective model.
- The `pi_catalog` portion of `GET /api/settings/models` is fail-closed: a Pi projection or catalog read failure returns a typed `503` (`pi_catalog_unavailable`) instead of an empty list that could be mistaken for a healthy legacy-only inventory. The separate `GET /api/settings/pi-catalog` endpoint remains the detailed diagnostic surface.
- `GET /api/settings/pi-catalog` returns the full secret-free Pi catalog. `PiModelManagement` supports both a visible dropdown/browse path and autocomplete search. Selecting a model resolves URL, protocol, capabilities, effort levels, and pricing from the catalog; users never type an endpoint URL.
- Pi OAuth metadata distinguishes API key, browser PKCE, and device-code methods. OpenAI is explicit: OpenAI API is API-key based, while the shared Codex models expose Pi's ChatGPT subscription OAuth with Browser login and Device code (headless) choices. Browser callbacks verify state and never return tokens.
- Pi endpoint, provider, and model mutations refresh the live `PiModelManager` catalog immediately. Both Istara and Pi Agentic Loop requests therefore resolve against the same current authority without requiring a backend restart.
- The first credential-ready Pi provider endpoint becomes the persisted global chat
  default automatically. Admins can switch it with
  `POST /api/settings/pi-default`; deleting the selected endpoint safely falls
  back to the remaining first connected endpoint. Chat sessions may still keep
  an explicit endpoint override.
- `POST` and `PUT /api/settings/pi-endpoints` share one preparation path: a
  sparse PUT inherits omitted endpoint fields, catalog provider/model choices
  refill the canonical URL/capabilities/pricing, and the same HTTPS/loopback
  and Keychain-reference validation applies atomically before replacement.
  Newly supplied API keys are written only to Keychain; an existing encrypted
  OAuth credential is retained unless a new completed flow is supplied.
- `GET /api/settings/security-integrity` is global-admin-only and reports value-free health counters for encrypted-field and telemetry persistence failures. It never returns keys, ciphertext, provider URLs, prompts, or research content.
- `POST /api/settings/agentic-engine` and `POST /api/settings/strict-routing` return the boolean result of their environment persistence attempt. In read-only deployments the in-memory setting may change for the current process, but `persisted` is `false` so the UI cannot imply that the value will survive a restart.
- `POST /api/settings/telemetry/toggle` updates the in-memory telemetry switch first. If a read-only deployment cannot persist `TELEMETRY_ENABLED`, the endpoint still returns 200 with an explicit process-scoped persistence warning; only expected OS-level write failures are contained, while unexpected persistence errors remain visible.
- Settings is role-composed rather than a single global-admin surface. Researcher-safe personal panels such as compute donation, security factors, sessions, and updates may render for researchers, while global-admin panels for governed evolution, users, connection strings, LLM infrastructure, telemetry, and team-mode toggles are gated before mounting so their admin-only API calls are never made by normal researcher journeys.
- `/api/settings/status` also includes `runtime.frontend` freshness diagnostics. The status bar shows `Runtime bundle stale` when the production Next build predates tracked frontend source files, preventing stale bundles from being mistaken for current project-isolation behavior.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes. The shared UI tokens and state contract live in root `DESIGN.md` and the semantic projection in `frontend/src/app/globals.css`.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_settings.py`
- `tests/test_runtime_source_boundary.py`
- `tests/test_settings_agentic_pi_endpoints.py` — provider-default selection,
  switching, and deletion fallback.

## Related Features

- [settings.llm-servers](../../settings/llm-servers/architecture.md)
- [compute.pool](../../compute/pool/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-55 / CF-684
- Spec/task: CF-SPEC-91 / CF-1156
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
