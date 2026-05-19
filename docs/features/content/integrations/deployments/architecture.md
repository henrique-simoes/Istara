---
stable_id: integrations.deployments
title: Research Deployments
ui_path: Integrations > Deployments
audience: architecture
status: documented
related_features: ["integrations.deployment-dashboard", "integrations.surveys", "integrations.messaging"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentsTab.tsx", "frontend/src/components/integrations/DeploymentWizard.tsx", "backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
api_references: ["backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
test_references: ["tests/test_deployments.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-767
---

# Research Deployments Architecture

## Implementation Summary

Deployments configure participant-facing research deployments and link them to channels, questions, findings, and timeline views.

## Frontend Surface

- `frontend/src/components/integrations/DeploymentsTab.tsx`
- `frontend/src/components/integrations/DeploymentWizard.tsx`
- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`
- `DeploymentsTab` reads `activeProjectId` from `frontend/src/stores/projectStore.ts` and passes it into `fetchDeployments(activeProjectId)` before rendering deployment rows or summary counts.
- The tab derives a `scopedDeployments` list from the store by matching `deployment.project_id` to the active project, so stale deployment state from a previous project cannot populate the list, counts, or selected detail view.

### API And Backend

- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`
- Deployment list requests must include `project_id`; the route enforces project access before returning deployment records, including for global admins using the project-facing Integrations route. The admin dashboard remains the only intended global aggregation surface.
- Deployment creation validates every `channel_instance_id` against the deployment `project_id` before storing the deployment, so a deployment in one project cannot route participant content through another project's messaging channel.
- Deployment response handling, conversations, transcripts, analytics, and overview counters all require the conversation/deployment/channel records to match the same project boundary before participant content or findings are read, updated, or summarized.

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/DeploymentsTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Deployments are project-owned integration records. Any agent, skill, LLM, MCP, channel, or deployment worker that uses deployment data must preserve the same active-project and authorization boundary before routing participant content or generated research artifacts.

## Tests And Verification

- `tests/test_deployments.py` exercises API-level project isolation for deployment channel ownership, deployment overview conversation counts, and cross-project response rejection.
- `tests/test_project_scope_contracts.py` asserts that `DeploymentsTab` imports the project store, fetches deployments with the active project id, renders only `scopedDeployments`, and does not fall back to a global `fetchDeployments()` call.

## Related Features

- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/architecture.md)
- [integrations.surveys](../../integrations/surveys/architecture.md)
- [integrations.messaging](../../integrations/messaging/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-767
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
