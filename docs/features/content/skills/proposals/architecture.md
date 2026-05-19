---
stable_id: skills.proposals
title: Skill Proposals
ui_path: Skills > Proposals
audience: architecture
status: documented
related_features: ["skills.catalog", "agents.proposals"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/skills/SkillsView.tsx", "backend/app/api/routes/skills.py"]
api_references: ["backend/app/api/routes/skills.py"]
test_references: ["tests/test_skills.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870
---

# Skill Proposals Architecture

## Implementation Summary

Skill proposal flows present candidate tool or capability changes for review before they are adopted.

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
- Skill update proposals are stored with their source `project_id`; list, approve, and reject APIs require the active project and return 404 for proposals from another project.
- Approving skill update or skill creation proposals requires an active, unpaused project. Rejecting old proposals can still happen while a project is paused so stale improvement work can be cleared without dispatching new processing.
- `SkillsView` clears and reloads proposal state when the active project changes so self-evolution review never carries proposals from a previous project.
- Skill execution health is tracked per project for proposal review. Low utility no longer auto-deprecates or mutates a global skill definition from one project's execution history.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent execution passes the task project into skill improvement proposals and governed-evolution evidence, preserving project authorization for review.
- Proposal generation and approval are treated as project content processing; paused projects must not create new skill improvement work from background execution or apply project-specific proposals into the shared catalog.
- Project-scoped low-utility warnings are broadcast only to the owning project; global skill lifecycle changes require explicit governed review rather than background mutation.
- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- `tests/test_skills.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [skills.catalog](../../skills/catalog/architecture.md)
- [agents.proposals](../../agents/proposals/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
