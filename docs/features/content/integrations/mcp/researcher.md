---
stable_id: integrations.mcp
title: MCP Integrations
ui_path: Integrations > MCP
audience: researcher
status: documented
related_features: ["skills.catalog", "agents.registry"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/MCPTab.tsx", "frontend/src/components/integrations/MCPAccessPolicyEditor.tsx", "frontend/src/components/integrations/MCPAuditLog.tsx", "backend/app/api/routes/mcp.py"]
api_references: ["backend/app/api/routes/mcp.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# MCP Integrations

## What It Does

The MCP tab configures Model Context Protocol server access, policies, and audit visibility.

## Why It Exists

MCP Integrations exists so the work represented by Integrations > MCP has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Integrations > MCP
- Navigation group: Integrations
- Primary component: `MCPTab`

## How UX Researchers Use It

- Open Integrations > MCP from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with mcp integrations in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Integrations > MCP when the current research task needs mcp integrations.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: skills.catalog, agents.registry.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with mcp integrations.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [skills.catalog](../../skills/catalog/researcher.md)
- [agents.registry](../../agents/registry/researcher.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/integrations/MCPTab.tsx`, `frontend/src/components/integrations/MCPAccessPolicyEditor.tsx`, `frontend/src/components/integrations/MCPAuditLog.tsx`, `backend/app/api/routes/mcp.py`
- API references: `backend/app/api/routes/mcp.py`
- Tests: none recorded
