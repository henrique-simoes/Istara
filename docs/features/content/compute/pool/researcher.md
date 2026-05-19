---
stable_id: compute.pool
title: Compute Pool
ui_path: Compute Pool
audience: researcher
status: documented
related_features: ["settings.compute-donation", "settings.general"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/common/ComputePoolView.tsx", "backend/app/api/routes/compute.py", "backend/app/core/compute_pool.py", "backend/app/core/compute_registry_routing.py"]
api_references: ["backend/app/api/routes/compute.py"]
test_references: ["tests/test_compute.py", "tests/compute_cases/status_contracts.py", "tests/compute_cases/stats_websocket.py", "tests/test_compute_registry_model_loading.py", "tests/test_compute_registry_hardening.py", "tests/test_network_discovery.py", "tests/test_project_rbac.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-774; CF-SPEC-66 / CF-856; CF-SPEC-70 / CF-899
---

# Compute Pool

## What It Does

Compute Pool provides active-project visibility into available compute nodes, routing, and local or pooled execution capacity. If one physical Mac is reachable through more than one local network address, Istara treats those aliases as one machine for the Total RAM, CPU, and connected-node display. A reachable LM Studio server can show as online even when no model is currently loaded; in that state it is visible for capacity and model availability, but not counted as ready for chat routing. Donated compute can only receive project prompts or embeddings for projects included in its authorized donation scope, and browser/JWT donation scope follows the donor's current database role and project memberships rather than old token claims. Donated nodes outside the active project do not appear in project pool status for any role.

## Why It Exists

Compute Pool exists so the work represented by Compute Pool has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Compute Pool
- Navigation group: Secondary
- Primary component: `ComputePoolView`

## How UX Researchers Use It

- Open Compute Pool from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with compute pool in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.
- Use the machine count under Total Nodes as the trusted capacity count when multiple LLM services share the same hardware.
- Read the node status as two separate ideas: online means the provider API is reachable, while ready means a model is loaded and available for routing.
- Treat donated compute as project-bound capacity. If a machine is not authorized for the active project, it is hidden from that project pool and is not eligible to process that project's content.
- Regular Compute Pool views require an active project. Cross-project capacity belongs in admin reporting, not this project surface.

## Supported Workflows

- Start from Compute Pool when the current research task needs compute pool.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.compute-donation, settings.general.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with compute pool.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- RAM and CPU totals reflect unique physical hardware, not every IP address or provider process registered in the pool.
- Servers with no loaded model remain online when reachable and show their loadable model capabilities, but continue to score as not ready until a model is loaded, even if an older health flag has not caught up yet.
- Relay/browser donors without a validated project scope are status-only and cannot receive project chat, task, report, integration, or embedding payloads.
- A donor who loses admin or project membership access loses matching compute donation scope on the next relay registration.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.compute-donation](../../settings/compute-donation/researcher.md)
- [settings.general](../../settings/general/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/common/ComputePoolView.tsx`, `backend/app/api/routes/compute.py`, `backend/app/core/compute_pool.py`
- API references: `backend/app/api/routes/compute.py`
- Tests: `tests/test_compute.py`, `tests/compute_cases/status_contracts.py`, `tests/compute_cases/stats_websocket.py`, `tests/test_compute_registry_model_loading.py`, `tests/test_compute_registry_hardening.py`, `tests/test_network_discovery.py`, `tests/test_project_rbac.py`, `tests/test_project_scope_contracts.py`
