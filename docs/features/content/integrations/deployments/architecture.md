---
stable_id: integrations.deployments
title: Research Deployments
ui_path: Integrations > Deployments
audience: architecture
status: documented
related_features: ["integrations.deployment-dashboard", "integrations.surveys", "integrations.messaging"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentsTab.tsx", "frontend/src/components/integrations/DeploymentWizard.tsx", "backend/app/api/routes/deployments.py"]
api_references: ["backend/app/api/routes/deployments.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Research Deployments Architecture

## Implementation Summary

Deployments configure participant-facing research deployments and link them to channels, questions, findings, and timeline views.

## Frontend Surface

- `frontend/src/components/integrations/DeploymentsTab.tsx`
- `frontend/src/components/integrations/DeploymentWizard.tsx`
- `backend/app/api/routes/deployments.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/deployments.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/DeploymentsTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/architecture.md)
- [integrations.surveys](../../integrations/surveys/architecture.md)
- [integrations.messaging](../../integrations/messaging/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
