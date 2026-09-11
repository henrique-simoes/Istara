# Plan B — Pi production runtime as a supervised Node worker with Istara authority RPC

## Planning verdict

Build a production runtime package outside `labs/` and run it as a lazily started,
supervised Node child of the Python backend. The real
`@earendil-works/pi-agent-core` `Agent` owns the selected turn: prompt/follow-up/steering
progression, provider-stream invocation, tool-call sequencing, and Pi event emission.
Python remains the sole authority for authentication, project scope, persisted sessions,
canonical tool schemas and implementations, research-validity transitions, human review,
telemetry, and rollback.

The boundary is a versioned NDJSON protocol over private stdin/stdout. It is intentionally
not an HTTP sidecar: there is no extra listening port, deployment surface, or auth domain,
and test teardown can prove the child is gone. The runtime is default-off and must fail
closed after explicit Pi selection; it must never silently fall back to the legacy Python
ReAct loop.

## Evidence behind the design

- `labs/pi-replacement/src/istara-pi-adapter.mjs` is the only current production-like
  importer of Pi Agent Core. Its `Agent` and event behavior are reusable, but its
  `CanonicalToolFacade`, faux provider, and in-memory product state are not.
- `backend/app/api/routes/chat.py` still executes both Pi-selected native-tool and text
  paths through `ollama.chat_stream`; Pi currently changes registration/model/telemetry,
  not loop ownership.
- `backend/app/core/compute_registry_routing.py::_select_candidates` prioritizes an
  authorized `relay`/`browser` node for a strict model match. A model alias is therefore
  not an API endpoint identity.
- `backend/app/core/pi_replacement.py` contains a canned channel response and isolated
  source/memory/steering probes whose result remains `production_test_ready: false`.
- A2A and Autoresearch currently add Pi telemetry around the existing paths; neither
  delegates its agentic work to a Pi-owned runtime.
- `backend/app/core/compute_route_evidence.py` launches untracked telemetry tasks while the
  global pytest fixture disposes the async DB engine after each test. This is the leading
  causal hypothesis for the aggregate-only SQLite lock and must be proven before changing
  timeouts or serializing the suite.

## Scope and non-goals

In scope:

- a production Node runtime and Python supervisor/adapter;
- explicit OpenAI-compatible and Anthropic-compatible API endpoint identity;
- Pi-selected chat, task/plan execution, A2A, `pi_local`, governed Autoresearch,
  steering/follow-up, and canonical research/memory service integration;
- all 15 scenarios through the production adapter with test-owned persistence;
- deterministic telemetry/DB cleanup, living docs, security controls, and evidence.

Out of scope:

- changing relay/browser registration, connection strings, WebSocket protocol, donor
  capacity, model advertisement, or ordinary donated scheduling;
- external Telegram, WhatsApp, Google Chat, webhook, or other live traffic;
- changing the Research Spine acceptance rules or automating human Done/report approval;
- loading local models, deploying, pushing, opening a PR, or touching `LLMs/` or
  `Model_Finetuning/`.

## Architecture

### 1. Production package and process ownership

Create `runtime/pi-agent/` with its own locked production dependencies and no import from
`labs/pi-replacement`. The package contains:

- `src/worker.mjs`: NDJSON dispatcher and process lifecycle;
- `src/session-runtime.mjs`: one real Pi `Agent` per authoritative session key;
- `src/provider-factory.mjs`: OpenAI-compatible and Anthropic-compatible Pi provider
  adapters, including the test-owned loopback transport;
- `src/protocol.mjs`: protocol version, schemas, redaction, and terminal error mapping;
- Node tests for handshake, event order, session continuity, tool RPC, cancellation,
  malformed frames, provider errors, and secret redaction.

Add a Python `PiRuntimeManager` (split into focused modules under
`backend/app/core/pi_runtime/`) that owns exactly one child per backend process. It starts
only after `pi_replacement_requested()` and endpoint validation both succeed. It maintains
bounded per-run queues, correlates messages by `run_id`, serializes mutations per session,
and permits independent sessions to run concurrently. FastAPI lifespan shutdown calls
`close()`, cancels active runs, waits a bounded grace interval, then terminates/kills only
the child PID it created.

Protocol commands:

