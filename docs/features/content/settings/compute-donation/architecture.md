---
stable_id: settings.compute-donation
title: Compute Donation
ui_path: Settings > Compute Donation
audience: architecture
status: documented
related_features: ["compute.pool", "settings.general"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/common/DonateComputeToggle.tsx", "frontend/src/components/settings/ConnectionStringPanel.tsx", "backend/app/api/routes/compute.py", "backend/app/api/routes/connections.py", "backend/app/core/compute_node_invocation.py", "backend/app/core/compute_pool.py", "backend/app/core/compute_registry_routing.py"]
api_references: ["backend/app/api/routes/compute.py", "backend/app/api/routes/connections.py"]
test_references: ["tests/test_compute.py", "tests/compute_cases/stats_websocket.py", "tests/test_project_rbac.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-754; CF-SPEC-63 / CF-814; CF-SPEC-70 / CF-899
---

# Compute Donation Architecture

## Implementation Summary

Compute donation lets a browser session or relay process contribute local compute capacity under controlled limits. Donated nodes are never treated as global project processors: project prompt and embedding payloads are routed to a donor only when the relay is authenticated and its resolved project scope includes the active project. Browser/JWT relay scope is derived from the current database user role and project memberships for bound sessions, not from stale token role claims. The relay node methods themselves reject missing or mismatched project ids before sending websocket payloads, so direct callers inherit the same project-content boundary as registry-routed requests.

## Frontend Surface

- `frontend/src/components/common/DonateComputeToggle.tsx`
- `backend/app/core/compute_pool.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/compute.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/DonateComputeToggle.tsx` and the UI navigation path recorded in the inventory.
- Browser donation uses the authenticated user's current database role and project memberships as its donation scope. Bound auth sessions are rehydrated from the database before relay registration so user deletion, demotion, or membership changes are reflected in the donation boundary.
- Relay/desktop donation strings must include at least one selected project in team mode. The relay sends the issued connection string back to `/ws/relay`, where the server verifies issuance, active status, token type, expiry, and `allowed_project_ids` before the node can process project content.
- Team-mode relay validation rejects wildcard donation scope, including legacy all-project donation strings, so donated machines cannot silently become global project processors.
- A relay authenticated only by the shared network token can register for status but is excluded from prompt and embedding routing because it has no project scope.
- Direct relay/browser dispatch through `ComputeNode.chat`, `ComputeNode.chat_stream`, `ComputeNode.embed`, or `ComputeNode.embed_batch` requires the active project to match the node's resolved donation scope before any content is sent over websocket or direct streaming transport.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- LLM prompt and embedding routing is guarded by project scope before donated relay/browser nodes are selected.

## Tests And Verification

- `tests/test_compute.py`
- `tests/compute_cases/stats_websocket.py`
- `tests/test_project_rbac.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [compute.pool](../../compute/pool/architecture.md)
- [settings.general](../../settings/general/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754; CF-SPEC-63 / CF-814; CF-SPEC-70 / CF-899
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
