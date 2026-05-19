---
stable_id: settings.llm-servers
title: LLM Server Settings
ui_path: Settings > LLM Servers
audience: researcher
status: documented
related_features: ["chat.model-controls", "settings.connection-strings"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py"]
api_references: ["backend/app/api/routes/llm_servers.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_llm_servers.py"]
last_verified: 2026-05-19
compass: CF-SPEC-94 / CF-1193
---

# LLM Server Settings

## What It Does

Settings manages configured LLM providers, server endpoints, provider labels, and active model switching.

## Why It Exists

LLM Server Settings exists so the work represented by Settings > LLM Servers has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > LLM Servers
- Navigation group: Settings
- Primary component: `SettingsView`

## How UX Researchers Use It

- Open Settings > LLM Servers from the Istara navigation or the parent tab.
- Global admins can use the visible controls to manage shared LLM provider endpoints. Non-admin team-mode users see the locked state instead of shared endpoint details.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > LLM Servers when the current research task needs llm server settings.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: chat.model-controls, settings.connection-strings.

## Inputs, Outputs, And Expected Outcomes

- Admin-only shared provider endpoint inventory, status, forms, and health-check results shown by the referenced component and routes.
- Non-admin users receive a permission-gated state with no endpoint inventory or probe controls.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.model-controls](../../chat/model-controls/researcher.md)
- [settings.connection-strings](../../settings/connection-strings/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/SettingsView.tsx`, `frontend/src/lib/modelProviders.ts`, `backend/app/api/routes/llm_servers.py`
- API references: `backend/app/api/routes/llm_servers.py`
- Tests: `frontend/src/lib/modelProviders.test.ts`