| Python to Node | Purpose |
|---|---|
| `hello` | Require an exact protocol and Pi package version handshake. |
| `session.open` | Bind authoritative project/session/agent identity, persisted history revision, system prompt, endpoint reference, model, and allowed tool catalog. |
| `turn.prompt` | Begin a user turn on a bound session. |
| `turn.follow_up` | Queue Pi `followUp()` without creating a second agent loop. |
| `turn.steer` | Invoke Pi `steer()` for an active turn. |
| `turn.abort` | Abort the run/session and require a terminal acknowledgement. |
| `tool.result` | Return a canonical Istara tool result for a Node-originated call. |
| `provider.bind` | Supply a short-lived provider binding on the private pipe; values are never echoed or persisted. |
| `session.close` / `shutdown` | Release state and prove cleanup. |

Node to Python emits `run.started`, Pi-native `agent.*`/`message.*`/`tool.*` events,
`tool.call`, normalized usage/cost, `run.completed`, and one terminal `run.failed` or
`run.aborted`. Every frame carries `protocol_version`, `run_id`, `session_key`, and a
monotonic sequence number. stdout is protocol-only; diagnostics go to sanitized stderr.
Payload and line sizes, active sessions, in-flight tool calls, and queue depth are bounded.

### 2. Session continuity, cancellation, and failure semantics

The authoritative session key is a server-generated digest of
`(project_id, chat_session_id-or-task_id, agent_id, endpoint_id, model)`; the model cannot
supply or alter any element. Python sends the persisted message history plus a revision on
first open. Reuse requires the same revision and endpoint/model identity; a mismatch closes
and rehydrates the Node agent instead of appending to stale state. Successful turns persist
through existing Istara services before the acknowledged revision advances.

Request disconnect, task cancellation, steering abort, runtime timeout, provider timeout,
child EOF, malformed protocol, or tool-authority rejection produces one terminal event,
clears pending futures, and releases the session lock. No Pi-selected request falls through
to Python ReAct. Retries are bounded and phase-aware: a provider call may retry only before
visible output or a side-effecting tool result; the runtime never replays an acknowledged
tool call. Child restart may rehydrate a later turn from persisted history, but it does not
resume an ambiguous in-flight turn.

### 3. Canonical tool authority bridge

Build the run's catalog in Python from the existing canonical `OPENAI_TOOLS`, skill-tool
builder, and any route-specific allowlist. Convert the existing JSON Schema mechanically
to the Pi tool parameter object; add a contract test that normalizes and compares every
name/description/schema so Node cannot acquire a divergent hand-maintained catalog.

Pi tool `execute` sends `tool.call` to Python. Python looks up the opaque `run_id`, ignores
all model-supplied scope fields, re-injects the authenticated `project_id`, `agent_id`,
task/session handles, and role, validates the arguments against the same schema, and calls
the existing canonical executor/service. It returns a JSON/text result tagged with the
original Pi tool-call id. Unknown, forbidden, duplicate, cross-project, post-abort, or
oversized calls are rejected and audited.

Research-writing tools may create only source/evidence/candidate or provisional artifacts.
They enter existing evidence-unit, coding, reliability, reconciliation, review, and report
services. The Pi catalog excludes any direct transition to accepted/reportable, human
approval, Done, production promotion, or global memory. ReasoningBank, Memento skill
memory, RAG, and `ModelSkillStats` are invoked only through existing project-scoped
services and receive verified outcome/governance state; raw provider/tool success cannot
become a strong positive learning signal.

### 4. Endpoint identity and provider routing

Reuse the persisted, encrypted `LLMServer` record as the source of API configuration. Add
an explicit Pi endpoint selection setting/reference; resolve it to an immutable per-run
`PiEndpointBinding` containing:

`endpoint_id`, `provider_family`, `model_id`, `credential`, `timeout`, `retry_budget`, and
a private base URL. Only `openai_compat`/supported OpenAI-family types and `anthropic` are
accepted. The public/event form contains only `endpoint_id`, provider family, model id, and
a non-reversible route handle. Host, hostname, path, credential, headers, and endpoint
fingerprints never enter logs, SSE, DB telemetry, captures, exceptions, or review docs.

Endpoint resolution is by exact persisted `LLMServer.id` and explicit model, not priority
or alias. Reject a missing/deleted/unhealthy/non-API/relay/browser endpoint before child
startup. The Node provider talks to only that binding. It does not call
`ComputeRegistry._select_candidates`, so relay/browser nodes are structurally ineligible.
Keep the ordinary ComputeRegistry path unchanged for non-Pi traffic.

