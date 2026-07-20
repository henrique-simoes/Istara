# Build Stream — Pi production runtime completion

<!-- STATUS BLOCK -->
```yaml
item: pi-production-runtime-completion
branch: Review_pi_test
cf: { spec: CF-SPEC-7, tasks: [pi-runtime-complete-20260720-PLAN-A, pi-runtime-complete-20260720-PLAN-B, pi-runtime-complete-20260720-PLAN-C, pi-runtime-complete-20260720-IMPL, pi-runtime-complete-20260720-REVIEW, FIX-pi-runtime-complete-20260720-REVIEW-r1, CF-120..CF-133] }
phase: "Phase 1 — private endpoint and lifecycle foundations"
stage: S4-remediate
status: in-progress
blocked_on: null
last: { agent: gpt-5.6-sol, at: 2026-07-20T03:24:43Z, ledger: L-13 }
next_action: "Remediate F-1 through F-3 in FIX-pi-runtime-complete-20260720-REVIEW-r1, then run the conductor-created delta re-review."
```
<!-- /STATUS BLOCK -->

## Plan overview (roadmap)

**Problem.** The current candidate proves the Pi Agent in a lab, but production routes
still use Istara's Python loop with a DeepSeek model-selection shim. A2A, channels,
Autoresearch, research governance, memory, and steering are telemetry or test exercisers,
not Pi-owned production loops. API routing also shares model-based candidate selection
with donated relay/browser compute, so identical model aliases can violate the required
Petals/API independence.

**Outcome.** The real Pi Agent owns opt-in production loop execution across the complete
experiment surface; Istara remains the authority for product state, security, canonical
tools, research validity, human approval, telemetry, and rollback. API/OpenAI-compatible/
Anthropic-compatible endpoint routes are pinned by identity and cannot consume donated
compute. All 15 scenarios and predefined tests pass through the production adapter, with
bounded redacted DeepSeek evidence and no external live channel traffic.

**Appetite.** One full architecture-and-implementation conductor cycle, including
independent review and remediation until dry. Prefer a narrow stable runtime boundary and
reuse existing Istara contracts over duplicating product logic in Pi.

**Non-goals.** No replacement or redesign of Petals-style donation; no external channel
traffic; no local model loading; no production deployment; no remote push/PR; no bypass of
research or human approval gates; no changes to protected local model/training folders.

**Top risks.** Cross-language runtime lifecycle and streaming; duplicated tool contracts;
auth/project-scope bypass; provider secret leakage; same-model donor collision; fabricated
research acceptance; flaky async DB cleanup; overclaiming lab evidence as production proof.

**Documentation impact.** Update affected living feature docs and generated site, provider
and compute-pool architecture, Pi experiment/review packet, test inventory, and this
lifecycle file. Preserve prior dated artifacts as historical evidence.

| Phase | Goal | Acceptance / verify | Status |
|---|---|---|---|
| 0 | Three independent production designs converge on one executable architecture | conductor consensus + owner approval | in-progress |
| 1 | Establish real Pi production runtime and canonical tool/provider boundary | production adapter contract tests | planned |
| 2 | Integrate all agentic-loop seams and governed persistence | 15 production scenarios | planned |
| 3 | Prove endpoint routing and Petals isolation | adversarial same-model routing + compute/relay suites | planned |
| 4 | Run full regression, security, docs, bounded DeepSeek evidence | all required commands green | planned |
| 5 | Independent review/remediation and local PR-ready handoff | reviewer pass, CF acceptance, clean worktree/branch | planned |

## Acceptance criteria

### AC-1: Production Pi ownership
Given Pi is explicitly selected and enabled, when an agentic turn executes, then the real
Pi Agent Core owns turn progression and tool execution while Istara-owned contracts enforce
state, authorization, and governance.

### AC-2: Baseline rollback
Given Pi is disabled or not selected, when the same route executes, then baseline Istara
behavior is unchanged and no Pi runtime/provider work occurs.

### AC-3: Endpoint identity and donation independence
Given an API endpoint and an authorized donated node advertise the same model alias, when a
Pi API request executes, then only the pinned API endpoint is called; when an ordinary
donated-compute request executes, the donor remains eligible and project-scoped.

### AC-4: Complete production scenario matrix
Given the 15 canonical experiment scenarios, when they run through the production Pi
adapter, then every scenario passes using real Istara service contracts rather than the
lab-only facade.

### AC-5: Governed research and memory
Given Pi produces sources, evidence, memories, skill statistics, task/report state, or
Autoresearch output, when the workflow persists it, then provisional/accepted/reportable
state is computed by existing governance and no model fabricates approval.

### AC-6: Safe channels and external boundaries
Given channel scenarios execute, when Pi processes them, then `pi_local` and local webhook
fixtures exercise the real loop without external channel traffic or credentials.

### AC-7: Verification and evidence
Given implementation is complete, when the predefined regression, benchmark, feature-doc,
security, compute, relay, and bounded DeepSeek checks run, then all pass with exact evidence,
redacted secrets, a clean aggregate compute suite, and no new Compass Forge drift.


<!-- consensus-winning-plan -->
## Winning consensus plan

# Plan C — Pi Agent Core owns the production loop via a promoted, supervised runtime worker

Architect C, task `pi-runtime-complete-20260720-REPLAN-C-r1` (the original
`pi-runtime-complete-20260720-PLAN-C` produced no artifact — zero evidence rows — so this
is the first complete Plan C, written from independent inspection of the seams in §1),
CF-SPEC-7, branch `Review_pi_test` (local only, no push, no PR).

*r2 repair note (task `pi-runtime-complete-20260720-REPLAN-C-r2`):* full re-audit of every
seam claim, referenced path, npm script, and ladder command in this plan against the code
at worktree head `161fb0cf`; corrected the lab facade tool count (29, not 30) in §1 and §4.
Architecture, phases, acceptance, risks, and rollback unchanged. Grounding baseline
re-confirmed: `python -m pytest tests/test_pi_replacement_candidate.py -q` → 12 passed.

## 1. Verified seam map (evidence base)

Every load-bearing claim below was confirmed by direct code inspection on 2026-07-20:

