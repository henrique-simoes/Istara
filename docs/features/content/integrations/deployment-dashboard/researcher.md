---
stable_id: integrations.deployment-dashboard
title: Deployment Dashboard
ui_path: Integrations > Deployments > Dashboard
audience: researcher
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentDashboard.tsx", "backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
api_references: ["backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
test_references: ["tests/test_deployments.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-767
---

# Deployment Dashboard

## What It Does

The deployment dashboard has sub-tabs for live status, questions, participants, findings, channels, and timeline activity.

## Why It Exists

Deployment Dashboard exists so the work represented by Integrations > Deployments > Dashboard has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Integrations > Deployments > Dashboard
- Navigation group: Integrations
- Primary component: `DeploymentDashboard`

## How UX Researchers Use It

- Open Integrations > Deployments > Dashboard from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with deployment dashboard in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Integrations > Deployments > Dashboard when the current research task needs deployment dashboard.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: integrations.deployments, findings.evidence.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with deployment dashboard.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Conversation details, transcripts, responses, and analytics are read or updated only when they belong to the same project as the selected deployment.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [integrations.deployments](../../integrations/deployments/researcher.md)
- [findings.evidence](../../findings/evidence/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/integrations/DeploymentDashboard.tsx`, `backend/app/api/routes/deployments.py`, `backend/app/services/deployment_service.py`
- API references: `backend/app/api/routes/deployments.py`, `backend/app/services/deployment_service.py`
- Tests: `tests/test_deployments.py`