The adversarial proof registers an API endpoint and an authorized relay/browser donor
that advertise the same model. A Pi production turn must hit the API fixture exactly once
and send zero WebSocket donor requests. A subsequent ordinary Istara request for the same
project/model must select and complete on the donor, preserving positive donation behavior.

### 5. Production integration points

Use one `PiExecutionService` facade so routes do not each invent runtime semantics:

- **Chat:** after auth/project/session checks and prompt/RAG/system-policy construction,
  branch before `_generate_native_tools`/text ReAct. Translate Pi events to the existing SSE
  contract, persist assistant/tool outcome through current message/session services, and
  propagate disconnect/abort. The unselected branch is byte-for-byte behaviorally
  unchanged and does not start Node or resolve a Pi credential.
- **Task and plan-and-execute:** branch the real agent research/execution entry point when
  the owning task/run is explicitly Pi-selected. Pi owns the loop; task transitions,
  locks, artifacts, review state, and scheduler wakeups remain existing Python services.
- **A2A:** retain JSON-RPC parsing, auth, replay, rate, size, agent/project scope, and
  `tasks/send` admission before Pi is invoked. The accepted task is passed to
  `PiExecutionService`; delegation and reports use canonical A2A/task/report tools. Denied
  requests create neither Pi work nor Pi telemetry. Pi cannot directly create a report.
- **Channels:** after the current instance/project/paused checks and inbound persistence,
  `pi_local` invokes a real Pi channel turn and persists/sends the outbound through normal
  channel contracts. Remove the canned response. Ordinary adapters and messages without
  Pi selection never invoke the runtime. Telegram-like/webhook coverage uses only local
  fixture messages and the `pi_local` adapter.
- **Autoresearch:** the governed experiment runner may select Pi for an explicitly
  sandboxed experiment. Pi can run the hypothesis/evaluation tool sequence and persist
  candidate evidence, but promotion remains an existing governance proposal plus human
  decision. `dry_run` remains mutation-free; default-off remains unchanged.
- **Steering/follow-up:** connect the existing project-scoped steering manager to the
  active Pi session. Deliver each queue item once, acknowledge it only after Pi accepts it,
  and abort using the same run cancellation path. Preserve existing REST/WebSocket scope
  checks and system-prompt protected blocks.

Delete or narrow the synthetic `exercise_pi_*` helpers once each scenario has a production
caller. A readiness endpoint may aggregate real run evidence, but it must not manufacture
tasks, nuggets, confidence, review events, coding reliability, approvals, or reportability.

### 6. Telemetry and deterministic cleanup

Derive telemetry from Pi events plus Istara service outcomes: run/turn ids, endpoint id,
provider family, model id, session revision, event/tool counts, success/error taxonomy,
token usage, latency, and cost. Persist no prompts, tool arguments/results, source text,
credentials, base URLs, hosts, or endpoint fingerprints in telemetry. Raw bounded live
captures follow the existing redaction contract and cumulative USD 0.50 cap.

Before changing SQLite settings, reproduce the aggregate lock with the predefined compute
suite and instrument outstanding route-telemetry tasks at test boundaries. Replace
fire-and-forget `loop.create_task(_emit())` with a small owned background-task registry:
tasks remove themselves on completion; `drain_compute_telemetry()` awaits them; application
shutdown and the pytest teardown fixture drain before engine disposal. Preserve best-effort
telemetry semantics while making lifecycle ownership explicit. Add a regression that
delays a telemetry write, finishes a compute call, drains, disposes, and proves no pending
task/lock/warning. Do not "fix" the symptom by inflating `sqlite_busy_timeout_ms`, adding
suite sleeps, or disabling telemetry.

## Phased task graph

### Phase 0 — Baseline, contracts, and failing proofs

Definition of Ready: CF gate-before captured; dirty files classified; current 12 Pi tests,
lab matrix, and aggregate compute suite results recorded; no active live server/model.

Work:

1. Add protocol schemas and Python/Node contract tests first.
2. Add failing tests for real Agent ownership, no legacy-loop call, exact endpoint identity,
   same-model donor isolation, cancellation cleanup, and aggregate telemetry drain.
