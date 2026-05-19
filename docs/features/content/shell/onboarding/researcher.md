---
stable_id: shell.onboarding
title: View Onboarding
ui_path: Shell > Onboarding
audience: researcher
status: documented
related_features: ["shell.navigation", "chat.overview"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/common/ViewOnboarding.tsx", "frontend/src/hooks/useViewOnboarding.ts", "frontend/src/stores/tourStore.ts"]
api_references: []
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# View Onboarding

## What It Does

Reusable onboarding overlays and tour state introduce major Istara views and offer context-specific chat prompts.

## Why It Exists

View Onboarding exists so the work represented by Shell > Onboarding has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Onboarding
- Navigation group: Shell
- Primary component: `ViewOnboarding`

## How UX Researchers Use It

- Open Shell > Onboarding from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with view onboarding in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Onboarding when the current research task needs view onboarding.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.navigation, chat.overview.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with view onboarding.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.navigation](../../shell/navigation/researcher.md)
- [chat.overview](../../chat/overview/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/common/ViewOnboarding.tsx`, `frontend/src/hooks/useViewOnboarding.ts`, `frontend/src/stores/tourStore.ts`
- API references: none recorded
- Tests: none recorded
