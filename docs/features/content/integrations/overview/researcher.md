---
stable_id: integrations.overview
title: Integrations Overview
ui_path: Integrations > Overview
audience: researcher
status: documented
related_features: ["integrations.messaging", "integrations.deployments", "integrations.mcp"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/IntegrationsView.tsx", "frontend/src/components/integrations/IntegrationsOverview.tsx", "frontend/src/stores/integrationsStore.ts"]
api_references: ["backend/app/api/routes/channels.py", "backend/app/api/routes/deployments.py"]
test_references: ["tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-56 / CF-698; CF-SPEC-59 / CF-740
---

# Integrations Overview

## What It Does

The Integrations overview summarizes connected channels, deployment surfaces, and integration health for the active project.

## Why It Exists

Integrations Overview exists so the work represented by Integrations > Overview has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Integrations > Overview
- Navigation group: Integrations
- Primary component: `IntegrationsOverview`

## How UX Researchers Use It

- Open Integrations > Overview from the Istara navigation or the parent tab.
- Review channels, deployments, and survey integrations that belong to the active project.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Integrations > Overview when the current research task needs integrations overview.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: integrations.messaging, integrations.deployments, integrations.mcp.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped channels, deployments, and survey integrations associated with integrations overview.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Recent Activity is expected to show only channels and deployments associated with the active project; global MCP inventory is separate from project-owned activity.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [integrations.messaging](../../integrations/messaging/researcher.md)
- [integrations.deployments](../../integrations/deployments/researcher.md)
- [integrations.mcp](../../integrations/mcp/researcher.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/integrations/IntegrationsView.tsx`, `frontend/src/components/integrations/IntegrationsOverview.tsx`, `frontend/src/stores/integrationsStore.ts`
- API references: `backend/app/api/routes/channels.py`, `backend/app/api/routes/deployments.py`
- Tests: `tests/test_project_scope_contracts.py`
