---
stable_id: shell.navigation
title: Application Navigation
ui_path: Shell > Navigation
audience: architecture
status: documented
related_features: ["shell.projects", "shell.search", "shell.keyboard-shortcuts", "shell.onboarding"]
related_glossary: ["wcag", "compass-forge"]
code_references: ["frontend/src/lib/navigation.ts", "frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/layout/Sidebar.tsx", "frontend/src/components/layout/MobileNav.tsx"]
api_references: []
test_references: ["frontend/src/lib/navigation.test.ts"]
last_verified: 2026-09-01
compass: CF-SPEC-53 / CF-657
---

# Application Navigation Architecture

## Implementation Summary

The main shell organizes Istara into primary, secondary, utility, and mobile navigation surfaces and routes each selected view into the mounted work area.

## Frontend Surface

- `frontend/src/lib/navigation.ts`
- `frontend/src/components/layout/HomeClient.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/MobileNav.tsx`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`
- `frontend/src/stores/projectStore.ts`

### API And Backend

- None recorded.

## Architecture Notes

- The feature is mounted through `frontend/src/lib/navigation.ts` and the UI navigation path recorded in the inventory.
- Role-gated entries are filtered before rendering in both desktop and mobile shells. In particular, `primaryNavItemsForRole` keeps researcher-only Loops out of viewer navigation while preserving it for researcher and admin roles.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `frontend/src/lib/navigation.test.ts` verifies role-specific primary navigation, including the viewer Loops exclusion.

## Related Features

- [shell.projects](../../shell/projects/architecture.md)
- [shell.search](../../shell/search/architecture.md)
- [shell.keyboard-shortcuts](../../shell/keyboard-shortcuts/architecture.md)
- [shell.onboarding](../../shell/onboarding/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)
- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
