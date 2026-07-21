# MASTER PLAN — Full Pi Replacement of Istara's Agentic Loop & Model Management (except Petals)

<!-- STATUS BLOCK -->
```yaml
item: pi-full-replacement
branch: Review_pi_test (continue in this worktree)
cf: { spec: CF-SPEC-8 (to be created at M0 — see §12), predecessor: CF-SPEC-7 }
phase: "Master plan authored; execution not started"
stage: S1-plan (this document IS the approved plan seed for the conductor)
status: ready-for-conductor
blocked_on: "owner approval of this plan + benchmark budget envelope (§10.6, §13)"
authored_by: claude-fable-5 (independent reviewer of CF-SPEC-7), 2026-07-20
grounding: all file:line references verified on Review_pi_test @ c1d3d7ff via 6 parallel
  code-reading agents + Compass Forge impact queries; see §14 Method
next_action: "Owner reviews §13 decision points; then run /conductor with this file as the
  governing plan (do NOT let the conductor re-plan from scratch — see §12.1)"
```
<!-- /STATUS BLOCK -->

## Read this first (for every agent that opens this file)

**Mission.** Migrate EVERY process and call that goes through Istara's original agentic
loop and model management — except Petals-style donated compute — to the Pi runtime
(`pi-runtime/` Node worker hosting `@earendil-works/pi-agent-core@0.80.10` +
`backend/app/core/pi_runtime/`), with **no placeholder code and no endpoint left
untouched**, then run an industry-class paired benchmark of Pi vs. Istara's native engine
across the 10 evaluation axes in §10, documented both as Build Stream lifecycle records
and as an academic article comparing ReAct engines (§11).

**Definition of done (the only definition that counts):**

> If any product LLM call site outside the explicit Petals allowlist (§4.3) still invokes
> `ollama.chat`, `ollama.chat_stream`, `llm_router.chat`, `compute_registry.chat*`, or
> `node.chat` directly — instead of going through the `AgenticDispatcher` (§5.1) with a
> **fully implemented** Pi path — the migration is NOT complete. This is enforced by a
> machine-checkable count-to-zero ratchet test (§4.2), not by prose claims.

**Engine Parity Principle.** The legacy engine is NOT deleted in this plan. Every surface
routes through the dispatcher, which can execute the turn on `engine=pi` or
`engine=legacy`. Both paths must be complete and production-real — that is what makes the
paired benchmark (§10) valid. Deleting the legacy path is a post-benchmark owner decision
(explicitly out of scope, §13.4). "No placeholder code" applies to the **Pi path**: every
dispatcher call must reach the real pi-agent-core Agent through the real worker; stubs,
canned responses, `NotImplementedError`, and silent legacy fallbacks are forbidden.

**Fail-closed rule (inherited from CF-SPEC-7, still binding).** When `engine=pi` is
selected and the Pi path cannot run (endpoint/secret/worker failure), the request fails
with a typed error. It never silently falls through to legacy. `engine=legacy` behavior
stays byte-identical to today.

**What is explicitly OUT of scope:** Petals/donated relay+browser compute (§4.3 allowlist —
never touch); Whisper STT (`transcription.py:187,264` — speech-to-text, not the agentic
loop); Google Stitch external design API (`design_tools.py:175,338,444` — third-party SaaS,
not model routing); deleting the legacy engine; external live channel traffic; `LLMs/` and
`Model_Finetuning/` folders.

---

## 1. Ground truth: where we actually are

Read these two documents before writing any code:

1. `/Users/user/Documents/Istara-main/comparison-Istara-pi/2026-07-20-pi-replacement-review-diagnosis.md`
   — the independent review of the CF-SPEC-7 branch. Its findings register (A/B/C IDs) is
   referenced throughout this plan. Headline: the current candidate covers **2 of 69
   product chat call sites**; 2 Blocker + 6 Major runtime defects are open; several
   hardening claims are documented but not implemented; the test layer never drives real
   ASGI routes.
2. `docs/build-stream/2026-07-20-pi-production-runtime-completion.md` — the CF-SPEC-7
   lifecycle file (what exists and how it got here).

What already exists and is REAL (verified, reuse it):

| Asset | Where | State |
|---|---|---|
| Node worker hosting real Agent, NDJSON stdio protocol | `pi-runtime/src/{worker,session,provider,protocol,tools}.mjs` (~620 LOC) | Works; needs §6 hardening |
| Python supervisor (one child, lazy start, handshake) | `backend/app/core/pi_runtime/supervisor.py` (360 LOC) | Works; has B-1/B-2 blockers |
| `PiExecutionService` + 4 seams (chat, delegation, pi_local, autoresearch) | `backend/app/core/pi_runtime/engine.py` (502), `seams.py` (212) | Works opt-in; narrow API |
| Identity-pinned endpoint resolver, Keychain secrets, registry-disjoint | `backend/app/core/pi_runtime/endpoints.py` (105) | Works; extend into PiModelManager (§5.2) |
| Tool catalog export from `OPENAI_TOOLS` + authority round-trip | `backend/app/core/pi_runtime/tools.py`, `engine.py:183-187` | Works; allowlist NOT enforced (B-12 → §6) |
| Donor-isolation proof both directions | `tests/pi_production/test_same_model_donor_isolation.py` | Keep green forever |
| 32 seam-level production tests + 13 candidate tests + 4 node tests | `tests/pi_production/`, `tests/test_pi_replacement_candidate.py` | Green; upgrade per §6.3 |

Key upstream API facts that CONSTRAIN the design (verified against
`pi-runtime/node_modules/@earendil-works/*/dist/*.d.ts`, v0.80.10):

- **pi-ai has NO structured-output / response_format / JSON-mode API.** The only
  mechanisms are (a) forced tool call via `toolChoice` and reading `toolCall.arguments`,
  or (b) prompt-and-parse. Istara uses `response_format` with strict JSON schemas at
  multiple sites (planner `agent_research.py:478`, skill factory `skill_factory.py:717`,
  research-validity coder `research_validity_service.py:556`). → §5.4 defines
  **structured-via-forced-tool** as the standard replacement.
- **pi-ai has NO embeddings API** (grep-confirmed absent). → §9 Embeddings Gateway.
- **Vision input IS supported** (`ImageContent`, `model.input: ("text"|"image")[]`).
- **Custom endpoints** are built with a `Model` object carrying `baseUrl` (per-model) and
  `api: "openai-completions" | "anthropic-messages"`, optionally via `createProvider()`;
  Ollama is addressable at `http://localhost:11434/v1`, LM Studio at
  `http://localhost:1234/v1`.
- **Usage is exact and rich**: `{input, output, cacheRead, cacheWrite, totalTokens,
  cost:{...,total}}` per assistant message, plus `stopReason` — this powers the token/cost
  axes of §10 natively.
- `Agent.steer/followUp` take an `AgentMessage` object (not a string); `abort()` and
  `waitForIdle()` exist; `toolExecution: "sequential"` is already what we use.
- Provider-level `timeoutMs`, `maxRetries`, `maxRetryDelayMs` exist on `StreamOptions` —
  the current worker ignores them (diagnosis B-12); §6 wires them.

## 2. Full inventory: every call that goes through the loop / model plane today

The single load-bearing routing fact (verify before believing anything else):

```
backend/app/core/ollama.py:383      ollama = compute_registry
backend/app/core/llm_router.py:73   llm_router = compute_registry
```

Every `ollama.*` / `llm_router.*` product call terminates in
`ComputeRegistryInvocationMixin.chat` (`compute_registry_invocation.py:205`),
`.chat_stream` (`:546`), `.embed` (`:924`), `.embed_batch` (`:987`).

**Totals (exhaustive sweep, two independent agents, cross-checked against Compass Forge
reverse-import analysis of `ollama.py` → 21 consumers and `llm_router.py` → 16 consumers):**

- **69 product chat call sites** (40 in `backend/app/core/`, 29 in
  `api/routes/ + services/ + agents/ + skills/`; the core sweep's own summary line said
  39 but its table contains 40 rows — the table is authoritative, recounted)
- **17 product embedding call sites** (all funneling through `embeddings.py:50,90` +
  `validation.py:522`)
- **1 external agent loop** bypassing the registry entirely: `browser_service.py:83`
  (browser-use + `langchain_openai.ChatOpenAI`, its own 10-step loop) — reached from chat
  tool `browse_website`
