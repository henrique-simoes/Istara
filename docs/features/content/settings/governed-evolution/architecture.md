---
stable_id: settings.governed-evolution
title: Governed Evolution
ui_path: Settings > Governed Evolution
audience: architecture
status: documented
related_features: ["meta.hyperagent", "quality.dashboard"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/GovernedEvolutionView.tsx", "frontend/src/lib/improvementGovernanceApi.ts", "frontend/src/lib/dgmhArchiveApi.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/improvement_governance.py", "backend/app/api/routes/dgmh_archive.py", "backend/app/api/routes/reasoning_bank.py", "backend/app/core/improvement_governance.py", "backend/app/core/dgmh_archive.py", "backend/app/core/reasoning_bank.py"]
api_references: ["backend/app/api/routes/improvement_governance.py", "backend/app/api/routes/dgmh_archive.py", "backend/app/api/routes/reasoning_bank.py"]
test_references: ["tests/test_improvement_governance.py", "tests/test_dgmh_archive.py", "tests/test_reasoning_bank.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Governed Evolution Architecture

## Implementation Summary

Governed Evolution displays project-scoped proposals, archive variants, reasoning memories, and contract information for controlled system self-improvement.

## Frontend Surface

- `frontend/src/components/settings/GovernedEvolutionView.tsx`
- `frontend/src/lib/improvementGovernanceApi.ts`
- `frontend/src/lib/dgmhArchiveApi.ts`
- `frontend/src/lib/api.ts`
- `backend/app/api/routes/improvement_governance.py`
- `backend/app/api/routes/dgmh_archive.py`
- `backend/app/api/routes/reasoning_bank.py`
- `backend/app/core/improvement_governance.py`
- `backend/app/core/dgmh_archive.py`
- `backend/app/core/reasoning_bank.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/improvement_governance.py`
- `backend/app/api/routes/dgmh_archive.py`
- `backend/app/api/routes/reasoning_bank.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/settings/GovernedEvolutionView.tsx` and the UI navigation path recorded in the inventory.
- The view does not fetch governed evolution data without an active project. Proposal, archive, and ReasoningBank requests pass the active `project_id`; backend routes reject missing project scope and verify that the project exists before returning project content.
- Proposal and archive action routes bind the record id to the same `project_id` supplied by the UI, so approvals, sandbox evaluations, applies, reverts, and quarantines cannot act on records from another project.
- ReasoningBank retrieval through this API excludes global memories when a project scope is supplied, preventing project-facing prompt context from mixing with unscoped traces.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Governed evolution, DGM-H archive, and ReasoningBank are agentic governance surfaces. They remain admin-only, but this project-facing settings surface still requires an explicit active project; cross-project aggregation belongs to dedicated admin reporting surfaces.

## Tests And Verification

- `tests/test_improvement_governance.py`
- `tests/test_dgmh_archive.py`
- `tests/test_reasoning_bank.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [meta.hyperagent](../../meta/hyperagent/architecture.md)
- [quality.dashboard](../../quality/dashboard/architecture.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