3. Inventory each of the 15 scenarios as lab-contract, production-adapter, or live-bounded
   proof; require a production-adapter test for every row.

Acceptance: tests fail for the intended missing production behavior, not fixture/setup
errors; gate debt is recorded as inherited (especially existing large files).

Rollback: test/doc-only commit; revert without runtime impact.

### Phase 1 — Runtime worker, supervisor, providers, and tool RPC

Definition of Ready: protocol and redaction contracts reviewed; exact Pi package version
locked; endpoint record and secure-field resolver identified.

Work:

1. Implement `runtime/pi-agent` and `PiRuntimeManager` handshake/session/turn lifecycle.
2. Implement OpenAI-compatible and Anthropic-compatible provider bindings, exact endpoint
   selection, bounded retries, normalized events/usage, and secret redaction.
3. Implement mechanically derived canonical tool schemas and the authenticated Python
   execution bridge.
4. Add startup-on-first-Pi-request, EOF/restart, cancellation, timeout, queue bound, and
   shutdown tests.

Acceptance: a test-owned HTTP provider drives the real Pi `Agent` through text, tool call,
tool result, follow-up, steering, and completion; canonical tools mutate only the requested
test project; no child remains after teardown.

Rollback: disable `pi_replacement_enabled`, remove the endpoint id, and stop the managed
child; baseline Python remains intact.

### Phase 2 — Chat and task execution

Definition of Ready: Phase 1 contract suite green and supervisor cleanup proven.

Work:

1. Branch Pi-selected chat before the Python native/text loops and preserve the existing
   SSE/persistence envelope.
2. Integrate Pi at the real task/agent execution boundary for plan-and-execute, documents,
   structured outputs, skills, memory/RAG, and system-prompt policy.
3. Connect steering/follow-up/abort to the active Pi session.

Acceptance: selected routes prove Pi event ordering and assert the legacy loop/provider
was never called; unselected regression snapshots match baseline; session continuation and
restart rehydration preserve history exactly once.

Rollback: feature selection off returns all calls to the untouched legacy branch; close
all Pi sessions.

### Phase 3 — A2A, channels, governed Autoresearch, and Research Spine

Definition of Ready: canonical tool bridge passes cross-project and governance negatives.

Work:

1. Invoke Pi only after accepted A2A admission and preserve delegation/report gates.
2. Replace `pi_local` canned output with the real production Pi loop; cover local
   Telegram-like/webhook fixture lifecycle only.
3. Run governed Autoresearch through Pi in sandbox/dry-run modes without auto-promotion.
4. Route source/evidence, coding, reliability/reconciliation, tasks/findings/documents,
   ReasoningBank, Memento, RAG, and skill-stat behavior through existing services.

Acceptance: all research outputs remain provisional until real independent coding,
reconciliation where required, and human-approved Done state; denial paths produce no Pi
work; channels cannot cross projects; no external traffic occurs.

Rollback: remove Pi selection metadata from these callers and stop `pi_local`; existing
A2A/channel/Autoresearch services remain authoritative.

### Phase 4 — Endpoint/Petals isolation and deterministic compute suite

Definition of Ready: API endpoint binding and donor test doubles both expose the same alias.

Work:

1. Add the same-model adversarial negative/positive test without broad donation changes.
2. Prove OpenAI-compatible and Anthropic-compatible exact endpoint/model behavior,
   controlled failure, and no cross-endpoint retry.
3. Confirm and fix the unowned telemetry-task cause; add explicit drain/shutdown.

Acceptance: Pi calls only the selected API endpoint, ordinary donated scheduling still
calls the donor, and the aggregate compute suite passes repeatedly without SQLite locks,
pending tasks, event-loop warnings, or sleeps.

Rollback: endpoint constraint changes are additive; Pi off preserves current scheduler.
The telemetry drain can remain independently because it fixes lifecycle ownership without
changing donor routing.

### Phase 5 — Full 15-scenario proof, docs, security, and handoff

Definition of Ready: every prior phase green; no unresolved Blocker/Major review finding.

Work:

1. Run all 15 scenarios through the production adapter with test-owned DB and provider
   fixture; retain the lab matrix as a separate fast contract layer.
2. Run one or more explicitly authorized bounded DeepSeek production-path cases only if
   Keychain availability and the remaining cumulative USD 0.50 budget are verified.
