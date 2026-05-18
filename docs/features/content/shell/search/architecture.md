---
stable_id: shell.search
title: Global Search
ui_path: Shell > Search
audience: architecture
status: needs-verification
related_features: ["shell.navigation", "shell.keyboard-shortcuts"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/common/SearchModal.tsx"]
api_references: []
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Global Search Architecture

## Implementation Summary

The shell exposes a command/search modal from the sidebar and keyboard shortcut so users can find navigable work surfaces and project objects.

## Frontend Surface

- `frontend/src/components/layout/HomeClient.tsx`
- `frontend/src/components/common/SearchModal.tsx`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- None recorded.

## Architecture Notes

- The feature is mounted through `frontend/src/components/layout/HomeClient.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [shell.navigation](../../shell/navigation/architecture.md)
- [shell.keyboard-shortcuts](../../shell/keyboard-shortcuts/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
