---
stable_id: memory.health
title: Memory Health
ui_path: Memory > Health
audience: architecture
status: needs-verification
related_features: ["memory.knowledge", "quality.dashboard"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "backend/app/core/vector_health.py", "backend/app/core/embeddings.py", "backend/app/core/rag.py", "backend/app/core/validation.py", "backend/app/core/agentic/dispatcher.py", "backend/app/core/pi_runtime/embedding_profile.py", "backend/app/core/pi_runtime/embeddings_gateway.py", "backend/app/core/pi_runtime/model_manager.py", "backend/app/core/pi_runtime/model_manager_provisioning.py", "backend/app/main.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py", "tests/test_rag_resilience.py", "tests/pi_production/test_embedding_profile_authority.py", "tests/pi_production/test_w8_embeddings_gateway.py", "tests/pi_production/test_w1_dispatcher_authority.py", "tests/test_validation_project_scope.py", "tests/pi_migration/test_count_to_zero.py"]
last_verified: 2026-08-25
compass: CF-SPEC-60 / CF-757; CF-SPEC-8 (Pi replacement W8)
---

# Memory Health Architecture

## Implementation Summary

Memory health surfaces status and quality signals for memory or retrieval infrastructure in the active project.

## Frontend Surface

- `frontend/src/components/memory/MemoryView.tsx`
- `backend/app/core/vector_health.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/memory.py`

### Embeddings Gateway Migration (Pi Replacement W8)

#### Pi-owned embedding profile (2026-08 migration)

- Pi Model Management owns one persisted, versioned, immutable `EmbeddingProfile`. Startup loads or
  creates version 1 immediately after database initialization and before any embedding or vector-health
  probe. Version 1 captures the exact previously effective model/endpoint/cache identity once; later
  changes to classical chat-provider settings cannot mutate runtime selection or public metadata.
- Every engine choice—including Istara/legacy loop—uses the profile model and exact endpoint through
  `PiModelManager`. There is no direct legacy Ollama provisioning path. A missing endpoint, endpoint
  model mismatch, or caller model override fails typed; model-name equality alone is insufficient.
- Cache keys and learned dimensions use the profile's `cache_namespace`. Version 1 preserves the old
  model-name namespace, so bootstrap does not invalidate compatible entries. Profile id/version are
  emitted in gateway outcomes and safe profile metadata is exposed without URLs, keys, or tokens.
- Every project Lance index has an authoritative `.embedding-profile.json` binding. Existing stores
  may be adopted only by version 1; reads and writes fail closed after any profile/model/cache/
  dimension/dtype/normalization mismatch. New rows also carry profile metadata when their table schema
  supports it. Vector health reports `profile_mismatch` and requires governed re-indexing rather than
  suggesting that a dimension-only match is sufficient.

