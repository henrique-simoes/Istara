---
stable_id: integrations.mcp
title: MCP Integrations
ui_path: Integrations > MCP
audience: architecture
status: documented
related_features: ["skills.catalog", "agents.registry"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/MCPTab.tsx", "frontend/src/components/integrations/MCPServerSetup.tsx", "frontend/src/components/integrations/MCPAccessPolicyEditor.tsx", "frontend/src/components/integrations/MCPAuditLog.tsx", "frontend/src/stores/integrationsStore.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/mcp.py", "backend/app/mcp/server.py", "backend/app/services/mcp_client_manager.py", "backend/app/services/mcp_security.py"]
api_references: ["backend/app/api/routes/mcp.py", "backend/app/mcp/server.py", "backend/app/services/mcp_client_manager.py", "backend/app/services/mcp_security.py"]
test_references: ["tests/test_mcp.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-55 / CF-684; CF-SPEC-60 / CF-762; CF-SPEC-60 / CF-776; CF-SPEC-65 / CF-842; CF-SPEC-68 / CF-870
---

# MCP Integrations Architecture

## Implementation Summary

The MCP tab configures project-owned Model Context Protocol client connections plus admin-only MCP server exposure controls. Registered MCP clients are scoped by `project_id` and deduplicated by project, normalized transport, and URL so repeated featured-server connects do not show the same server multiple times inside one project.

## Frontend Surface

- `frontend/src/components/integrations/MCPTab.tsx`
- `frontend/src/components/integrations/MCPServerSetup.tsx`
- `frontend/src/components/integrations/MCPAccessPolicyEditor.tsx`
- `frontend/src/components/integrations/MCPAuditLog.tsx`
- `frontend/src/stores/integrationsStore.ts`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/mcp.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/mcp.py`
- `backend/app/mcp/server.py`
- `backend/app/services/mcp_client_manager.py`
- `backend/app/services/mcp_security.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/MCPTab.tsx` and the UI navigation path recorded in the inventory.
- Featured server labels must identify the server itself; non-Brazilian servers such as Playwright use a neutral server icon instead of Brazil-specific labeling.
- `MCPTab` passes the active project id into MCP client listing, discovery, deletion, and featured-server connect flows, clears stale client state during project changes, and renders only clients whose `project_id` matches the active project.
- The shared integrations store applies a second project filter and per-project URL/transport dedupe to MCP client rows before rendering, which prevents repeated server registrations such as multiple copies of the same featured MCP endpoint from appearing in one project view.
- `MCPServerSetup` refuses test/save flows without an active project, stamps new external MCP server registrations with that project id, and uses the same active project for discovery and cleanup if the connection test fails.
- `backend/app/api/routes/mcp.py` requires `project_id` for project-facing MCP client lists, tool aggregation, featured server browsing, client registration, featured connects, and every server-id action route. It verifies the project exists and authorizes reads as project viewer while client discovery, deletion, health checks, cached tools, and tool calls remain project-admin operations. A server id from another project resolves as not found even for a global admin using the project-facing Integrations API.
- `backend/app/services/mcp_client_manager.py` requires a project id for registration, list, tool aggregation, discovery, tool calls, health checks, and deletion, and loads server records by both id and project id before returning cached tools or making outbound MCP calls.
- The external Istara MCP server treats project-content tools as project-scoped. `get_findings`, `search_memory`, `execute_skill`, `deploy_research`, and `get_deployment_status` require `project_id`; empty MCP project allowlists mean no project is exposed, not unrestricted access.
- MCP `search_memory` calls project-scoped retrieval with the requested project id rather than an empty/global memory id. MCP deployment status is filtered by project, and skill/report execution is rejected for paused projects before content processing.
- MCP `list_projects` is filtered by the access policy allowlist and returns an empty list when no project ids are allowed, preventing external agents from enumerating project names by default.
- Legacy/global MCP client rows are not returned by project-facing Integrations APIs; any cross-project MCP reporting must use a dedicated global-admin surface.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, tool/resource exposure, and project ownership synchronized with the cited route or integration component.
- The MCP access policy allowlist is an external-agent authorization boundary. A tool policy may be enabled, but it still cannot access project content unless the requested project id is explicitly allowed or the policy uses the admin-only wildcard.

## Tests And Verification

- `tests/test_mcp.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [skills.catalog](../../skills/catalog/architecture.md)
- [agents.registry](../../agents/registry/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-55 / CF-684; CF-SPEC-60 / CF-762; CF-SPEC-60 / CF-776; CF-SPEC-65 / CF-842; CF-SPEC-68 / CF-870
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
