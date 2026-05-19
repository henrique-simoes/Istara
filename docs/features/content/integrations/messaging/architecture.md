---
stable_id: integrations.messaging
title: Messaging Integrations
ui_path: Integrations > Messaging
audience: architecture
status: documented
related_features: ["integrations.overview", "integrations.deployment-dashboard"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/integrations/MessagingTab.tsx", "frontend/src/components/integrations/ChannelInstanceCard.tsx", "frontend/src/components/integrations/ChannelMessagesPanel.tsx", "frontend/src/components/integrations/ChannelConversationsPanel.tsx", "frontend/src/components/integrations/ChannelSetupWizard.tsx", "backend/app/api/routes/channels.py", "backend/app/api/routes/webhooks.py", "backend/app/services/channel_service.py", "backend/app/services/inbound_processor.py"]
api_references: ["backend/app/api/routes/channels.py", "backend/app/api/routes/webhooks.py"]
test_references: ["tests/test_channels.py", "tests/test_channel_inbound.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-762; CF-SPEC-60 / CF-773; CF-SPEC-60 / CF-776
---

# Messaging Integrations Architecture

## Implementation Summary

Messaging connects external conversation channels such as team or participant messaging tools into Istara.

## Frontend Surface

- `frontend/src/components/integrations/MessagingTab.tsx`
- `frontend/src/components/integrations/ChannelInstanceCard.tsx`
- `frontend/src/components/integrations/ChannelMessagesPanel.tsx`
- `frontend/src/components/integrations/ChannelConversationsPanel.tsx`
- `frontend/src/components/integrations/ChannelSetupWizard.tsx`
- `backend/app/api/routes/channels.py`
- `backend/app/api/routes/webhooks.py`
- `backend/app/services/channel_service.py`
- `backend/app/services/inbound_processor.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/integrationsStore.ts`

### API And Backend

- `backend/app/api/routes/channels.py`
- `backend/app/api/routes/webhooks.py`
- `backend/app/services/channel_service.py`
- `backend/app/services/inbound_processor.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/integrations/MessagingTab.tsx` and the UI navigation path recorded in the inventory.
- `MessagingTab` passes the active project into channel listing, clears stale channel state during project changes, and renders only channel records whose `project_id` matches the active project.
- Channel cards, setup testing, message history, and conversation detail panels pass the active project into every channel detail, lifecycle, health, message, conversation, and cleanup call so stale channel ids from another project cannot be dereferenced.
- `backend/app/api/routes/channels.py` requires an explicit `project_id` for project-facing channel lists and detail routes, verifies the channel instance belongs to that same project even for global admins, and enforces project viewer access for reads; channel creation and lifecycle mutations remain project-admin operations.
- `backend/app/services/channel_service.py` filters message and conversation rows by the same project and stamps new recorded messages with the owning channel instance project when a caller does not already provide one.
- Inbound message routing resolves active deployments only within the receiving channel instance's project and only when the deployment explicitly lists that channel instance, so an active deployment from another project or an unbound deployment cannot receive participant content.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- `tests/test_channels.py`
- `tests/test_channel_inbound.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [integrations.overview](../../integrations/overview/architecture.md)
- [integrations.deployment-dashboard](../../integrations/deployment-dashboard/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-762; CF-SPEC-60 / CF-773; CF-SPEC-60 / CF-776
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
