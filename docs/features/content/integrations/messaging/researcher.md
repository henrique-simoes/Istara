---
stable_id: integrations.messaging
title: Messaging Integrations
ui_path: Integrations > Messaging
audience: researcher
status: documented
related_features: ["integrations.overview", "integrations.deployment-dashboard"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/MessagingTab.tsx", "frontend/src/components/integrations/ChannelSetupWizard.tsx", "backend/app/api/routes/channels.py"]
api_references: ["backend/app/api/routes/channels.py", "backend/app/api/routes/webhooks.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Messaging Integrations

## What It Does

Messaging connects external conversation channels such as team or participant messaging tools into Istara.

## Why It Exists

Messaging Integrations exists so the work represented by Integrations > Messaging has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Integrations > Messaging
- Navigation group: Integrations
- Primary component: `MessagingTab`

## How UX Researchers Use It

- Open Integrations > Messaging from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with messaging integrations in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Integrations > Messaging when the current research task needs messaging integrations.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: integrations.overview, integrations.deployment-dashboard.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with messaging integrations.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [integrations.overview](../../integrations/overview/researcher.md)
- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/researcher.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/integrations/MessagingTab.tsx`, `frontend/src/components/integrations/ChannelSetupWizard.tsx`, `backend/app/api/routes/channels.py`
- API references: `backend/app/api/routes/channels.py`, `backend/app/api/routes/webhooks.py`
- Tests: none recorded
