---
stable_id: integrations.mcp
title: MCP Integrations
ui_path: Integrations > MCP
audience: researcher
status: documented
related_features: ["skills.catalog", "agents.registry"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/MCPTab.tsx", "frontend/src/components/integrations/MCPServerSetup.tsx", "frontend/src/components/integrations/MCPAccessPolicyEditor.tsx", "frontend/src/components/integrations/MCPAuditLog.tsx", "backend/app/api/routes/mcp.py"]
api_references: ["backend/app/api/routes/mcp.py"]
test_references: ["tests/test_mcp.py", "tests/test_mcp_ui_contracts.py", "frontend/src/lib/mcpUrl.test.ts", "tests/test_project_scope_contracts.py"]
last_verified: 2026-09-02
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-759; CF-SPEC-60 / CF-776
---

# MCP Integrations

## What It Does

The MCP tab configures Model Context Protocol connections for the active project. Admin users can also review global MCP server exposure controls, but connected external MCP clients shown in Integrations are project-owned.

## Why It Exists

MCP Integrations exists so the work represented by Integrations > MCP has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Integrations > MCP
- Navigation group: Integrations
- Primary component: `MCPTab`

## How UX Researchers Use It

- Open Integrations > MCP from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with MCP integrations in the active project context.
- Add or connect external MCP servers only after selecting the project that is allowed to use those tools.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Integrations > MCP when the current research task needs mcp integrations.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: skills.catalog, agents.registry.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped MCP server registrations associated with the selected project.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Discovery, deletion, health checks, cached tool views, and tool calls only operate on MCP servers owned by the active project.
- If a server save is rejected (for example, because the URL or headers are invalid), the setup form remains available and shows the returned error so the researcher can correct the input.
- The setup form keeps Test Connection and Save Server disabled until the URL is an absolute HTTP(S) endpoint without embedded credentials or query parameters, and shows an inline correction message for malformed values.
- Admin MCP audit review in the Integrations MCP tab is filtered to the active project. Cross-project MCP audit aggregation is reserved for explicit global-admin reporting surfaces.
- If an external MCP health check or tool call fails, the UI receives stable credential/network guidance; private endpoint and transport exception details stay in server logs.

## Caveats

- No active project means the connected MCP server list is empty and new connections are disabled.
- Legacy global MCP clients are admin API inventory and are not shown as project MCP connections.
- A connected server from another project should not appear or be actionable in the current project's MCP tab, even if the same user can administer both projects.
- MCP audit entries from another project should not appear in the current project's MCP tab, even for users who can administer both projects.
- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [skills.catalog](../../skills/catalog/researcher.md)
- [agents.registry](../../agents/registry/researcher.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/integrations/MCPTab.tsx`, `frontend/src/components/integrations/MCPServerSetup.tsx`, `frontend/src/components/integrations/MCPAccessPolicyEditor.tsx`, `frontend/src/components/integrations/MCPAuditLog.tsx`, `backend/app/api/routes/mcp.py`
- API references: `backend/app/api/routes/mcp.py`
- Tests: `tests/test_mcp.py`, `tests/test_project_scope_contracts.py`
