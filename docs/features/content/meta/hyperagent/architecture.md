---
stable_id: meta.hyperagent
title: Meta-Agent
ui_path: Meta-Agent
audience: architecture
status: documented
related_features: ["settings.governed-evolution", "agents.registry"]
related_glossary: ["a2a", "compass-forge"]
code_references: ["frontend/src/components/meta/MetaHyperagentView.tsx", "backend/app/api/routes/meta_hyperagent.py", "backend/app/core/meta_hyperagent.py"]
api_references: ["backend/app/api/routes/meta_hyperagent.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Meta-Agent Architecture

## Implementation Summary

The Meta-Agent surface exposes the meta-hyperagent system for inspecting or governing higher-level agentic improvement behavior.

## Frontend Surface

- `frontend/src/components/meta/MetaHyperagentView.tsx`
- `backend/app/api/routes/meta_hyperagent.py`
- `backend/app/core/meta_hyperagent.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/meta_hyperagent.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/meta/MetaHyperagentView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [settings.governed-evolution](../../settings/governed-evolution/architecture.md)
- [agents.registry](../../agents/registry/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