| Seam | Today (file:line) | Gap the plan closes |
|---|---|---|
| Lab Agent host | `labs/pi-replacement/src/istara-pi-adapter.mjs:145-170` — real `Agent` with `streamFn`, `sessionId`, `toolExecution: "sequential"`, event subscription at :161-168 | Proven only in-process in the lab; no production importer exists |
| Lab live provider | `istara-pi-adapter.mjs:312-339,419-440` — pi-ai `deepseekProvider()`, `completeSimple` | Live calls bypass `Agent` entirely; live-inside-Agent is unproven everywhere |
| Lab Agent APIs | `steer`/`followUp`/`abort` exist in `@earendil-works/pi-agent-core@0.80.10` (`dist/agent.d.ts:82-96`) but have **zero** call sites in the lab | Steering/follow-up/abort must be wired for the first time and tested against the real Agent |
| Lab tool facade | `labs/pi-replacement/src/canonical-tool-facade.mjs:82-481` — 29 TypeBox tools, in-memory state, `validateToolCall` at :496-510 | Lab-only state; production must execute canonical Python tools instead |
| Usage/cost evidence | `labs/pi-replacement/src/raw-llm-capture.mjs:5-10,30-40,89-185` — pricing table, `estimateDeepSeekCostUsd`, redacted record builders | Production-quality code worth promoting; spend ledger `$0.09096299` / cap `$0.50` at `scenarios/collect-replacement-artifacts.mjs:12,394-402` |
| Production tools | `backend/app/skills/system_actions.py:79-431` — **17** `OPENAI_TOOLS` (OpenAI function JSON Schema); executor `execute_tool` at :752-786; `TOOL_EXECUTORS` at :1193-1211 | The lab's 29 tools are a superset contract; §4 maps every scenario to real production surfaces |
| Chat dispatch | `backend/app/api/routes/chat.py` — handler :501, project gate :507, prompt-RAG/system-prompt pipeline :607-775 (protected spine block :695, defined :102-115), Pi header check inside the SSE generator :803, fail-closed envelope :78-99, Python ReAct `_generate_native_tools` :154-344 (`execute_tool` call :293), `_generate_text_fallback` :347-470, post-stream save in fresh `async_session()` :891-914, fire-and-forget DAG compaction :922 | Pi currently only pins `deepseek-v4-pro` with `strict_model_routing=True` through `ollama.chat_stream`; the Python loop still owns every turn |
| Pi shim | `backend/app/core/pi_replacement.py` — selection predicate :38-49, `ensure_pi_deepseek_registered` :52-86 (registers a transient `openai_compat` node into `ComputeRegistry`), `record_pi_a2a_event` :124-141, canned `build_pi_channel_response` :144-174, exercisers :224-493 with `production_test_ready: False` at :492 | Registration into the shared registry is the donor-collision vector; exercisers must be deleted, not extended |
| Compute routing | `backend/app/core/compute_registry_routing.py` — `_select_candidates` :88-204; relay/browser need advertised models :106-108; strict+project sort **prefers relay/browser donors** :182-188; donor content gate `_node_authorized_for_project_content` :206-228; telemetry call sites :648,675,701 | A model alias is not endpoint identity; the strict sort would pick a same-alias donor over the pinned Pi node |
| Endpoint config | `backend/app/models/llm_server.py` (persisted `LLMServer`, encrypted `api_key`) auto-registers into `ComputeRegistry` on save at `backend/app/api/routes/llm_servers.py:70`; Keychain helper `backend/app/config.py:16-36`; Pi settings `config.py:207-213` + resolver :251-256 | `LLMServer` rows cannot represent a Pi-private endpoint without re-entering shared scheduling |
| A2A | `backend/app/api/routes/a2a.py:306-483` — full gate chain (auth → rate → size → replay → project scope → persist → audit), Pi telemetry hook :471-478; **no agentic work executes in the route** — execution is the orchestrator inbox poll `backend/app/core/agent_lifecycle.py:562-587` (`_handle_delegate` :589) | Pi delegation must hook the orchestrator dispatch, not the JSON-RPC route |
| Channels | `backend/app/services/inbound_processor.py:100-292`; canned Pi branch (no active deployment) :183-191; `PiLocalAdapter` `backend/app/channels/pi_local.py:8-53`; lifecycle/ownership `backend/app/services/channel_service.py:243-366`; router wiring `backend/app/main.py:424-429` | Canned response must become a real in-process Pi turn |
| Autoresearch | `backend/app/api/routes/autoresearch.py:584-652` — dry-run envelope :613-637; runner map :85-92; background `_run_loop` :641-652 | No governed Pi execution mode exists between dry-run and the legacy runners |
| Steering | `backend/app/core/steering.py:60-381` (project-scoped queues, `abort` :353-374); routes `backend/app/api/routes/steering.py:103-342`; consumer `agent_lifecycle.py:300-306` | Manager is in-process only; never reaches a live agent loop |
| SQLite lock | `backend/app/core/compute_route_evidence.py:52-102` — untracked `loop.create_task(_emit())` at :102; each emit opens its own `async_session()` + commit (`backend/app/core/telemetry.py:57,90`); autouse disposal fixture `tests/conftest.py:13-20` | Unowned async work outlives tests and races engine disposal |
| Baseline tests | `tests/test_pi_replacement_candidate.py` — 12 tests: 5 chat-side :41-289, 3 channel :290-439, 1 readiness :440-484, 2 A2A :485-610, 1 autoresearch :611+ | Must be re-pointed at Pi-loop ownership without losing fail-closed semantics |

## 2. Architecture decisions

**D-C1 — One supervised Node worker (`pi-runtime/`), promoted from the proven lab core, speaking versioned NDJSON over stdin/stdout.**
A new top-level package `pi-runtime/` (sibling of `relay/`; the name is free — verified no `pi-runtime/` or `runtime/` exists) hosts the real `Agent`. It is **not authored from scratch**: the Agent-host block, event-subscription mapping, and usage/cost normalization + redacted capture builders are copied-and-hardened from `istara-pi-adapter.mjs:145-180,249-276` and `raw-llm-capture.mjs` (the lab keeps its own copies; production never imports from `labs/`). On top of that proven core the worker adds the three things the lab never had: a process protocol, `steer`/`followUp`/`abort` wired to the real Agent APIs, and a real provider HTTP stack (no `fauxProvider` outside Node unit tests). Python gains `backend/app/core/pi_runtime/` with a `PiRuntimeSupervisor` owning exactly one child per backend process: lazy start on the first validated Pi request, handshake, per-session multiplexing, bounded queues, and owned teardown (FastAPI lifespan close → cancel runs → grace → terminate → kill only the child PID it created).

*Trade-offs.* A long-lived supervised child beats per-request `node` spawns (session continuity, sub-turn latency, one cleanup point) at the cost of supervisor complexity — bounded by P1's orphan/crash test matrix. stdio beats a localhost HTTP sidecar: no port, no auth domain, no endpoint fingerprints in `netstat`, and teardown provably kills the stream's only writer. The backend has no existing supervisor pattern (verified: all in-process asyncio), so the supervisor reuses the repo's asyncio lifecycle idioms (`start/stop/wake` + `asyncio.Event` from `agent_lifecycle.py:105-149`) rather than inventing threads.

**D-C2 — Server-owned session identity with revision-checked rehydration.**
`session_key = HMAC(project_id, chat_session_id | task_id | a2a_message_id, agent_id, endpoint_id, model)` computed in Python; the model can supply or alter none of it. Python sends persisted history + revision at `session.open`; a revision or endpoint/model mismatch closes and rehydrates instead of appending to stale state. A child restart fails affected sessions closed; an ambiguous in-flight turn is never resumed — only a later turn may rehydrate from persisted history.

**D-C3 — Canonical tools are exported from Python per run; execution is an authority round-trip.**
The run catalog is built in Python from `OPENAI_TOOLS` plus the route's allowlist, serialized mechanically (the OpenAI `parameters` block is already JSON Schema — the shape pi-agent-core tools validate against) and sent at `session.open`. No TypeBox catalog is hand-maintained in Node; a contract test normalizes and compares every name/description/schema and constructs each tool in the worker so drift fails at CI, not at runtime. A Pi tool `execute` emits `tool.call`; Python looks up the server-side run record, re-injects authenticated `project_id`/`agent_id` (model-supplied scope fields are ignored), validates arguments, and calls the existing `execute_tool` (`system_actions.py:752`). Unknown, forbidden, duplicate, cross-project, post-abort, or oversized calls return a structured tool error and are audited — they never kill the session and never throw across the pipe.

