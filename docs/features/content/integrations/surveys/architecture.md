---
stable_id: integrations.surveys
title: Survey Integrations
ui_path: Integrations > Surveys
audience: architecture
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/SurveysTab.tsx", "frontend/src/components/integrations/SurveySetupWizard.tsx", "frontend/src/stores/integrationsStore.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/surveys.py"]
api_references: ["backend/app/api/routes/surveys.py"]
test_references: ["tests/test_surveys.py", "tests/test_project_scope_contracts.py", "tests/test_integration_simulation_scope.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-762; CF-SPEC-60 / CF-776; CF-SPEC-65 / CF-842; CF-SPEC-82 / CF-1061
---

# Survey Integrations Architecture

## Implementation Summary

Surveys configures participant question and survey collection flows connected to project research.

## Frontend Surface

- `frontend/src/components/integrations/SurveysTab.tsx`
- `frontend/src/components/integrations/SurveySetupWizard.tsx`
- `frontend/src/stores/integrationsStore.ts`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/surveys.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/surveys.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/SurveysTab.tsx` and the UI navigation path recorded in the inventory.
- `SurveysTab` requests survey integrations and links with the active project id, clears stale integration state on project changes, and renders only survey integrations whose `project_id` matches the active project.
- Linked surveys are cleared before each project fetch and filtered by active `project_id` before rendering, preventing survey links from a previous project from lingering in the table while a new project loads.
- `SurveysTab` passes the active project id into survey link sync and integration deletion actions, while `SurveySetupWizard` refuses connection tests without an active project and stamps new integrations with that project id.
- `backend/app/api/routes/surveys.py` requires `project_id` on project-facing integration and survey-link lists, integration deletion, platform survey listing/creation, link sync, and response reads. Survey links must use an integration bound to the same active project before syncing or returning responses, and stale ids from another project resolve as not found.
- Simulation and benchmark survey integration calls must include the active project id on by-id sync, response, deletion, and cleanup URLs, so the harness cannot validate global survey-link behavior by accident.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Survey ingestion creates provisional visible nuggets plus raw survey-response evidence units for the Research Spine. These artifacts are not reportable until governed coding, reliability/reconciliation, and Done-task gates accept the linked evidence.
- Skills or agents that analyze survey or deployment responses may propose candidate findings, but they cannot mark those outputs as accepted report evidence.

## Tests And Verification

- `tests/test_surveys.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_integration_simulation_scope.py`

## Related Features

- [integrations.deployments](../../integrations/deployments/architecture.md)
- [findings.evidence](../../findings/evidence/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-762; CF-SPEC-60 / CF-776; CF-SPEC-65 / CF-842; CF-SPEC-82 / CF-1061
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
