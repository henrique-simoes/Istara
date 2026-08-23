---
stable_id: settings.llm-servers
title: Legacy LLM Server Compatibility
ui_path: Settings > Pi Model Management (legacy compatibility only)
audience: researcher
status: compatibility-only
related_features: ["chat.model-controls", "settings.connection-strings"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py", "backend/app/api/routes/settings.py", "backend/app/core/network_discovery.py", "backend/app/core/pi_runtime/model_manager.py"]
api_references: ["backend/app/api/routes/llm_servers.py", "backend/app/api/routes/settings.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_llm_servers.py", "tests/pi_production/test_w8_embeddings_gateway.py"]
last_verified: 2026-07-22
compass: CF-SPEC-94 / CF-1193; CF-SPEC-8
---

# Legacy LLM Server Compatibility

## What It Does

The legacy LLM Server API and persisted rows remain as a reversible compatibility/migration plane for existing installations, local serving, and donated compute. The legacy catalog is no longer rendered as a competing model-management UI in normal Settings; Pi Model Management owns provider/model selection for cloud/API connections.

## Why It Exists

LLM Server Settings exists so the work represented by Settings > LLM Servers has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > LLM Servers
- Navigation group: Settings
- Primary component: `SettingsView`

## How UX Researchers Use It

- Do not look for a separate LLM Servers section in normal Settings; it has been removed from the user-facing catalog.
- Existing backend routes and rows are preserved for migration, rollback, local serving, and donated-compute compatibility.
- Use Settings > Pi Model Management for the supported provider/model and authentication workflow.

## Supported Workflows

- Start from Settings > Pi Model Management for new cloud/API model connections.
- Treat legacy LLM Server rows/routes as compatibility data only; changes must preserve rollback and existing local/donor behavior.
- Move to Chat > Model Controls to choose enabled models for a conversation.

## Inputs, Outputs, And Expected Outcomes

- Admin-only shared provider endpoint inventory, status, forms, and health-check results shown by the referenced component and routes.
- Non-admin users receive a permission-gated state with no endpoint inventory or probe controls.

## Engine Catalog Parity

- Istara can run on a legacy engine or the newer Pi replacement engine, and each engine keeps its own view of the available model servers. Pi Replacement wave W8 keeps those views in sync: adding, editing, deleting, or auto-discovering an LLM server in Settings now refreshes the Pi engine's model catalog as well as the legacy one, so a server you register once is available to both engines without a restart.
- The sync is one-directional — registered servers flow into the Pi catalog, but Pi never writes back or changes how the legacy engine schedules work, and shared relay/donor capacity is still never offered to Pi traffic.
- The settings model list also reports the Pi catalog alongside the legacy list. It shows only identity information — which endpoints and model names exist and what kind they are — never server addresses or API keys, and it is available whether the servers are currently reachable or offline.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.model-controls](../../chat/model-controls/researcher.md)
- [settings.connection-strings](../../settings/connection-strings/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/SettingsView.tsx`, `frontend/src/lib/modelProviders.ts`, `backend/app/api/routes/llm_servers.py`, `backend/app/api/routes/settings.py`, `backend/app/core/network_discovery.py`
- API references: `backend/app/api/routes/llm_servers.py`, `backend/app/api/routes/settings.py`
- Tests: `frontend/src/lib/modelProviders.test.ts`, `tests/test_llm_servers.py`, `tests/pi_production/test_w8_embeddings_gateway.py`