- **~30 infrastructure/transport sites** inside the registry/node/provider clients
  (stay: they ARE the legacy engine + donated-compute plane)
- Out of scope: Whisper ×2, Stitch ×3

The complete per-site tables (file:line, enclosing function, params, output handling,
loop membership) are embedded in the wave sections (§8) — every one of the 69+17+1 sites
appears in exactly one wave (checksum: W2:9 + W3:8 + W4:3 + W5:28 + W6:14 + W7:8 = 70
chat+browser, + W8:17 embeds = 87 = full product inventory). If during implementation you find a site not listed here,
you MUST add it to the inventory script (§4.2) and to the correct wave table in this file
in the same commit — that is how the map stays alive.

Mapping protocol used and to be repeated per wave (Compass Forge — see §3): grep finds
call sites; CF `intelligence impact` finds consumers grep misses (it found
`devops_agent.py`, `agent.py`, `agent_models.py`, `adaptive_validation.py`,
`settings.py`, `network_discovery.py` — all import-only or health-only, verified).

## 3. Compass Forge mapping & execution protocol (mandatory, every wave)

Compass Forge is the execution record. Run everything from the worktree root
(`/Users/user/Documents/Istara-main-pi-replacement`) so CF resolves the right project.

Per wave, in order:

```bash
# 1. Before touching code — capture the gate baseline for the wave task
compass-forge gate before --task <CF-task-id> --summary

# 2. Map the blast radius of every file you will touch (repeat per file)
compass-forge intelligence impact --path backend/app/core/agent_research.py --limit 100
compass-forge intelligence test-impact --path backend/app/core/agent_research.py

# 3. Pull a context pack for the change intent (cheaper than re-reading everything)
compass-forge context "migrate research spine ReAct loop to PiExecutionService" --pack-type standard

# 4. Ask CF what tests the change implies, and reconcile with the wave's test list
compass-forge suggest-tests "replace ollama.chat in agent_research.py with agentic dispatcher"

# 5. While implementing: record evidence rows on your CF task
compass-forge task evidence <task-id> --kind command ...   # (use the task evidence flow the
                                                           # conductor harness already records)

# 6. After the wave's ladder is green
compass-forge gate after --task <CF-task-id> --summary     # 0 new/actionable required
compass-forge decision record --title "W<N> complete" --body "<counts + ladder results + allowlist delta>"
```

Rules:
- `gate after` must show **0 new failures / 0 drift / 0 security findings**; the inherited
  `unexpected_large_files` debt (28) is the only tolerated non-zero.
- Every wave updates the count-to-zero allowlist (§4.2) and records the shrink in its CF
  decision. A wave whose allowlist did not shrink by exactly its site count is not done.
- CF-SPEC-3, CF-SPEC-5, CF-SPEC-6 are stale-open (45 tasks) from earlier cycles. At M0,
  record a supersession decision against each (diagnosis C-7) so `task ready` output is
  clean for the conductor cast.

## 4. The count-to-zero contract (how "no endpoints left untouched" becomes checkable)

### 4.1 New inventory script — `scripts/pi_migration_inventory.py`

Deterministic scanner (no LLM): walks `backend/app/` (excluding `tests/`), regex-matches
direct invocations of the legacy plane:

```python
PATTERNS = [
    r"\bollama\.chat(_stream)?\(",
    r"\bllm_router\.chat\(",
    r"\bcompute_registry\.chat(_stream)?\(",
    r"\.node\.chat\(",              # direct per-node dispatch (validation, dual-coder)
    r"\bserver\.chat\(",
    r"\bollama\.embed(_batch)?\(",
    r"\bllm_router\.embed_batch\(",
    r"\bChatOpenAI\(",              # browser_service bypass
]
```

Output: JSON `{file, line, pattern, snippet}` rows. Run: `python scripts/pi_migration_inventory.py --json`.

### 4.2 Ratchet test — `tests/pi_migration/test_count_to_zero.py`

- Loads `tests/pi_migration/legacy_allowlist.yaml` — the ONLY file allowed to authorize a
  direct legacy call. Asserts: `set(inventory) ⊆ set(allowlist)` **and**
  `len(allowlist) == expected_count_for_current_wave` (a literal number updated by each
  wave — the ratchet).
- The allowlist starts at W1 containing all 87 product sites (69 chat + 17 embed + 1
  browser bypass) plus the permanent infrastructure section; each wave's exit criterion
  removes its sites.
- **Final state (W9):** allowlist contains ONLY §4.3. Any new direct call added later
  fails CI. This test is added to the standard ladder and to
  `tests/e2e_test.py`'s phase list.

### 4.3 Permanent allowlist (Petals + engine internals — NEVER migrate)

| Category | Files/symbols (verified) |
|---|---|
| Donated-compute transport | `compute_node_transport.py:298-333`; ws branches `compute_node_invocation.py:57-77,178-191,323-333,362-372`; relay routes `api/routes/compute.py` (whole file); `relay/` CLI; `DonateComputeToggle.tsx` |
| Donor scheduling/authorization | `compute_registry_routing.py:106-109,120-124,181-190,206-228`; `compute_registry_invocation.py:184-203,231-238,288-311,628-648,940-943,1003-1008` |
| Donor lifecycle/telemetry/heartbeat | `compute_registry_lifecycle.py:38-79,161-163,443-476`; `compute_node.py:77-91`; connection strings (`connection_string.py`, `api/routes/connections.py`) |
| Legacy-engine internals (the baseline the benchmark compares against) | registry invocation/routing/helpers/lifecycle internals; `OllamaClient`/`LMStudioClient` transports; health/capability probes (`compute_registry_lifecycle.py:568,586`, `model_capabilities.py:590`, `lmstudio.py:97`, `vector_health.py:19`) |
| Local model lifecycle (provisioner, §5.2.3 re-uses it) | `pull_model`/`ensure_model` `compute_registry_invocation.py:1153-1177`, `ollama.py:74-86,210-223`; LM Studio JIT load `compute_node_models.py:282-407`; recovery `compute_registry_routing.py:350-633` |

Product call sites are NOT in this table. All 69 chat sites, all 17 embed sites, and the
browser bypass migrate to the dispatcher.

## 5. Target architecture

### 5.1 `AgenticDispatcher` — the single choke point

New package `backend/app/core/agentic/` (`dispatcher.py`, `types.py`). Every product call
site is rewritten to call one of FIVE verbs; nothing else is exposed:

```python
# backend/app/core/agentic/dispatcher.py  (shape — implementer refines signatures)
from app.core.agentic.types import EngineChoice, TurnResult, StructuredResult, EnsembleResult

class AgenticDispatcher:
    """Single entry point for every agentic-loop / model invocation in Istara.

    Engine resolution order (first match wins):
      1. per-call override (benchmark harness / A2A envelope metadata)
      2. request header x-istara-agent-engine (existing pi_replacement.py:35-46 predicate)
      3. project setting agentic_engine (new column, W1)
      4. settings.agentic_engine_default ("legacy" until owner flips it)
    """

    async def chat_turn(self, *, project_id, agent_id, session_key, system_prompt,
                        messages, tools=None, params: TurnParams,
                        stream_cb=None, steering_binding=None,
                        engine: EngineChoice | None = None) -> TurnResult: ...
        # Pi: PiExecutionService.run_chat_turn (existing, extended)
        # Legacy: ollama.chat_stream ReAct exactly as chat.py does today

    async def completion(self, *, purpose: str, project_id, system, messages,
                         params: TurnParams, engine=None) -> TurnResult: ...
        # one-shot, no tools. Pi: new engine.run_completion (§5.3)
        # `purpose` is a REQUIRED short slug ("dag_compaction", "debate_synthesis",
        # "skill_reflection", ...) — it keys telemetry, the usage ledger (§5.5) and
        # the benchmark's per-step attribution. Every migrated site picks a unique slug.

    async def structured(self, *, purpose, project_id, system, messages,
                         schema: dict, params, engine=None) -> StructuredResult: ...
        # Pi: forced-tool structured output (§5.4). Legacy: response_format via
        # llm_schema_adapter exactly as today. Returns parsed object + raw + usage.

    async def ensemble(self, *, purpose, project_id, prompt_spec, n: int,
                       distinct: bool, temperatures=None, engine=None) -> EnsembleResult: ...
        # W7. Pi: n turns across n distinct PiModelManager endpoints (distinct=True)
        # or n samples on one endpoint (self-MoA). Legacy: validation.py behavior.

    async def embed(self, *, texts: list[str], project_id=None, engine=None) -> list[list[float]]: ...
        # W8. Pi: EmbeddingsGateway (§9). Legacy: registry embed path.

agentic = AgenticDispatcher()   # module singleton, mirroring the ollama/llm_router idiom
```

