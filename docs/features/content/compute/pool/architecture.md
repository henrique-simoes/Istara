---
stable_id: compute.pool
title: Compute Pool
ui_path: Compute Pool
audience: architecture
status: documented
related_features: ["settings.compute-donation", "settings.general"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/ComputePoolView.tsx", "frontend/src/stores/computeStore.ts", "backend/app/api/routes/compute.py", "backend/app/core/compute_registry_helpers.py", "backend/app/core/compute_registry_invocation.py", "backend/app/core/compute_registry_lifecycle.py", "backend/app/core/compute_registry_routing.py", "backend/app/core/network_discovery.py", "backend/app/core/compute_pool.py"]
api_references: ["backend/app/api/routes/compute.py"]
test_references: ["tests/test_compute.py", "tests/test_compute_registry_model_loading.py", "tests/test_compute_registry_hardening.py", "tests/test_network_discovery.py", "tests/test_project_rbac.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-774
---

# Compute Pool Architecture

## Implementation Summary

Compute Pool provides active-project operational visibility into available compute nodes, routing, and local or pooled execution capacity. Hardware totals are deduplicated by physical provider machine so local/network/relay views of the same server do not inflate RAM or CPU totals. Local interface aliases are canonicalized before endpoint display and capacity aggregation, so one Mac exposed through multiple LAN IP addresses appears as one logical endpoint for the same provider and port. Provider reachability is reported separately from chat readiness: a reachable LM Studio server with loadable models but no model in memory is online, not offline, while routing still treats it as not ready until a model is loaded.

Donated relay/browser nodes are treated as a project-content security boundary. Regular Compute Pool endpoints require an authorized `project_id` for every role, including global admins, and node stats, hardware totals, available models, and model warnings are filtered to local/server-owned capacity plus donors authorized for that project. Cross-project compute aggregation belongs only on explicit admin reporting surfaces. Prompt, chat, embedding, and model-load recovery paths may only select donated nodes when the request carries a concrete `project_id` and the node's authenticated donation scope includes that project. Server-owned local/network nodes remain available for unscoped internal work.

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
- Compute registry identity uses passive local OS interface aliases to collapse duplicate local endpoints without silently merging unrelated remote machines that happen to expose the same model catalog.
- Network discovery excludes all known local interface aliases before probing the subnet, preventing the server from discovering itself through a second LAN address.
- Relay/browser donors carry `allowed_project_ids` resolved from either the authenticated user's project memberships or a validated compute-donation connection string. A bare network token can connect for status only, not receive project content.
- Team-mode compute donation strings with wildcard project scope are rejected at relay validation so legacy all-project tokens cannot become global project processors.
- `ComputeRegistry._select_candidates(..., project_id=...)` is the central guard: relay/browser nodes are excluded unless the project scope matches, preventing unpatched callers without project context from leaking content to donated machines.
- `ComputeRegistry.get_stats(project_id=...)` and `get_warnings(project_id=...)` reuse the same project visibility rule so the regular Compute Pool UI cannot disclose other projects' donors, models, hosts, or RAM totals. The `/api/compute/nodes`, `/api/compute/stats`, and `/api/compute/model-warnings` routes reject missing `project_id` instead of falling back to global admin capacity.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_compute.py`
- `tests/test_project_rbac.py`
- `tests/test_compute_registry_hardening.py`
- `tests/test_compute_registry_model_loading.py`
- `tests/test_network_discovery.py`

## Related Features

- [settings.compute-donation](../../settings/compute-donation/architecture.md)
- [settings.general](../../settings/general/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-774
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
