# Agentic Core — Dispatcher, Engines, and the Count-to-Zero Contract

Spec lineage: `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`
(waves W0–W9). Status: **complete (W9)** — the migration ratchet is at 0.

The agentic core is the single choke point for every model invocation in
Istara product code. No product module calls a model transport directly;
everything enters through the `AgenticDispatcher`
(`backend/app/core/agentic/dispatcher.py`), which resolves an engine,
executes, and records usage. The dispatcher contains no business logic and
never silently switches engines.

## The five verbs (plus the task seam)

Product call sites use exactly these entry points:

| Verb | Used for | Examples |
|---|---|---|
| `chat_turn` | stateful multi-message turns | A2A collaboration replies, chat |
| `completion` | single text completions | report narratives, interview follow-ups, debate rounds |
| `structured` | schema-bound JSON output (Pi forced-tool subset) | MECE categorization, LLM-as-judge, dual-coder |
| `ensemble` | n-sample consensus, optionally `distinct=True` (fail-closed) | dual_run, full_ensemble, self_moa |
| `embed` | embedding vectors | semantic skill match, RAG, consensus embeddings |

The W1 `react` seam covers the agentic task loops (chat, interfaces,
research spine, steering). `distinct=True` ensembles never fabricate
diversity from one endpoint: they fail closed
(`PiEndpointResolutionError` / `insufficient_distinct_legacy_servers`) and
degrade down the documented chain (full_ensemble → dual_run → self_moa).

## Engine resolution

First match wins:

1. per-call override (`engine=` — benchmark harness, A2A envelope metadata)
2. request header `x-istara-agent-engine`
3. project setting `projects.agentic_engine` (`"legacy"` / Pi value / `""` =
   inherit)
4. global `settings.agentic_engine_default` (`"legacy"` until the owner
   flips the rollout)

Two engines:

- **legacy** — `backend/app/core/agentic/legacy.py`. The permanent legacy
  executor preserves the pre-dispatcher behavior on the existing
  ComputeRegistry/ollama plane, including the distinct-server ensemble used
  by validation. This is the benchmark baseline and the default today.
- **pi** — `PiExecutionService` / `PiModelManager`
  (`backend/app/core/pi_runtime/`). Endpoint identities come from the Pi
  catalog projection of persisted LLM server entries; provisioning
  (`ensure_endpoint_model`) handles local Ollama/LM Studio JIT loading and
  fails typed on unknown or unavailable planes.

Embeddings follow the same dispatch: legacy engine → the unchanged
`ollama.embed*` plane via the legacy executor; Pi engine → the W8
`EmbeddingsGateway` (`pi_runtime/embeddings_gateway.py`), which enforces the
vector-space invariant (dimension/dtype validation, startup probes in
`main.py`) and normalizes provider usage accounting.

## Usage accounting

Every verb records exactly one row per dispatch in the agentic usage ledger
(`agentic/usage_ledger.py`) — success, error, abort, endpoint-resolution
failure, and legacy-executor failure alike. The embeddings gateway never
writes its own rows; the dispatcher's `purpose="embed"` row is the single
accounting record. Result-returning verbs expose the endpoint identity and
status fields their typed result supports (`endpoint_id` or `endpoint_ids`);
the `embed` verb returns vectors only. Durable route evidence lives in the
usage row (`endpoint_id`, `node_id`, outcome) and its identity-only telemetry
span (`route_id`), not in a presumed result envelope, so traceability can audit
which endpoint produced a dispatch without storing prompts, responses, URLs,
or keys.

## The count-to-zero contract (W9 final state)

Direct legacy-plane calls (`ollama.*`, `llm_router.*`,
`compute_registry.*` aliases, direct per-node dispatch, unmarked
`ChatOpenAI` browser bypasses) are forbidden in `backend/app/` product code.
The contract is enforced mechanically:

- `scripts/pi_migration_inventory.py` — deterministic scanner for direct
  legacy-plane call sites (patterns from master plan §4.1). A
  `ChatOpenAI(` construction whose endpoint identity is resolved through
  `PiModelManager` carries the inline `# pi-governed` marker and is exempt
  (F-W2-1b governance decision); unmarked constructions are flagged.
