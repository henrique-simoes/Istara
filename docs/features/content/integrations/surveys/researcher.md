---
stable_id: integrations.surveys
title: Survey Integrations
ui_path: Integrations > Surveys
audience: researcher
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/SurveysTab.tsx", "frontend/src/components/integrations/SurveySetupWizard.tsx", "backend/app/api/routes/surveys.py"]
api_references: ["backend/app/api/routes/surveys.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Survey Integrations

## What It Does

Surveys configures participant question and survey collection flows connected to project research.

## Why It Exists

Survey Integrations exists so the work represented by Integrations > Surveys has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Integrations > Surveys
- Navigation group: Integrations
- Primary component: `SurveysTab`

## How UX Researchers Use It

- Open Integrations > Surveys from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with survey integrations in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Integrations > Surveys when the current research task needs survey integrations.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: integrations.deployments, findings.evidence.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with survey integrations.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [integrations.deployments](../../integrations/deployments/researcher.md)
- [findings.evidence](../../findings/evidence/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/integrations/SurveysTab.tsx`, `frontend/src/components/integrations/SurveySetupWizard.tsx`, `backend/app/api/routes/surveys.py`
- API references: `backend/app/api/routes/surveys.py`
- Tests: none recorded