**D-C4 — Endpoint identity is a Pi-private resolver; nothing Pi ever enters `ComputeRegistry`.**
New `backend/app/core/pi_runtime/endpoints.py` (`PiEndpointResolver`) reads a settings-defined endpoint list (`settings.pi_api_endpoints`: `endpoint_id`, `provider_kind ∈ {openai_compat, anthropic_compat}`, `base_url`, `model`, `keychain_service`, `keychain_account`, `timeout_ms`, `max_retries`), with the existing `pi_replacement_deepseek_*` settings (`config.py:207-213`) mapped as the default `pi-deepseek-default` entry for continuity. Resolution is exact `endpoint_id` + model; secrets resolve at turn time via `_read_macos_keychain_secret` (`config.py:16-36`) and travel only inside a `provider.bind` frame on the private pipe — never argv, env files, logs, SSE, telemetry, or evidence. `ensure_pi_deepseek_registered`'s `ComputeRegistry` registration (`pi_replacement.py:52-86`) is **removed**: that registration is precisely what lets a same-alias donor outrank the Pi node under the strict+project sort (`compute_registry_routing.py:182-188`).
*Explicitly rejected:* reusing persisted `LLMServer` rows as the Pi endpoint source — saving an `LLMServer` auto-registers it into `ComputeRegistry` (`llm_servers.py:70`), which re-opens the exact collision the mandate forbids, and guarding that would edit shared scheduling code, violating "avoid broad changes to donation code". The disjoint resolver makes the forbidden path unrepresentable instead of merely unlikely. Donation scheduling never consults the resolver; Pi never consults `ComputeRegistry`. Isolation is proven behaviorally (§6), not asserted structurally.

**D-C5 — One facade, five seams, hooked where the work actually executes.**
A single `PiExecutionService` (in `backend/app/core/pi_runtime/engine.py`) owns runtime semantics so no route reinvents them:

- **Chat** — dispatch replaces the current pin block at `chat.py:803`, *after* the untouched auth/session/prompt-RAG/protected-block pipeline (:507-775). The engine drives a Pi turn and translates worker events into the existing SSE envelope (`chunk`/`tool_call`/`done`/`error`), persisting through the same message/session services. Fail-closed: resolver miss, Keychain miss, spawn/handshake failure, or mid-turn crash emit the typed `pi_registration_unavailable`-style error with zero provider transport and **no** fall-through into `_generate_native_tools`/`_generate_text_fallback` (the non-Pi branch stays byte-identical — AC-2).
- **A2A** — the route gate chain (`a2a.py:306-478`) is untouched. The hook is where delegated work really executes: the orchestrator inbox dispatch (`agent_lifecycle.py:562-587`, `_handle_delegate` :589). When a persisted, admitted A2A message carries Pi selection (stamped at admission only), the dispatch routes the work item through `PiExecutionService.run_delegation` — agent-role system prompt, task payload as the user turn, delegation-safe tool subset — persisting results through existing A2A/task services. Denied requests create no Pi session, no spans, no rows (already asserted by the existing denial test). Reports stay behind existing report-eligibility gates; Pi cannot create a report directly.
- **`pi_local`** — the no-deployment branch (`inbound_processor.py:183-191`) calls `run_channel_turn` with the inbound text and channel/project context; the outbound persists and sends through the normal channel contracts. The canned text (`pi_replacement.py:144-174`) is deleted. Ownership, pause, cross-project, and stop/delete semantics live above the seam and are unchanged; no external adapter is touched.
- **Autoresearch** — a governed `pi_governed` mode slots between the dry-run envelope (`autoresearch.py:613-637`) and `_get_runner`: it requires `autoresearch_enabled` + Pi header + project researcher scope, runs one bounded Pi turn with a read-only/proposal-only catalog, and persists a **candidate proposal** (`governance_required=True`, `report_evidence=False`). No background loop, no filesystem mutation, no promotion — human gates unchanged (AC-5).
- **Steering** — the engine registers a per-session binding with `SteeringManager`: queued items drain into `turn.steer` only while a turn is active (delivered once, acked on acceptance), follow-ups map to `turn.follow_up`, abort maps to `turn.abort` producing exactly one terminal event. Manager project scoping (:88-91,146-151) and protected system-prompt blocks are unchanged.

**D-C6 — Governed artifacts only; exercisers are deleted, and scenario proof moves to routes and services.**
`pi_replacement.py:224-493` (`write_pi_source_evidence_chain`, `exercise_pi_done_report_gate`, `record_pi_memory_governance_fanout`, `exercise_pi_steering_interrupt_probe`, `exercise_pi_production_readiness`) is deleted once each surface has a production caller. Pi-driven tools may create only source/evidence/candidate or provisional artifacts; accepted/reportable/Done/promotion transitions remain exclusive to existing governance services and human review. ReasoningBank, Memento skill memory, and `ModelSkillStats` are written only through existing project-scoped services with verified outcomes — raw tool/provider success never becomes a strong positive signal (Self-Improvement Governance Contract).

**D-C7 — Telemetry with endpoint-identity-only route labels, and instrument-first SQLite-lock causality.**
Usage (tokens, tool counts, stop reason, latency, cost from the promoted pricing table) is recorded through the existing recorder keyed by `endpoint_id` + provider family + model — never base URL, host, or key material. For the aggregate-suite lock: P0 first **reproduces and instruments** (registry wrapping the `create_task` sites, pending-task counters at test boundaries) to prove the `compute_route_evidence.py:102` → `telemetry.py:57,90` mechanism, and audits the other unowned tasks in scope — `chat.py:922` DAG compaction and the post-stream save block :891-914. The fix is ownership, not timeouts: a module task registry with `done_callback` discard, `drain_compute_telemetry()` awaited in the autouse fixture teardown **before** `engine.dispose()` (`conftest.py:13-20`) and in app shutdown, plus a regression test that delays a telemetry write across a compute call and proves no pending task/lock/warning. `sqlite_busy_timeout_ms` changes only if instrumentation shows residual contention after ownership is fixed, as a separately evidenced change. Proof = three consecutive aggregate compute-suite runs (§8), not one.

## 3. Wire protocol (worker contract)

One JSON object per line on stdin/stdout; stdout is protocol-only (sanitized diagnostics to stderr). Every frame carries `v` (protocol version), `run_id`, `session_key`, and a monotonic `seq`. Payload sizes, line sizes, active sessions, in-flight tool calls, and queue depth are bounded; malformed frames are terminal for the run, never for the process silently.

- Python → worker: `hello` (exact protocol + Pi package versions), `session.open` (session key, system prompt with protected blocks, history + revision, catalog, limits), `provider.bind` (short-lived binding; never echoed/persisted), `turn.prompt`, `turn.follow_up`, `turn.steer`, `turn.abort` (requires terminal ack), `tool.result`, `session.close`, `shutdown`.
- Worker → Python: `ready`, `run.started`, `assistant.delta`, `thinking.delta`, `tool.call`, `run.completed` (normalized usage/cost/stop reason), exactly one of `run.failed` / `run.aborted` as the terminal event, `session.closed`, `fatal`.

