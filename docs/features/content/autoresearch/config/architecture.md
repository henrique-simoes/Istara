---
stable_id: autoresearch.config
title: Autoresearch Configuration
ui_path: Autoresearch > Config
audience: architecture
status: documented
related_features: ["autoresearch.experiments", "chat.model-controls"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_runners/rag_params.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w6_autoresearch_runners.py"]
last_verified: 2026-07-22
compass: CF-SPEC-60 / CF-754; CF-SPEC-8 (Pi replacement W6)
---

# Autoresearch Configuration Architecture

## Implementation Summary

Autoresearch configuration sets parameters for automated research strategies and runs.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `backend/app/core/autoresearch_runners/rag_params.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`
- Configuration reads are global runtime settings, but status refreshes shown in this tab still use the active project id.

### API And Backend

- `backend/app/api/routes/autoresearch.py`
- Autoresearch configuration mutations and global enable/disable toggles require global admin access because they affect every project. Project-facing status, experiments, and leaderboard routes remain project-scoped.

### Agentic Dispatcher Migration (Pi Replacement W6)

- Pi Replacement wave W6 (master plan `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` §8 W6, spec CF-SPEC-8) routes the autoresearch RAG-parameter runner's LLM call through the shared `AgenticDispatcher` (`backend/app/core/agentic/dispatcher.py`, module singleton `agentic`) on the Pi engine, and keeps the legacy `llm_router.chat` branch verbatim on the legacy engine. Engine selection is per experiment and defaults to the global `settings.agentic_core` flag (`pi` when enabled, otherwise `legacy`). The full six-runner routing table, engine-selection precedence, and model/temperature sweep semantics are documented on the [autoresearch.experiments](../../autoresearch/experiments/architecture.md) architecture page; this page covers the RAG-parameter runner specifically.
- `RAGParamsRunner._llm_hypothesis` (`backend/app/core/autoresearch_runners/rag_params.py`) issues its next-parameter suggestion as `agentic.completion(purpose="autoresearch.rag_params.hypothesize", spine_phase="plan")`. The dispatcher is the single choke point that resolves the concrete engine and endpoint and fails closed on a selected engine that cannot execute rather than silently falling back (see [chat.model-controls](../../chat/model-controls/architecture.md) for the full precedence: per-call override, then the `x-istara-agent-engine` request header, then the project `agentic_engine` setting, then `settings.agentic_engine_default`).
- RAG retrieval-eval embedding stays legacy until W8 (master plan §8 W6 design decision 2): only the suggestion chat migrates. The retrieval-eval embedding in `_score_single_query` (`embed_text`) is deliberately left on the legacy plane and is never routed through `agentic.embed` until the W8 embeddings gateway lands. The count-to-zero migration allowlist tracks the migrated chat site and the deferred embed site as separate entries so the deferral is an explicit, tracked decision rather than a missed site.
- Project scope is preserved: the RAG-parameter runner carries the authorized project id bound by the autoresearch engine into its dispatcher call for engine resolution, telemetry, and execution scope, so a Pi run cannot resolve an engine, record telemetry, or execute against a project other than the one that authorized the experiment. Global configuration mutations still require global admin access and contain no project content; runtime experiment execution still requires project authorization.
- Rollback: set `settings.agentic_core` to `False` (or select the `legacy` engine for the project) and the runner falls back to its preserved `llm_router.chat` branch with no schema or behavior change; the count-to-zero ratchet stays at 70 because the legacy branch is preserved rather than retired.

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes. Global config changes must not expose or process project content; runtime experiment execution still requires project authorization.

## Tests And Verification

- `tests/test_autoresearch.py` verifies non-admin researchers cannot mutate global autoresearch config and admins can.
- `tests/test_project_scope_contracts.py` verifies project-facing autoresearch calls carry project ids.
- `tests/pi_production/test_w6_autoresearch_runners.py` verifies the RAG-parameter runner routes `_llm_hypothesis` through `agentic.completion` (`autoresearch.rag_params.hypothesize`) with the legacy branch preserved, and that the retrieval-eval embedding in `_score_single_query` stays on the legacy plane (never routed through `agentic.embed`) with the W8 deferral documented in-line.
- Regenerate and validate the machine manifests and static site with `python scripts/feature_docs.py --seed-missing --generate-site --check`.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/architecture.md)
- [chat.model-controls](../../chat/model-controls/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754; CF-SPEC-8 (Pi replacement W6 autoresearch-runner dispatcher migration)
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
