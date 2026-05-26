---
stable_id: findings.codebook
title: Findings Codebook
ui_path: Findings > Codebook
audience: architecture
status: documented
related_features: ["findings.evidence", "findings.review"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodebookViewer.tsx", "backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
api_references: ["backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
test_references: ["tests/test_codebooks.py", "tests/test_project_scope_contracts.py", "tests/test_research_validity_contract.py"]
last_verified: 2026-05-21
compass: CF-SPEC-78 / CF-1005; CF-SPEC-124 / CF-1590
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
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Codebook and code reads/mutations are project-content surfaces. They must reject stale ids from any other project with `404`, even when the same authenticated user can access both projects through another surface.

## Tests And Verification

- `tests/test_codebooks.py`
- `tests/test_project_scope_contracts.py`

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
