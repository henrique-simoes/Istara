---
stable_id: integrations.deployment-dashboard
title: Deployment Dashboard
ui_path: Integrations > Deployments > Dashboard
audience: architecture
status: documented
related_features: ["integrations.deployments", "findings.evidence"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/integrations/DeploymentDashboard.tsx", "backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
api_references: ["backend/app/api/routes/deployments.py", "backend/app/services/deployment_service.py"]
test_references: ["tests/test_deployments.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-767
---

# Deployment Dashboard Architecture

## Implementation Summary

The deployment dashboard has sub-tabs for live status, questions, participants, findings, channels, and timeline activity.

## Frontend Surface

- `frontend/src/components/integrations/DeploymentDashboard.tsx`
- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/deployments.py`
- `backend/app/services/deployment_service.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/DeploymentDashboard.tsx` and the UI navigation path recorded in the inventory.
- Conversation detail, transcript, response handling, and analytics routes verify that the conversation and deployment belong to the same project before exposing or updating participant content.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Adaptive follow-up generation routes through the deployment's project id, and donated or routed compute must receive only content from projects the requester is authorized to use.

## Tests And Verification

- `tests/test_deployments.py`

## Related Features

- [integrations.deployments](../../integrations/deployments/architecture.md)
- [findings.evidence](../../findings/evidence/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-767
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
