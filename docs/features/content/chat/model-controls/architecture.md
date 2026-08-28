---
stable_id: chat.model-controls
title: Chat Model Controls
ui_path: Chat > Model Controls
audience: architecture
status: documented
related_features: ["settings.llm-servers", "settings.general", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/components/chat/ChatModelControls.tsx", "frontend/src/components/chat/chatViewParts.tsx", "frontend/src/components/common/SettingsView.tsx", "frontend/src/components/settings/PiModelManagement.tsx", "frontend/src/lib/modelCatalog.ts", "frontend/src/stores/chatStore.ts", "frontend/src/stores/sessionStore.ts", "frontend/src/lib/chatApi.ts", "frontend/src/lib/modelProviders.ts", "backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py", "backend/app/api/routes/settings.py", "backend/app/main.py", "backend/app/core/agentic/dispatcher.py", "backend/app/core/agentic/legacy.py", "backend/app/core/agentic/usage_ledger.py", "backend/app/core/pi_runtime/engine.py", "backend/app/core/pi_runtime/oauth.py"]
api_references: ["backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py", "backend/app/core/agentic/usage_ledger.py"]
test_references: ["frontend/src/lib/modelCatalog.test.ts", "frontend/src/lib/modelProviders.test.ts", "tests/test_chat.py", "tests/test_settings.py", "tests/test_settings_agentic_pi_endpoints.py", "tests/pi_migration/test_model_management_migration.py", "tests/pi_production/test_pi_catalog_ux.py", "tests/pi_production/test_w1_agentic_contract.py", "tests/pi_production/test_w1_dispatcher_authority.py", "tests/pi_production/test_legacy_long_horizon.py", "tests/pi_production/test_chat_pi_asgi.py", "tests/benchmarks/long_horizon_runner.py", "tests/simulation/scenarios/10-settings-models.mjs", "tests/simulation/scenarios/26-model-session-persistence.mjs"]
last_verified: 2026-08-27
compass: CF-SPEC-77 / CF-986; CF-SPEC-8
---

# Chat Model Controls Architecture

## Implementation Summary

Chat exposes a workbench-style model and effort menu so users can choose the provider/model and the exact provider-native effort levels supported by that model. A usage menu reports input, output, total, cache-read, cache-write, cost, context used, turns, engine, stop reason, and whether the values are exact or estimated.

## Frontend Surface

- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/components/chat/chatViewParts.tsx`
- `frontend/src/lib/modelProviders.ts`
- `backend/app/core/pi_runtime/model_manager.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/chatStore.ts` — transcript streaming plus session usage totals.
- `frontend/src/stores/sessionStore.ts` — active model, endpoint, and effort selection.

### API And Backend

- `backend/app/api/routes/settings.py`
- `backend/app/core/pi_runtime/model_manager.py`

`ChatModelControls` is visible in Chat for project viewers with a selected session. It has one browseable, searchable model menu (chevron opens the list; typing filters it), an exact effort select populated from Pi `thinkingLevels`, and a usage popover. Pi catalog entries that are not configured are visible but disabled with an explanation; legacy engine mode exposes the safe local/server model inventory instead. Choosing a configured Pi entry persists both `model_override` and `endpoint_override`, so two providers exposing the same model id cannot silently collide.

`GET /api/chat/model-catalog` is project-scoped and secret-free. Its configured Pi entries are filtered through the same project-admission predicate used by resolution, so an unauthorized Petals donor is not presented as selectable and then rejected only after dispatch; the global settings catalog remains unscoped. `GET /api/chat/usage/{project_id}` is project/session-scoped and returns content-free ledger aggregates plus per-dispatch identity rows (`session_id`, `purpose`, engine, model, endpoint/node handles, task binding, outcome, and accounting flags), so a bounded client can prove that every chat turn belongs to the requested session, authorized task, and requested engine rather than trusting only the latest row or the query filter. `POST /api/chat` accepts an optional project-scoped `task_id` and emits an additive `usage` SSE event after each governed turn. Existing transcript/session payloads remain backward compatible.

### Agentic Dispatcher And Engine Selection (Pi Replacement W1)

The selected Chat model menu is a generation control only. It never changes the embedding model or the research-validity gates. Provider-native effort is forwarded to Pi as `TurnParams.thinking_mode`; the legacy prompt control remains conservative and never exposes private reasoning.

- `backend/app/core/agentic/dispatcher.py` (`AgenticDispatcher`, module
  singleton `agentic`) is the single choke point for every agentic-loop or
  model invocation. It exposes exactly five verbs — `chat_turn`, `completion`,
  `structured`, `ensemble`, and `embed` — and contains no business logic: it
  only resolves the engine, executes, and records usage.
- `backend/app/core/agentic/__init__.py` re-exports that module singleton rather
  than constructing a second dispatcher; package and module imports therefore
  share one Pi authority and one usage/instrumentation state.
- Engine selection resolves in a fixed precedence order (first match wins):
  per-call override (benchmark harness / A2A envelope metadata), then the
  `x-istara-agent-engine` request header predicate, then the project setting
  `agentic_engine`, then `settings.agentic_engine_default`. A selected engine
  that cannot execute raises a typed dispatch error; the dispatcher never
  silently falls back to the other engine. The per-call boundary normalizes
  every supported Pi spelling (`pi`, `pi-candidate`, `pi-replacement`, and
  `deepseek-pi`) before branching, so direct A2A/benchmark/service callers
  cannot accidentally route an admitted Pi request through the legacy loop.
- Both loop seams are real: Pi selections execute through the isolated
  `PiExecutionService` (`run_completion` / `run_structured` / `run_react`), and
  Istara selections execute through the Python legacy executor
  (`backend/app/core/agentic/legacy.py`). That executor retains Istara's loop
  and Python tool semantics but delegates provider-only turns, structured
  output, ensembles, and embeddings to Pi Model Management. Both are first-
  class loop modes over one provider/model authority and remain benchmarkable
  on the same axes. Neither seam silently changes loop mode on failure.
- Provider identity is carried separately from the requested/configured model:
  Pi terminal receipts expose `served_model` when the provider reports it, and
  the dispatcher preserves that field through streamed `chat_turn` results and
  usage-ledger accounting. The legacy loop's provider-only turns use the same
  Pi-managed resolver, so both loop choices can be compared against one
  endpoint/model authority without treating a configured label as proof of
  service. Formal Research Spine coding remains fail-closed when this receipt
  is absent.
- `TurnParams` (`model`, `temperature`, `max_tokens`, `thinking_mode`,
  `min_context`, `timeout_s`, `max_turns`, `require_vision`) is forwarded
  unchanged on every verb. The Pi path maps them onto pi-ai turn options
  (`temperature`, `max_tokens`, `thinking_level`, provider `timeout_ms`);
  `min_context` and `require_vision` map to capability admission in the Pi
  model catalog, and `max_turns` bounds the ReAct tool loop. The chat route's
  eight-tool ceiling maps to nine Pi model-turn starts (initial response,
  eight possible tool continuations, then the final synthesis turn), matching
  the legacy loop instead of failing one model turn early.
- **Embedding identity policy (W3).** Chat controls are generation controls
  only: temperature/thinking/effort never select or mutate the embedding
  model. Both loop modes embed through the Pi-governed gateway with the one canonical model
  (`default_embed_model()` / `_embed_model_name()`), and the engine selector
  in Project Settings surfaces that identity as safe metadata (`embed_model`
  in the project response — model name only, never an endpoint/URL/key) and
  never offers a per-engine embedding choice. Cached embedding vectors are
  validated against the engine's known dimension for that model (established
  by the startup vector-space probes and every validated provider response):
  a numeric entry written under a different embedding model/dimension is
  discarded and re-embedded instead of flowing into retrieval, and entries
  whose dimension cannot be verified yet are treated as misses (fail closed).
  See the "Engine buttons" paragraph in
  [settings.project](../../settings/project/architecture.md) for the
  evidence-backed, provisional comparative summaries shown next to the
  selector.
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
  pi-ai usage including `cost.total` when every sample has a provider receipt;
  mixed/absent real-provider ensemble usage is estimated as one complete
  dispatch from preserved sample text. The public ensemble result and durable
  row share this all-or-nothing boundary. Legacy rows carry provider-reported
  usage where present and otherwise estimate input/output with the existing
  `count_tokens` counter and mark `estimate=true` — estimated and exact numbers
  are never mixed silently.
  A separate short identity-only trace span
  (`event_kind="agentic_usage"`,
  `route_id="agentic:<engine>:<endpoint|node|unresolved>"`) is recorded for
  trace continuity; the accounting row never lives inside that 120-char
  identity field. Ledger identity fields carry `endpoint_id`/`node_id` only,
  never endpoint URLs, keys, prompts, or response content.

## Architecture Notes

- The feature is mounted through `frontend/src/components/chat/ChatView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agentic Core Resolution (CF-SPEC-1)

Each chat turn resolves its engine in one order: operator flag `pi_replacement_enabled` → per-request header `x-istara-agent-engine` → persisted `projects.agentic_engine` → global `settings.agentic_engine_default`. The model-catalog indicator calls the same resolver, so the picker cannot advertise a different engine under an operator flag or request override. The frontend echoes the core shown in the model-controls chip through that header (`chatStore.engine`, sourced from `/api/chat/model-catalog`); when the catalog is unavailable the header is omitted so the persisted choice governs. Deployments that declare their provider plane as a deterministic wire stub (`LLM_PROVIDER_CONTRACT_STUB=true`, set by the QA and connectivity-acceptance stacks) reject interactive chat before any session or message write with an SSE `provider_stub_chat_blocked` error instead of serving canned contract text. The legacy/Istara preflight asks the same Pi Model Management resolver with the requested `project_id`, so a Petals projection from another project's consent scope cannot admit a turn and an authorized later donor is still considered. The resolver also excludes Pi catalog entries marked `kind=local` while that stub flag is set; a deterministic stack therefore cannot accidentally execute its local Ollama/LM Studio fixture while still allowing an admitted remote Pi endpoint to serve the test.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `frontend/src/lib/modelProviders.test.ts`
- `tests/test_settings_agentic_pi_endpoints.py`
- `tests/test_model_source.py` — explicit/default local selections resolve through the Pi catalog, and stub-marked stacks filter local catalog entries before fallback.
- `tests/pi_production/test_w1_agentic_contract.py`
- `tests/pi_production/test_w1_dispatcher_authority.py` — shared Pi Model Management authority for both engine choices, including legacy/Istara multi-turn tool-loop execution, cumulative usage, and provider-served identity preservation.
- `tests/pi_production/test_legacy_long_horizon.py` — seven-step legacy/Istara tool-loop horizon parity through the same shared manager, with cumulative usage and served-identity assertions.
- `tests/pi_production/test_pi_ensemble_accounting.py` — Pi ensemble usage exactness is all-or-nothing across samples; mixed provider receipts produce an explicit estimate rather than a partial exact ledger row.
- `tests/pi_production/test_chat_pi_asgi.py` — real-ASGI two-call transcript rehydration after worker restart for both the native Pi loop and the legacy Istara loop over the shared Pi Model Management service.
- `tests/benchmarks/long_horizon_runner.py` — Docker-only two-call acceptance binds both dispatch receipts to one authorized task and requires unique, successful model/endpoint provenance.

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

## Sole model-management write authority (2026-08-25)

Pi Model Management is the only model/provider write authority for every
agentic engine. The Istara in-process loop and the Pi Agentic Loop retain their
different orchestration semantics, but both resolve model identity and
endpoint identity through the Pi-managed catalog. Local servers and donated
compute remain transport/lifecycle infrastructure; they do not create a
second model catalog or global provider selector.

The Settings selector therefore presents two canonical execution modes: `Pi`
and `Istara` (the legacy-compatible in-process loop). The Istara description
must name the shared Pi Model Management catalog as its provider/model
authority; references to a standalone “ComputeRegistry/Ollama plane” or
“legacy plane” are transport-compatibility terminology, not a second
management endpoint or an independent model-selection path.

## Regular DashScope custom-provider contract (2026-08-28)

Pi 0.84.3 can load regular Alibaba DashScope Model Studio through the custom
provider file `~/.pi/agent/models.json`, using the OpenAI-compatible base URL
`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, the
`DASHSCOPE_API_KEY` environment reference, and Qwen compatibility flags that
emit `enable_thinking` rather than unsupported `reasoning_effort`. Istara's
canonical catalog mirrors this as the separate `dashscope` provider with
`qwen3.7-plus` and `qwen3.7-flash` entries, so PI Model Management can resolve
the same identity instead of rejecting the provider or silently rewriting it
to Qwen Token Plan. The regular DashScope credential and Token Plan
credentials/base URLs are not interchangeable; a Token Plan login must remain
labelled and tested as its own provider. Docker acceptance must inject the
DashScope key only into the container process and must record the provider-
reported `served_model` before either Qwen endpoint can count as an
independent Research Spine coder.

The former `POST /api/settings/model` and `POST /api/settings/provider` routes
remain only as authenticated deprecated adapters for older clients. They
always return `410 pi_model_management_required` with a successor link to
`/api/settings/pi-endpoints` before model discovery, pulling, provider
reconstruction, settings mutation, or environment persistence. Read-only
`GET /api/settings/models` remains a compatibility inventory while clients
migrate; it exposes both transport inventory and a secret-free Pi catalog.
Every merged Settings row is explicitly non-switchable. Settings labels Pi
entries as managed by Pi and classical rows as compatibility/active-transport
inventory, renders no classical Switch or Pull control, and exposes no
frontend `switchModel` or `switchProvider` client. Endpoint creation, update,
deletion, authentication, and model admission live only in
`PiModelManagement` through `/api/settings/pi-endpoints`.

## Qwen thinking compatibility (2026-08-28)

Custom OpenAI-compatible endpoints resolved by Pi Model Management carry their
non-secret `pi_provider` identity into the worker. Qwen, Qwen Cloud/DashScope,
and the Qwen Token Plan variants are marked as reasoning-capable with Pi's
Qwen compatibility contract, so a non-`off` `thinking_level` emits
`enable_thinking: true` and does not emit the unsupported OpenAI
`reasoning_effort` field. The contract is covered by a deterministic worker
payload test; live acceptance must still prove the provider-served model,
thinking output/metadata, and endpoint/account provenance inside the Docker
runner. A regular `sk-ws-*` DashScope credential must not be labeled as a
Token Plan credential unless the configured Token Plan endpoint accepts it.

Codex OAuth model receipts use Pi's SSE transport for these managed turns.
Pi's optional Codex WebSocket path does not expose the terminal response
metadata to Istara's served-model observer, so allowing it here would permit a
successful `gpt-5.6-luna` request without a provider-reported identity. A
Codex turn without `served_model` remains usable for ordinary chat but cannot
count as an independent Research Spine coder.

The simulation harness likewise never pins or restores a classical global
model. A requested fixed test model must already be admitted in the Pi catalog
or setup fails with an actionable error. Settings scenario 10 proves the Pi
management surface is visible and classical mutation controls are absent;
scenario 26 proves both deprecated writes return 410 with the Pi successor and
that their negative probes leave the read-only inventory unchanged before it
continues with session persistence coverage.

Application startup may register configured transport nodes, discover/load
transport registrations, and run health checks. It must not automatically
choose another provider, pull a chat model, issue a chat-completion probe to
guess the loaded model, mutate the configured chat model, or persist that
choice. Model loading happens only on explicit governed request paths.
