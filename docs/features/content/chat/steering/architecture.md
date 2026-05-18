---
stable_id: chat.steering
title: Chat Steering
ui_path: Chat > Steering
audience: architecture
status: documented
related_features: ["chat.overview", "context.editor"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SteeringInput.tsx", "backend/app/api/routes/steering.py"]
api_references: ["backend/app/api/routes/steering.py"]
test_references: ["tests/test_steering_api.py"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat Steering Architecture

## Implementation Summary

Steering controls collect lightweight user guidance that can shape downstream assistant behavior and project context.

## Frontend Surface

- `frontend/src/components/common/SteeringInput.tsx`
- `backend/app/api/routes/steering.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/steering.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/SteeringInput.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_steering_api.py`

## Related Features

- [chat.overview](../../chat/overview/architecture.md)
- [context.editor](../../context/editor/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
