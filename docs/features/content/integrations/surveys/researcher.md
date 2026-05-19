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
test_references: ["tests/test_surveys.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-776
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
- Survey platform connection, integration removal, linked survey sync, and response review operate only on survey records owned by the active project.

## Caveats

- No active project means survey platform connection and sync actions are disabled or rejected.
- A survey integration or link from another project should not appear or be actionable in the current project's Survey tab, even if the same user can administer both projects.
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
- Tests: `tests/test_surveys.py`, `tests/test_project_scope_contracts.py`
