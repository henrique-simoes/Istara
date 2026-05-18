---
stable_id: interfaces.figma
title: Configuration
ui_path: Interfaces > Configuration
audience: architecture
status: needs-verification
related_features: ["interfaces.screens", "integrations.overview"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/interfaces/FigmaTab.tsx", "backend/app/api/routes/interfaces_integrations.py"]
api_references: ["backend/app/api/routes/interfaces_integrations.py"]
test_references: ["tests/test_project_scope_contracts.py"]
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657; CF-SPEC-59 / CF-740
---

# Configuration Architecture

## Implementation Summary

The Configuration tab connects interface work with design-tool setup, including Figma-oriented import or export flows.

## Frontend Surface

- `frontend/src/components/interfaces/FigmaTab.tsx`
- `backend/app/api/routes/interfaces_integrations.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/interfacesStore.ts`

### API And Backend

- `backend/app/api/routes/interfaces_integrations.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interfaces/FigmaTab.tsx` behind the `Configuration` tab label, and the UI navigation path is recorded in the inventory.
- `tests/test_project_scope_contracts.py` guards the source-level tab-label contract so the project-facing Interfaces tab does not regress to the old `Figma` menu copy.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_project_scope_contracts.py`

## Related Features

- [interfaces.screens](../../interfaces/screens/architecture.md)
- [integrations.overview](../../integrations/overview/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-59 / CF-740; local UI copy update 2026-05-18
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