Non-negotiables:
- `TurnParams` carries `model, temperature, max_tokens, thinking_mode, min_context,
  timeout_s, max_turns, require_vision` — the union of every param observed in the 68-site
  inventory. The Pi path maps them onto pi-ai options (`temperature`, `maxTokens`,
  `thinkingLevel`, provider `timeoutMs`); `min_context` maps to endpoint admission in
  PiModelManager; `thinking_mode` maps to `thinkingLevel` where the model supports it and
  to the existing prompt-directive injection (`llm_thinking.py:18-83`) where it doesn't.
- Every dispatcher call records ONE usage-ledger row (§5.5) regardless of engine — this is
  what makes the benchmark's token axes comparable.
- The dispatcher NEVER contains business logic. Prompt building, parsing, persistence stay
  at the call sites/services. The dispatcher only: resolves engine, executes, records.

### 5.2 `PiModelManager` — model management, Pi-side (replaces registry for agentic traffic)

Extends `backend/app/core/pi_runtime/endpoints.py` into
`backend/app/core/pi_runtime/model_manager.py`. **It never consults ComputeRegistry, and
ComputeRegistry never consults it** (the CF-SPEC-7 isolation invariant, kept forever;
`tests/pi_production/test_same_model_donor_isolation.py` must stay green through every
wave).

Catalog sources (all become `PiEndpoint` entries with exact identity):

1. **Static settings endpoints** — existing `settings.pi_api_endpoints` +
   `pi-deepseek-default` (unchanged).
2. **Persisted `LLMServer` rows** (`models/llm_server.py`) — projected read-only into the
   Pi catalog at load/save time as `openai_compat`/`anthropic_compat` endpoints with the
   row's encrypted key. Projection is one-directional (DB row → Pi catalog entry);
   nothing Pi-side writes back or registers into the live registry
   (`llm_servers.py:70` keeps doing its registry thing for the legacy engine).
3. **Local serving** — Ollama at `settings.ollama_host + "/v1"`, LM Studio at
   `settings.lmstudio_host + "/v1"` (ports/paths verified: `config.py:73,78`,
   `compute_node_transport.py:124-141`). Marked `kind=local`.
4. **Never**: relay/browser donors.

Capabilities each entry carries (the parity subset of §2's registry semantics that is
meaningful for static endpoints — from the verified parity checklist):
`model` (exact id), `context_window`, `max_tokens`, `supports_tools`,
`supports_vision` (`model.input` gate), `family` (openai_compat/anthropic_compat),
`cost_per_mtok` (feeds pi-ai `Model.cost` → native cost accounting), `timeout_ms`,
`max_retries`.

Selection API (all resolution is exact-identity or capability-filtered over the catalog —
no donor-style scoring):

```python
class PiModelManager:
    def resolve(self, *, endpoint_id=None, model=None, require_vision=False,
                min_context=0) -> PiEndpoint            # raises PiEndpointResolutionError
    def resolve_distinct(self, n: int, *, model=None, exclude=()) -> list[PiEndpoint]
        # W7: n endpoints with distinct identity for ensemble/dual-coder diversity;
        # fail-closed if fewer than n exist (never silently reuse one endpoint as "two")
    def catalog(self) -> list[PiEndpointInfo]           # feeds /settings UI + benchmarks
```

**Local provisioner (`model_manager_provisioning.py`, W8):** ensure-model / JIT-load /
context-reload for `kind=local` endpoints, by CALLING the existing proven helpers
(`ensure_model` `compute_registry_invocation.py:1168`, LM Studio load
`compute_node_models.py:282-363`) through a thin adapter that takes host+model — NOT by
reimplementing them. This preserves the [LOCAL]-tagged semantics (pull, JIT load, context
reload, loaded-state awareness) that would otherwise be lost when local servers are
addressed as plain `/v1` endpoints (verified loss list: registry-semantics report §3).
Provisioning failures surface as typed resolution errors — fail-closed, no fallback.

### 5.3 Engine API completion (`PiExecutionService` extensions, W1)

The current engine exposes only chat/channel/delegation/autoresearch turn shapes. Add:

```python
async def run_completion(self, *, purpose, project_id, agent_id, system, messages,
                         params) -> PiTurnOutcome
    # single provider round-trip, no tool catalog sent, returns text + usage + stop_reason
async def run_structured(self, *, purpose, project_id, agent_id, system, messages,
                         schema: dict, params) -> PiStructuredOutcome   # §5.4
async def run_react(self, *, purpose, project_id, agent_id, session_key, system,
                    messages, tool_names: list[str], extra_tools: list[DynamicTool],
                    params, steering_binding=None) -> PiTurnOutcome
    # task-shaped tool loop: hard max_turns budget (default 8, matching legacy
    # MAX_TOOL_ITERATIONS), per-run tool subset ENFORCED Python-side (§6 fix of B-12),
    # supports extra per-run dynamic tools (run_skill — §8 W3)
async def run_ensemble(...)   # W7, over resolve_distinct
```

Worker protocol additions (bump `PROTOCOL_VERSION`; both sides validate — fixes the
one-sided `seq` from B-12):

- `turn.prompt` gains optional `output_schema` (JSON Schema) and `tool_choice`
  (`"auto" | "required" | {"name": ...}`) and `max_turns`.
- `provider.bind` gains `params: {temperature, max_tokens, thinking_level, timeout_ms,
  max_retries}` — the worker passes them to pi-ai `StreamOptions` (currently dead config,
  B-12).
- `run.completed` already carries usage; extend with `turn_count`, `tool_call_count`, and
  pi-ai's exact `usage.cost.total`.

### 5.4 Structured output = forced tool call (the standard replacement for `response_format`)

pi-ai has no response_format, so the worker implements `output_schema` like this
(verified APIs only):

```js
// pi-runtime/src/session.mjs — when turn.prompt carries output_schema
import { Type } from "@earendil-works/pi-ai";   // TypeBox re-export

const structuredTool = {
  name: "emit_structured_output",
  label: "Emit structured output",
  description: "Return the final answer as a single structured object matching the schema.",
  parameters: jsonSchemaToTypeBox(frame.output_schema),   // mechanical translation; reject
                                                          // unsupported constructs at
                                                          // session.open, not mid-turn
  execute: async (_id, params) => {
    session.capturedStructured = params;                  // captured, not "executed"
    return { content: [{ type: "text", text: "ok" }], details: {}, terminate: true };
  },
};
// api-level forcing, per family:
//   openai-completions: options.toolChoice = { type: "function", function: { name: "emit_structured_output" } }
//   anthropic-messages: options.toolChoice = { type: "tool", name: "emit_structured_output" }
```

Python-side `run_structured` validates the captured object against the ORIGINAL JSON
schema (jsonschema lib) before returning — the TypeBox translation is a model-side aid,
Python revalidation is the contract. On validation failure: one bounded repair turn
(mirroring `skill_factory.py:755` semantics), then typed failure. Never return unparsed
text as if it were structured.

Legacy-path equivalence note for reviewers: legacy `structured()` keeps using
`llm_schema_adapter` (`:57-73,111-133` incl. the Anthropic forced-tool trick at
`:136-152` — which is exactly the same mechanism, so the two engines are methodologically
comparable on this axis).

### 5.5 Usage ledger (feeds §10 axes 5–7)

New `backend/app/core/agentic/usage_ledger.py`: one row per dispatcher call —
`{ts, engine, purpose, project_id, agent_id, task_id?, spine_phase?, endpoint_id|node_id,
model, input_tokens, output_tokens, cache_read, cache_write, total_tokens, cost_usd,
tool_calls, turns, latency_ms, stop_reason, outcome}`.

- Pi engine: exact numbers from pi-ai `Usage` (incl. `cost.total`).
- Legacy engine: provider-reported usage where the response carries it; otherwise
  `estimate=true` with the existing `count_tokens` estimator
  (`compute_registry_routing.py:797-822`). The `estimate` flag is carried into every
  benchmark table — estimated and exact numbers are never mixed silently.
