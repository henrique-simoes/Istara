---
stable_id: findings.review
title: Findings Code Review
ui_path: Findings > Review
audience: architecture
status: documented
related_features: ["findings.codebook", "tasks.review"]
related_glossary: ["triangulation", "fleiss-kappa"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodeReviewQueue.tsx", "frontend/src/lib/researchIntegrityApi.ts", "backend/app/api/routes/research_validity.py", "backend/app/services/research_validity_service.py", "backend/app/core/research_validity.py", "backend/app/models/code_application.py"]
api_references: ["backend/app/api/routes/code_applications.py", "backend/app/api/routes/codebooks.py", "backend/app/api/routes/research_validity.py"]
test_references: ["tests/test_code_applications.py", "tests/test_project_scope_contracts.py", "tests/test_research_validity_contract.py"]
last_verified: 2026-08-26
compass: CF-SPEC-78 / CF-1005; CF-SPEC-124 / CF-1590
---

# Findings Code Review Architecture

## Implementation Summary

The Review tab presents code review queues for validating and adjudicating qualitative coding work. Review mutations pass the active project id and the backend binds each code-application id to that same project before applying reviewer decisions. The queue now exposes evidence-unit, coding-run, route/model/donor, reliability, reconciliation, and promotion state so researchers can see why a code can be accepted, blocked, or sent back for review.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `frontend/src/components/findings/CodeReviewQueue.tsx`
- `frontend/src/lib/researchIntegrityApi.ts`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/code_applications.py`
- `backend/app/api/routes/codebooks.py`
- `backend/app/api/routes/research_validity.py`
- `backend/app/services/research_validity_service.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Code review is a project-content surface. Pending queues and review mutations must stay inside the caller's authorized active project and must not infer project scope from a globally unique application id.
- The legacy `bulk-approve` compatibility route is deliberately fail-closed with no database side effects. Confidence and accepted reliability/promotion status are review signals, never a reconciliation decision; each application must be accepted, rejected, or revised through the individual auditable review route.
- Researchers review coded evidence units, not keyword tags. Code applications should point at stable evidence units and coding runs whenever the corrected pipeline produced them.
- Governed coding runs are started from the project-scoped research-validity route with researcher access. The service persists model coder identities, route evidence, reliability matrix output, and promotion state so the review queue can distinguish accepted coding from low-consensus or lower-assurance output.
- Approving, rejecting, or revising a disputed code application creates a `ReconciliationDecision`, updates the code application's reconciliation/promotion state, and links the decision back into the Evidence Graph with a `reconciled_by` edge. A task remains blocked while any low-agreement code application is still unreconciled.
- Project code-application reads accept `coding_run_id` so benchmark and review clients can prove that every application in one run has an explicit accepted/revised reconciliation decision without mixing rows from another run.
- A completed run with Fleiss/alpha and `promotion_status=accepted` is still provisional for report purposes until each application is approved, reconciled, and linked to its decision; acceptance counters and task gates use that stricter state.
- Task review snapshots expose task-linked coding-run status and blocked review items. Kanban review should explain whether the task is waiting on low agreement, no accepted code applications, missing route evidence, or human reconciliation before Done approval or report routing.

## Tests And Verification

- `tests/test_code_applications.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_research_validity_contract.py`

## Related Features

- [findings.codebook](../../findings/codebook/architecture.md)
- [tasks.review](../../tasks/review/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-78 / CF-1005; CF-SPEC-124 / CF-1590
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