Retry discipline: a provider call may retry (bounded, same endpoint only) only before any visible output or any acknowledged side-effecting tool result; acknowledged tool calls are never replayed. Disconnect, cancellation, timeout, EOF, protocol violation, or authority rejection each produce exactly one terminal event, clear pending futures, and release the session lock.

## 4. Production scenario matrix (AC-4) — with the lab-tool coverage mapping

New pytest package `tests/pi_production/` maps 1:1 to the 15 catalog contracts
(`labs/pi-replacement/src/scenario-catalog.mjs:7-757`). Each test drives real ASGI routes +
real services + test-owned DB, with the real worker running against a **loopback provider
stub**: a `127.0.0.1` ephemeral-port HTTP server implementing the OpenAI-compatible (and,
where marked, Anthropic-compatible) wire format with scripted deterministic completions.
Unlike `fauxProvider` this exercises the genuine pi-ai provider HTTP stack inside the real
`Agent` loop, credential-free. The lab matrix stays as the fast contract layer and is never
cited as production evidence.

Coverage rule: the lab facade declares 29 tools; production chat canonically exposes 17
(`system_actions.py:79-431`). Where a lab canonical id has a production tool counterpart
(`tasks.create→create_task`, `documents.search→search_documents`, `memory.search→search_memory`,
`findings.search→search_findings`, …) the scenario asserts the real tool executes. Where it
does not (research-spine step recording, reasoning-bank store/retrieve, memento, autoresearch
propose/measure, eval emit, benchmark map, model-route record, webhook receive, channel
create/receive/respond as agent tools), the production proof drives the corresponding
**routes/services** inside the same Pi-run scenario and asserts governance state — the lab
tool name is never treated as a production API. The full id-by-id mapping table is committed
in the review packet so coverage claims are auditable.

| # | Lab scenario id | Production surfaces driven | Key assertions |
|---:|---|---|---|
| 1 | `chat.tool_loop.task_and_finding` | `POST /api/chat` + Pi header, loopback stub | Worker `run.started`/`tool.call` observed; `_generate_native_tools` spy never called; task + finding rows persisted in the test project; SSE envelope unchanged; telemetry span carries `endpoint_id` |
| 2 | `task.plan_execute.lifecycle` | Multi-turn Pi session (same session key) + task tools/services | Plan-and-execute steps continue one Pi session; task locks/status/review owned by Python services; `move_task` to `in_review` allowed, Done blocked without human action |
| 3 | `documents.tools.slice` | Document create/search/read/attach via canonical tools + routes | Canonical schemas and project checks enforced; cross-project document access denied |
| 4 | `structured_outputs.core_eval` | Structured output via OpenAI-compat **and** Anthropic-compat stubs | Valid output accepted; invalid output fails under the existing schema contract; both provider families exercised |
| 5 | `memory.rag.slice` | `search_memory` tool, `/memory/{project_id}` routes, Prompt-RAG `retrieve_context` | Project-only reads; cross-project denial; source-grounded results |
| 6 | `skills.three_skill_slice` | Three skills via canonical skill execution in a Pi turn | Requested order honored; protected blocks (spine contract, `chat.py:695`) present in the system prompt sent over the pipe |
| 7 | `a2a.debate_report.slice` | `tasks/send` admission → orchestrator inbox dispatch → `run_delegation` | All gates precede Pi; delegation persists normally; report creation blocked until existing gates pass; denial yields zero Pi sessions/spans/rows |
| 8 | `channel.lifecycle.simulated_slice` | `pi_local` create/start/inject/respond/stop via `channel_service` + `inbound_processor` | Real loop response (canned text gone); inbound/outbound persisted; ownership cleanup on stop |
| 9 | `research.spine.step_tracker` | Source/document routes → evidence units (`candidate_only`) → `/research-validity`, task, finding, report routes | Exact source spans; coding/reliability/reconciliation state real; provisional work cannot become Done/reportable; no test seeds acceptance |
| 10 | `autoresearch.governed_experiment.slice` | Governed Pi mode on `/autoresearch/start` | Candidate proposal only (`governance_required`, `report_evidence=False`); dry-run still mutation-free; no background loop; promotion blocked |
| 11 | `memory.reasoningbank.memento.slice` | ReasoningBank/Memento/skill-stat services in a Pi run | Scoped, verified outcomes recorded; raw-success promotion signals rejected; no global-memory writes |
| 12 | `channels.webhook.telegram.lifecycle` | Local webhook/Telegram-like fixtures through channel contracts | Zero external adapter/network traffic (transport spy); lifecycle ordering preserved |
| 13 | `steering.system_prompt.loop.slice` | `/steering` queue/follow-up/abort against a live Pi turn | Steer delivered once mid-turn; follow-up queued per Pi semantics; abort yields exactly one terminal event and full cleanup; protected blocks unremovable by user/tool content |
| 14 | `benchmarks.evals.real_user.contract` | Benchmark/eval/simulation/real-user contract ids mapped to production-run results | Every contract id resolves to a `tests/pi_production` result or an explicitly labeled gap — never the lab facade or a telemetry-only hook |
| 15 | `model.routing.telemetry.slice` | Endpoint resolution + telemetry inspection + adversarial same-model test | Exact endpoint/model/session identity; token/tool/latency/cost correct; no secret/host/fingerprint in any artifact |

## 5. Phased task breakdown

**P0 — Contracts, failing proofs, lock causality (test/doc-only commit).**
Protocol schema + redaction contract; failing tests for Agent ownership (legacy-loop spy), exact endpoint identity, same-model donor isolation, cancellation cleanup, telemetry drain, and 15 skeleton scenario tests marked to fail; committed lab→production mapping table; instrument the untracked-telemetry hypothesis and reproduce the aggregate lock; CF `gate before` captured, inherited large-file debt classified.
*Exit:* tests fail for the intended missing behavior, not fixture errors; lock mechanism demonstrated in writing.

**P1 — Worker, supervisor, resolver, tool bridge.**
`pi-runtime/` (promoted Agent core + protocol worker + provider factory for both families + dynamic tools + steer/followUp/abort); Python `pi_runtime/` package (protocol codec, supervisor, `PiEndpointResolver`, tool bridge); remove the `ComputeRegistry` registration from the Pi path. Node tests with `fauxProvider` + loopback stub (`node --test pi-runtime/test`); pytest supervisor tests with a scripted fake worker and the real worker in stub mode, incl. EOF/restart/abort/timeout/orphan assertions.
*Exit:* prompt → `tool.call` → `tool.result` → `run.completed` round-trip green with zero network and zero orphan processes.

**P2 — Chat production loop.**
`PiExecutionService` chat path + dispatch at `chat.py:803`; SSE mapping; persistence; fail-closed matrix (resolver miss, Keychain miss, spawn/handshake failure, mid-turn crash, client disconnect); session continuity across follow-up turns. Rewrite the 5 chat-side tests in `tests/test_pi_replacement_candidate.py:41-289` to assert worker event ownership while keeping fail-closed semantics identical.
*Exit:* scenario 1 green through the production route; non-Pi chat regression byte-identical.

