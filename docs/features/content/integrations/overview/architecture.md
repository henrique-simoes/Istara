---
stable_id: integrations.overview
title: Integrations Overview
ui_path: Integrations > Overview
audience: architecture
status: documented
related_features: ["integrations.messaging", "integrations.deployments", "integrations.mcp"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/IntegrationsView.tsx", "frontend/src/components/integrations/IntegrationsOverview.tsx", "frontend/src/stores/integrationsStore.ts", "frontend/src/lib/api.ts", "backend/app/services/deployment_service.py", "backend/app/services/channel_service.py", "backend/app/services/mcp_client_manager.py"]
api_references: ["backend/app/api/routes/channels.py", "backend/app/api/routes/deployments.py", "backend/app/api/routes/surveys.py", "backend/app/api/routes/mcp.py", "backend/app/services/deployment_service.py", "backend/app/services/channel_service.py", "backend/app/services/mcp_client_manager.py"]
test_references: ["tests/test_channels.py", "tests/test_mcp.py", "tests/test_deployments.py", "tests/test_project_scope_contracts.py", "tests/test_integration_simulation_scope.py"]
last_verified: 2026-05-19
compass: CF-SPEC-56 / CF-698; CF-SPEC-59 / CF-740; CF-SPEC-60 / CF-767; CF-SPEC-65 / CF-842; CF-SPEC-82 / CF-1061
---

# Integrations Overview Architecture

## Implementation Summary

The Integrations overview summarizes connected channels, deployment surfaces, and integration health for the active project.

## Frontend Surface

- `frontend/src/components/integrations/IntegrationsView.tsx`
- `frontend/src/components/integrations/IntegrationsOverview.tsx`
- `frontend/src/stores/integrationsStore.ts`
- `frontend/src/lib/api.ts`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/channels.py`
- `backend/app/api/routes/deployments.py`
- `backend/app/api/routes/surveys.py`
- `backend/app/api/routes/mcp.py`
- `backend/app/services/deployment_service.py`
- `backend/app/services/channel_service.py`
- `backend/app/services/mcp_client_manager.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/IntegrationsView.tsx` and the UI navigation path recorded in the inventory.
- `frontend/src/components/integrations/IntegrationsOverview.tsx` passes the active project into channel, deployment, survey, and MCP-client fetches, then defensively filters recent activity and summary counts by `project_id`.
- If the live browser shows unscoped Recent Activity despite the source contracts above, operators should check the status bar for `Runtime bundle stale`. That signal comes from `/api/settings/status` and indicates the running production frontend build predates source fixes.
- The overview resets its loaded state on active-project changes and ignores stale fetch completions from the previous project, so old Recent Activity rows cannot linger while a new project is loading.
- If there is no active project, the integrations store clears project-owned channel, deployment, survey, and MCP client lists rather than calling list endpoints without a project scope.
- The integrations store filters every fetched channel, deployment, survey integration, and MCP client by the active `project_id` before storing; MCP clients are also deduplicated within that project by normalized transport and URL.
- Project-owned integration list APIs require `project_id` even for global admins; admin dashboard/reporting routes are the only intended cross-project aggregation surfaces.
- Deployment overview metrics count only conversations attached to deployments in the active project, preventing another project's deployment activity from appearing as Recent Activity or summary volume.
- MCP client/tool totals are project-owned inventory in the Integrations view; global MCP server exposure controls remain admin-only management state.
- `tests/test_channels.py` and `tests/test_mcp.py` exercise service/API scope boundaries for channel and MCP helper paths; `tests/test_deployments.py` exercises the API-level conversation count boundary; `tests/test_project_scope_contracts.py` locks the source contract so project-owned recent activity is built from scoped collections and not from global integration lists.
- `tests/test_integration_simulation_scope.py` scans simulation and real-user benchmark integration calls so by-id channel, deployment, survey, and MCP operations keep the active `project_id` in the URL instead of proving old global paths.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- `tests/test_deployments.py`
- `tests/test_channels.py`
- `tests/test_mcp.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_integration_simulation_scope.py`

## Related Features

- [integrations.messaging](../../integrations/messaging/architecture.md)
- [integrations.deployments](../../integrations/deployments/architecture.md)
- [integrations.mcp](../../integrations/mcp/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-56 / CF-698; CF-SPEC-59 / CF-740; CF-SPEC-60 / CF-767; CF-SPEC-65 / CF-842; CF-SPEC-82 / CF-1061
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
