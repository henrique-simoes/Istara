---
stable_id: settings.project
title: Project Settings
ui_path: Project Settings
audience: architecture
status: documented
related_features: ["shell.projects", "settings.general"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/ProjectSettingsView.tsx", "backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py", "backend/app/api/routes/autoresearch.py", "backend/app/api/routes/loops.py", "backend/app/api/routes/meta_hyperagent.py", "backend/app/api/routes/skills.py", "backend/app/core/agent_lifecycle.py", "backend/app/core/agent_execution.py", "backend/app/core/autoresearch_engine.py", "backend/app/core/self_evolution.py", "backend/app/core/sub_agent_worker.py", "backend/app/core/scheduler.py", "backend/app/core/file_watcher.py"]
api_references: ["backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py"]
test_references: ["tests/test_tasks.py", "tests/test_loops.py", "tests/test_autoresearch.py", "tests/test_agent_learning_scope.py", "tests/test_meta_hyperagent.py", "tests/test_skills.py", "tests/test_file_watcher_config.py", "tests/test_project_rbac.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-55 / CF-684; CF-SPEC-72 / CF-927
---

# Project Settings Architecture

## Implementation Summary

Project Settings configure project-specific metadata and operational preferences separate from global system settings. Pausing a project is an execution boundary: agent pickers, direct execution, sub-agent workers, schedules, and watched-folder ingestion defer work for paused projects instead of reaching LLM, embedding, or skill-improvement paths. Project-admin permission request queues and review actions are also active-project-bound, so stale request ids from another project cannot be reviewed from the current project's settings.

## Frontend Surface

- `frontend/src/components/settings/ProjectSettingsView.tsx`
- `backend/app/api/routes/projects.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/projects.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/settings/ProjectSettingsView.tsx` and the UI navigation path recorded in the inventory.
- Paused projects may still keep backlog tasks, scheduled tasks, and watched-folder configuration, but those surfaces must not dispatch work until the project is unpaused.
- Paused projects also block project-content skill execution/planning, autoresearch runs, self-evolution scans/promotions, Meta-Hyperagent starts/applies, loop resume, and schedule creation or re-enable paths.
- Project Settings lists pending permission requests with `project_id=activeProjectId` and sends the same active project id when approving or rejecting, while the backend resolves request ids by both request id and project id before authorization or mutation.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent, scheduler, file watcher, skill proposal, autoresearch, self-evolution, Meta-Hyperagent, MCP, and skill execution side effects must treat `Project.is_paused` as a hard dispatch guard.

## Tests And Verification

- `tests/test_tasks.py`
- `tests/test_loops.py`
- `tests/test_autoresearch.py`
- `tests/test_agent_learning_scope.py`
- `tests/test_meta_hyperagent.py`
- `tests/test_skills.py`
- `tests/test_file_watcher_config.py`
- `tests/test_project_rbac.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [shell.projects](../../shell/projects/architecture.md)
- [settings.general](../../settings/general/architecture.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-55 / CF-684; CF-SPEC-72 / CF-927
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