**P3 — Seams: A2A, channel, Autoresearch, steering, governed artifacts.**
Orchestrator inbox Pi dispatch + accepted/denial matrix (update the 2 A2A tests); real `pi_local` turn (update the 3 channel tests); governed autoresearch mode (update the dry-run test, add no-mutation/no-promotion proofs); steering bridge against a live turn; delete the exercisers and rewrite the readiness test (`:440-484`) into governed production-path tests for spine/memory/ReasoningBank/Memento via routes.
*Exit:* scenarios 2-13 green; denial paths produce no Pi work.

**P4 — Providers, adversarial isolation, compute determinism.**
Anthropic-compatible stub + structured-output matrix; retry/error taxonomy; **mandated adversarial test**: a Pi endpoint and an authorized relay/browser donor both advertising `deepseek-v4-pro` — a Pi request hits only the API stub (transport spies assert zero donor frames), and an ordinary strict-model Istara request still selects and completes on the donor (`_select_candidates` behavior unchanged); negative twin: donated scheduling never sees resolver entries. Land the telemetry-ownership fix + regression; run the aggregate compute suite 3× consecutively.
*Exit:* both isolation directions proven; scenarios 14-15 green; suite deterministic.

**P5 — Full proof, bounded live evidence, docs, handoff.**
All 15 `tests/pi_production` green; lab `validate` + `paired:no-model` + `collect:artifacts` (labeled fast contract layer); **one** bounded live DeepSeek production-path call — Keychain preflight, no auto-retry, spend preflight against the cumulative USD 0.50 ledger (starting from the recorded `$0.09096299`), in-memory redaction before any write, blocked-not-substituted if unavailable; living feature docs + generated site + dated review packet with **regenerated exact counts** (the stale `8` vs current `12` finding is closed by regeneration, never hand-copying); security benchmark; CF `gate after`; spec acceptance without `--force`.
*Exit:* the full §8 ladder green; branch locally review-ready.

## 6. Acceptance criteria

1. Pi off/unselected ⇒ byte-identical legacy behavior; no worker spawn, no endpoint resolution, no Pi telemetry (AC-2).
2. Pi selected ⇒ the real pi-agent-core `Agent` observably owns the turn (worker `run.started`/`tool.call` asserted) and the Python ReAct loop is never entered (AC-1).
3. Every tool call executes in Python with real auth/project scope; unknown/unauthorized/cross-project calls return structured errors and are audited; the catalog contract test proves zero schema duplication in Node.
4. Pi requests carry an exact `endpoint_id`; the adversarial same-model test proves API-only routing for Pi **and** preserved donor scheduling for ordinary Istara (AC-3); no base URL/key/host/fingerprint in logs, SSE, telemetry, or evidence.
5. All 15 scenarios pass in `tests/pi_production/` against real services (AC-4); the lab matrix passes separately and is labeled non-production evidence.
6. All research/memory/steering/Autoresearch artifacts remain provisional/blocked absent real gates; the deleted exercisers have no surviving caller; no test manufactures acceptance, review events, reliability, or approval (AC-5).
7. `pi_local` and webhook fixtures exercise the real loop with zero external channel traffic (AC-6).
8. The aggregate compute suite passes 3× consecutively with the telemetry drain; no `database is locked`, no pending-task or event-loop warnings (AC-7).
9. Exactly ≤1 live DeepSeek request, redacted, within the cumulative USD 0.50 cap; blocked-not-substituted without the Keychain secret.
10. Docs/site/packet/lifecycle state identical post-change counts; CF-SPEC-7 accepted without force; branch local-only; `LLMs/` and `Model_Finetuning/` untouched.

## 7. Security and negative matrix

- Disabled/unselected: no worker process, secret resolution, endpoint call, Pi span, or behavior change.
- Selected but endpoint/secret/package/handshake/provider invalid: fail closed before the legacy loop and before any tool side effect.
- Cross-project session/tool/A2A/channel/steering handles: not-found/forbidden, no content-bearing telemetry.
- Same-alias donor: zero Pi frames to the donor; ordinary authorized scheduling still succeeds; unauthorized donor still rejected.
- Replayed/duplicate tool ids and A2A messages: no duplicate side effect (replay cache + tool-call id tracking).
- Abort/timeout/disconnect/child crash: exactly one terminal event; no pending future, session lock, orphan process, open transport, or late DB write.
- Model output cannot set project, agent, endpoint, acceptance, reliability, reconciliation, review, Done, reportability, promotion, or global-memory scope.
- Secrets only inside `provider.bind` on the private pipe; redaction-before-write for live captures; secret-scan over the review packet.

## 8. Verification ladder (exact commands; every referenced path verified to exist)

```bash
node --test pi-runtime/test
python -m pytest tests/pi_production -q
python -m pytest tests/test_pi_replacement_candidate.py -q
python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_a2a_service_scope.py tests/test_channels.py tests/test_channel_inbound.py tests/test_channel_resilience.py -q
python -m pytest tests/test_autoresearch.py tests/test_steering.py tests/test_steering_api.py tests/test_steering_manager.py tests/test_steering_project_scope_contracts.py tests/test_tasks.py tests/test_documents.py tests/test_findings.py tests/test_reports.py tests/test_memory.py tests/test_research_validity_contract.py tests/test_model_provider_contract.py tests/test_project_scope_contracts.py tests/test_reasoning_bank.py tests/test_sessions.py -q
python -m pytest tests/test_compute.py tests/test_compute_registry_hardening.py tests/test_compute_registry_model_loading.py tests/test_compute_vision_routing.py -q   # run 3 consecutive times; V-ISO adversarial test lives here
npm --prefix labs/pi-replacement run validate && npm --prefix labs/pi-replacement run paired:no-model && npm --prefix labs/pi-replacement run collect:artifacts
npm --prefix relay test
npm --prefix tests/real_user_benchmark run check
npm --prefix tests/simulation run test:static
python -m pytest tests/benchmarks/test_orchestration.py -q && python tests/benchmarks/run_benchmarks.py
python scripts/feature_docs.py --seed-missing --generate-site --check
python scripts/security_benchmark.py --fail-on-threshold
```

Then CF `gate before` (captured at P0) / `gate after` with inherited large-file debt separated
from new drift, `git status --short`, `git diff --check`, `git remote -v` (unchanged, no
push). Every teardown asserts no orphan `node` processes and no live worker. The single
bounded live command runs last, only after explicit permission + Keychain preflight + budget
check, followed immediately by packet redaction/secret scan:

