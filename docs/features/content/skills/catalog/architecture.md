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
test_references: ["tests/test_skills.py", "tests/test_project_scope_contracts.py", "tests/test_simulation_project_scope_contracts.py", "tests/simulation/lib/api-client.mjs", "tests/simulation/scenarios/06-skill-execution.mjs", "tests/simulation/scenarios/20-all-skills-comprehensive.mjs", "tests/simulation/scenarios/22-architecture-evaluation.mjs", "tests/simulation/scenarios/41-skill-creation.mjs", "tests/document_corpus/canonical/skill-coverage-map.json"]
last_verified: 2026-05-21
compass: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870; CF-SPEC-104 / CF-1309; CF-SPEC-116; CF-SPEC-123 / CF-1581
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
- Simulation skill catalog checks keep the global `/api/skills` definition list unchanged, but every skill health or proposal request in the harness includes the active simulation project id.
- When the simulation runner has deliberately entered maintenance mode, live skill execution checks record the backend's 409 deferral as expected test isolation instead of treating paused agent/LLM operations as product failure.
- Scenario 20 verifies registration and fixture coverage for the full skill catalog, then executes a deterministic bounded live subset by default; set `ISTARA_SCENARIO20_SKILL_LIMIT` to the current catalog size for a deliberate full live sweep.
- `tests/document_corpus/canonical/skill-coverage-map.json` maps the canonical UX research corpus to the current skill catalog so document-heavy skill tests can choose representative research material instead of inventing tiny one-off documents.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Skill health APIs require explicit `project_id` so one project's execution quality, failures, and pending updates are not exposed in another project.
- Skill execution is project content processing and must never fall back to a global project id or run against a paused project.
- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- `tests/test_skills.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_simulation_project_scope_contracts.py`
- `tests/simulation/lib/api-client.mjs`
- `tests/simulation/scenarios/06-skill-execution.mjs`
- `tests/simulation/scenarios/20-all-skills-comprehensive.mjs`
- `tests/simulation/scenarios/22-architecture-evaluation.mjs`
- `tests/simulation/scenarios/41-skill-creation.mjs`
- `tests/document_corpus/canonical/skill-coverage-map.json`

## Related Features

- [skills.proposals](../../skills/proposals/architecture.md)
- [agents.registry](../../agents/registry/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-68 / CF-870; CF-SPEC-104 / CF-1309; CF-SPEC-116; CF-SPEC-123 / CF-1581
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