- Persisted via the existing telemetry span machinery (`telemetry.py`) under a new
  `event_kind="agentic_usage"`, draining through the already-fixed owned-task drain.
  Identity fields follow the CF-SPEC-7 rule: `endpoint_id` only, never base_url/keys.

## 6. Wave 0 — hardening & evidence integrity (blocks everything else)

Fix every Blocker/Major from the diagnosis BEFORE migrating more traffic onto the runtime.
Each item lands with a regression test named here. IDs reference the diagnosis register.

| # | Fix | Where | Test |
|---|---|---|---|
| H-1 (B-1) | Python→worker frame size: chunk or reject before send. Implement `MAX_LINE_BYTES` check in `supervisor._send` + a `payload.chunk` frame pair for oversized `session.open`/`tool.result` (worker reassembles; bound total). A poisoned reader must terminate the RUN, not broadcast process-`fatal` | `supervisor.py:94-100`, `protocol.mjs:44-59`, `worker.mjs:190-194` | `tests/pi_production/test_frame_limits.py`: 1 MB tool result round-trips; concurrent session survives |
| H-2 (B-2) | `asyncio.create_subprocess_exec(..., limit=8*1024*1024)`; on reader death with live child: kill child, clear `_ready`, restart on next `ensure_started`; add crash-loop backoff (3 restarts/60 s → fail-closed) | `supervisor.py:75-82,118-124` | same file: >64 KiB stdout line recovers within one turn |
| H-3 (B-3) | Per-`session_key` asyncio lock: second concurrent open of same key waits or gets typed `session_busy`; `run_turn` filters frames by `run_id` | `supervisor.py:165-166,213-237`, `chat.py:147` | duplicate-send race test |
| H-4 (B-4) | Keychain reads via `asyncio.to_thread` + per-endpoint TTL cache (60 s); add `ISTARA_PI_SECRET_<ID>` env fallback for non-macOS (parity with `llm_fallback_api_key` precedent, `config.py:272-279`) — removes the macOS-only ceiling before the benchmark | `endpoints.py:83`, `config.py:43-63` | event-loop-stall test (probe latency under concurrent turn) |
| H-5 (B-5) | Steering binding keyed `(agent_id, project_id, session_key)`; pump checks its own binding, not the global single slot; document SteeringManager multi-process limitation in `PROTOCOL.md` | `engine.py:231-256`, `steering.py:269-285` | two concurrent turns, zero spurious aborts |
| H-6 (B-6) | `max_turns` enforced worker-side (count `turn_start` events, abort with `run.failed:turn_budget_exceeded`) + Python-side wall-clock `timeout_s` per run (not per frame-gap) + per-run cost ceiling from the ledger | `session.mjs`, `supervisor.py:214` | tool-loop fixture that would loop forever stops at budget |
| H-7 (B-7) | Register session queue only after successful open; `try/finally` around the full turn incl. open | `engine.py:190-228` | leak test: 100 failed opens, `_sessions` empty, 8-slot cap intact |
| H-8 (B-8) | `pi_local` turn moved OUTSIDE the DB transaction: persist inbound, commit, run turn, persist outbound in new session | `inbound_processor.py:177-234` | crash-mid-turn keeps inbound row |
| H-9 (B-9,B-11,m-items) | await/catch `steer`/`followUp` handlers; guard `_settleRun` agent deref; typed 503 for `PiWorkerError`/`TimeoutError` in autoresearch route; validate `protocol_version` in `ready`; telemetry distinguishes `aborted` from `error`; failed chat turn does NOT persist an assistant message (align with fail-closed contract) | `worker.mjs:123-129`, `session.mjs:149`, `autoresearch.py:656-667`, `supervisor.py:128-131`, `engine.py:458`, `chat.py:1021-1073` | one test each |
| H-10 (B-12) | **Enforce the Python-side tool allowlist**: `tool_handler` rejects any name outside the run's catalog (`catalog_tool_names()` finally gets its caller) with structured error + audit row | `engine.py:183-187`, `tools.py:43` | compromised-worker test: `web_fetch` from delegation session → rejected |
| H-11 (B-12) | Implement `timeout_ms`/`max_retries` pass-through to pi-ai `StreamOptions`; retry only before first visible output (pi-ai `isRetryableAssistantError` helper); both-side `seq` validation; remove the dead "HMAC/bounded/restart" claims from PROTOCOL.md or implement them — doc and code must agree line-for-line after W0 | `provider.mjs:33-52`, `session.mjs`, `PROTOCOL.md` | provider 500-then-success loopback test |
| H-12 | Worker capacity: `MAX_SESSIONS` configurable; supervisor grows to a bounded worker POOL (`pi_worker_pool_size`, default 2, round-robin by session_key hash) — required before W3 puts orchestrator traffic on it | `protocol.mjs:14`, `supervisor.py` | 20 concurrent turns across pool |
| H-13 (C-1) | Convert chat + one seam test to REAL ASGI (`httpx.ASGITransport`, the pattern used elsewhere in `tests/`); auth/middleware/SSE-over-HTTP exercised; fix the review packet's false "real ASGI routes" claim in the CF-SPEC-7 lifecycle file with a correction entry (never edit history, append) | `tests/pi_production/` | `test_chat_pi_asgi.py` |
| H-14 (C-2) | Coverage map derives from `labs/pi-replacement/src/scenario-catalog.mjs` (parse the ids) instead of a static dict; skips fail loudly when node is absent (`pytest.fail`, not skip, when `PI_REQUIRE_NODE=1` — CI sets it) | `tests/pi_production/test_scenario_coverage_map.py` | itself |

Exit: full existing ladder green + all new W0 tests + `gate after` clean. Only then W1.

## 7. Waves 1–9 at a glance

| Wave | Scope | Sites | Allowlist after |
|---|---|---:|---:|
| W0 | Hardening + evidence integrity | 0 | 87 (all product sites listed, ratchet armed) |
| W1 | Dispatcher, PiModelManager, engine API (`run_completion`/`run_structured`/`run_react`), usage ledger, count-to-zero armed | 0 | 87 |
| W2 | Interactive: chat, design chat, presentation, compaction, summarizer, UI-audit, browser tool | 9 | 78 |
| W3 | Research spine + steering executor (the heart) | 8 | 70 |
| W4 | A2A handlers (collaboration, debate ×2) | 3 | 67 |
| W5 | Skills, reports, interview services | 28 | 39 |
| W6 | Autoresearch runners (6 runners) | 14 | 25 |
| W7 | Validation/consensus + dual-coder (`run_ensemble`, `resolve_distinct`) | 8 | 17 |
| W8 | Embeddings gateway + model-management UX parity | 17 | 0 product |
| W9 | Final ratchet to permanent allowlist, docs regeneration, full ladder ×3, CF acceptance | 0 | permanent only |
| B1–B4 | Benchmark program (§10) — B1 starts after W2, full runs after W9 | — | — |

Each wave = one CF task group + one conductor phase + one commit series + one ledger entry.
Max 5 files per commit (CLAUDE.md phased-execution rule); waves > 5 files use parallel
sub-agents per sub-surface exactly as the conductor already casts them.

## 8. Wave details (call-site-by-call-site)

Formatting note: each wave lists **(a)** its complete site table (from the verified
inventory — these are exhaustive, not examples), **(b)** migration guidance + one worked
code example, **(c)** its test additions, **(d)** its verification ladder additions.
Params column abbreviations: T=temperature, MT=max_tokens, RF=response_format,
TM=thinking_mode, MC=min_context.

### W2 — Interactive surfaces (9 sites)

