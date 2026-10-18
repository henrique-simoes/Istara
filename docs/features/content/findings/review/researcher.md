---
stable_id: findings.review
title: Findings Code Review
ui_path: Findings > Review
audience: researcher
status: needs-verification
related_features: ["findings.codebook", "tasks.review"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodeReviewQueue.tsx", "frontend/src/lib/researchIntegrityApi.ts"]
api_references: ["backend/app/api/routes/code_applications.py", "backend/app/api/routes/codebooks.py"]
test_references: ["tests/test_code_applications.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-10-18
compass: CF-SPEC-78 / CF-1005
---

# Findings Code Review

## What It Does

The Review tab presents code review queues for validating and adjudicating qualitative coding work.

## Why It Exists

Findings Code Review exists so the work represented by Findings > Review has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Findings > Review
- Navigation group: Findings
- Primary component: `CodeReviewQueue`

## How UX Researchers Use It

- Open Findings > Review from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with findings code review in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Findings > Review when the current research task needs findings code review.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: findings.codebook, tasks.review.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with findings code review.
- Approve/reject actions carry the active project id so stale queue items or links from another project cannot change records in the current project.
- A coding run is not report-ready from model agreement alone. Every code application must show approved review, accepted/reconciled reconciliation state, and a linked decision; clients can scope the review list by `coding_run_id`.
- High confidence does not authorize bulk acceptance. The old bulk-approve compatibility route refuses the request without changing data; use the per-application review controls so each decision is recorded in the reconciliation ledger.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Decision-Model Triage

If your project uses decision models (for example JEV), they look at each coded quote after a
coding run finishes and ask whether the evidence unit really supports the code. Once a decision
model has been calibrated against enough of your own reviews, items it doubts can appear first in
the queue. It never accepts or rejects a code for you, and it never changes the reliability result.
Your review decision is what teaches Istara how far to trust it.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.codebook](../../findings/codebook/researcher.md)
- [tasks.review](../../tasks/review/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/findings/FindingsView.tsx`, `frontend/src/components/findings/CodeReviewQueue.tsx`, `frontend/src/lib/researchIntegrityApi.ts`
- API references: `backend/app/api/routes/code_applications.py`, `backend/app/api/routes/codebooks.py`
- Tests: `tests/test_code_applications.py`, `tests/test_project_scope_contracts.py`

## Decision-model flags

When a project's decision model is trusted, items it flagged or was unsure about move up the code review queue and carry a short note with its probability that the excerpt supports the code. The note never appears for items it is still being measured on, or for the random audit sample, so it cannot influence how you judge them. Your reconciliation decision is the only one that counts.
