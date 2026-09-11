---
stable_id: settings.llm-servers
title: Legacy LLM Server Compatibility
ui_path: Settings > Pi Model Management (legacy compatibility only)
audience: researcher
status: deprecated
related_features: ["chat.model-controls", "settings.connection-strings"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/settings.py", "backend/app/api/routes/petals.py", "backend/app/core/pi_runtime/model_manager.py", "backend/app/core/petals_bridge.py"]
api_references: ["backend/app/api/routes/settings.py", "backend/app/api/routes/petals.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_settings_agentic_pi_endpoints.py", "tests/pi_production/test_w1_agentic_contract.py", "tests/petals_bridge/test_petals_bridge.py", "tests/pi_production/test_w8_embeddings_gateway.py"]
last_verified: 2026-08-24
compass: CF-SPEC-94 / CF-1193; CF-SPEC-8
---

# Legacy LLM Server Compatibility

## What It Does

The classical LLM Server API has been retired. Persisted rows remain as read-only migration input, while Pi Model Management owns provider/model selection for both Istara and Pi Agentic Loop. Donated compute joins that catalog only through the governed Petals bridge.

## Why It Exists

LLM Server Settings exists so the work represented by Settings > LLM Servers has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > LLM Servers
- Navigation group: Settings
- Primary component: `SettingsView`

## How UX Researchers Use It

- Do not look for a separate LLM Servers section in normal Settings; it has been removed from the user-facing catalog.
- Existing rows are preserved for migration and rollback; the old public CRUD route is not mounted.
- Use Settings > Pi Model Management for the supported provider/model and authentication workflow.

## Supported Workflows

- Start from Settings > Pi Model Management for new cloud/API model connections.
- Treat legacy LLM Server rows as compatibility data only; new configuration belongs in Pi Model Management.
- Move to Chat > Model Controls to choose enabled models for a conversation.

## Inputs, Outputs, And Expected Outcomes

- Admin-only Pi provider/model inventory, authentication, and status shown by the referenced component and routes.
- Non-admin users receive a permission-gated state with no endpoint inventory or probe controls.

## Engine Catalog Parity

- Istara and Pi Agentic Loop are two first-class loop modes over one Pi Model Management authority. Changing the loop does not switch model catalogs.
- Endpoint/provider/model changes refresh live managers without a restart. The projection is one-directional: Pi does not write back to legacy rows or donor records.
- Healthy, explicitly consented, project-authorized relay/browser donors may appear through the identity-pinned Petals bridge. Same-model replicas provide availability, not additional independent Research Spine coders.
- Catalog responses expose identity/capability metadata, never addresses, API keys, tokens, prompts, or research content.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.model-controls](../../chat/model-controls/researcher.md)
- [settings.connection-strings](../../settings/connection-strings/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/SettingsView.tsx`, `frontend/src/lib/modelProviders.ts`, `backend/app/api/routes/settings.py`, `backend/app/api/routes/petals.py`, `backend/app/core/pi_runtime/model_manager.py`, `backend/app/core/petals_bridge.py`
- API references: `backend/app/api/routes/settings.py`, `backend/app/api/routes/petals.py`
- Tests: `frontend/src/lib/modelProviders.test.ts`, `tests/test_settings_agentic_pi_endpoints.py`, `tests/pi_production/test_w1_agentic_contract.py`, `tests/petals_bridge/test_petals_bridge.py`, `tests/pi_production/test_w8_embeddings_gateway.py`
