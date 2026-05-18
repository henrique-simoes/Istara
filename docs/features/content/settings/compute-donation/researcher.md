---
stable_id: settings.compute-donation
title: Compute Donation
ui_path: Settings > Compute Donation
audience: researcher
status: documented
related_features: ["compute.pool", "settings.general"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/common/DonateComputeToggle.tsx", "backend/app/core/compute_pool.py"]
api_references: ["backend/app/api/routes/compute.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Compute Donation

## What It Does

Compute donation lets a browser session contribute local compute capacity under controlled limits.

## Why It Exists

Compute Donation exists so the work represented by Settings > Compute Donation has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Compute Donation
- Navigation group: Settings
- Primary component: `DonateComputeToggle`

## How UX Researchers Use It

- Open Settings > Compute Donation from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with compute donation in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Compute Donation when the current research task needs compute donation.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: compute.pool, settings.general.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with compute donation.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [compute.pool](../../compute/pool/researcher.md)
- [settings.general](../../settings/general/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/common/DonateComputeToggle.tsx`, `backend/app/core/compute_pool.py`
- API references: `backend/app/api/routes/compute.py`
- Tests: none recorded
