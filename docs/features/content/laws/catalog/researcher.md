---
stable_id: laws.catalog
title: UX Laws Catalog
ui_path: UX Laws > Catalog
audience: researcher
status: documented
related_features: ["laws.compliance", "findings.evidence"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/laws/LawsView.tsx", "frontend/src/stores/lawsStore.ts", "backend/app/api/routes/laws.py"]
api_references: ["backend/app/api/routes/laws.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# UX Laws Catalog

## What It Does

The UX Laws catalog gives researchers a structured reference for applying UX laws to research and design interpretation.

## Why It Exists

UX Laws Catalog exists so the work represented by UX Laws > Catalog has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: UX Laws > Catalog
- Navigation group: UX Laws
- Primary component: `LawsView`

## How UX Researchers Use It

- Open UX Laws > Catalog from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with ux laws catalog in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from UX Laws > Catalog when the current research task needs ux laws catalog.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: laws.compliance, findings.evidence.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with ux laws catalog.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [laws.compliance](../../laws/compliance/researcher.md)
- [findings.evidence](../../findings/evidence/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/laws/LawsView.tsx`, `frontend/src/stores/lawsStore.ts`, `backend/app/api/routes/laws.py`
- API references: `backend/app/api/routes/laws.py`
- Tests: none recorded
