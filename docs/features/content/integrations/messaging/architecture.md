---
stable_id: integrations.messaging
title: Messaging Integrations
ui_path: Integrations > Messaging
audience: architecture
status: documented
related_features: ["integrations.overview", "integrations.deployment-dashboard"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/MessagingTab.tsx", "frontend/src/components/integrations/ChannelSetupWizard.tsx", "backend/app/api/routes/channels.py"]
api_references: ["backend/app/api/routes/channels.py", "backend/app/api/routes/webhooks.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Messaging Integrations Architecture

## Implementation Summary

Messaging connects external conversation channels such as team or participant messaging tools into Istara.

## Frontend Surface

- `frontend/src/components/integrations/MessagingTab.tsx`
- `frontend/src/components/integrations/ChannelSetupWizard.tsx`
- `backend/app/api/routes/channels.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/channels.py`
- `backend/app/api/routes/webhooks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/MessagingTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [integrations.overview](../../integrations/overview/architecture.md)
- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
