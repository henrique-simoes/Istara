---
stable_id: findings.review
title: Findings Code Review
ui_path: Findings > Review
audience: researcher
status: needs-verification
related_features: ["findings.codebook", "tasks.review"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodeReviewQueue.tsx"]
api_references: ["backend/app/api/routes/codebooks.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
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
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.codebook](../../findings/codebook/researcher.md)
- [tasks.review](../../tasks/review/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/findings/FindingsView.tsx`, `frontend/src/components/findings/CodeReviewQueue.tsx`
- API references: `backend/app/api/routes/codebooks.py`
- Tests: none recorded
