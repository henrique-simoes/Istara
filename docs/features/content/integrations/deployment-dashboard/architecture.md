---
stable_id: integrations.deployment-dashboard
title: Deployment Dashboard
ui_path: Integrations > Deployments > Dashboard
audience: architecture
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentDashboard.tsx", "frontend/src/components/integrations/ConversationTranscript.tsx", "frontend/src/lib/api.ts", "backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
api_references: ["backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
test_references: ["tests/test_deployments.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-767; CF-SPEC-60 / CF-773
---

# Deployment Dashboard Architecture

## Implementation Summary

The deployment dashboard has sub-tabs for live status, questions, participants, findings, channels, and timeline activity.

## Frontend Surface

- `frontend/src/components/integrations/DeploymentDashboard.tsx`
- `frontend/src/components/integrations/ConversationTranscript.tsx`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`
- `DeploymentDashboard` uses the selected deployment's `project_id` when loading analytics and conversations and when invoking lifecycle actions, so a stale deployment id cannot open or mutate another active project's deployment.
- `ConversationTranscript` receives the same project id and sends it to the transcript API before participant messages are read.

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/DeploymentDashboard.tsx` and the UI navigation path recorded in the inventory.
- Deployment detail, lifecycle, conversation detail, transcript, response handling, and analytics routes require the caller's active project id and verify that the conversation and deployment belong to that project before exposing or updating participant content.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Adaptive follow-up generation routes through the deployment's project id, and donated or routed compute must receive only content from projects the requester is authorized to use.

## Tests And Verification

- `tests/test_deployments.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [integrations.deployments](../../integrations/deployments/architecture.md)
- [findings.evidence](../../findings/evidence/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-767; CF-SPEC-60 / CF-773
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
