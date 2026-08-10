---
stable_id: settings.llm-servers
title: LLM Server Settings
ui_path: Settings > LLM Servers
audience: researcher
status: documented
related_features: ["chat.model-controls", "settings.connection-strings"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/SettingsView.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py", "backend/app/api/routes/settings.py", "backend/app/core/network_discovery.py", "backend/app/core/pi_runtime/model_manager.py"]
api_references: ["backend/app/api/routes/llm_servers.py", "backend/app/api/routes/settings.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_llm_servers.py", "tests/pi_production/test_w8_embeddings_gateway.py"]
last_verified: 2026-07-22
compass: CF-SPEC-94 / CF-1193; CF-SPEC-8
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
