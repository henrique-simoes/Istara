---
stable_id: interfaces.handoff
title: Interface Handoff
ui_path: Interfaces > Handoff
audience: architecture
status: needs-verification
related_features: ["interfaces.screens", "findings.reports"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/interfaces/HandoffTab.tsx", "frontend/src/stores/interfacesStore.ts", "backend/app/api/routes/interfaces_integrations.py"]
api_references: ["backend/app/api/routes/interfaces_integrations.py"]
test_references: ["tests/test_interfaces.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-763
---

# Interface Handoff Architecture

## Implementation Summary

Handoff packages interface outputs into developer-facing specifications or exportable artifacts for the active project.

## Frontend Surface

- `frontend/src/components/interfaces/HandoffTab.tsx`
- `frontend/src/stores/interfacesStore.ts`
- `backend/app/api/routes/interfaces_integrations.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/interfacesStore.ts`

### API And Backend

- `backend/app/api/routes/interfaces_integrations.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interfaces/HandoffTab.tsx` and the UI navigation path recorded in the inventory.
- `GET /api/interfaces/handoff/briefs` requires an explicit `project_id`, checks project viewer access, and filters `DesignBrief.project_id` in the query.
- Handoff brief generation uses the request project's id; developer specs are authorized through the selected screen's project before returning screen content.
- Handoff briefs and developer specs include content-free `research_validity` summaries. Their source findings are rendered as accepted or provisional, and provisional sources must not be treated as report-ready research evidence.
- Developer specs read the same hydrated screen/source-finding state exposed by the Screens API, so a design handoff cannot silently strip the Research Spine status from generated or imported interface work.
- `HandoffTab` clears selected/expanded state when the active project changes and renders only briefs and screens that match the active project.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_interfaces.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [interfaces.screens](../../interfaces/screens/architecture.md)
- [findings.reports](../../findings/reports/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-763
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
