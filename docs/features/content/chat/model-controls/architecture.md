---
stable_id: chat.model-controls
title: Chat Model Controls
ui_path: Chat > Model Controls
audience: architecture
status: documented
related_features: ["settings.llm-servers", "settings.general", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/components/chat/chatViewParts.tsx", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/llm_servers.py", "backend/app/core/agentic/dispatcher.py", "backend/app/core/agentic/legacy.py", "backend/app/core/agentic/usage_ledger.py", "backend/app/core/pi_runtime/engine.py", "backend/app/core/pi_runtime/protocol.py"]
api_references: ["backend/app/api/routes/llm_servers.py", "backend/app/core/llm_router.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_llm_servers.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w1_agentic_contract.py"]
last_verified: 2026-07-20
compass: CF-SPEC-77 / CF-986; CF-SPEC-8
---

# Chat Model Controls Architecture

## Implementation Summary

Chat exposes model, thinking, and reasoning controls so users can tune how the assistant responds within the configured local or server-backed model environment.

## Frontend Surface

- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/components/chat/chatViewParts.tsx`
- `frontend/src/lib/modelProviders.ts`
- `backend/app/api/routes/llm_servers.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/chatStore.ts`

### API And Backend

- `backend/app/api/routes/llm_servers.py`
- `backend/app/core/llm_router.py`

Model controls may display shared LLM-provider availability, but the backing
server inventory and manual health-check APIs require authenticated global
access in team mode before endpoint status or capability metadata is returned.
Project prompt, retrieval, and compute payloads remain governed by the active
project routes that call the model controls.

### Agentic Dispatcher And Engine Selection (Pi Replacement W1)

- `backend/app/core/agentic/dispatcher.py` (`AgenticDispatcher`, module
  singleton `agentic`) is the single choke point for every agentic-loop or
  model invocation. It exposes exactly five verbs — `chat_turn`, `completion`,
  `structured`, `ensemble`, and `embed` — and contains no business logic: it
  only resolves the engine, executes, and records usage.
- Engine selection resolves in a fixed precedence order (first match wins):
  per-call override (benchmark harness / A2A envelope metadata), then the
  `x-istara-agent-engine` request header predicate, then the project setting
  `agentic_engine`, then `settings.agentic_engine_default`. A selected engine
  that cannot execute raises a typed dispatch error; the dispatcher never
  silently falls back to the other engine.
- Both engine seams are real: Pi selections execute through the isolated
  `PiExecutionService` (`run_completion` / `run_structured` / `run_react`), and
  legacy selections execute through the byte-compatible legacy executor
  (`backend/app/core/agentic/legacy.py`), which drives the same
  ComputeRegistry-backed `app.core.ollama.ollama` plane the 87 inventory sites
  already use — `ollama.chat` for completion/structured/ReAct and
  `ollama.embed_batch` for embed — with identical parameter names and message
  shapes, so Pi and legacy remain benchmarkable on the same axes. Neither seam
  ever falls back to the other: a selected engine executes or raises.
- `TurnParams` (`model`, `temperature`, `max_tokens`, `thinking_mode`,
  `min_context`, `timeout_s`, `max_turns`, `require_vision`) is forwarded
  unchanged on every verb. The Pi path maps them onto pi-ai turn options
  (`temperature`, `max_tokens`, `thinking_level`, provider `timeout_ms`);
  `min_context` and `require_vision` map to capability admission in the Pi
  model catalog, and `max_turns` bounds the ReAct tool loop.
- Structured output is a forced tool call, never free-form JSON text: the Pi
  worker registers an `emit_structured_output` capture tool
  (`pi-runtime/src/structured.mjs`) whose parameters are a mechanical
  JSON-Schema translation (unsupported constructs fail closed at session open
  with `structured_output_schema_unsupported`, never mid-turn) and forces that
  tool choice. A turn that answers with free-form text instead of the forced
  call raises `structured_output_missing`; Python then revalidates the captured
  object against the original JSON Schema, allows exactly one bounded repair
  turn, and raises a typed `structured_output_invalid` fail-closed failure
  instead of returning an error-shaped result. The legacy structured path keeps
  using `llm_schema_adapter`'s OpenAI-compatible JSON-schema `response_format`
  plus `parse_json_object`, so both engines yield a schema-validated object and
  stay methodologically comparable.
- The Pi worker wire protocol is versioned (`PROTOCOL_VERSION = 2`, pinned in
  both `backend/app/core/pi_runtime/protocol.py` and
  `pi-runtime/src/protocol.mjs`); v2 is what carries the forced structured
  frames (`output_schema`, `tool_choice`, and the captured `structured`
  object). Both sides validate the version at handshake and per frame, and a
  worker answering with a mismatched version is rejected
  (`protocol_version_mismatch`) and reclaimed rather than used.
- Every dispatcher call persists exactly one durable, queryable usage-ledger
  row (`backend/app/core/agentic/usage_ledger.py` writes `AgenticUsageRow` into
  the `agentic_usage_rows` table, migration `023_agentic_usage_ledger`)
  regardless of engine or outcome: success, error, abort, endpoint-resolution
  failure, and a raising legacy executor each record their one row, with
  pre-dispatch failures zeroed and stamped `error_type`. Pi rows carry exact
  pi-ai usage including `cost.total`; legacy rows carry provider-reported usage
  where present and otherwise estimate input/output with the existing
  `count_tokens` counter and mark `estimate=true` — estimated and exact numbers
  are never mixed silently. A separate short identity-only trace span
  (`event_kind="agentic_usage"`,
  `route_id="agentic:<engine>:<endpoint|node|unresolved>"`) is recorded for
  trace continuity; the accounting row never lives inside that 120-char
  identity field. Ledger identity fields carry `endpoint_id`/`node_id` only,
  never endpoint URLs, keys, prompts, or response content.

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `frontend/src/lib/modelProviders.test.ts`
- `tests/test_llm_servers.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [settings.llm-servers](../../settings/llm-servers/architecture.md)
- [settings.general](../../settings/general/architecture.md)
- [compute.pool](../../compute/pool/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-77 / CF-986; CF-SPEC-8 (Pi replacement W1 dispatcher)
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.

## Model-management compatibility (2026-08-22)

Legacy `LLMServer` rows are projected into the Pi canonical resolver through a
secret-free, idempotent plan. Relay rows remain `legacy_only`; malformed or
unsupported rows are `blocked`; no source row is deleted. The projected provider
set (ollama, lmstudio, openai_compat, anthropic, anthropic_compat, vllm, sglang,
llamacpp, mlx) is the single source of truth shared with the Pi catalog
projection (`PiModelManager._project_llm_server`), so a row the plan marks
`projected` always reaches the catalog and a `blocked` row never does. Admins can
inspect counts, source checksums, and rollback readiness at
`GET /api/settings/model-management/migration-status`. Engine selection remains
explicit and fail-closed: a Pi/provider failure never falls back to legacy.
