---
stable_id: findings.codebook
title: Findings Codebook
ui_path: Findings > Codebook
audience: researcher
status: documented
related_features: ["findings.evidence", "findings.review"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodebookViewer.tsx", "backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py", "backend/app/services/research_validity_service.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
test_references: ["tests/test_codebooks.py", "tests/test_project_scope_contracts.py", "tests/test_research_validity_contract.py", "tests/pi_production/test_w7_validation.py"]
last_verified: 2026-09-02
compass: CF-SPEC-8 / FIX-pi-full-20260720-w7-REVIEW-r1-docs; CF-SPEC-78 / CF-1005
---

# Findings Codebook

## What It Does

The Codebook tab surfaces qualitative coding structures and codebook versions associated with project findings.

## Why It Exists

Findings Codebook exists so the work represented by Findings > Codebook has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Findings > Codebook
- Navigation group: Findings
- Primary component: `CodebookViewer`

## How UX Researchers Use It

- Open Findings > Codebook from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with findings codebook in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Findings > Codebook when the current research task needs findings codebook.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.evidence, findings.review.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with findings codebook.
- Direct codebook and code actions stay bound to the active project; stale links or ids from other projects do not open or update records in this view.
- Creating or renaming a codebook returns its saved details and a zero code count when it has no codes; the response remains usable without a refresh.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Independent Coding And Reliability

- In the Pi-enabled path, Istara asks the dispatcher for independent structured coding passes through `validity.coder`. Selection and dispatch use one request-scoped `PiExecutionService` paired with its `PiModelManager` snapshot, and each pass is pinned to a concrete endpoint identity from the authorized project catalog.
- Model identity is the independence unit. Two endpoints serving the same model are replicas, not separate coders; repeated calls to one model do not count as independent agreement. Endpoint identity remains required for route provenance and provider-identity drift checks.
- If enough distinct model identities are not available, the coding run is blocked and records a failed route-evidence reason. It does not silently switch engines or accept provisional codes as reliable.
- Codes remain provisional until source-grounded reliability, reconciliation, and human review gates are complete. Only then may findings proceed toward accepted research evidence and reports.

## Rollback And Migration Boundary

Select the `legacy` engine for the project (or keep the legacy global default) to return coder calls to the dispatcher's permanent project-authorized legacy executor. W8 now routes embedding consumers through `agentic.embed`: legacy keeps the unchanged `ollama.embed*` plane, while Pi uses the `EmbeddingsGateway`; the codebook's structured-coder route does not change that embedding boundary.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.evidence](../../findings/evidence/researcher.md)
- [findings.review](../../findings/review/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Evidence

- Source files: `frontend/src/components/findings/FindingsView.tsx`, `frontend/src/components/findings/CodebookViewer.tsx`, `backend/app/api/routes/codebooks.py`, `backend/app/api/routes/codebook_versions.py`, `backend/app/services/research_validity_service.py`, `backend/app/core/agentic/dispatcher.py`
- API references: `backend/app/api/routes/codebooks.py`, `backend/app/api/routes/codebook_versions.py`
- Tests: `tests/test_codebooks.py`, `tests/test_project_scope_contracts.py`, `tests/test_research_validity_contract.py`, `tests/pi_production/test_w7_validation.py`
