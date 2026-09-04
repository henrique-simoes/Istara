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
test_references: ["tests/test_codebooks.py", "tests/test_project_scope_contracts.py", "tests/test_research_validity_contract.py", "tests/pi_production/test_w7_validation.py", "tests/pi_production/test_w7_pi_manager_integration.py"]
last_verified: 2026-09-02
compass: CF-SPEC-8 / FIX-pi-full-20260720-w7-REVIEW-r1-docs; CF-SPEC-78 / CF-1005; CF-SPEC-124 / CF-1590
---

# Findings Codebook Architecture

## Implementation Summary

The Codebook tab surfaces qualitative coding structures and codebook versions associated with project findings. Project-facing codebook and code by-id routes require the active project id and load records by both record id and project id before returning or mutating data. Create and update responses explicitly eager-load the codes relationship before serialization, so an empty codebook returns `201`/`200` instead of triggering an async lazy-load `500`.

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
- Governed coding reads Pi Model Management without loading a model, requests at least three distinct model identities, and dispatches each coder with `structured(purpose="validity.coder")` pinned to that coder's exact endpoint. Selection and dispatch carry one request-scoped `PiExecutionService` paired with its `PiModelManager` snapshot, while the dispatcher remains responsible for usage-ledger accounting. Both Istara and Pi loop modes use this same provider authority; loop choice cannot bypass coding independence.
- The structured coder adapter also verifies the provider-reported endpoint identity against the endpoint pinned in `TurnParams`. A mismatch is a failed coder attempt, not usable route evidence; no code applications or reliability score may be promoted from that response.
- Reliability preserves both model and endpoint provenance, but the rater-independence unit is the model identity. Same-model endpoint replicas do not count as separate coders. Each admitted coder must cover every selected evidence unit after one bounded repair; otherwise it is excluded and the run remains blocked when the requested width is no longer met.
- A coding application is admissible only when its non-empty returned quote is an exact contiguous substring of the resolved evidence unit's raw source text. A valid unit ID cannot make a paraphrase or fabricated quote source-grounded; rejected applications count as missing coverage and therefore fail the reliability gate closed.
- The resulting code applications remain provisional until reliability, reconciliation, and human review gates accept them. A blocked or insufficient coding run cannot promote findings into reportable evidence.
- Embedding consumers route through `agentic.embed`; both loop modes use the Pi-governed `EmbeddingsGateway` and the canonical vector-space identity.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Codebook and code reads/mutations are project-content surfaces. They must reject stale ids from any other project with `404`, even when the same authenticated user can access both projects through another surface.
- Engine selection changes loop semantics only. The permanent Istara executor and the Pi agentic loop both resolve provider/model identities through Pi Model Management; neither may silently switch engines or bypass the Research Spine gate.

## Tests And Verification

- `tests/test_codebooks.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_research_validity_contract.py` — exact source-span grounding, protected prompt blocks, persistence, reliability, reconciliation, and reportability contracts.
- `tests/pi_production/test_w7_validation.py` — three-model minimum, exact endpoint pinning, same-model replica rejection, complete grounded-unit coverage, schema constraints, and fail-closed blocked coding runs.
- `tests/pi_production/test_w7_pi_manager_integration.py` — the positive coding-run path uses the real `AgenticDispatcher` with its paired Pi Model Manager; a deterministic provider seam verifies that all three selected endpoint/model identities reach `validity.coder` structured dispatch before Spine acceptance.

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
