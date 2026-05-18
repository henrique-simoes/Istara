---
stable_id: compute.pool
title: Compute Pool
ui_path: Compute Pool
audience: architecture
status: documented
related_features: ["settings.compute-donation", "settings.general"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/ComputePoolView.tsx", "frontend/src/stores/computeStore.ts", "backend/app/api/routes/compute.py", "backend/app/core/compute_registry_helpers.py", "backend/app/core/compute_registry_invocation.py", "backend/app/core/compute_registry_lifecycle.py", "backend/app/core/network_discovery.py", "backend/app/core/compute_pool.py"]
api_references: ["backend/app/api/routes/compute.py"]
test_references: ["tests/test_compute_registry_model_loading.py", "tests/test_compute_registry_hardening.py", "tests/test_network_discovery.py"]
last_verified: 2026-05-18
compass: CF-SPEC-58 / CF-731
---

# Compute Pool Architecture

## Implementation Summary

Compute Pool provides operational visibility into available compute nodes, routing, and local or pooled execution capacity. Hardware totals are deduplicated by physical provider machine so local/network/relay views of the same server do not inflate RAM or CPU totals. Local interface aliases are canonicalized before endpoint display and capacity aggregation, so one Mac exposed through multiple LAN IP addresses appears as one logical endpoint for the same provider and port. Provider reachability is reported separately from chat readiness: a reachable LM Studio server with loadable models but no model in memory is online, not offline, while routing still treats it as not ready until a model is loaded.

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
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_compute_registry_hardening.py`
- `tests/test_compute_registry_model_loading.py`
- `tests/test_network_discovery.py`

## Related Features

- [settings.compute-donation](../../settings/compute-donation/architecture.md)
- [settings.general](../../settings/general/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-58 / CF-731
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
