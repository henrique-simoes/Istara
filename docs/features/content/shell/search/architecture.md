---
stable_id: shell.search
title: Project Search
ui_path: Shell > Search
audience: architecture
status: documented
related_features: ["shell.navigation", "shell.keyboard-shortcuts"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/common/SearchModal.tsx", "frontend/src/lib/api.ts"]
api_references: ["backend/app/api/routes/findings.py"]
test_references: ["tests/test_project_scope_contracts.py", "tests/test_findings.py"]
last_verified: 2026-09-02
compass: CF-SPEC-60 / CF-772
---

# Project Search Architecture

## Implementation Summary

The shell exposes a command/search modal from the sidebar and keyboard shortcut so users can find findings inside the active project.

## Frontend Surface

- `frontend/src/components/layout/HomeClient.tsx`
- `frontend/src/components/common/SearchModal.tsx`
- `frontend/src/lib/api.ts`

## State, API, And Backend Contracts

### Stores

- `backend/app/api/routes/findings.py`

### API And Backend

- None recorded.

## Architecture Notes

- The feature is mounted through `frontend/src/components/layout/HomeClient.tsx` and the UI navigation path recorded in the inventory.
- Findings search does not fall back to global lists when no active project is selected. The modal waits for `activeProjectId`, then calls project-scoped findings list clients.
- Cross-project findings search remains available only through the explicit admin-only global findings search route used by admin/reporting surfaces.
- Project-scoped findings search combines document-RAG results with exact text matches from manual nuggets, facts, insights, and recommendations so manually-created artifacts remain discoverable when they are not embedded. Search does not alter their provisional research-validity state.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Findings results are project content. The search modal and findings list API clients require an authorized active project before reading nuggets, facts, insights, or recommendations.

## Tests And Verification

- `tests/test_project_scope_contracts.py`
- `tests/test_findings.py`

## Related Features

- [shell.navigation](../../shell/navigation/architecture.md)
- [shell.keyboard-shortcuts](../../shell/keyboard-shortcuts/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-772
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
