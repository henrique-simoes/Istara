---
stable_id: settings.project
title: Project Settings
ui_path: Project Settings
audience: architecture
status: documented
related_features: ["shell.projects", "settings.general"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/ProjectSettingsView.tsx", "frontend/src/components/settings/AgenticCoreSection.tsx", "frontend/src/components/layout/Sidebar.tsx", "frontend/src/lib/types.ts", "frontend/src/lib/utils.ts", "backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py", "backend/app/api/routes/autoresearch.py", "backend/app/api/routes/loops.py", "backend/app/api/routes/meta_hyperagent.py", "backend/app/api/routes/skills.py", "backend/app/core/agent_lifecycle.py", "backend/app/core/agent_execution.py", "backend/app/core/agentic/dispatcher.py", "backend/app/core/autoresearch_engine.py", "backend/app/core/self_evolution.py", "backend/app/core/sub_agent_worker.py", "backend/app/core/scheduler.py", "backend/app/core/file_watcher.py"]
api_references: ["backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py"]
test_references: ["tests/test_tasks.py", "tests/test_loops.py", "tests/test_autoresearch.py", "tests/test_agent_learning_scope.py", "tests/test_meta_hyperagent.py", "tests/test_skills.py", "tests/test_file_watcher_config.py", "tests/test_project_rbac.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w8_embeddings_gateway.py", "tests/simulation/scenarios/79-engine-selector.mjs"]
last_verified: 2026-07-22
compass: CF-SPEC-55 / CF-684; CF-SPEC-72 / CF-927; CF-SPEC-8 (Pi replacement W8 engine selector)
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

### Per-Project Agent Engine Selector (Pi Replacement W8)

- `ProjectUpdate.agentic_engine` (`backend/app/api/routes/projects.py`) accepts
  `legacy` or any `PI_ENGINE_VALUES` member; `""`/`null` means the project
  inherits the global default engine, and any other value is rejected with
  422. `_project_response`/`ProjectResponse` expose the stored
  `agentic_engine` so the frontend can render the current selection.
- This is the project-level engine pin the W1 dispatcher already reads at
  level-3 resolution (`backend/app/core/agentic/dispatcher.py`): per-call
  override first, then the `x-istara-agent-engine` header, then the project
  `agentic_engine` setting, then `settings.agentic_engine_default` (see
  [chat.model-controls](../../chat/model-controls/architecture.md) for the
  full precedence).
- Project list/detail responses also expose `global_agentic_engine`, a
  normalized `pi`/`legacy` view of the current global default. The frontend
  uses it for inherited project badges and labels, so an inherited project
  reflects the real default instead of a hard-coded Legacy label.
- On the frontend, `frontend/src/lib/types.ts` adds
  `Project.agentic_engine?: string | null` and `frontend/src/lib/utils.ts`
  adds `agentEngineLabel()` (Pi for `pi`, `pi-candidate`, `pi-replacement`,
  and `deepseek-pi`; Legacy otherwise). `AgenticCoreSection` is the shared
  first-class comparison surface used by global Settings and Project Settings;
  it replaces the former compact selector/status-grid row and explains each
  engine before showing the provisional benchmark snapshot.
  `frontend/src/components/layout/Sidebar.tsx` shows a per-project engine
  indicator badge (`aria-label="Engine: Pi|Legacy"`) next to the phase
  subtitle, and `frontend/src/components/settings/ProjectSettingsView.tsx`
  adds an "Agent Engine" section: a `role="radiogroup"`
  (`aria-label="Agent engine"`) with explicit Pi / Istara engine buttons for
  project admins — saved through `updateProject(id, { agentic_engine })` —
  and a read-only badge for non-admins. The three choices are "Inherit global
  default", `legacy` (Istara), and `pi` (Pi).
- **Engine buttons carry evidence-backed, provisional comparative summaries
  (W3).** `frontend/src/lib/modelCatalog.ts` exports
  `ENGINE_COMPARATIVE_SUMMARIES`, one entry per engine with a plain-language
  description, best-for guidance, benchmark rows, and a concise summary
  grounded in the accepted Pi-vs-Istara benchmark bundle
  `comparison-Istara-pi/reports/20260801T010602Z/scorecard.json` (verdict
  `no_significant_difference`: no judged axis reaches significance at 95%
  CI). Each summary lists its evidence provenance and is rendered with a
  "Provisional" badge — comparative model prose is never presented as
  accepted research evidence (Research Spine contract), and the selector
  never fabricates performance claims.
- **Embedding identity policy.** Both engines share one canonical embedding
  model (`embed_model`, exposed as safe metadata in the project response —
  model name only, never an endpoint/URL/key). Switching engines never
  changes the embedding space; cached vectors are validated against the
  engine's known embedding dimension for that model (learned from startup
  probes and provider responses), so an entry written under a different
  embedding model/dimension is discarded and re-embedded instead of reaching
  retrieval.
- **Accessibility contract.** The shared section is a native radiogroup: every
  option is a real radio input (keyboard arrow-key navigation, `aria-checked`
  from the native control), the group is `aria-labelledby` the section
  heading, each option is a labelled `<label>` with a visible `:focus-visible`
  ring, and the embedding identity line is part of the explanatory content.
  Controls use a 44px floor, stable borders, and explicit loading/error states.
  The read-only badge keeps `aria-label="Agent engine"` for non-admins.
- Simulation scenario `tests/simulation/scenarios/79-engine-selector.mjs`
  (registered in `tests/simulation/lib/scenario-registry.mjs`) walks the
  radiogroup, the comparative-summary provenance, and the badge end to end.

## Architecture Notes

- The feature is mounted through `frontend/src/components/settings/ProjectSettingsView.tsx` and the UI navigation path recorded in the inventory.
- Paused projects may still keep backlog tasks, scheduled tasks, and watched-folder configuration, but those surfaces must not dispatch work until the project is unpaused.
- Paused projects also block project-content skill execution/planning, autoresearch runs, self-evolution scans/promotions, Meta-Hyperagent starts/applies, loop resume, and schedule creation or re-enable paths.
- The pause route performs a project-owned background shutdown pass: it stops a running Meta-Hyperagent loop for that project, requests stop on an AutoResearch loop owned by that project, and stops active messaging channel adapters for that project.
- Project Settings lists pending permission requests with `project_id=activeProjectId` and sends the same active project id when approving or rejecting, while the backend resolves request ids by both request id and project id before authorization or mutation.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent, scheduler, file watcher, skill proposal, autoresearch, self-evolution, Meta-Hyperagent, messaging integration, MCP, and skill execution side effects must treat `Project.is_paused` as a hard dispatch guard.

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
- `tests/pi_production/test_w8_embeddings_gateway.py` verifies `ProjectUpdate.agentic_engine` validation (accepted engine values, inherit-default semantics, 422 on unknown values).
- `tests/simulation/scenarios/79-engine-selector.mjs` walks the per-project engine selector and the Sidebar engine badge.
- Regenerate and validate the machine manifests and static site with `python scripts/feature_docs.py --seed-missing --generate-site --check`.

## Related Features

- [shell.projects](../../shell/projects/architecture.md)
- [settings.general](../../settings/general/architecture.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-55 / CF-684; CF-SPEC-72 / CF-927; CF-SPEC-8 (Pi replacement W8 per-project agent engine selector)
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
