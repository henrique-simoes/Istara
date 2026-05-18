---
stable_id: integrations.surveys
title: Survey Integrations
ui_path: Integrations > Surveys
audience: architecture
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/SurveysTab.tsx", "frontend/src/components/integrations/SurveySetupWizard.tsx", "backend/app/api/routes/surveys.py"]
api_references: ["backend/app/api/routes/surveys.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Survey Integrations Architecture

## Implementation Summary

Surveys configures participant question and survey collection flows connected to project research.

## Frontend Surface

- `frontend/src/components/integrations/SurveysTab.tsx`
- `frontend/src/components/integrations/SurveySetupWizard.tsx`
- `backend/app/api/routes/surveys.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/surveys.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/SurveysTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [integrations.deployments](../../integrations/deployments/architecture.md)
- [findings.evidence](../../findings/evidence/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