3. Update exact test counts and evidence in affected living feature docs, generated site,
   compute/provider docs, and a new dated review packet; do not rewrite older historical
   packets except to add a clear successor pointer if repository convention permits.
4. Run security benchmark, feature-doc generator, CF gate-after, independent review, and
   delta remediation until dry. Drain/close the runtime before CF acceptance; finish every
   linked task with evidence so acceptance needs no force.

Acceptance: lifecycle, final packet, feature docs, manifests, and command evidence state
the same exact post-change counts and residual risks; worktree contains no secrets or
runtime artifacts.

Rollback: one config/feature-flag action restores baseline; process shutdown and endpoint
unbind are verified; no migration destroys user data.

## Production scenario acceptance matrix

| # | Production proof through real Pi adapter and real Istara authority |
|---:|---|
| 1 | Chat turn invokes canonical task/finding tools, persists scoped state, emits Pi/tool/telemetry events, and never enters Python ReAct. |
| 2 | Plan-and-execute continues the same Pi session across steps while Istara owns task locks/status/review. |
| 3 | Document lookup/create and tool results use canonical schemas, project checks, and persisted services. |
| 4 | Structured output succeeds for OpenAI-compatible and Anthropic-compatible fixtures; invalid output fails under the existing schema contract. |
| 5 | Memory/RAG reads are project-only and source-grounded; no global/cross-project leakage. |
| 6 | Three representative skills run through canonical skill execution in requested order and protected prompt blocks remain present. |
| 7 | A2A admission precedes Pi; delegation persists normally; report creation remains blocked until existing gates pass. |
| 8 | `pi_local` create/start/inject/respond/stop uses the real loop, persists inbound/outbound correctly, and cleans ownership. |
| 9 | Exact source spans become evidence units/candidate atoms; coding/reliability/reconciliation state is real; provisional work cannot become Done/reportable. |
| 10 | Autoresearch uses sandboxed Pi execution, dry-run is mutation-free, and promotion requires governed review. |
| 11 | ReasoningBank/Memento/skill stats receive scoped, verified outcomes and reject raw-success promotion signals. |
| 12 | Local webhook/Telegram-like fixtures traverse channel contracts with zero external adapter/network traffic. |
| 13 | Steering/follow-up reaches the active Agent once, abort cleans up, and system-prompt policy cannot be removed by user/tool content. |
| 14 | Benchmark/eval/simulation/real-user contract ids map to actual production results, not the lab facade or telemetry-only hooks. |
| 15 | Exact endpoint/model/session identity and token/tool/latency/cost telemetry are correct and free of secrets/endpoint fingerprints. |

## Security and negative acceptance

- Pi disabled/unselected: no Node process, secret resolution, endpoint call, Pi telemetry,
  or behavior change.
- Selected but missing/invalid endpoint, secret, package, handshake, or provider: fail
  closed before the legacy loop and before a tool side effect.
- Cross-project session/tool/A2A/channel/steering handles: reject as not found/forbidden and
  emit no content-bearing telemetry.
- Same alias on donor: donor receives zero Pi frames; ordinary authorized scheduling still
  succeeds; unauthorized donor remains rejected.
- Replayed/duplicate tool ids and A2A messages: execute no duplicate side effect.
- Abort/timeout/disconnect/child crash: exactly one terminal event, no pending future,
  session lock, orphan process, open transport, or late DB write.
- Model output cannot set project, agent, endpoint, acceptance, reliability, reconciliation,
  review, Done, reportability, promotion, or global-memory scope.
- Logs/SSE/telemetry/captures contain no credential, authorization header, raw endpoint,
  hostname/path, or reversible endpoint fingerprint.

## Exact verification campaign

Run from the repository root. The implementer may split the impacted pytest bundle while
developing, but final evidence must include the aggregate commands exactly as listed.

