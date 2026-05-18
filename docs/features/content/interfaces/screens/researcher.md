---
stable_id: interfaces.screens
title: Screens Gallery
ui_path: Interfaces > Screens
audience: researcher
status: documented
related_features: ["interfaces.generate", "interfaces.handoff"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/interfaces/ScreensGalleryTab.tsx", "frontend/src/components/interfaces/ScreenPreview.tsx", "backend/app/api/routes/interfaces_screens.py"]
api_references: ["backend/app/api/routes/interfaces_screens.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Screens Gallery

## What It Does

Screens displays generated interface screens and previews for review.

## Why It Exists

Screens Gallery exists so the work represented by Interfaces > Screens has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interfaces > Screens
- Navigation group: Interfaces
- Primary component: `ScreensGalleryTab`

## How UX Researchers Use It

- Open Interfaces > Screens from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with screens gallery in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interfaces > Screens when the current research task needs screens gallery.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: interfaces.generate, interfaces.handoff.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with screens gallery.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [interfaces.generate](../../interfaces/generate/researcher.md)
- [interfaces.handoff](../../interfaces/handoff/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/interfaces/ScreensGalleryTab.tsx`, `frontend/src/components/interfaces/ScreenPreview.tsx`, `backend/app/api/routes/interfaces_screens.py`
- API references: `backend/app/api/routes/interfaces_screens.py`
- Tests: none recorded
