---
stable_id: shell.navigation
title: Application Navigation
ui_path: Shell > Navigation
audience: researcher
status: documented
related_features: ["shell.projects", "shell.search", "shell.keyboard-shortcuts", "shell.onboarding"]
related_glossary: ["wcag", "compass-forge"]
code_references: ["frontend/src/lib/navigation.ts", "frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/layout/Sidebar.tsx", "frontend/src/components/layout/MobileNav.tsx"]
api_references: []
test_references: ["frontend/src/lib/navigation.test.ts"]
last_verified: 2026-09-01
compass: CF-SPEC-53 / CF-657
---

# Application Navigation

## What It Does

The main shell organizes Istara into primary, secondary, utility, and mobile navigation surfaces and routes each selected view into the mounted work area.

## Why It Exists

Application Navigation exists so the work represented by Shell > Navigation has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Navigation
- Navigation group: Shell
- Primary component: `HomeClient / Sidebar / MobileNav`

## How UX Researchers Use It

- Open Shell > Navigation from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with application navigation in the active project context.
- Viewers see the core primary navigation only; researcher-only entries such as Loops appear for researcher and admin roles.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Navigation when the current research task needs application navigation.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.projects, shell.search, shell.keyboard-shortcuts, shell.onboarding.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with application navigation.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.projects](../../shell/projects/researcher.md)
- [shell.search](../../shell/search/researcher.md)
- [shell.keyboard-shortcuts](../../shell/keyboard-shortcuts/researcher.md)
- [shell.onboarding](../../shell/onboarding/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)
- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/lib/navigation.ts`, `frontend/src/components/layout/HomeClient.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/MobileNav.tsx`
- API references: none recorded
- Tests: `frontend/src/lib/navigation.test.ts`
