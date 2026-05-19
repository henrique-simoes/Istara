---
stable_id: shell.keyboard-shortcuts
title: Keyboard Shortcuts
ui_path: Shell > Keyboard Shortcuts
audience: architecture
status: documented
related_features: ["shell.search", "shell.navigation"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/common/KeyboardShortcuts.tsx"]
api_references: []
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Keyboard Shortcuts Architecture

## Implementation Summary

HomeClient wires global shortcuts for search, view switching, shortcut help, and right-panel toggling.

## Frontend Surface

- `frontend/src/components/layout/HomeClient.tsx`
- `frontend/src/components/common/KeyboardShortcuts.tsx`

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

- [shell.search](../../shell/search/architecture.md)
- [shell.navigation](../../shell/navigation/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
