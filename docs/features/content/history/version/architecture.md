---
stable_id: history.version
title: Version History
ui_path: History
audience: architecture
status: documented
related_features: ["backup.view", "chat.sessions", "loops.history"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/common/VersionHistory.tsx", "backend/app/core/versioning.py"]
api_references: ["backend/app/api/routes/projects.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Version History Architecture

## Implementation Summary

History lists project or artifact version events for traceability and recovery.

## Frontend Surface

- `frontend/src/components/common/VersionHistory.tsx`
- `backend/app/core/versioning.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/projects.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/VersionHistory.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [backup.view](../../backup/view/architecture.md)
- [chat.sessions](../../chat/sessions/architecture.md)
- [loops.history](../../loops/history/architecture.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
