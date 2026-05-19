---
stable_id: meta.hyperagent
title: Meta-Agent
ui_path: Meta-Agent
audience: architecture
status: documented
related_features: ["settings.governed-evolution", "agents.registry"]
related_glossary: ["a2a", "compass-forge"]
code_references: ["frontend/src/components/meta/MetaHyperagentView.tsx", "backend/app/api/routes/meta_hyperagent.py", "backend/app/core/meta_hyperagent.py", "backend/app/skills/skill_usage.py"]
api_references: ["backend/app/api/routes/meta_hyperagent.py"]
test_references: ["tests/test_meta_hyperagent.py", "tests/test_project_scope_contracts.py", "tests/test_security_benchmark.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Meta-Agent Architecture

## Implementation Summary

The Meta-Agent surface exposes the meta-hyperagent system for inspecting or governing higher-level agentic improvement behavior inside the active project.

## Frontend Surface

- `frontend/src/components/meta/MetaHyperagentView.tsx`
- `backend/app/api/routes/meta_hyperagent.py`
- `backend/app/core/meta_hyperagent.py`
- `backend/app/skills/skill_usage.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/meta_hyperagent.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/meta/MetaHyperagentView.tsx` and the UI navigation path recorded in the inventory.
- All project-facing Meta-Hyperagent status, proposals, observations, variants, toggle, and mutation routes require an explicit `project_id`, verify the project is visible to the admin subject, and filter persisted records by exact project id.
- The observation loop is no longer started globally during application startup. It starts only from a project-scoped UI/API request and records its active project id.
- Skill usage stats now maintain per-project counters so Meta-Hyperagent skill-selection analysis does not infer proposals from another project's execution history.
- Self-evolution tuning proposals require project-local learning evidence. An empty project, or a project with only global/other-project learning history, must not generate threshold-lowering proposals.
- Confirmed Meta-Hyperagent overrides are persisted under project-specific override buckets instead of process-wide override keys.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, active project ids, and review surfaces before changing assumptions.
- Meta-Hyperagent WebSocket proposal broadcasts include `project_id` so live updates are delivered only to connections scoped to the same active project.

## Tests And Verification

- `tests/test_meta_hyperagent.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_security_benchmark.py`

## Related Features

- [settings.governed-evolution](../../settings/governed-evolution/architecture.md)
- [agents.registry](../../agents/registry/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