- `tests/pi_migration/legacy_allowlist.yaml` — the ONLY file allowed to
  authorize a direct call. **Final state: `product: []`,
  `ratchet.expected_product_sites: 0`, permanent entries only.** The
  permanent section names the infrastructure that never migrates (master
  plan §4.3): donated-compute transport and relay routes, donor
  scheduling/authorization, donor lifecycle/telemetry/heartbeat,
  legacy-engine internals (the benchmark baseline, including the
  dispatcher's own legacy executor), and local model lifecycle
  (provisioning/JIT load/recovery).
- `tests/pi_migration/test_count_to_zero.py` — asserts
  `inventory ⊆ allowlist` and the ratchet literal (0). Any new direct call
  fails CI.
- `scripts/check_integrity.py` — runs the same ratchet
  (`check_pi_migration_count_to_zero`) as part of release-governance
  integrity.

W9 retired the per-site legacy fallthrough branches that waves W4–W7 had
preserved behind the `agentic_core` feature flag: the dispatcher path is
now the only path in the 53 affected sites (A2A handlers, skills, reports,
interview services, autoresearch runners, validation/consensus/dual-coder).
Behavior under `engine="legacy"` is preserved by construction, because the
legacy plane is still reached — exclusively through the dispatcher's
permanent legacy executor. The `agentic_core` setting survives only as the
engine-string default for the autoresearch subsystem
(`autoresearch_runners/__init__.py: resolve_engine`); it no longer gates
product call-site branches. Autoresearch binds an explicit `pi` or `legacy`
choice once at experiment start, while other dispatcher callers use the
precedence documented above.

## User-facing Agentic Core and chat controls

Global Settings and Project Settings use the shared `AgenticCoreSection` rather than a compact status-grid select. It explains Pi and Istara in non-specialist language, shows the shared embedding invariant, and labels benchmark comparisons provisional with source and date. Project choice remains inherit/Pi/Istara and preserves dispatcher precedence.

Chat uses `ChatModelControls`: the provider/model menu supports both browseable dropdown and autocomplete; unconfigured catalog entries are visible but disabled; selecting a configured model persists both `model_override` and `endpoint_override` so equal model ids from OpenAI API and OpenAI Codex cannot collide. The effort menu is populated from Pi's exact `thinkingLevels` metadata. The usage popover and `GET /api/chat/usage/{project_id}` show content-free input/output/total/cache read/cache write/cost/turn/context telemetry and explicitly distinguish provider-reported values from estimates. `/api/chat` adds a usage SSE event without changing transcript events.

## Pi authentication boundary

Pi model management is catalog-driven: `GET /api/settings/pi-catalog` and project-readable `GET /api/chat/model-catalog` expose provider/model capability metadata, never secrets. OpenAI is represented accurately as OpenAI API versus OpenAI Codex — ChatGPT subscription. Codex exposes Pi's two login choices: browser PKCE with state-verified callback and headless device code. Browser callbacks return only a success/failure page; access/refresh tokens remain in Keychain or encrypted local custody. The worker has a distinct `openai_codex` transport for the Codex Responses API.

## What the agentic core is not

- It is transport and accounting, not evidence. Model outputs still enter
  the Research Spine as candidate artifacts and must pass the source-grounded
  coding, reliability, reconciliation, and human-review gates before they are
  reportable (`docs/architecture/research-validity-contract.md`).
- It does not weaken project isolation: every verb carries `project_id`,
  and donor/endpoint authorization stays in the registry's project-scope
  checks.
- It does not delete the legacy plane. The registry, transports, and probes
  remain as the legacy engine, the donor network, and the benchmark
  baseline — reachable only through the dispatcher from product code.

## Key files

- `backend/app/core/agentic/dispatcher.py` — engine resolution + verbs
- `backend/app/core/agentic/legacy.py` — permanent legacy executor
- `backend/app/core/agentic/usage_ledger.py` — one-row-per-dispatch accounting
- `backend/app/core/pi_runtime/` — Pi engine, model manager, endpoints,
  embeddings gateway, provisioning
- `scripts/pi_migration_inventory.py` — legacy-plane scanner
- `tests/pi_migration/legacy_allowlist.yaml` + `test_count_to_zero.py` —
  the ratchet
- `tests/pi_production/` — per-wave contract suites (W1–W8)

## Embedding and control invariants

Chat controls affect generation only and must never select or mutate the
embedding model. Both engines use the configured default embedding model;
startup probes compare provider-reported model and dimension before switching
is trusted. Provider responses and cached vectors share one typed validation
boundary, and cache hits are additionally checked against the engine's known
dimension for that model (probe- and provider-established): stale-dimension or
malformed entries are discarded and re-embedded, and unverifiable entries are
treated as misses (fail closed).
