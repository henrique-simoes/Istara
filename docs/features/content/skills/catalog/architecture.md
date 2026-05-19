---
stable_id: skills.catalog
title: Skills Catalog
ui_path: Skills > Catalog
audience: architecture
status: documented
related_features: ["skills.proposals", "agents.registry"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/skills/SkillsView.tsx", "backend/app/api/routes/skills.py", "backend/app/core/agent_skill_tools.py"]
api_references: ["backend/app/api/routes/skills.py"]
test_references: ["tests/test_skills.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870
---

# Skills Catalog Architecture

## Implementation Summary

The Skills catalog lists available capabilities agents can use or propose for research workflows.

## Frontend Surface

- `frontend/src/components/skills/SkillsView.tsx`
- `backend/app/api/routes/skills.py`
- `backend/app/core/agent_skill_tools.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/skills.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/skills/SkillsView.tsx` and the UI navigation path recorded in the inventory.
- Skill definitions remain the shared catalog, while health, usage, and proposal badges are fetched with the active project and reset on project changes.
- Skill execution and planning require an active, unpaused project before the agent is invoked, so paused projects cannot trigger LLM/skill work through the catalog surface.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Skill health APIs require explicit `project_id` so one project's execution quality, failures, and pending updates are not exposed in another project.
- Skill execution is project content processing and must never fall back to a global project id or run against a paused project.
- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- `tests/test_skills.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [skills.proposals](../../skills/proposals/architecture.md)
- [agents.registry](../../agents/registry/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
