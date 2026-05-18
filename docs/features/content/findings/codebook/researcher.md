---
stable_id: findings.codebook
title: Findings Codebook
ui_path: Findings > Codebook
audience: researcher
status: documented
related_features: ["findings.evidence", "findings.review"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodebookViewer.tsx", "backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
api_references: ["backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
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
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [findings.evidence](../../findings/evidence/researcher.md)
- [findings.review](../../findings/review/researcher.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Evidence

- Source files: `frontend/src/components/findings/FindingsView.tsx`, `frontend/src/components/findings/CodebookViewer.tsx`, `backend/app/api/routes/codebooks.py`, `backend/app/api/routes/codebook_versions.py`
- API references: `backend/app/api/routes/codebooks.py`, `backend/app/api/routes/codebook_versions.py`
- Tests: none recorded
