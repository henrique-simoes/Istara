---
stable_id: integrations.deployments
title: Research Deployments
ui_path: Integrations > Deployments
audience: researcher
status: documented
related_features: ["integrations.deployment-dashboard", "integrations.surveys", "integrations.messaging"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentsTab.tsx", "frontend/src/components/integrations/DeploymentWizard.tsx", "backend/app/api/routes/deployments.py"]
api_references: ["backend/app/api/routes/deployments.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Research Deployments

## What It Does

Deployments configure participant-facing research deployments and link them to channels, questions, findings, and timeline views.

## Why It Exists

Research Deployments exists so the work represented by Integrations > Deployments has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Integrations > Deployments
- Navigation group: Integrations
- Primary component: `DeploymentsTab`

## How UX Researchers Use It

- Open Integrations > Deployments from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with research deployments in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Integrations > Deployments when the current research task needs research deployments.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: integrations.deployment-dashboard, integrations.surveys, integrations.messaging.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with research deployments.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/researcher.md)
- [integrations.surveys](../../integrations/surveys/researcher.md)
- [integrations.messaging](../../integrations/messaging/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/integrations/DeploymentsTab.tsx`, `frontend/src/components/integrations/DeploymentWizard.tsx`, `backend/app/api/routes/deployments.py`
- API references: `backend/app/api/routes/deployments.py`
- Tests: none recorded
