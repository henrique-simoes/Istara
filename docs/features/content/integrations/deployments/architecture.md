---
stable_id: integrations.deployments
title: Research Deployments
ui_path: Integrations > Deployments
audience: architecture
status: documented
related_features: ["integrations.deployment-dashboard", "integrations.surveys", "integrations.messaging"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentsTab.tsx", "frontend/src/components/integrations/DeploymentWizard.tsx", "frontend/src/components/integrations/DeploymentDashboard.tsx", "frontend/src/components/integrations/ConversationTranscript.tsx", "frontend/src/lib/api.ts", "backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
api_references: ["backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
test_references: ["tests/test_deployments.py", "tests/test_project_scope_contracts.py", "tests/test_integration_simulation_scope.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-767; CF-SPEC-60 / CF-773; CF-SPEC-62 / CF-793; CF-SPEC-75 / CF-964; CF-SPEC-82 / CF-1061; CF-SPEC-93 / CF-1184
---

# Research Deployments Architecture

## Implementation Summary

Deployments configure participant-facing research deployments and link them to channels, questions, findings, and timeline views.

## Frontend Surface

- `frontend/src/components/integrations/DeploymentsTab.tsx`
- `frontend/src/components/integrations/DeploymentWizard.tsx`
- `frontend/src/components/integrations/DeploymentDashboard.tsx`
- `frontend/src/components/integrations/ConversationTranscript.tsx`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`
- `DeploymentsTab` reads `activeProjectId` from `frontend/src/stores/projectStore.ts` and passes it into `fetchDeployments(activeProjectId)` before rendering deployment rows or summary counts.
- The tab derives a `scopedDeployments` list from the store by matching `deployment.project_id` to the active project, so stale deployment state from a previous project cannot populate the list, counts, or selected detail view.
- `DeploymentWizard` fetches channels with the active project id, filters available channels by the same project id, and refuses deployment creation unless both an active project and deployment type are present.

### API And Backend

- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`
- Deployment list requests must include `project_id`; the route enforces project access before returning deployment records, including for global admins using the project-facing Integrations route. The admin dashboard remains the only intended global aggregation surface.
- Deployment detail, analytics, lifecycle, conversation list, conversation detail, and transcript routes also require the active `project_id`; an omitted project id returns 400, and a deployment id from another project resolves as 404 instead of silently using the record's owning project.
- By-id deployment routes authorize the requested active project before loading the deployment, then fetch by both deployment id and project id so stale cross-project ids cannot drive project-facing actions or existence checks.
- `deployment_service` helpers for deployment lookup, lifecycle, response handling, analytics, conversations, and transcripts also require `project_id`, so background jobs or future internal callers cannot accidentally resolve deployment or conversation records by global id alone.
- Deployment creation validates the project with the same active-project helper used by dispatch paths before writing a row; global admins cannot create deployments for missing or paused projects through the project-facing Integrations API.
- Deployment creation validates every `channel_instance_id` against the deployment `project_id` before storing the deployment, so a deployment in one project cannot route participant content through another project's messaging channel.
- Inbound channel processors attach participant messages only to same-project deployments that explicitly list the receiving channel instance; deployments with no channels are not a global fallback.
- Deployment activation and participant response handling reject paused projects before dispatching participant-facing work, updating adaptive conversation state, or reaching LLM-backed follow-up generation.
- Deployment response handling, conversations, transcripts, analytics, and overview counters all require the conversation/deployment/channel records to match the same project boundary before participant content or findings are read, updated, or summarized.
- Simulation and real-user benchmark deployment paths must carry active project scope on by-id lifecycle, response, analytics, conversation, delete, and channel cleanup calls, proving the same boundary exercised by the UI.

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/DeploymentsTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Deployments are project-owned integration records. Any agent, skill, LLM, MCP, channel, or deployment worker that uses deployment data must preserve the same active-project and authorization boundary before routing participant content or generated research artifacts.

## Tests And Verification

- `tests/test_deployments.py` exercises API-level project isolation for active-project creation, deployment channel ownership, deployment overview conversation counts, by-id active-project matching across detail/lifecycle/conversation/transcript routes, direct service-helper project scope enforcement, and cross-project response rejection.
- `tests/test_project_scope_contracts.py` asserts that `DeploymentsTab`, `DeploymentDashboard`, `ConversationTranscript`, and the deployment API client pass the active project id into list, detail, lifecycle, analytics, conversation, and transcript calls rather than falling back to global deployment ids.
- `tests/test_integration_simulation_scope.py` prevents simulation and real-user benchmark deployment calls from reintroducing unscoped by-id integration paths.

## Related Features

- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/architecture.md)
- [integrations.surveys](../../integrations/surveys/architecture.md)
- [integrations.messaging](../../integrations/messaging/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-767; CF-SPEC-60 / CF-773; CF-SPEC-62 / CF-793; CF-SPEC-75 / CF-964; CF-SPEC-82 / CF-1061; CF-SPEC-93 / CF-1184
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