```bash
python -m pytest tests/pi_live/test_pi_runtime_deepseek.py -m pi_live -q
```

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `steer`/`followUp`/`abort` never before exercised against the real Agent | P1 wires and tests them against the real worker first; scenario 13 is the production proof; no seam depends on them before P1 exit |
| Live model never previously hosted inside an `Agent` (lab used `completeSimple` directly) | Loopback stub drives the real pi-ai HTTP stack inside the Agent in P1; the single bounded live call in P5 is the only first-party live proof and is labeled as such |
| Supervisor lifecycle bugs (orphans, half-closed pipes, deadlocked handshake) | Handshake timeout, process-group kill of only the owned PID, per-module orphan assertions, restart-fails-closed tested in P1 |
| Cross-language schema serialization loss | Mechanical JSON-Schema pass-through + contract test constructing every tool in the worker; unsupported constructs rejected at `session.open`, not mid-turn |
| Endpoint resolver re-introduces a config collision | Settings-defined list, exact `endpoint_id` match, no ComputeRegistry writes anywhere in the Pi path; adversarial test runs in every regression (compute bundle) |
| SQLite-lock diagnosis is incomplete | Instrument-first in P0; audit `chat.py:922` and `:891-914` alongside `compute_route_evidence.py:102`; unrelated defects become new CF tasks, never silent scope growth or timeout inflation |
| Scenario coverage quietly falls back to lab-facade proofs | §4 coverage rule + committed id-by-id mapping; scenario 14 requires contract ids to resolve to production results or labeled gaps |
| Governed paths manufacture acceptance | Exercisers deleted (not deprecated); tests assert provisional/blocked via public routes; reviewer verifies no seeded acceptance |
| Secret/endpoint-fingerprint leakage | Secrets only in `provider.bind`; telemetry keyed by `endpoint_id`; redaction-before-write; packet secret scan |
| Cost/retry overrun on the live check | One-call guard, no auto-retry, worst-case preflight vs the `$0.09096299`→`$0.50` ledger |
| Version drift between lab and worker | Pin `@earendil-works/pi-agent-core`/`pi-ai` `0.80.10` + lockfile in `pi-runtime/`; a check asserts lab and worker resolve the same version |

## 10. Rollback

- Commits split per phase (P0 tests/docs; P1 worker/resolver; P2 chat; P3 seams; P4 isolation/determinism; P5 docs/evidence) — revert the smallest offending commit; never reset the shared worktree.
- Runtime rollback is configuration: Pi header absent / `pi_replacement_enabled` false ⇒ legacy path with zero Pi code executed; empty endpoint list ⇒ fail-closed typed error without touching `ComputeRegistry`; a dead or unstarted worker degrades to the same typed error, never to silent fallback.
- Deleting `pi-runtime/` and `backend/app/core/pi_runtime/` restores the pre-plan surface; donation, relay, channel, and research code are untouched by design.
- The telemetry-ownership fix may stay independently — it fixes lifecycle ownership without changing routing.
- Live-evidence failure ⇒ retain sanitized failure metadata only, mark the criterion blocked, no retry, no substitute provider.
- Rollback proof: non-Pi chat regression, fail-closed Pi tests, aggregate compute suite, security benchmark, feature-doc check, CF after-gate.

## 11. Definition of done / handoff

Done means: the production package imports the real Pi Agent Core; selected chat/task/A2A/channel/Autoresearch turns show Pi-owned provider and tool event progression while Istara contracts enforce state, authorization, and governance; API routing is exact by endpoint identity with both adversarial directions proven; all 15 production scenarios and the full §8 ladder pass; the compute suite is deterministically clean; teardown leaves no child/task/DB residue; docs and exact counts agree; security and CF gates show no new drift; and CF-SPEC-7 is accepted without force. Implementation begins only after cross-judge consensus and owner approval; the branch stays local, and protected folders stay untouched.

## Decision log

<!-- consensus-winner-decision -->
DEC-consensus-winner | 2026-07-20 | S1-plan | conductor
Context: three architect cross-votes completed
Decision: slot c selected from pi-runtime-complete-20260720-REPLAN-C-r1
Why: votes={"a": {"task": "pi-runtime-complete-20260720-JUDGE-A", "vote": "c"}, "b": {"task": "pi-runtime-complete-20260720-JUDGE-B", "vote": "c"}, "c": {"task": "pi-runtime-complete-20260720-JUDGE-C", "vote": "a"}}; tiebreak_used=False; plan_file=docs/build-stream/plans/pi-runtime-complete-20260720-plan-c.md



DEC-1 | 2026-07-20 | S0 | owner
Context: The audit showed the candidate was suitable for continued experiments but was not
a production Pi replacement and did not hard-isolate API routes from matching donors.
Decision: Complete every audited finding through a fresh planning-enabled Build Stream
Conductor cycle, using three architects and cross-judging before implementation.
Why: The owner explicitly requested full remediation and architect convergence; the blast
radius requires independent designs and evidence-gated review rather than another local shim.

## Ledger

### L-1 | 2026-07-20T01:33:00Z | S0-frame | codex-gpt-5 | framer | —
Did: Created CF-SPEC-7, recorded the complete production/Petals boundary and verification
bar, and prepared the planning-enabled conductor instruction packet.
Result: Owner-approved scope is durable and ready for three-architect planning.
Verified: `git status --short --branch` was clean before framing; prior conductor status
reported 19/19 tasks complete, reviewer pass, converged, daemon down.
Next: Dispatch architects A/B/C and cross-judges; pause on the winning plan for owner approval.

### L-2 | 2026-07-20T01:36:00Z | S1-plan | codex-gpt-5 | planner | Phase 0
Did: Clarified and planned CF-SPEC-7 without force, generated its linked requirement tasks,
and imported the planning-enabled conductor graph with three architects, cross-judges,
implementer, independent reviewer, and fixer roles.
Result: The complete audit packet is embedded in every architect, implementer, and reviewer
work order; the pipeline is linked to CF-SPEC-7 and ready for cast generation.
Verified: `make_pipeline.py ... --with-planning --spec CF-SPEC-7` imported five pipeline
tasks and four dependency edges with all nine run-scoped roles verified.
Next: Generate the registry-routed cast, run real CLI preflight, and spawn via Terminal.app.

### L-3 | 2026-07-20T01:52:01Z | S1-plan | claude-fable-5 | architect | Phase 0 <!-- bsc-ledger:pi-runtime-complete-20260720-PLAN-A -->
Did: Wrote independent consensus Plan A to docs/build-stream/plans/pi-runtime-complete-20260720-plan-a.md: supervised Node pi-runtime sidecar
(NDJSON/stdio) hosting the real pi-agent-core Agent, Python-exported canonical tool
manifest (no schema duplication), and a ComputeRegistry-disjoint ApiEndpointRegistry for
endpoint-identity pinning and Petals isolation; 5 phases, 15-scenario production test
matrix, exact verification ladder, risks, rollback.
Result: Plan A complete and buildable; pi-runtime-complete-20260720-PLAN-A
Verified: `python -m pytest tests/test_pi_replacement_candidate.py -q` -> 12 passed
(grounding baseline); code seams confirmed by direct inspection (chat.py L154/L501,
pi_replacement.py L52-86/L144-174, compute_registry_routing.py L154-190, a2a.py L306-478).
Next: Cross-judging of plans A/B/C, then owner approval of the consensus winner.

