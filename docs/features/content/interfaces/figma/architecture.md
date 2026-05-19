---
stable_id: interfaces.figma
title: Configuration
ui_path: Interfaces > Configuration
audience: architecture
status: needs-verification
related_features: ["interfaces.screens", "integrations.overview"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/interfaces/FigmaTab.tsx", "frontend/src/components/interfaces/InterfacesOnboarding.tsx", "frontend/src/stores/interfacesStore.ts", "backend/app/api/routes/interfaces_common.py", "backend/app/api/routes/interfaces_integrations.py", "backend/app/models/interface_config.py", "backend/app/services/figma_service.py", "backend/app/services/stitch_service.py"]
api_references: ["backend/app/api/routes/interfaces_integrations.py"]
test_references: ["tests/test_interfaces.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-59 / CF-740; CF-SPEC-60 / CF-763
---

# Configuration Architecture

## Implementation Summary

The Configuration tab connects interface work with design-tool setup, including Figma-oriented import/export flows and Stitch-backed generation setup. Configuration is project-owned: a token or API key saved here belongs to the active project, not to a global process setting.

## Frontend Surface

- `frontend/src/components/interfaces/FigmaTab.tsx`
- `frontend/src/components/interfaces/InterfacesOnboarding.tsx`
- `frontend/src/stores/interfacesStore.ts`
- `backend/app/api/routes/interfaces_common.py`
- `backend/app/api/routes/interfaces_integrations.py`
- `backend/app/models/interface_config.py`
- `backend/app/services/figma_service.py`
- `backend/app/services/stitch_service.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/interfacesStore.ts`

### API And Backend

- `backend/app/api/routes/interfaces_integrations.py`
- `backend/app/models/interface_config.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interfaces/FigmaTab.tsx` behind the `Configuration` tab label, and the UI navigation path is recorded in the inventory.
- `tests/test_project_scope_contracts.py` guards the source-level tab-label contract so the project-facing Interfaces tab does not regress to the old `Figma` menu copy.
- Configuration actions require an active project in the UI and call project-scoped backend routes. Global admins still configure a concrete project; the route does not fall back to a global configuration path.
- Figma and Stitch secrets are stored on `ProjectInterfaceConfig` as encrypted per-project fields. The configure routes no longer mutate `settings.figma_api_token`, `settings.stitch_api_key`, or process environment values.
- Figma file helpers require `project_id`, check project access, and use the active project's Figma token before reading components or design-system data.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Stitch is reached through the Stitch MCP protocol with the active project's encrypted API key. It must never use a process-wide fallback for project-facing Interfaces flows.

## Tests And Verification

- `tests/test_interfaces.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [interfaces.screens](../../interfaces/screens/architecture.md)
- [integrations.overview](../../integrations/overview/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-59 / CF-740; CF-SPEC-60 / CF-763
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
