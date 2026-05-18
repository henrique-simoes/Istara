---
stable_id: skills.create
title: Create Skill
ui_path: Skills > Create
audience: architecture
status: needs-verification
related_features: ["skills.catalog", "agents.create"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/skills/SkillsView.tsx", "backend/app/api/routes/skills.py"]
api_references: ["backend/app/api/routes/skills.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Create Skill Architecture

## Implementation Summary

Create Skill supports adding or configuring a new skill surface from inside Istara.

## Frontend Surface

- `frontend/src/components/skills/SkillsView.tsx`
- `backend/app/api/routes/skills.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/skills.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/skills/SkillsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [skills.catalog](../../skills/catalog/architecture.md)
- [agents.create](../../agents/create/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
