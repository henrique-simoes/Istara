---
stable_id: settings.connection-strings
title: Connection Strings
ui_path: Settings > Connection Strings
audience: researcher
status: documented
related_features: ["settings.llm-servers", "settings.users"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/settings/ConnectionStringPanel.tsx", "backend/app/api/routes/connections.py", "backend/app/core/connection_string.py"]
api_references: ["backend/app/api/routes/connections.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Connection Strings

## What It Does

Connection string settings provide governed admin-only configuration for sensitive external or local service connection data.

## Why It Exists

Connection Strings exists so the work represented by Settings > Connection Strings has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Connection Strings
- Navigation group: Settings
- Primary component: `ConnectionStringPanel`

## How UX Researchers Use It

- Open Settings > Connection Strings from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with connection strings in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Connection Strings when the current research task needs connection strings.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.llm-servers, settings.users.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with connection strings.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.llm-servers](../../settings/llm-servers/researcher.md)
- [settings.users](../../settings/users/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/settings/ConnectionStringPanel.tsx`, `backend/app/api/routes/connections.py`, `backend/app/core/connection_string.py`
- API references: `backend/app/api/routes/connections.py`
- Tests: none recorded
