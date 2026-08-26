---
stable_id: settings.general
title: System Status, Agentic Core, And Pi Models
ui_path: Settings > System Status, Agentic Core, And Pi Models
audience: researcher
status: documented
related_features: ["settings.llm-servers", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/components/settings/AgenticCoreSection.tsx", "frontend/src/components/settings/PiModelManagement.tsx", "backend/app/api/routes/settings.py", "backend/app/core/pi_runtime/endpoint_policy.py", "backend/app/core/pi_runtime/catalog.py", "backend/app/core/pi_runtime/oauth.py"]
api_references: ["backend/app/api/routes/settings.py"]
test_references: ["tests/test_settings.py", "tests/test_settings_agentic_pi_endpoints.py", "tests/pi_production/test_pi_catalog_ux.py"]
last_verified: 2026-08-26
compass: CF-SPEC-53 / CF-657
---

# System Status And Models

## What It Does

Settings shows backend and LLM status, a dedicated Agentic Core explanation/choice, hardware/model guidance, and a Pi model-management workbench. Pi lets an administrator browse the complete provider/model list or type to autocomplete, then use the authentication method Pi supports.

## Why It Exists

System Status And Models exists so the work represented by Settings > System Status And Models has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > System Status And Models
- Navigation group: Settings
- Primary component: `SettingsView`

## How UX Researchers Use It

- Open Settings > System Status, Agentic Core, And Pi Models from the Istara navigation.
- Read the Agentic Core comparison before choosing Pi or Istara; the benchmark snapshot is explicitly provisional.
- In Pi Model Management, click the provider/model arrows to browse or type to autocomplete. For OpenAI, choose OpenAI API for an API key or OpenAI Codex — ChatGPT subscription for Browser login or Device code (headless) OAuth.
- Return to Chat to choose any connected model and its exact effort levels.

## Supported Workflows

- Start from Settings > System Status, Agentic Core, And Pi Models when the current task needs global execution or provider configuration.
- Use the visible controls to connect a model without typing an endpoint URL; credentials stay in server custody.
- Move to Chat to change the model and effort for an individual conversation.

## Inputs, Outputs, And Expected Outcomes

- Global Agentic Core and Pi endpoint configuration updates for authorized administrators.
- A visible, searchable provider/model list with API-key and Pi OAuth choices.
- Legacy backend compatibility data remains preserved but is not a competing normal Settings catalog.
- Editing an existing Pi connection uses the same catalog, URL, Keychain-custody,
  and OAuth-preservation rules as adding one; sparse edits keep the endpoint's
  derived capabilities and secret reference, while invalid edits are rejected.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [compute.pool](../../compute/pool/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/SettingsView.tsx`, `frontend/src/components/settings/AgenticCoreSection.tsx`, `frontend/src/components/settings/PiModelManagement.tsx`, `backend/app/api/routes/settings.py`, `backend/app/core/pi_runtime/endpoint_policy.py`, `backend/app/core/pi_runtime/catalog.py`, `backend/app/core/pi_runtime/oauth.py`
- API references: `backend/app/api/routes/settings.py`
- Tests: `tests/test_settings.py`, `tests/test_settings_agentic_pi_endpoints.py`, `tests/pi_production/test_pi_catalog_ux.py`