### L-11 | 2026-07-20T03:11:00Z | S2-execute | gpt-5.6-terra | executor | Phase 1 — private endpoint and lifecycle foundations <!-- bsc-ledger:pi-runtime-complete-20260720-IMPL -->
Did: Added `core/pi_runtime` endpoint resolver and typed Pi endpoint settings; removed Pi's transient LLM-router registration; added owned compute telemetry task draining, regression tests, and living compute-pool documentation.
Result: Pi endpoint selection is exact by endpoint identity and cannot advertise into or be selected by donated compute. Async compute telemetry is now drained before test DB-engine disposal. The real Node Pi Agent worker and production loop seams remain outstanding.
Verified: `python -m pytest tests/test_pi_runtime_endpoints.py tests/test_compute_route_evidence_lifecycle.py -q` (3 passed); `python scripts/feature_docs.py --seed-missing --generate-site --check` (passed); `git diff --check` (passed). Legacy Pi suite stalled at its eighth channel test during focused investigation, so it is not claimed as verification.
Next: Continue P1 worker/supervisor/tool bridge, then replace the Python ReAct Pi path and re-run the full matrix; stage exit: partial foundation committed with explicit residual risks.

## Phase 0 — architecture and production boundary

**Frame/Plan.** Architects must resolve the cross-language Pi runtime boundary, canonical
tool bridge, endpoint identity/provider representation, Petals isolation, governed loop
integration, rollback, and exact full-test campaign. Detailed instructions live in
`docs/build-stream/conductor-instructions/pi-production-runtime-completion.md`.

### Review (Phase 0) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|

**Remediation:** Pending architect consensus and cross-judging.

**Phase summary:** Pending.

## Phase 1 — private endpoint and lifecycle foundations

### Review (Phase 1) — Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| F-1 | Blocker | Product / Integration | `backend/app/api/routes/chat.py`; production Pi seams | The implementation stops at endpoint/telemetry foundations: the real Pi Agent Core worker and authority bridge, Pi-owned turn/tool loop, required governed integrations, and all 15 production-adapter scenarios remain absent. | FIX-pi-runtime-complete-20260720-REVIEW-r1 | open |
| F-2 | Blocker | Security / Integration | `backend/app/api/routes/chat.py:199-204`, `backend/app/core/compute_registry_routing.py:154-190` | Endpoint resolution is validation-only; Pi chat still invokes the shared registry by model alias with strict project routing, which prioritizes an authorized same-model relay/browser donor. | FIX-pi-runtime-complete-20260720-REVIEW-r1 | open |
| F-3 | Major | Tests | implementation evidence 343-346 | Verification covers only the resolver/drain foundation and omits the required production scenario, aggregate compute isolation, impacted-suite, lab/relay/benchmark/simulation, docs, security, and gate acceptance matrix. | FIX-pi-runtime-complete-20260720-REVIEW-r1 | open |

**Remediation:** Pending `FIX-pi-runtime-complete-20260720-REVIEW-r1` and a conductor-created delta re-review.

**Phase summary:** Review failed; endpoint resolution is a useful foundation but is neither a production Pi invocation path nor proof of API-versus-donor isolation.

## Summary (S5 — whole plan)

Pending implementation, independent review, remediation, final evidence, and local
PR-ready handoff.

### L-4 | 2026-07-20T01:52:24Z | S1-plan | gpt-5.6-sol | planner | pi-runtime-complete-20260720-architect-b <!-- bsc-ledger:pi-runtime-complete-20260720-PLAN-B -->
Did: pi-runtime-complete-20260720-architect-b stage on task pi-runtime-complete-20260720-PLAN-B (harness fallback entry; the model did not append one).
Result: task pi-runtime-complete-20260720-PLAN-B finished; worktree head f86a4f51.
Verified: see Compass Forge evidence rows on pi-runtime-complete-20260720-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-5 | 2026-07-20T01:57:22Z | S1-plan | claude-fable-5 | architect | Phase 0 <!-- bsc-ledger:pi-runtime-complete-20260720-REPLAN-A-r1 -->
Did: r1 repair of consensus Plan A (docs/build-stream/plans/pi-runtime-complete-20260720-plan-a.md). Root cause of the repair round: conductor validated the PLAN-A candidate before the harness stage_attribution row (evidence 305) landed — plan artifact itself was intact. Repair pass: audited every file/command the plan references; fixed two stale paths (tests/test_autoresearch.py, tests/benchmarks/test_orchestration.py + run_benchmarks.py) and added the lab paired:no-model deterministic matrix to the verification ladder; added r1 repair note to the plan header. Architecture, phases, acceptance, risks, rollback unchanged.
Result: Plan A candidate valid and buildable; pi-runtime-complete-20260720-REPLAN-A-r1
Verified: `python -m pytest tests/test_pi_replacement_candidate.py -q` -> 12 passed; path-existence audit of 25 plan-referenced files -> all exist post-fix; `python tests/benchmarks/run_benchmarks.py --help` -> valid CLI; npm script inventory confirmed validate/paired:no-model/collect:artifacts, relay test, real_user_benchmark check, simulation test:static.
Next: cross-judging of plans A/B/C once architect C finishes; conductor consensus, then owner approval.

### L-6 | 2026-07-20T02:30:24Z | S1-plan | kimi-code/k3 | planner | pi-runtime-complete-20260720-architect-c <!-- bsc-ledger:pi-runtime-complete-20260720-REPLAN-C-r1 -->
Did: pi-runtime-complete-20260720-architect-c stage on task pi-runtime-complete-20260720-REPLAN-C-r1 (harness fallback entry; the model did not append one).
Result: task pi-runtime-complete-20260720-REPLAN-C-r1 finished; worktree head b3c5d550.
Verified: see Compass Forge evidence rows on pi-runtime-complete-20260720-REPLAN-C-r1 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-7 | 2026-07-20T02:34:04Z | S1-plan | claude-fable-5 | reviewer | Phase 0 <!-- bsc-ledger:pi-runtime-complete-20260720-JUDGE-A -->
Did: Consensus judge slot a for CF-SPEC-7. Read both candidate plans (docs/build-stream/plans/pi-runtime-complete-20260720-plan-b.md, plan-c.md) and verified their discriminating code claims by direct inspection (llm_servers.py LLMServer save -> live registry registration; compute_registry_routing.py:182-188 strict+project sort prefers relay/browser donors; compute_route_evidence.py untracked loop.create_task(_emit())). Files touched: this lifecycle file only (no plan edits, per judge contract).
Result: plan_vote recorded for slot c. Plan C wins: it identifies and structurally avoids the LLMServer/ComputeRegistry donor-collision side effect that Plan B's endpoint reuse silently re-enters, hooks A2A at the orchestrator dispatch where delegated work executes, and carries a verified file:line seam map plus an auditable 30-vs-17 tool coverage mapping. pi-runtime-complete-20260720-JUDGE-A
Verified: Read of both plan files; sed inspection of backend/app/api/routes/llm_servers.py:55-85, backend/app/core/compute_registry_routing.py:178-192, backend/app/core/compute_route_evidence.py:95-110 -> all three Plan C claims confirmed. No tests run (judge stage; no code changed).
Next: remaining cross-judge votes, conductor consensus_result, then owner approval of the winning plan.

