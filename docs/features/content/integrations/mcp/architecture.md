---
stable_id: integrations.mcp
title: MCP Integrations
ui_path: Integrations > MCP
audience: architecture
status: documented
related_features: ["skills.catalog", "agents.registry"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/MCPTab.tsx", "frontend/src/components/integrations/MCPAccessPolicyEditor.tsx", "frontend/src/components/integrations/MCPAuditLog.tsx", "backend/app/api/routes/mcp.py", "backend/app/services/mcp_client_manager.py"]
api_references: ["backend/app/api/routes/mcp.py"]
test_references: ["tests/test_mcp.py"]
last_verified: 2026-05-18
compass: CF-SPEC-55 / CF-684; CF-SPEC-60 / CF-759
---

# MCP Integrations Architecture

## Implementation Summary

The MCP tab configures project-owned Model Context Protocol client connections plus admin-only MCP server exposure controls. Registered MCP clients are scoped by `project_id` and deduplicated by project, normalized transport, and URL so repeated featured-server connects do not show the same server multiple times inside one project.

## Frontend Surface

- `frontend/src/components/integrations/MCPTab.tsx`
- `frontend/src/components/integrations/MCPAccessPolicyEditor.tsx`
- `frontend/src/components/integrations/MCPAuditLog.tsx`
- `backend/app/api/routes/mcp.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/mcp.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/MCPTab.tsx` and the UI navigation path recorded in the inventory.
- Featured server labels must identify the server itself; non-Brazilian servers such as Playwright use a neutral server icon instead of Brazil-specific labeling.
- `MCPTab` passes the active project id into MCP client listing and featured-server connect flows. Without an active project, project-owned connected-server lists are empty and creation is disabled.
- `backend/app/api/routes/mcp.py` requires `project_id` for team-mode MCP client registration and featured connects, verifies the project exists, and authorizes the caller as project admin before client discovery, deletion, health checks, tool listing, or tool calls.
- Legacy/global MCP client rows remain accessible only through explicit global-admin API access without a project filter; project-facing Integrations views do not request or display them.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, tool/resource exposure, and project ownership synchronized with the cited route or integration component.

## Tests And Verification

- `tests/test_mcp.py`

## Related Features

- [skills.catalog](../../skills/catalog/architecture.md)
- [agents.registry](../../agents/registry/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-55 / CF-684; CF-SPEC-60 / CF-759
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
