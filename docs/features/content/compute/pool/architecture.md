---
stable_id: compute.pool
title: Compute Pool
ui_path: Compute Pool
audience: architecture
status: documented
related_features: ["settings.compute-donation", "settings.general"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/ComputePoolView.tsx", "frontend/src/stores/computeStore.ts", "backend/app/api/routes/compute.py", "backend/app/core/compute_node_invocation.py", "backend/app/core/compute_registry_helpers.py", "backend/app/core/compute_registry_invocation.py", "backend/app/core/compute_registry_lifecycle.py", "backend/app/core/compute_registry_routing.py", "backend/app/core/network_discovery.py", "backend/app/core/compute_pool.py"]
api_references: ["backend/app/api/routes/compute.py"]
test_references: ["tests/test_compute.py", "tests/compute_cases/status_contracts.py", "tests/compute_cases/stats_websocket.py", "tests/compute_cases/routing.py", "tests/test_compute_registry_model_loading.py", "tests/test_compute_registry_hardening.py", "tests/test_network_discovery.py", "tests/test_project_rbac.py", "tests/test_project_scope_contracts.py", "tests/test_validation_project_scope.py", "tests/real_user_benchmark/run.mjs"]
last_verified: 2026-05-21
compass: CF-SPEC-60 / CF-774; CF-SPEC-63 / CF-814; CF-SPEC-63 / CF-815; CF-SPEC-66 / CF-856; CF-SPEC-70 / CF-899; CF-SPEC-90 / CF-1142; CF-SPEC-92 / CF-1170; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581
---

# Compute Pool Architecture

## Implementation Summary

Compute Pool provides active-project operational visibility into available compute nodes, routing, and local or pooled execution capacity. Hardware totals are deduplicated by physical provider machine so local/network/relay views of the same server do not inflate RAM or CPU totals. Local interface aliases are canonicalized before endpoint display and capacity aggregation, so one Mac exposed through multiple LAN IP addresses appears as one logical endpoint for the same provider and port. Provider reachability is reported separately from chat readiness: a reachable LM Studio server with loadable models but no model in memory is online, not offline, while routing still treats it as not ready until a model is loaded.

Donated relay/browser nodes are treated as a project-content security boundary. Regular Compute Pool endpoints require an authorized `project_id` for every role, including global admins, and node stats, hardware totals, available models, and model warnings are filtered to local/server-owned capacity plus donors authorized for that project. Cross-project compute aggregation belongs only on explicit admin reporting surfaces, currently `/api/admin/compute/stats`, which is protected by global-admin authorization and is separate from the project-facing `/api/compute/*` contract. Prompt, chat, embedding, and model-load recovery paths may only select donated nodes when the request carries a concrete `project_id` and the node's authenticated donation scope includes that project. For browser/JWT relay connections, bound auth sessions resolve the current database user and project memberships before scope is assigned, so a stale admin token cannot keep all-project donation rights after the user is demoted or removed. The direct relay/browser `ComputeNode` dispatch methods enforce the same rule before sending any websocket payload, so lower-level callers cannot bypass the registry selector. Server-owned local/network nodes remain available for unscoped internal work.

The architecture is Petals-inspired in collaboration and donation semantics, but it routes whole requests to authorized OpenAI-compatible or relay/browser nodes. It does not implement Petals-equivalent transformer layer sharding or cross-machine model partitioning.

## Frontend Surface

- `frontend/src/components/common/ComputePoolView.tsx`
- `backend/app/api/routes/compute.py`
- `backend/app/core/compute_pool.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/computeStore.ts`

### API And Backend

- `backend/app/api/routes/compute.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/ComputePoolView.tsx` and the UI navigation path recorded in the inventory.
- Model chips are rendered from both advertised loaded models and cached model capability records, so capability-only models remain visible in the pool UI.
- Node payloads expose `is_reachable`, `is_ready`, `readiness_state`, and `reachable_nodes` so UI labels can distinguish online/no-model-loaded from offline/unreachable without changing the conservative routing meaning of `alive_nodes`.
- Compute registry identity uses passive local OS interface aliases and the configured local provider source to collapse duplicate local endpoints without silently merging unrelated remote machines that happen to expose the same model catalog. When a configured local LAN endpoint and a network-discovered endpoint have different IPs but the same provider, port, path, and matching hardware or model evidence, the registry treats the network entry as a stale alias of the configured local service.
- Node readiness derives from explicit readiness state before legacy health booleans, so a stale `is_healthy` flag cannot make `no_model_loaded` look routable.
- Network discovery excludes all known local interface aliases before probing the subnet, preventing the server from discovering itself through a second LAN address.
- Relay/browser donors carry `allowed_project_ids` resolved from either the authenticated user's current database-backed role and project memberships or a validated compute-donation connection string. A bare network token can connect for status only, not receive project content.
- Admin-generated compute donation strings auto-provision `NETWORK_ACCESS_TOKEN` when the server has none configured, then embed that token in the signed donation string. User invite strings still do not carry relay credentials.
- Bound browser/JWT relay sessions use `current_user_context_for_payload` before deriving donation scope, and `_scope_from_user` re-reads the database user role before granting all-project admin scope.
- Team-mode compute donation strings with wildcard project scope are rejected at relay validation so legacy all-project tokens cannot become global project processors.
- `ComputeRegistry._select_candidates(..., project_id=...)` is the central guard: relay/browser nodes are excluded unless the project scope matches, preventing unpatched callers without project context from leaking content to donated machines.
- `ComputeRegistry._sorted_servers(project_id=...)` applies the same project visibility rule for legacy validation and LLM router compatibility paths, so ensemble validation can use authorized project donors without making unscoped validation global.
- `ComputeNode.chat`, `ComputeNode.chat_stream`, `ComputeNode.embed`, and `ComputeNode.embed_batch` also require the request project to match `allowed_project_ids` before direct relay/browser websocket or streaming dispatch, preventing tests, maintenance scripts, or future services from bypassing registry project filtering.
- `ComputeRegistry.get_stats(project_id=...)` and `get_warnings(project_id=...)` reuse the same project visibility rule so the regular Compute Pool UI cannot disclose other projects' donors, models, hosts, or RAM totals. The `/api/compute/nodes`, `/api/compute/stats`, and `/api/compute/model-warnings` routes reject missing `project_id` instead of falling back to global admin capacity; global fleet stats are exposed only by `/api/admin/compute/stats` after `require_global_admin`.
- Compute node stats distinguish donor lifecycle states: registration/health comes from visible relay/browser nodes, selection increments `selected_request_count`, successful chat/stream service increments `served_request_count`, and failures increment `failed_request_count`. The real-user benchmark must use these counters or explicit backend route logs/forced topology to prove donor usage; a model override alone is not proof that donated compute served a request.
- Collaborative benchmark scoring separates technical relay verification from natural orchestration evidence. After real chat, task execution, review, and findings work, the benchmark snapshots project-scoped compute stats and records selected/served counter deltas without pinning a specific donor or bypassing Istara's model manager. Observing scheduler activity is not enough for full agentic-orchestration credit; the score remains capped until donated relay usage is actually proven.
- Multi-donor real-user benchmarks leave `STRICT_AUTO_ROUTING` off by default. Enabling it is an explicit single-model isolation mode, because strict routing can intentionally exclude otherwise healthy donated models whose advertised model names differ from the Mac Studio live-test profile.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_compute.py`
- `tests/compute_cases/status_contracts.py`
- `tests/compute_cases/stats_websocket.py`
- `tests/compute_cases/routing.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_project_rbac.py`
- `tests/test_compute_registry_hardening.py`
- `tests/test_compute_registry_model_loading.py`
- `tests/test_network_discovery.py`
- `tests/test_validation_project_scope.py`
- `tests/real_user_benchmark/run.mjs`

## Related Features

- [settings.compute-donation](../../settings/compute-donation/architecture.md)
- [settings.general](../../settings/general/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-774; CF-SPEC-63 / CF-814; CF-SPEC-63 / CF-815; CF-SPEC-66 / CF-856; CF-SPEC-70 / CF-899; CF-SPEC-90 / CF-1142; CF-SPEC-92 / CF-1170; CF-SPEC-121; CF-SPEC-122; CF-SPEC-123 / CF-1581
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