### L-8 | 2026-07-20T02:36:52Z | S1-plan | gpt-5.6-sol | reviewer | Phase 0 <!-- bsc-ledger:pi-runtime-complete-20260720-JUDGE-B -->
Did: Compared the two supplied consensus candidates, `docs/build-stream/plans/pi-runtime-complete-20260720-plan-a.md` and `docs/build-stream/plans/pi-runtime-complete-20260720-plan-c.md`; recorded the judge-b vote and self-report in Compass Forge. Files touched: this lifecycle file only; neither candidate plan was edited.
Result: Voted for slot c. Plan C is stronger at the execution seams: it hooks A2A where delegated work actually runs, specifies server-owned revision-checked session identity and replay-safe protocol bounds, maps the lab's 30-tool contract to the real 17-tool plus route/service production surface, and investigates SQLite lock causality before choosing mitigation. Task pi-runtime-complete-20260720-JUDGE-B.
Verified: `sed -n '1,220p' docs/build-stream/plans/pi-runtime-complete-20260720-plan-a.md` and `sed -n '1,280p' docs/build-stream/plans/pi-runtime-complete-20260720-plan-c.md` -> both candidates read completely; Compass Forge command evidence 321, plan_vote 322, self_report 323 recorded successfully. No tests run because this consensus-judge stage changes no code.
Next: stage exit: plan_vote for judge slot b recorded; conductor may collect the remaining vote and compute consensus.

### L-9 | 2026-07-20T02:45:53Z | S1-plan | kimi-code/k3 | reviewer | Phase 0 <!-- bsc-ledger:pi-runtime-complete-20260720-JUDGE-C -->
Did: Consensus judge slot c for CF-SPEC-7 (assigned pair: Plan A vs Plan B). Read both candidate plans in full and independently verified the discriminating code claims by direct inspection: persisted LLMServer records register into the live router/compute plane (llm_servers.py:64-78 _register_and_probe_server), strict+project model sort prefers relay/browser donors (compute_registry_routing.py:179-190), untracked loop.create_task(_emit()) telemetry (compute_route_evidence.py:102), ensure_pi_deepseek_registered exists (pi_replacement.py:52). Existence-checked all 18 existing test files referenced across both plans' verification campaigns (18/18 present). Files touched: this lifecycle file only (no plan edits, per judge contract).
Result: plan_vote recorded for slot a. Plan A wins on the load-bearing architectural decision: its ComputeRegistry-disjoint ApiEndpointRegistry makes the audited API/donor alias collision unrepresentable and it explicitly removes the audited ensure_pi_deepseek_registered transient node, whereas Plan B's LLMServer reuse (verified to live in the shared registry plane) never addresses that artifact. Plan B's superior protocol rigor (revision-digest sessions, phase-aware retry, terminal-event taxonomy) and failing-tests-first/sqlite-root-cause discipline are flagged for the implementer to absorb. pi-runtime-complete-20260720-JUDGE-C
Verified: file-existence audit 18/18 OK; read inspection of llm_servers.py:40-99, compute_registry_routing.py:148-197, compute_route_evidence.py:40-102, pi_replacement.py:52 -> all cited claims confirmed. No tests run (judge stage; no code changed).
Next: remaining cross-judge votes, conductor consensus_result, then owner approval of the winning plan.

### L-10 | 2026-07-20T02:46:40Z | S1-plan | kimi-code/k3 | architect | Phase 0 <!-- bsc-ledger:pi-runtime-complete-20260720-REPLAN-C-r2 -->
Did: r2 repair of consensus Plan C (docs/build-stream/plans/pi-runtime-complete-20260720-plan-c.md). Root cause of the repair round: conductor validated the REPLAN-C-r1 candidate before the harness stage_attribution row landed (evidence 315, 02:30:24Z, after r2 was created 02:29:24Z) - same race as PLAN-A r1; plan artifact was intact. Repair pass: re-audited all 31 seam claims, 32 ladder paths, npm script inventory, and symbol-level facts against head 161fb0cf; corrected one factual drift (lab facade tool count 30 -> 29 unique canonicalIds, canonical-tool-facade.mjs:82-481) in sections 1 and 4; added r2 repair note to the plan header. Architecture, phases, acceptance, risks, rollback unchanged.
Result: Plan C candidate valid, buildable, and factually exact; pi-runtime-complete-20260720-REPLAN-C-r2
Verified: `python -m pytest tests/test_pi_replacement_candidate.py -q` -> 12 passed in 34.98s; audit script -> 31/31 seam claims PASS; 31/32 ladder paths exist (tests/pi_production is planned-new in P0); npm scripts validate/paired:no-model/collect:artifacts, relay test, real_user_benchmark check, simulation test:static all present; pi-agent-core 0.80.10 steer/followUp/abort confirmed at agent.d.ts:82-96 with zero lab call sites; spend ledger 0.09096299 USD / cap 0.5 confirmed at scenarios/collect-replacement-artifacts.mjs:12,399.
Next: cross-judging of plans A/B/C completes; conductor consensus, then owner approval.

### L-12 | 2026-07-20T02:57:25Z | S1-plan | conductor | planner | Phase 0 <!-- bsc-ledger:pi-runtime-complete-20260720-PLAN-C -->
Did: Reconciled the original blocked Plan C scaffold after its governed repair lineage completed. The original Kimi session produced no plan artifact and was stopped after prolonged inactivity; `REPLAN-C-r1` produced Plan C, and `REPLAN-C-r2` supplied the final corrected attribution and factual audit.
Result: The original `PLAN-C` dependency is fulfilled by `REPLAN-C-r2`, which won cross-judging 2-1 and received explicit owner approval. The original task was marked done only to release its pre-existing `PLAN-C -> IMPL` pipeline edge; its failed attempt remains recorded as blocked/canceled in actor and task history.
Verified: Compass Forge evidence row 339 records `superseded_by=pi-runtime-complete-20260720-REPLAN-C-r2` and `owner_approved=true`; the conductor `approve` action selected `REPLAN-C-r2` as the governing plan.
Next: Dispatch the independent code reviewer after the implementation task completes.

### L-13 | 2026-07-20T03:24:43Z | S3-review | gpt-5.6-sol | reviewer | Phase 1 — private endpoint and lifecycle foundations <!-- bsc-ledger:pi-runtime-complete-20260720-REVIEW -->
Did: Independently reviewed commits `78f00556..5e65e62e`, the implementer evidence, endpoint/telemetry tests, production chat invocation seam, shared ComputeRegistry routing contract, docs, and lifecycle status. Files touched: this lifecycle file only.
Result: Fail verdict recorded on `pi-runtime-complete-20260720-REVIEW`; raised F-1 and F-2 Blockers plus F-3 Major and created `FIX-pi-runtime-complete-20260720-REVIEW-r1`. The private resolver validates identity but is not used to invoke Pi; selected chat remains on the old Python/shared-registry loop and can prefer an authorized same-model donor.
Verified: `python -m pytest tests/test_pi_runtime_endpoints.py tests/test_compute_route_evidence_lifecycle.py tests/test_compute_registry_hardening.py::test_strict_project_model_routing_prefers_authorized_relay_over_local_duplicate -q` -> 4 passed; `python -m pytest tests/test_pi_replacement_candidate.py -q` -> 12 passed in 33.41s; `git diff --check 22d1b956..HEAD` -> passed; `compass-forge gate after --task pi-runtime-complete-20260720-REVIEW --summary` -> no new failures, inherited large-file debt only.
Next: stage exit: remediate F-1 through F-3 under `FIX-pi-runtime-complete-20260720-REVIEW-r1`, then delta re-review the changed surface.