- Pi Replacement wave W8 (master plan `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` §5.2.3/§5.5, spec CF-SPEC-8) gives the Pi engine its own embeddings plane. pi-ai cannot execute embeddings, so the new `backend/app/core/pi_runtime/embeddings_gateway.py` calls the embedding endpoint directly over HTTP (`httpx`) while staying under Pi identity management: the endpoint is resolved by `PiModelManager.resolve_embed(model)`, which treats a concrete requested embedding model as an exact capability requirement, prefers the active local provider when it advertises that model, and allows a configured remote `openai_compat` endpoint with the requested model to win over unrelated local entries. When the model is `default`, the active local provider anchors the vector space; an anthropic-only or otherwise incompatible catalog fails closed with `PiEndpointResolutionError` rather than silently falling back to the legacy plane, and response cardinality is validated (`PiEmbeddingError`) so a malformed endpoint response cannot poison the vector store.
- The dispatcher's `embed` verb (`backend/app/core/agentic/dispatcher.py`) routes by resolved engine: Pi goes to the gateway — constructed lazily from the new public `PiExecutionService.model_manager()` accessor and injectable via the dispatcher's `embeddings_gateway=` constructor kwarg — while legacy keeps the unchanged `ollama.embed*` plane in `backend/app/core/agentic/legacy.py`. Gateway failures raise typed errors and never fall back to legacy; the W1 fail-closed stub `pi_embed_gateway_unavailable` is retired. W8 also fixed a latent W1 bug where `legacy._embed` passed `project_id=` to `OllamaClient.embed_batch`, which takes no such kwarg and would have raised `TypeError` on the real client.
- Usage-ledger accounting keeps the dispatcher's one-row-per-dispatch contract (master plan §5.5): `AgenticDispatcher.embed` records the single `purpose="embed"` accounting row and the gateway never writes rows itself, so a cache-miss embed is counted exactly once regardless of engine.
- Embedding accounting preserves provider-reported token usage and cost when an OpenAI-compatible response supplies them, including endpoint-rate pricing when token usage is present but provider cost is omitted. Local or remote responses without usage are recorded as governed estimates (with estimated input tokens and cost when configured), never as exact zero consumption.
- The shared embedding wrappers in `backend/app/core/embeddings.py` keep `embedding_cache` in front and route cache misses through `agentic.embed`. Model, cache namespace, and provisioning now come from `EmbeddingProfile` for every engine; engine selection cannot change vector identity. `backend/app/core/validation.py` `_get_embeddings` remains project-scoped and degrades to `[]` on failure.
- The new provisioner `backend/app/core/pi_runtime/model_manager_provisioning.py` (master plan §5.2.3) exposes `ensure_endpoint_model(endpoint, model)`: remote endpoints are a no-op (`False`), `kind=local` Ollama entries go through `OllamaClient.ensure_model` (list + pull), LM Studio entries use the existing `ComputeNode.load_model` JIT-load contract, and a disabled, unavailable, or false LM Studio load fails typed rather than being ignored. Unknown local planes fail typed (`provision_unsupported_local_endpoint:<id>`).
- Vector-space invariant: `assert_vector_space_invariant()` is an async startup gate that reuses `vector_health.check_embedding_dimensions()` to probe the legacy and Pi dispatcher paths independently with the configured model. It compares the provider-produced dimensions and model identity, raises `VectorSpaceInvariantError` on mismatch or an unusable probe, and `backend/app/main.py` converts that failure into a startup refusal. Gateway, dispatcher-wrapper, and cache writes reject empty, ragged, non-numeric, and non-finite vectors before they can poison stored vectors.
- Engine rollback changes orchestration behavior, not embedding authority. Istara and Pi loop choices
  share the active Pi-owned profile; changing the profile itself is not a rollback control and remains
  blocked until a governed re-embed/re-index/activation workflow is available.

## Architecture Notes

- The feature is mounted through `frontend/src/components/memory/MemoryView.tsx` and the UI navigation path recorded in the inventory.
- Health statistics are read through the project-scoped memory route after project visibility is verified.
- `MemoryView` remounts the Health tab on active-project changes so one project's memory statistics do not linger in another project view.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_memory.py`
- `tests/pi_production/test_embedding_profile_authority.py` covers persistence, provider independence,
  exact endpoint pinning, startup ordering, safe metadata, Lance binding, and profile-mismatch health.
- `tests/pi_production/test_w8_embeddings_gateway.py` verifies the W8 embeddings plane: MockTransport gateway HTTP behavior, `resolve_embed` ordering and anthropic-only fail-closed resolution, independent legacy/Pi startup probes and dimension mismatch refusal, malformed-vector rejection before cache writes, wrapper cache-in-front dispatch through `agentic.embed`, project-scoped validation embedding, provisioner behavior per endpoint kind, DB-projection reset, the merged settings model catalog, `ProjectUpdate.agentic_engine` validation, and static wiring checks.
- `tests/pi_production/test_w1_dispatcher_authority.py` and `tests/pi_production/test_w1_agentic_contract.py` assert embed dispatch now reaches the gateway on the Pi engine instead of the retired `pi_embed_gateway_unavailable` stub.
- `tests/test_validation_project_scope.py` asserts validation embedding project scope through the `agentic.embed` spy.
- `tests/pi_migration/test_count_to_zero.py` keeps the legacy allowlist ratchet green at 0; only permanent infrastructure entries remain allowlisted.
- Regenerate and validate the machine manifests and static site with `python scripts/feature_docs.py --seed-missing --generate-site --check`.

## Related Features

- [memory.knowledge](../../memory/knowledge/architecture.md)
- [quality.dashboard](../../quality/dashboard/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757; CF-SPEC-8 (Pi replacement W8 embeddings gateway + vector-space invariant)
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
