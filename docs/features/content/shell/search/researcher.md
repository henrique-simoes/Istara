---
stable_id: shell.search
title: Global Search
ui_path: Shell > Search
audience: researcher
status: needs-verification
related_features: ["shell.navigation", "shell.keyboard-shortcuts"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/components/common/SearchModal.tsx"]
api_references: []
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Global Search

## What It Does

The shell exposes a command/search modal from the sidebar and keyboard shortcut so users can find navigable work surfaces and project objects.

## Why It Exists

Global Search exists so the work represented by Shell > Search has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Search
- Navigation group: Shell
- Primary component: `SearchModal`

## How UX Researchers Use It

- Open Shell > Search from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with global search in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Search when the current research task needs global search.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.navigation, shell.keyboard-shortcuts.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with global search.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.navigation](../../shell/navigation/researcher.md)
- [shell.keyboard-shortcuts](../../shell/keyboard-shortcuts/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/layout/HomeClient.tsx`, `frontend/src/components/common/SearchModal.tsx`
- API references: none recorded
- Tests: none recorded
