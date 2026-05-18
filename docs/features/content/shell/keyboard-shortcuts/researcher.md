---
stable_id: shell.keyboard-shortcuts
title: Keyboard Shortcuts
ui_path: Shell > Keyboard Shortcuts
audience: researcher
status: documented
related_features: ["shell.search", "shell.navigation"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/common/KeyboardShortcuts.tsx"]
api_references: []
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Keyboard Shortcuts

## What It Does

HomeClient wires global shortcuts for search, view switching, shortcut help, and right-panel toggling.

## Why It Exists

Keyboard Shortcuts exists so the work represented by Shell > Keyboard Shortcuts has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Keyboard Shortcuts
- Navigation group: Shell
- Primary component: `KeyboardShortcuts`

## How UX Researchers Use It

- Open Shell > Keyboard Shortcuts from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with keyboard shortcuts in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Keyboard Shortcuts when the current research task needs keyboard shortcuts.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.search, shell.navigation.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with keyboard shortcuts.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.search](../../shell/search/researcher.md)
- [shell.navigation](../../shell/navigation/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/layout/HomeClient.tsx`, `frontend/src/components/common/KeyboardShortcuts.tsx`
- API references: none recorded
- Tests: none recorded
