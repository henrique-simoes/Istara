---
stable_id: findings.codebook
title: Findings Codebook
ui_path: Findings > Codebook
audience: architecture
status: documented
related_features: ["findings.evidence", "findings.review"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodebookViewer.tsx", "backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py", "backend/app/services/research_validity_service.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
test_references: ["tests/test_codebooks.py", "tests/test_project_scope_contracts.py", "tests/test_research_validity_contract.py", "tests/pi_production/test_w7_validation.py"]
last_verified: 2026-07-22
compass: CF-SPEC-8 / FIX-pi-full-20260720-w7-REVIEW-r1-docs; CF-SPEC-78 / CF-1005; CF-SPEC-124 / CF-1590
---

# Findings Codebook Architecture

## Implementation Summary

The Codebook tab surfaces qualitative coding structures and codebook versions associated with project findings. Project-facing codebook and code by-id routes require the active project id and load records by both record id and project id before returning or mutating data.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `frontend/src/components/findings/CodebookViewer.tsx`
- `backend/app/api/routes/codebooks.py`
- `backend/app/api/routes/codebook_versions.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/codebooks.py`
- `backend/app/api/routes/codebook_versions.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- Creating the first project codebook version records a content-free `codebook.freeze` telemetry event; later versions record `codebook.revise`. The span carries project and codebook-version handles only, so governed codebook lifecycle audits do not store code definitions, examples, prompts, or source quotes in telemetry.
- W7's governed dual-coder path is selected when the dispatcher resolves the project to the Pi engine. It reads the persisted endpoint catalog through `PiModelManager` without loading a model, requests distinct endpoint identities, and dispatches each coder with `structured(purpose="validity.coder")` pinned to that coder's exact `endpoint_id`. The coding schema stays inside the Pi forced-tool subset.
- Reliability preserves endpoint identity as the rater identity. Same-model endpoints remain distinct coders when their endpoint identities differ; model-name deduplication is not a substitute for endpoint identity. If the catalog cannot provide the requested distinct coders, selection fails closed, no coder dispatch occurs, route evidence records the failure, and the coding run remains `blocked` rather than switching engines or fabricating agreement.
- The resulting code applications remain provisional until reliability, reconciliation, and human review gates accept them. A blocked or insufficient coding run cannot promote findings into reportable evidence.
- Embedding dispatch remains a legacy-plane responsibility until W8. This W7 structured-coder migration does not authorize an embedding migration.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Codebook and code reads/mutations are project-content surfaces. They must reject stale ids from any other project with `404`, even when the same authenticated user can access both projects through another surface.
- Rollback is reversible: select the legacy project engine and the coders are served by the dispatcher's permanent legacy executor over the project-authorized registry servers. W9 retired the preserved per-site `coder.node` runner, so the dispatcher path is the only path; engine choice no longer changes the code path.

## Tests And Verification

- `tests/test_codebooks.py`
- `tests/test_project_scope_contracts.py`
- `tests/pi_production/test_w7_validation.py` — Pi/legacy selection, exact endpoint pinning, same-model distinct endpoint reliability, schema constraints, and fail-closed blocked coding runs.

## Related Features

- [findings.evidence](../../findings/evidence/architecture.md)
- [findings.review](../../findings/review/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Compass Evidence

- Spec/task: CF-SPEC-78 / CF-1005
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