```bash
python -m pytest tests/test_pi_runtime_protocol.py tests/test_pi_runtime_production_scenarios.py -q
python -m pytest tests/test_pi_replacement_candidate.py -q
python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_a2a_service_scope.py tests/test_channels.py tests/test_channel_inbound.py tests/test_channel_resilience.py tests/test_autoresearch.py tests/test_steering.py tests/test_steering_api.py tests/test_steering_manager.py tests/test_steering_project_scope_contracts.py tests/test_tasks.py tests/test_documents.py tests/test_findings.py tests/test_reports.py tests/test_memory.py tests/test_research_validity_contract.py tests/test_model_provider_contract.py tests/test_project_scope_contracts.py -q
python -m pytest tests/test_compute.py tests/test_compute_registry_hardening.py tests/test_compute_registry_model_loading.py tests/test_compute_vision_routing.py -q
python -m pytest tests/test_compute.py tests/test_compute_registry_hardening.py tests/test_compute_registry_model_loading.py tests/test_compute_vision_routing.py -q
npm --prefix runtime/pi-agent test
npm --prefix labs/pi-replacement run validate
npm --prefix labs/pi-replacement run paired:no-model
npm --prefix relay test
npm --prefix tests/real_user_benchmark run check
npm --prefix tests/simulation run test:static
python -m pytest tests/benchmarks/test_orchestration.py -v
python tests/benchmarks/run_benchmarks.py
python scripts/feature_docs.py --seed-missing --generate-site --check
python scripts/security_benchmark.py --fail-on-threshold
compass-forge gate after --task <implementation-task> --summary
```

Run the aggregate compute bundle twice in the same campaign to prove the lock fix is
deterministic rather than an isolated pass.

The bounded live command is deliberately not unconditional. After explicit permission,
Keychain preflight, and budget check, run the production adapter's dedicated live marker,
never the lab-only smoke path, and store only redacted artifacts:

```bash
python -m pytest tests/pi_live/test_pi_runtime_deepseek.py -m pi_live -q
```

## Documentation and evidence updates

At minimum inspect and update the living architecture pages for chat overview/sessions/
steering/model controls, A2A, messaging/channels, Autoresearch experiments, agent loops,
compute pool, findings evidence/review/reports, tasks review/send-report, documents, memory,
skills, and governed evolution. Add a living Pi runtime/provider page if no existing page
can own the protocol and endpoint contract. Regenerate the site/manifests with the required
feature-doc command. Update the dated final review packet with the exact new Pi scenario
and regression counts; the stale `8 passed` row must not survive as the current claim.

Compass Forge evidence must contain: gate-before/gate-after comparison; every exact command
and result; files touched; endpoint/donor adversarial trace; process cleanup proof; security
scorecard; generated-doc check; independent review verdict; and any bounded live cost total.

## Trade-offs and risks

| Choice/risk | Consequence and mitigation |
|---|---|
| Supervised child instead of in-process Python emulation | Adds protocol/process complexity, but it is the smallest boundary that lets the real TypeScript Pi Agent own the loop. Versioned frames, lazy start, bounded queues, and owned teardown contain the risk. |
| Direct exact API binding instead of ComputeRegistry scheduling | Duplicates a narrow provider-transport concern, but makes donor exclusion structural. Reuse encrypted `LLMServer` configuration and shared normalization/redaction helpers; do not duplicate donor scheduling. |
| Long-lived session cache | Enables real follow-up/steering and lowers startup cost, but can drift from DB. Require persisted revision matching and deterministic rehydration. |
| Cross-language canonical schemas | Serialization may lose unsupported schema features. Normalize/compare the entire catalog in contract tests and reject unsupported constructs at startup. |
| Provider retry after streaming/tool calls | Can duplicate visible output or side effects. Retry only before output and before an acknowledged side effect; otherwise fail terminally. |
| Broad integration surface | A single large cutover is unsafe. Land phases behind the same default-off selector, review each phase independently, and preserve the old branch untouched until final proof. |
| SQLite lock diagnosis may reveal more than telemetry tasks | Treat the untracked task as a hypothesis, instrument first, and fix the demonstrated owner. Any unrelated defect becomes a separate CF task rather than a timeout workaround. |

## Definition of Done

The plan is complete only when the real production package imports Pi Agent Core; selected
chat/task/A2A/channel/Autoresearch turns show Pi-owned provider and tool event progression;
all canonical state changes pass through Istara authority; API routing is exact by endpoint
and model identity; same-alias donors are both excluded from Pi and preserved for ordinary
scheduling; all 15 production scenarios and every required regression command pass; the
aggregate compute suite is deterministically clean; runtime teardown leaves no child/task/
DB residue; docs and exact counts agree; security and CF gates show no new drift; and an
independent reviewer has no open Blocker or Major finding. Rollback remains a default-off
configuration change with no destructive migration.
