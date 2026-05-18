---
stable_id: integrations.overview
title: Integrations Overview
ui_path: Integrations > Overview
audience: architecture
status: documented
related_features: ["integrations.messaging", "integrations.deployments", "integrations.mcp"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/IntegrationsView.tsx", "frontend/src/components/integrations/IntegrationsOverview.tsx", "frontend/src/stores/integrationsStore.ts"]
api_references: ["backend/app/api/routes/channels.py", "backend/app/api/routes/deployments.py"]
test_references: ["tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-56 / CF-698; CF-SPEC-59 / CF-740
---

# Integrations Overview Architecture

## Implementation Summary

The Integrations overview summarizes connected channels, deployment surfaces, and integration health for the active project.

## Frontend Surface

- `frontend/src/components/integrations/IntegrationsView.tsx`
- `frontend/src/components/integrations/IntegrationsOverview.tsx`
- `frontend/src/stores/integrationsStore.ts`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/channels.py`
- `backend/app/api/routes/deployments.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/IntegrationsView.tsx` and the UI navigation path recorded in the inventory.
- `frontend/src/components/integrations/IntegrationsOverview.tsx` passes the active project into channel, deployment, and survey fetches, then defensively filters recent activity and summary counts by `project_id`.
- MCP server/tool totals remain global integration inventory; project-owned channels, deployments, and survey integrations do not leak into another project's overview.
- `tests/test_project_scope_contracts.py` locks the source contract so project-owned recent activity is built from scoped collections and not from global integration lists.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- `tests/test_project_scope_contracts.py`

## Related Features

- [integrations.messaging](../../integrations/messaging/architecture.md)
- [integrations.deployments](../../integrations/deployments/architecture.md)
- [integrations.mcp](../../integrations/mcp/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-56 / CF-698; CF-SPEC-59 / CF-740
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