| Site | Today | Dispatcher verb → purpose slug |
|---|---|---|
| `api/routes/chat.py:316` (`_generate_native_tools`, ReAct #1, MAX=8) | `ollama.chat_stream`, tools=OPENAI_TOOLS | `chat_turn` → `chat.native` (Pi path already exists — rewire through dispatcher so BOTH engines share one entry) |
| `api/routes/chat.py:505` (`_generate_text_fallback`) | `ollama.chat_stream`, regex tools | `chat_turn` → `chat.text_fallback` (legacy-only branch of dispatcher; Pi engine never needs it — document that Pi always uses native tools) |
| `api/routes/interfaces.py:143` (`_generate_native_design_tools`, ReAct #2, MAX=3) | `ollama.chat_stream`, tools=OPENAI_DESIGN_TOOLS | `chat_turn` → `design.native` with `tool_names=DESIGN` catalog + `max_turns=3` |
| `api/routes/interfaces.py:588` (design text fallback) | `ollama.chat_stream` | `chat_turn` → `design.text_fallback` (legacy-only) |
| `api/routes/presentation.py:71` | `llm_router.chat`, T=0.3 | `completion` → `presentation.slides` |
| `core/context_dag.py:611` (`_summarize_batch`) | `ollama.chat`, T=0.2, MT=300 | `completion` → `dag_compaction` (KEEP Istara's DAG product; only the summarization call migrates — do not adopt pi's compaction helpers here) |
| `core/context_summarizer.py:72` | `ollama.chat`, T=0.3, MT=200 | `completion` → `context_summarize` |
| `services/browser_service.py:83` (browser-use ChatOpenAI, own 10-step loop) | direct OpenAI-compat HTTP, bypasses registry | Keep browser-use as the driver (it needs a live LangChain LLM object), but construct `ChatOpenAI` from a **PiModelManager-resolved endpoint** (`base_url`, key, model) instead of raw settings, and record its usage into the ledger under `tool.browse_website`. This closes the routing bypass without rewriting the third-party loop. Add to allowlist §4.3? NO — it leaves the allowlist because endpoint identity now comes from the Pi plane. |
| `agents/ui_audit_agent.py:499` | `ollama.chat`, T=0.3 | `completion` → `ui_audit.heuristics` (moved up from W5 — it's interactive-adjacent and trivial) |

Worked example — `context_dag.py:611` after migration:

```python
# before (context_dag.py:611)
response = await ollama.chat(messages=summary_messages, temperature=0.2,
                             max_tokens=settings.dag_summary_max_tokens)
summary = response["message"]["content"]

# after
from app.core.agentic import agentic
outcome = await agentic.completion(
    purpose="dag_compaction", project_id=self.project_id,
    system=None, messages=summary_messages,
    params=TurnParams(temperature=0.2, max_tokens=settings.dag_summary_max_tokens),
)
summary = outcome.text          # outcome.usage already recorded in the ledger
# mechanical fallback on outcome.failed stays EXACTLY as today (:622-639)
```

SSE contract: `chat_turn`'s Pi path keeps emitting the existing envelope
(`chunk`/`tool_call`/`done`/`error`) byte-compatible — the W0 H-13 ASGI test pins it.

Tests: `tests/pi_migration/test_w2_interactive.py` (each site × both engines × fail-closed);
design-chat scenario added to `tests/pi_production/`; simulation scenarios `31`, `71`
runnable with the engine flag (§10.4).

### W3 — Research spine + steering (8 sites; the heart of the product)

Loop map (verified, `L#` from the ground-truth spine report — keep these labels in CF
tasks/commits so reviewers can navigate):

| Site | Loop | Dispatcher verb → purpose | Session strategy |
|---|---|---|---|
| `core/agent_research.py:129,131` | L1 general ReAct (MAX=5, tools=OPENAI_TOOLS+`run_skill`) | `chat_turn`(react) → `spine.react` | ONE Pi session per task (`session_key=task:{task_id}`); `run_skill` injected as per-run dynamic tool via `run_react(extra_tools=...)`; ranked-candidate constraint preserved by building the tool schema from `build_run_skill_tool` (`agent_skill_tools.py:383`) exactly as today; 5-iteration cap → `max_turns=5` |
| `core/agent_research.py:478` | L2 planner (strict JSON schema, T=0.3, MT=900, MC, TM=off) | `structured` → `spine.plan` | schema is `openai_json_schema_response_format(name="istara_research_plan")` (`:456-460`) — passes through §5.4 unchanged; keep `parse_json_object` + `record_json_parse` telemetry |
| `core/agent_research.py:667` | L3 step executor (LLM steps) | `completion` → `spine.step_execute` | one call per non-skill step, carrying past-step results as today; DAG-parallel branch (`:577-583`, `asyncio.gather`) fans out to PARALLEL dispatcher calls — the worker pool (H-12) makes this safe; do NOT serialize the DAG |
| `core/agent_research.py:1062` | L5 reflection verifier (regex-JSON, T=0.1) | `structured` → `spine.verify` | upgrade the regex extraction to a proper schema `{verified: bool, confidence: number, reason: string}` — strictly better on BOTH engines (legacy gets response_format it never had; note this as a deliberate baseline improvement in the benchmark's threats-to-validity §11) |
| `core/self_check.py:75` | L6 claim verification (line-format, T=0.1) | `structured` → `spine.self_check` | same upgrade rationale; keep `confidence_to_score` mapping |
| `core/agent_execution.py:472` | L7 skill-improvement reflection (T=0.3) | `completion` → `spine.skill_reflection` | free text, trivial |
| `core/agent_lifecycle.py:519` | L10 steering executor | `chat_turn` → `steering.reply` | per-message Pi session; keyword-skill routing above it unchanged; this is where pi's native steer/followUp queues REPLACE the polling pattern — wire `SteeringBinding` (H-5) so `/steering` abort maps to `turn.abort` (true mid-turn abort is a NEW capability over legacy — flag it in benchmark axis 10 as an engine capability difference) |
| L4 skill executor (`agent_execution.py:59`) | — | no direct LLM call of its own (skills make the calls — W5); its `validation` step migrates in W7; its timeout/retry/backoff (600 s, 3 retries, `min(5*3^(n-1),120)`s) map onto `TurnParams.timeout_s` + existing task-level retry (unchanged) |

L8 (ReasoningBank/Memento) makes NO LLM calls (templated, `reasoning_bank.py:175-235`) —
no migration; it keeps firing as a persistence hook on dispatcher outcomes. L9 migrated in
W2. Persistence, checkpoints, findings storage, review states: UNTOUCHED — Istara remains
the authority (CF-SPEC-7 AC-5 still binding).

Spine-phase tagging (feeds §10 axis 4): every W3 dispatcher call passes
`spine_phase` into the ledger from this fixed taxonomy (source of truth:
`agent_execution.py` checkpoints + plan/step states):
`intent → context → plan → tool_selection → execution → recovery → grounding →
synthesis → review → governance` (the 10-phase set already defined in
`comparison-Istara-pi/metrics-schema.json:39-50`).

### W4 — A2A handlers (3 sites)

| Site | Today | Migration |
|---|---|---|
| `core/agent_lifecycle.py:857` `_handle_collaboration` | one `ollama.chat` w/ thread history + RAG | `chat_turn` → `a2a.collaboration`, history mapped as in `run_delegation(history=...)` (`seams.py:148` pattern) |
| `core/agent_lifecycle.py:942` `_initiate_debate` | synthesis call | `completion` → `a2a.debate_synthesis` |
| `core/agent_lifecycle.py:996` `_handle_debate` | critique call | `completion` → `a2a.debate_critique` |

Change of gate semantics (deliberate, owner-visible): today only Pi-flagged envelopes
(`a2a_task`, `pi_delegate`) reach Pi. After W4 the ENGINE decides — an `engine=pi`
project handles ALL A2A message types on Pi. The A2A route gate chain
(`a2a.py:306-478`) and report-eligibility gates are untouched. Denied requests still
produce zero Pi work (existing test keeps passing).

### W5 — Skills, reports, services (28 sites)

| Group | Sites | Verb → purpose |
|---|---|---|
| Skill factory | `skills/skill_factory.py:508` (plan, T=0.7, TM=off) → `completion`/`skill.plan`; `:717` (execute, strict RF + MC + token-budget) → `structured`/`skill.execute`; `:755` (repair#1, RF) → `structured`/`skill.repair_native`; `:794` (repair#2, plain) → `completion`/`skill.repair_plain`; `:863` (repair#3, findings) → `completion`/`skill.repair_findings` | The 4-stage fallback chain is PRESERVED as-is — it is the product's resilience contract; only the transport under each stage changes. §5.4's single bounded repair inside `run_structured` must NOT double-repair: pass `repair=False` from these sites |
| Discover skills | `channel_deployment.py:180,261`, `contextual_inquiry.py:36,83`, `diary_studies.py:28,70`, `user_interviews.py:201,297,337` | plan calls → `completion`/`skill.discover_plan`; analysis calls (JSON substring parse) → `structured`/`skill.discover_analyze` with schemas formalized from their current implicit shapes (write the schema down; both engines validate) |
| Intercoder | `intercoder.py:390,411,438,496,520` | `:390` plan → `completion`; coding steps `:411,438,496,520` → `structured`/`skill.kappa_*` (already `_parse_json_response`-shaped) |
| Reports | `report_manager.py:498,555,754,883,937,996` | `:498` → `completion`/`report.exec_summary`; `:555` MECE JSON → `structured`; `:754` weakest-section JSON → `structured`; `:883,937,996` narrative → `completion` |
| Interview services | `adaptive_interview.py:308,363`, `deployment_service.py:323` | `completion` → `channel.clarify` / `channel.saturation` / `channel.followup` (NONE-sentinel handling unchanged) |

### W6 — Autoresearch runners (14 sites)

All 6 runners migrate their calls mechanically (hypothesize/evaluate/score →
`completion` or `structured` with purposes `autoresearch.<runner>.<step>`). Two require
design decisions, already made here:

- **`model_temp.py:158,203`** — the runner sweeps models × temperatures across the pool.
  Pi version sweeps **PiModelManager catalog entries × temperatures** (`resolve()` per
  candidate). The experiment definition gains an `engine` field; on `engine=pi` the sweep
  space is the Pi catalog (incl. local Ollama/LM Studio entries — so the sweep is not
  degenerate with one endpoint). Legacy behavior unchanged. Fewer available endpoints than
  requested sweep width → recorded as `sweep_truncated`, never silently narrowed.
- **`rag_params.py:169` (+ its `embed_text` at `:231-234`)** — chat call migrates in W6;
  its embedding stays legacy until W8 (allowlist tracks the two separately).

The governed `pi_governed` autoresearch mode (CF-SPEC-7's proposal-only seam,
`autoresearch.py:643-669`) is UNCHANGED and remains the only path by which a Pi turn can
*propose* experiments; W6 is about the runners' own internal LLM calls once a human has
started an experiment. Governance gates (`governance_required`, no promotion) untouched.

### W7 — Validation / consensus / dual-coder (8 sites)

| Site | Today | Migration |
|---|---|---|
| `core/validation.py:152` `dual_run` | 2 distinct servers, direct `server.chat` | `ensemble(n=2, distinct=True)` → `validation.dual_run` |
| `core/validation.py:314` `full_ensemble` | 3+ servers | `ensemble(n=min_responses+1, distinct=True)` |
| `core/validation.py:373` `self_moa` | temp sweep on one model | `ensemble(n=len(temps), distinct=False, temperatures=[...])` |
| `core/validation.py:213` `adversarial_review` | 1 call | `completion` → `validation.adversarial` |
| `core/validation.py:431,470` `debate_rounds` | initial + rounds | `completion` ×(1+rounds) → `validation.debate` |
| `core/validation_executor.py:64` | judge call; **latent bug: reads `result.get("content")` but registry returns `message.content`** | `structured` → `validation.judge`; FIX the bug in the same commit (it means legacy adversarial scoring has been silently degraded — flag in benchmark notes) |
| `services/research_validity_service.py:556` dual-coder | pinned `coder.node.chat`, RF strict=False | `structured` over `resolve_distinct(n=max_coders)` → `validity.coder`; the "≥3 distinct model coders" reliability gate (`research-spine-probes.mjs:8-31`) maps to distinct Pi endpoint identities |
| `core/validation.py:522` `_get_embeddings` | `llm_router.embed_batch` (consensus similarity) | stays legacy until W8, then `agentic.embed` |

Fail-closed rule for `distinct=True`: fewer distinct endpoints than `n` ⇒ typed error
surfaced to the validation caller, which falls back to its existing "validation
unavailable" handling — never fabricate diversity from one endpoint.

### W8 — Embeddings gateway + model-management UX parity (17 embed sites + UX)

pi-ai cannot do embeddings, so the gateway is Python-direct HTTP under **Pi identity
management** (this is the honest interpretation of "model management replaced except
petals" — one identity/config/telemetry plane, even where pi-the-library can't execute):

- `backend/app/core/pi_runtime/embeddings_gateway.py`: resolves an embed endpoint from
  PiModelManager (`kind=local` Ollama `/api/embed`, or any `/v1/embeddings`-compatible
  entry), calls it with httpx, records ledger rows (`purpose="embed"`), keeps the
  existing `embedding_cache` in front.
- `agentic.embed` dispatches: Pi → gateway; legacy → `ollama.embed*` (unchanged).
- Migrate the wrappers, not the 14 downstream consumers: `embeddings.py:50`
  (`embed_text`) and `:90` (`embed_chunks`) call `agentic.embed`; `validation.py:522`
  calls it directly (project-scoped). Every consumer (`rag.py:604,639`,
  `prompt_rag.py:316,319,494`, `agent_memory.py:64,74`, `agent_skill_tools.py:338,341`,
  `agent_execution.py:824,832`, `rag_params.py:234`, `file_watcher.py:398`,
  `vector_health.py:19`) inherits the change with zero edits — verify with the inventory
  script that their indirect path is now dispatcher-owned.
- Embed model bootstrap (`ensure_embed_model`, `embeddings.py:100`) → provisioner (§5.2.3).
- **Vector-space invariant:** same embed model on both engines, asserted at startup
  (dimension probe reusing `vector_health.py`); an engine switch must NEVER silently
  change embedding space, or every stored vector is invalidated.
- UX parity: `api/routes/llm_servers.py` CRUD keeps working (legacy plane) AND projects
  into the Pi catalog (§5.2.2); `api/routes/settings.py` model pickers read merged
  catalog info; `network_discovery.py` results feed BOTH planes (discovered server → 
  LLMServer row → auto-projection). Frontend `Sidebar.tsx`/settings views get an engine
  indicator + per-project engine selector (single new store field; simulation scenario
  added — Layer 3 mandate).

### W9 — Final ratchet + docs + acceptance

1. `legacy_allowlist.yaml` reduced to §4.3 permanent entries; ratchet number = 0 product
   sites; inventory script wired into `scripts/check_integrity.py`.
2. Delete now-dead legacy-only glue ONLY where the dispatcher made it unreachable from
   product code (verify with CF `intelligence dead-code`; **no blind deletions** —
   CLAUDE.md rule). The registry itself stays (legacy engine + donors + benchmark
   baseline).
3. Regenerate living docs: `python scripts/update_agent_md.py`; feature docs
   (`scripts/feature_docs.py --seed-missing --generate-site --check`) — the agentic-engine
   feature page documents the dispatcher, engines, and count-to-zero contract; update
   `Tech.md` architecture narrative; persona files learn the dispatcher verbs
   (Completion Standard #4).
4. Full ladder (§8.6) ×3 consecutive, both engines; `gate after` clean; CF-SPEC-8
   acceptance WITHOUT `--force`; `TESTING.md` updated.

### 8.6 Standard verification ladder (every wave runs the subset it touches; W9 runs all)

```bash
node --test pi-runtime/test
python -m pytest tests/pi_production tests/pi_migration -q
python -m pytest tests/test_pi_replacement_candidate.py -q
python scripts/pi_migration_inventory.py --json | python -m json.tool > /dev/null   # scanner health
python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py \
  tests/test_a2a_service_scope.py tests/test_channels.py tests/test_channel_inbound.py -q
python -m pytest tests/test_autoresearch.py tests/test_steering*.py tests/test_tasks.py \
  tests/test_documents.py tests/test_findings.py tests/test_reports.py tests/test_memory.py \
  tests/test_research_validity_contract.py tests/test_reasoning_bank.py tests/test_sessions.py -q
python -m pytest tests/test_compute.py tests/test_compute_registry_hardening.py \
  tests/test_compute_registry_model_loading.py tests/test_compute_vision_routing.py -q  # ×3, donor isolation lives here
python -m pytest tests/e2e_test.py -q
npm --prefix relay test && npm --prefix tests/real_user_benchmark run check && npm --prefix tests/simulation run test:static
python -m pytest tests/benchmarks/test_orchestration.py -q && python tests/benchmarks/run_benchmarks.py
python scripts/run_istara_evals.py --suite static --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
python scripts/security_benchmark.py --fail-on-threshold
```

All backend suites: isolated `DATABASE_URL=sqlite+aiosqlite:////tmp/<unique>.sqlite3`.
Teardown asserts zero orphan `node` processes. Live-LLM runs appear ONLY in §10 with
owner-approved budget.

## 9. (folded into W8 above — kept as a section anchor for cross-references)

## 10. Evaluation & benchmark program ("Pi vs Istara, industry-class")

### 10.1 Principles

1. **Paired, seeded, fixture-identical.** Every scenario runs on both engines with the
   same project fixtures, corpus, prompts, model, temperature, and seeds. Engine selected
   via the dispatcher (`x-istara-agent-engine` header — already supported by
   `tests/real_user_benchmark/lib/api-client.mjs:31,244`; plumb the flag into both
   `run.mjs` harnesses, which currently ignore it — verified gap).
2. **Determinism tiers.** T0 faux/scripted (contract), T1 loopback stub (transport),
   T2 live-local (Ollama/LM Studio — free, high-N), T3 live-API (DeepSeek et al. —
   owner-budgeted, low-N). Tier is recorded on every artifact; tiers never mix in one
   table.
3. **Judges are not the DUT.** LLM-as-judge model ≠ engine-under-test model; judging is
   blind (engine labels stripped), position-swapped (A/B then B/A), with deterministic
   checks always computed alongside. Judge prompts + rubric versions are sha256-logged.
4. **Exact tokens or labeled estimates** (§5.5) — never silently mixed.
5. **Statistics:** N≥5 paired runs per scenario per tier (T2; T3 N per budget);
   per-scenario paired deltas with 10k-resample bootstrap 95% CIs; report effect sizes;
   a delta whose CI crosses zero is reported as "no detected difference", never rounded
   up to a win. `metrics-schema.json:121-126` already reserves these fields.
6. **Fail-closed reporting:** a scenario that cannot run on an engine scores as
   `not_runnable` with reason — never silently dropped (mirrors real_user_benchmark's
   fail-closed gates).

### 10.2 The 10 owner axes → concrete metrics (producers in parentheses)

| # | Axis | Metrics | Producer |
|---|---|---|---|
| 1 | Tool calling | tool_name_accuracy, argument_schema_validity, hallucinated_call_rate, calls_per_success, recovery_rate after tool error | ledger + per-run trace; vocabulary from `agentic_eval_contract.json:108-123` |
| 2 | Feature integration | per-feature `criteria_scores`: reachable / project_scoped / expected_action / engine_behavior / evidence_emitted / graceful_failure (schema `metrics-schema.json:51-63`) | **feature-criteria compiler** (§10.3) over `docs/features/inventory.json` (86 features) |
| 3 | Final output quality | deterministic checks (reuse `run_istara_evals.py:308-377`) + judge rubric 1–7 (grounding, completeness, actionability, format) | paired runner + JudgeLayer |
| 4 | Research-spine per-step quality | per-phase judge score over the 10-phase taxonomy + deterministic gates (evidence-unit exactness, `candidate_only` discipline, review-state legality from `research_validity_service.py` states) | spine_phase-tagged ledger + trace |
| 5 | Memory load | memory_items + memory_tokens per step; retrieval precision@1/recall@3 on seeded gold (extend `rag_keyword_gold`, `run_istara_evals.py:538-558`); cross-session recall probe; process RSS of worker/backend sampled per run | ledger + eval suite + psutil sampler |
| 6 | Tokens per step / total | exact per-purpose/per-phase input/output/cache/total + cost_usd | usage ledger (Pi exact; legacy provider-reported/estimated-flagged) |
| 7 | Tool count vs quality | efficiency frontier (quality vs tool_calls scatter), quality_per_tool_call, marginal_tool_gain = (quality_tools − quality_no_tools)/calls on tool-optional scenarios | paired runner |
| 8 | Skills adherence | per-skill contract: expected phase (`base.py:12-15` Double-Diamond default), output schema validity, instruction-marker compliance, ordering (3-skill slice), judge instruction-following score | skill scenario pack + JudgeLayer |
| 9 | System-prompt adherence | protected-block survival probes (spine contract block `chat.py:695` region), persona-constraint compliance probes, adversarial injection suite (reuse `security_benchmark` patterns), thinking-leak rate (`llm_output` scrubbing effectiveness) | new probe suite `tests/pi_benchmark/probes/` |
| 10 | A2A efficiency-vs-quality | rounds, messages, tool_calls, wall-clock, tokens vs judge-scored outcome quality; dominance analysis (fewer interactions AND ≥ quality = win); Fleiss kappa on multi-coder agreement (prod `fleiss_kappa`) | A2A scenario pack + ledger |

Cross-cutting engine-capability diffs reported alongside (not scored): true mid-turn
abort (Pi-only), native cache accounting (Pi-only), streaming granularity, donor
reachability (legacy-only, by design).

### 10.3 New benchmark assets (all under `tests/pi_benchmark/`)

- `runner.py` — paired scenario runner: drives real ASGI/HTTP routes with the engine
  header, orchestrates N seeded repetitions, emits one `metrics-schema.json`-conformant
  record per run into `.results/runs/<ts>/` (same conventions as existing harnesses:
  manifest with git sha + input sha256 + redacted endpoint fingerprints, gitignored
  results dir, secret scan).
- `scenarios/` — three packs: (a) the 15 canonical Pi scenarios re-hosted route-level;
  (b) spine pack: full task lifecycle through the orchestrator (backlog→review) on seeded
  corpus (subset of `tests/document_corpus/canonical/`); (c) A2A pack
  (collaboration/debate/delegation chains).
- `feature_criteria.py` — compiler: `docs/features/inventory.json` → executable
  criteria per feature (route reachable, project-scope enforced via existing scope
  contracts, expected action smoke, evidence rows present, graceful-failure probe);
  features whose criteria cannot be auto-derived get an explicit `criteria: manual`
  entry — counted and reported, never silently skipped.
- `judge.py` — JudgeLayer: judge model config (owner-set, §13.2), blind A/B protocol,
  rubric bank (per axis), caching by (scenario, run, rubric_version) so re-reports never
  re-spend.
- `probes/` — system-prompt adherence + injection suite.
- Engine-flag plumbing: `tests/simulation/run.mjs` and `tests/real_user_benchmark/run.mjs`
  gain `--engine pi|legacy|both` (client support already exists; runner support is the
  verified gap).
- Legacy per-step usage capture: registry `chat/chat_stream` records provider-reported
  usage into the ledger (the ONLY registry edit this plan makes outside allowlisted
  areas — it is telemetry-additive, donor paths untouched; the long-horizon runner's
  chunk-count "tokens" bug at `long_horizon_runner.py:138` gets fixed to read the ledger).

### 10.4 Benchmark phases

| Phase | When | Tier | Content |
|---|---|---|---|
| B1 contract | after W2 | T0/T1 | 15 canonical scenarios + W2 surfaces, both engines, deterministic; regression-gates every later wave |
| B2 breadth | after W5 | T2 (local, free) | full scenario packs + feature-criteria matrix + probes, N≥5, both engines; first full report generation |
| B3 depth | after W9 | T2 high-N + T3 (owner budget) | spine pack end-to-end, A2A pack, memory-load runs, API-model quality tier; final paired statistics |
| B4 report | after B3 | — | §10.5 artifacts + §11 article results sections; owner rollout review |

### 10.5 Report generation (the "professional industry-class" deliverable)

`scripts/pi_benchmark_report.py` — reads all `.results/runs/` records + judge outputs,
computes the paired statistics, and emits into
`comparison-Istara-pi/reports/<ts>/`:

- `report.md` — full benchmark: methodology, per-axis tables with CIs, efficiency
  frontiers, feature matrix, capability-diff table, threats to validity, raw-artifact
  index. Every number generated from JSON — **hand-written numbers are forbidden**
  (CF-SPEC-7's regenerated-counts ethos, now a script guarantee).
- `report.html` — self-contained single file (inline CSS/JS, inline SVG charts, no
  external assets — same constraint discipline as `scripts/feature_docs.py`, the repo's
  one existing HTML generator; reuse its asset pipeline where practical). Sections:
  executive verdict, axis scorecards, per-scenario drill-down tables, token/cost
  dashboards, spine-phase heatmap, A2A dominance plot.
- `scorecard.json` — machine-readable roll-up (extends the real_user_benchmark
  16-dimension scorecard pattern with the 10 axes).
- A dated copy of `report.md` linked from `comparison-Istara-pi/README.md`.

### 10.6 Budgets & owner gates (hard rules)

- T0/T1/T2 are free (no external spend) — run at will.
- T3 (API models): the historical $0.50 DeepSeek envelope has $0.409 remaining — NOT
  enough for B3. Before ANY T3 run: produce a dry-run cost estimate (token counts from a
  T2 rehearsal × pricing table `raw-llm-capture.mjs:5-10`), present it, and obtain an
  explicit owner-approved envelope recorded as CF evidence (the CF-SPEC-7 pattern —
  evidence row on the benchmark task; approval must come from the owner in chat, an
  agent-recorded attestation alone is what the diagnosis flagged at C-6). Per-run cost
  ceilings enforced by the ledger (H-6). Judge-model spend counted in the same envelope.
- Redaction-before-write for all raw captures (reuse `raw-llm-capture.mjs` discipline /
  schema_version 3); secret scan over every report dir before it is linked anywhere.

## 11. Documentation program

### 11.1 Build Stream (operational record)

- New lifecycle file `docs/build-stream/2026-07-XX-pi-full-replacement.md` created at M0
  from this plan's §7 table (status block, phase table, acceptance criteria = §4 contract
  + §10 axes, decision log, append-only ledger). Every wave = one phase entry + ledger
  rows, same conventions as the CF-SPEC-7 file. Corrections append, never rewrite (the
  L-26/L-27 precedent).
- The CF-SPEC-7 lifecycle file gets a single appended correction entry for the false
  "real ASGI routes" claim (H-13) — reviewers of history must not inherit it.

### 11.2 Academic article (`comparison-Istara-pi/article/`)

Working title: *"Replacing a Production ReAct Engine: A Paired Evaluation Methodology for
Agentic LLM Runtimes."* Structure (each section drafted at its gating phase, results
auto-generated):

1. Introduction — the replacement problem; Istara as a full-surface testbed (chat, spine,
   A2A, skills, channels, autoresearch, memory).
2. Related work — ReAct; plan-and-execute / LLMCompiler-style DAG execution (Istara L3);
   agent benchmarks (AgentBench, τ-bench, GAIA, SWE-bench-Verified) and why
   single-task benchmarks under-measure integrated products; LLM-as-judge methodology and
   its failure modes (position bias, verbosity bias — mitigations in §10.1.3);
   agentic-evaluation surveys.
3. Systems — Istara native engine (registry + in-process loops L1–L10, §8 W3 map) vs Pi
   runtime (supervised worker, event-loop Agent, protocol) — architecture diagrams from
   the verified seam maps.
4. Method — paired design, tiers, seeds, metrics formulary (§10.2 verbatim), judge
   protocol, statistics; full reproducibility appendix (commands, sha256 manifests).
5. Results — auto-generated tables/figures from `scorecard.json` (never hand-edited).
6. Discussion — engineering trade-offs measured: in-process vs sidecar latency, token
   overheads, capability diffs (abort, caching), operational surface (worker pool,
   secrets, platforms).
7. Threats to validity — single-product generalization; judge model choice; the W3
   deliberate baseline improvements (regex→schema at two sites) and every other
   non-transport change made during migration (the plan requires logging each such change
   in `article/method-deltas.md` AS IT HAPPENS — the reviewer checks this file each wave).
8. Conclusion + data availability (run artifacts, redacted).

## 12. Conductor & Compass Forge execution packet

### 12.1 How to run this plan with /conductor (and how NOT to)

**Do not let the conductor re-plan.** This document is the winning plan. Set the pipeline
up with planning DISABLED (the CF-SPEC-7 cycle used `make_pipeline.py ... --with-planning`;
here use the no-planning variant) and register this file as the governing plan artifact.
The conductor's job is: cast generation → per-wave implementer/reviewer/fixer loops →
evidence → gates — S2→S5 only.

Per wave, the conductor phase packet is: goal = wave section (§6 or §8.WN verbatim),
acceptance = the wave's site count removed from the allowlist + its tests + ladder subset
+ gate clean, review mode = independent reviewer with delta re-reviews (the CF-SPEC-7
loop that worked). Suggested cast mirrors the roster that converged last cycle (architect
roles are NOT needed — implementation/review/fixer only).

### 12.2 M0 bootstrap checklist (first conductor session, ~1 day)

1. `compass-forge spec` — create CF-SPEC-8 from §0 mission + §4 contract + §10 axes as
   acceptance criteria; `spec plan` WITHOUT force; link wave tasks W0–W9 + B1–B4.
2. Record supersession decisions closing CF-SPEC-3/5/6 (45 stale-open tasks).
3. Create the new lifecycle file (§11.1); commit this plan + lifecycle + inventory script
   + ratchet test with the FULL allowlist (87 entries) — the ratchet is armed before any
   migration commit exists.
4. `compass-forge gate before` baseline for W0.

### 12.3 Standing rules for every cast member

- Read-Edit-Read; re-read files >10 messages old (CLAUDE.md).
- Grep is not an AST: after each site migration run the inventory script AND
  `compass-forge intelligence impact --path <file>` and reconcile.
- Max 5 files/commit; wave sub-batches of 5–8 files per sub-agent.
- Every commit message carries the wave tag (`W3:`) and site refs.
- No `Co-authored-by`; author `henrique-simoes <simoeshz@gmail.com>`; branch stays
  local-only until the owner says otherwise.
- Two-Strike Rule on any fix; evidence rows before "done"; `satisfied=false` when true.

## 13. Owner decision points (blocking, in order)

1. **Approve this plan** (or amend waves/scope) — gates M0.
2. **Judge + benchmark model policy** — which judge model (must differ from DUT models),
   which T2 local models (default: existing `google/gemma-4-e4b` test profile +
   LM Studio/llama.cpp donors already used by real_user_benchmark), which T3 API models
   (default: `deepseek-v4-pro` continuity).
3. **T3 budget envelope** — presented as a dry-run estimate before B3 (§10.6). No T3
   spend before explicit in-chat approval.
4. **Rollout decision after B4** — flip `agentic_engine_default`, staged per-project;
   legacy deletion is a NEW spec if Pi wins, not part of this one.

## 14. Method note (how this plan was grounded)

Authored 2026-07-20 against `Review_pi_test` @ `c1d3d7ff` by the independent reviewer of
CF-SPEC-7, from: (1) six parallel deep-read agents (eval infrastructure; call-site sweeps
of `core/` and `routes|services|agents|skills/`; pi package `.d.ts` API extraction;
registry semantics parity + Petals map; research-spine loop map) — raw reports preserved
verbatim in `docs/build-stream/plans/pi-full-replacement-research/` (six files; the
call-site tables there are the authoritative per-site inventory backing §2 and §8 — read
`research-callsites-core.md` + `research-callsites-rest.md` before touching any wave, and
`research-pi-api.md` before writing any worker/provider code); (2) Compass Forge
`intelligence impact` reverse-import
verification of the model plane's consumer set; (3) the CF-SPEC-7 diagnosis (§1). Every
file:line in this document was reported by an agent that read the file this week; if you
find one stale, fix the plan in the same commit as your code change — the plan is a
living document under the same Golden Rule as everything else in this repo.

### L-1 | 2026-07-21T10:37:02Z | S2-execute | kimi-code/k3 | executor | pi-full-20260720-w3-implementer <!-- bsc-ledger:pi-full-20260720-w3-IMPL -->
Did: pi-full-20260720-w3-implementer stage on task pi-full-20260720-w3-IMPL (harness fallback entry; the model did not append one).
Result: task pi-full-20260720-w3-IMPL finished; worktree head afb7343b.
Verified: see Compass Forge evidence rows on pi-full-20260720-w3-IMPL (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-2 | 2026-07-21T10:44:32Z | S3-review | claude-fable-5 | reviewer | W3 <!-- bsc-ledger:pi-full-20260720-w3-REVIEW -->
Did: W3 code review of pi-full-20260720-w3-IMPL. Pointer entry: the initiative's canonical ledger lives in `docs/build-stream/2026-07-20-pi-full-replacement.md` (W1/W2 precedent) — see its L-33 for the full review narrative, W3 findings register, and status block.
Result: PASS — zero Blocker/Major findings, 3 info observations; verdict recorded on pi-full-20260720-w3-REVIEW.
Verified: 44 W3/ratchet/W1-contract + 153 pi_production/pi_migration + 27 agents + 57 steering/integration/validity tests, all passed (see CF command evidence rows 849-851).
Next: conductor advances to W3 stage-exit acceptance; W4 A2A migration next.
