# Plan A — Pi Agent Core owns the production loop through a supervised runtime bridge

Architect A, task `pi-runtime-complete-20260720-PLAN-A` (r1 repair validated under `pi-runtime-complete-20260720-REPLAN-A-r1`), CF-SPEC-7, branch `Review_pi_test` (local only).

*r1 repair note:* full path audit of every file/command named in this plan; corrected `tests/test_autoresearch.py` and `tests/benchmarks/test_orchestration.py` + `run_benchmarks.py` (previous names did not exist) and added the lab `paired:no-model` deterministic matrix to the ladder. Architecture, phases, acceptance, risks, rollback unchanged.

## 1. Architecture summary

The audited candidate keeps Istara's Python ReAct loop (`backend/app/api/routes/chat.py::_generate_native_tools`, L154-345) and merely pins `deepseek-v4-pro` through `ComputeRegistry`. The real `@earendil-works/pi-agent-core` `Agent` runs only in `labs/pi-replacement/src/istara-pi-adapter.mjs`. Plan A closes that gap with three load-bearing decisions:

**D-A1 — A production Node "Pi runtime" sidecar owned by a Python supervisor, speaking NDJSON over stdio.** A new top-level Node package `pi-runtime/` (sibling of `relay/`, reusing the pinned `@earendil-works/pi-agent-core@0.80.10` and `@earendil-works/pi-ai` from the lab) hosts the real `Agent` with `streamFn`, `sessionId`, `toolExecution: "sequential"`, and event subscription exactly as the lab adapter does today (`istara-pi-adapter.mjs` L150-178). Python gains `backend/app/core/pi_runtime/supervisor.py` (`PiRuntimeSupervisor`), which spawns the sidecar with `asyncio.create_subprocess_exec`, performs a handshake, multiplexes per-session turns, and owns lifecycle: liveness, restart with fail-closed sessions, cancellation, and teardown. Wire protocol (one JSON object per line, versioned):

- Python → runtime: `hello` (tool manifest + protocol version), `start_turn` (session id, system prompt, messages, provider binding, limits), `tool_result`, `steer`, `follow_up`, `abort_turn`, `close_session`, `shutdown`.
- runtime → Python: `ready`, `turn_started`, `assistant_delta`, `thinking_delta`, `tool_call` (request — the runtime *asks Istara* to execute), `turn_finished` (usage: tokens/tool counts/stop reason), `session_error`, `fatal`.

Pi Agent Core therefore owns turn progression, tool-call sequencing, follow-up turns, steering interaction, and provider invocation. Istara owns everything behind the `tool_call`/`tool_result` seam: tool implementation, auth, project scope, persistence, research governance, telemetry, SSE shaping.

**D-A2 — Canonical tools are exported from Python, never redeclared in Node.** The single source of truth stays `backend/app/skills/system_actions.py` (`SYSTEM_TOOLS`/`OPENAI_TOOLS`). A new `backend/app/core/pi_runtime/tool_manifest.py` serializes the JSON-Schema tool definitions (name, description, parameters) into the `hello` message; the sidecar constructs pi-agent-core tools dynamically from that manifest, with `execute` implemented as a bridge round-trip. The lab's hand-written `canonical-tool-facade.mjs` TypeBox schemas remain lab-only (fast contract layer); a drift test asserts the manifest and the lab facade agree on tool names and required parameters, so the lab cannot silently diverge. No tool logic exists in Node; a `tool_call` for an unknown/unauthorized tool returns a structured tool error, never an exception that kills the session.

**D-A3 — API endpoint identity is a first-class registry disjoint from `ComputeRegistry`.** New `backend/app/core/api_endpoints.py` (`ApiEndpointRegistry`) holds `ApiEndpoint` records: `endpoint_id` (opaque, stable), `provider_kind ∈ {openai_compat, anthropic_compat}`, `base_url` (from env/Keychain-adjacent config, never logged), `model`, `keychain_service`/`keychain_account` (resolved at spawn/turn time via the existing `_read_macos_keychain_secret` path, `backend/app/config.py` L16-36), retry policy (bounded same-endpoint retries only), and timeouts. The existing `pi-deepseek-candidate` transient node (`pi_replacement.py::ensure_pi_deepseek_registered`, L52-86) is **removed from `ComputeRegistry`** and re-expressed as the default `ApiEndpoint` (`endpoint_id="pi-deepseek-default"`, service `istara-pi-deepseek`, account `openclaw`). Pi turns carry a resolved `provider binding` `{endpoint_id, provider_kind, base_url, model, api_key}` to the sidecar over stdio only (never argv, never env files); the sidecar configures pi-ai's OpenAI-compatible or Anthropic provider with that explicit `baseURL`. Pi execution **never consults `ComputeRegistry`**, so no model-alias match against a relay/browser donor is possible by construction; donated scheduling never consults `ApiEndpointRegistry`. Isolation is proven behaviorally (§6, V-ISO) rather than asserted structurally.

### Why this shape (trade-offs)

- *Sidecar vs per-request `node` spawn:* a supervised long-lived sidecar gives session continuity (Pi `Agent` instances persist per session id, mapping 1:1 to Istara `ChatSession`), sub-turn latency, and one cleanup point. Cost: supervisor complexity (restart, orphan reaping) — accepted and bounded in P1.
- *stdio NDJSON vs local HTTP/WebSocket:* stdio inherits the parent's lifetime (no port management, no localhost auth surface, no leaked endpoint fingerprints in netstat), and the repo already trusts subprocess seams (Keychain `security` calls in both stacks). Cost: no second consumer of the stream — acceptable, Python is the only consumer and re-emits SSE.
- *Tool-manifest export vs TypeBox duplication:* eliminates schema drift permanently; cost is that manifest serialization must cover the OpenAI JSON-Schema subset pi-agent-core validates — verified by a round-trip contract test (P1).
- *Registry split vs "source pin" flag inside `ComputeRegistry`:* a flag inside the shared selector keeps the shared code path and one subtle bug from re-enabling donor selection; a disjoint registry makes the forbidden path unrepresentable and keeps donation code untouched (mandated: avoid broad changes to donation code). Cost: a second, small registry — intentional.

## 2. Production integration per seam

**Chat (`POST /api/chat`).** At the top of the handler (`chat.py` L502), the existing `pi_replacement_requested()` header check (`x-istara-agent-engine`) dispatches to a new `PiChatEngine` (`backend/app/core/pi_runtime/chat_engine.py`) *before* the legacy loop is entered. `PiChatEngine` reuses the route's existing auth/project checks and Prompt-RAG preparation, resolves the `ApiEndpoint`, opens/reuses the supervisor session keyed by chat session, and translates bridge events into the existing SSE envelope (`chunk`/`tool`/`error`/`done`) and message persistence. Fail-closed: unresolved endpoint, missing Keychain secret, sidecar spawn failure, or handshake timeout emit the typed `pi_registration_unavailable`-style SSE error with **zero** provider transport and **no** fallback into `_generate_native_tools`/`_generate_text_fallback`. Non-Pi requests take the unmodified legacy path (baseline rollback, AC-2).

**A2A.** All existing gates stay untouched and ordered as today (`a2a.py` L306-470: auth → rate → replay → project scope → persistence → audit). After an accepted `tasks/send` persists, when the Pi engine is requested, the delegated work item executes through a `PiDelegationRunner` that drives the same `PiChatEngine` turn contract in-process (agent-role system prompt, task payload as the user turn), persisting resulting messages/artifacts through the existing A2A service. Reports remain gated by existing report eligibility; denial cases produce zero Pi spans and zero sidecar sessions. The current telemetry-only `record_pi_a2a_event` (L471-478) remains, now attached to a real execution.

**`pi_local` channel.** `build_pi_channel_response` (`pi_replacement.py` L144-174) is replaced: `inbound_processor.process_inbound_channel_message` (L184 call site) invokes the Pi engine in-process with the inbound text and channel/project context and sends the real Pi turn output through the registered `PiLocalAdapter`. Ownership, pause, cross-project, stop/delete semantics are unchanged (they live above this seam). No external channel adapters are touched; webhook/Telegram-like coverage uses local fixtures only.

**Autoresearch.** `dry_run` keeps its envelope (`autoresearch.py` L613-637). A governed Pi execution mode (opt-in body flag + Pi header + project authorization) runs a bounded Pi turn that may only produce a **candidate proposal record** with `governance_required=True`, `report_evidence=False`, no filesystem mutation, no promotion, no background runner beyond the audited path. Promotion/report stays behind the existing human-approval gates (AC-5).

**Research spine, memory/RAG, ReasoningBank/Memento/ModelSkillStats, steering.** The `production_test_ready: false` exercisers (`exercise_pi_production_readiness` and friends, `pi_replacement.py` L224-494) are deleted. Their coverage moves to production-path tests that drive real routes with the Pi engine active: sources/documents/tasks through their API routes; evidence/coding/reconciliation/report state observed through `/research-validity`, task, finding, and report routes asserting *provisional/blocked* (never seeded acceptance); `/memory/{project_id}/search` and Prompt-RAG with cross-project denial; ReasoningBank items recorded as process memory only; steering queue/steer/abort through `/steering` routes interacting with a live Pi turn via the bridge `steer`/`abort_turn` messages. `ModelSkillStats` and skill-memory record only what existing governance permits; raw tool success never becomes a strong positive signal (Self-Improvement Governance Contract).

**Telemetry.** `turn_finished` usage (tokens, tool counts, stop reason, latency, estimated cost from the lab's `raw-llm-capture.mjs` pricing table moved into shared config) is recorded through the existing telemetry recorder with `endpoint_id` as the route identity — never base URL, host, or key material.

## 3. Phased task breakdown

**P1 — Runtime bridge and endpoint registry (foundation).**
- T1.1 `pi-runtime/` package: protocol codec, `Agent` session host, dynamic tool construction from manifest, provider binding (openai-compatible + anthropic-compatible via pi-ai), usage extraction. Unit tests with `fauxProvider` (`node --test pi-runtime/test`).
- T1.2 `PiRuntimeSupervisor`: spawn/handshake/restart/abort/close, per-session mux, secret passing over stdio, orphan cleanup on interpreter exit (atexit + process-group kill). Pytest with a scripted fake sidecar and with the real sidecar in faux mode.
- T1.3 `tool_manifest.py` + drift test against `SYSTEM_TOOLS` and the lab facade.
- T1.4 `ApiEndpointRegistry` + config surface (`settings.pi_api_endpoints`), Keychain resolution, retry/timeout policy; remove `ensure_pi_deepseek_registered` from the `ComputeRegistry` path. Provider-contract unit tests.
- Exit: bridge round-trip (prompt → tool_call → tool_result → turn_finished) green under pytest with zero network.

**P2 — Chat production loop.**
- T2.1 `PiChatEngine` + `/api/chat` dispatch; SSE mapping; persistence; fail-closed matrix; session continuity across follow-up turns.
- T2.2 Rewrite the four chat-side tests in `tests/test_pi_replacement_candidate.py` (L42-289) to assert the Pi loop (sidecar events observed) instead of the pinned Python loop; keep fail-closed semantics identical.
- Exit: scenario 1 (chat tool loop, task, finding, telemetry) passes through production routes.

**P3 — Loop seams: A2A, channel, Autoresearch, research/memory/steering.**
- T3.1 `PiDelegationRunner` + A2A accepted/denial matrix.
- T3.2 `pi_local` real-loop response; channel lifecycle/ownership/cleanup tests updated.
- T3.3 Governed Autoresearch execution mode + no-mutation/no-promotion proofs.
- T3.4 Delete exercisers; land the governed production-path tests for spine/memory/ReasoningBank/Memento/steering (scenarios 5, 9, 10, 11, 13).
- Exit: scenarios 2–13 pass through the production adapter.

**P4 — Endpoint routing completeness, Petals isolation, compute determinism.**
- T4.1 Session continuity, controlled retry (same endpoint only), typed error taxonomy, telemetry fields; Anthropic-compatible endpoint covered by a local stub.
- T4.2 **Adversarial isolation test (mandated):** register a Pi `ApiEndpoint` and an authorized relay/browser donor both advertising `deepseek-v4-pro`; a Pi request must hit only the API endpoint stub (transport spies on both sides assert zero donor traffic); an ordinary strict-model Istara request must still select the donor (`compute_registry_routing._select_candidates` behavior unchanged, L154-190). Negative twin: donated scheduling never sees `ApiEndpointRegistry` entries.
- T4.3 Root-cause the aggregate-suite `sqlite3.OperationalError: database is locked`: the fire-and-forget telemetry tasks from `schedule_compute_telemetry_event` (`compute_route_evidence.py` L52) each open independent `async_session()` commits (`telemetry.py` L25-57) that outlive tests. Fix: track scheduled tasks in a module registry, add `drain_compute_telemetry()` awaited in fixture teardown (and app shutdown), and set sqlite `busy_timeout`/WAL in the test engine. Prove with 3 consecutive full-suite runs.
- Exit: aggregate compute suite deterministic; scenarios 14–15 pass; both isolation directions proven.

**P5 — Full regression, evidence, docs, handoff.**
- T5.1 Bounded DeepSeek production-path run: one request through `/api/chat` with the real sidecar and the Keychain secret, no retry, fixed limits, spend preflight against the cumulative USD 0.50 ledger, in-memory redaction before any write, evidence into the dated review packet.
- T5.2 Living docs: chat/A2A/compute/model-routing/messaging feature docs, provider + compute-pool architecture, review packet with exact current test counts (the stale `8 vs 12` finding — regenerate counts from the post-change run, never hand-copied), lifecycle file.
- T5.3 CF `gate before/after` comparison separating inherited large-file debt from new drift; spec coverage for CF-SPEC-7 without `--force`.
- Exit: full ladder (§6) green; local branch review-ready; no push.

## 4. Production scenario matrix (AC-4)

A new pytest package `tests/pi_production/` maps 1:1 to the 15 catalog contracts (`labs/pi-replacement/src/scenario-catalog.mjs`, `ISTARA_PI_SCENARIOS`), each test driving real ASGI routes + real services + test-owned DB with the real sidecar in **stub-provider mode**: a local `127.0.0.1` ephemeral-port HTTP stub implementing the OpenAI-compatible (and, where relevant, Anthropic-compatible) wire format with scripted deterministic completions. This exercises the genuine pi-agent-core loop and genuine pi-ai provider HTTP stack — unlike `fauxProvider`, which bypasses the provider transport — while remaining credential-free. Lab `npm run validate` + `collect:artifacts` matrix stays as the fast contract layer; it is never cited as production evidence. Scenario→test mapping is committed in the review packet so reviewers can audit coverage claims.

## 5. Acceptance criteria

1. Pi off/unselected ⇒ byte-identical legacy behavior; zero sidecar spawn, zero `ApiEndpointRegistry` reads (AC-2).
2. Pi selected ⇒ pi-agent-core `Agent` observably owns the turn (bridge `turn_started`/`tool_call` events asserted), Python loop not entered (AC-1).
3. Every canonical tool call executes in Python with real auth/project scope; unknown/unauthorized tools return structured errors; no schema duplicated in Node (drift test green).
4. Endpoint identity: Pi requests carry `endpoint_id`; same-model donor collision test proves API-only routing both directions (AC-3); no base URL/key/fingerprint in logs, SSE, telemetry, or evidence.
5. All 15 scenarios pass in `tests/pi_production/` against real services (AC-4); lab matrix separately green.
6. Research/memory/steering/Autoresearch artifacts remain provisional/blocked absent real gates; the deleted exercisers have no surviving caller; no test seeds acceptance (AC-5).
7. `pi_local` and webhook fixtures exercise the real loop with zero external channel traffic (AC-6).
8. Aggregate compute suite passes 3× consecutively with telemetry drain; no `database is locked` (AC-7).
9. Exactly ≤1 live DeepSeek request, redacted, under the cumulative USD 0.50 cap; blocked-not-substituted if Keychain unavailable.
10. Docs/site/packet/lifecycle agree with implementation, including exact post-change test counts; CF spec accepted without force; branch local-only, `LLMs/` and `Model_Finetuning/` untouched.

## 6. Verification ladder (exact commands)

Credential-free, in order (each recorded as CF command evidence):

```bash
node --test pi-runtime/test
python -m pytest tests/test_pi_replacement_candidate.py -q
python -m pytest tests/pi_production -q
python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_channels.py tests/test_channel_inbound.py tests/test_channel_resilience.py -q
python -m pytest tests/test_project_scope_contracts.py tests/test_research_validity_contract.py tests/test_research_integrity_validation.py tests/test_reasoning_bank.py tests/test_steering.py tests/test_autoresearch.py tests/test_sessions.py tests/test_model_provider_contract.py -q
python -m pytest tests/test_compute.py tests/test_compute_registry_hardening.py tests/test_compute_registry_model_loading.py tests/test_compute_vision_routing.py -q   # 3 consecutive runs (V-ISO isolation tests live here)
npm --prefix labs/pi-replacement run validate && npm --prefix labs/pi-replacement run paired:no-model && npm --prefix labs/pi-replacement run collect:artifacts
npm --prefix relay test
npm --prefix tests/real_user_benchmark run check
npm --prefix tests/simulation run test:static
python -m pytest tests/benchmarks/test_orchestration.py -q && python tests/benchmarks/run_benchmarks.py   # orchestration benchmark tests + runner
python scripts/feature_docs.py --seed-missing --generate-site --check
python scripts/security_benchmark.py --fail-on-threshold
```

Then Compass Forge `gate before`(captured at P1 start)/`gate after`, `spec coverage CF-SPEC-7`, `git status --short`, `git diff --check`, `git remote -v` (unchanged refs, no push). Finally the single bounded DeepSeek command (T5.1) followed immediately by the packet redaction/secret scan. Adversarial proof points: transport spies on every provider seam; denial cases assert zero sidecar sessions, zero spans, zero DB effects; teardown asserts no orphan `node` processes and no live sidecar after each test module.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Sidecar lifecycle bugs (orphans, deadlocked handshake, half-closed pipes) | Supervisor watchdog + handshake timeout, process-group kill on exit, per-test orphan assertion, restart-fails-closed semantics tested in P1 |
| Streaming/cancellation races across the bridge | Versioned protocol with explicit `abort_turn` ack; steering tests drive steer/abort mid-turn against the real sidecar |
| Tool-manifest subset mismatch with pi-agent-core validation | Round-trip contract test constructs every canonical tool in the sidecar and validates a sample call at P1 exit |
| Secret leakage via argv/env/logs/evidence | Secrets only on stdio frames; redaction-before-write; secret-scan gate; log fields limited to `endpoint_id`/hashes/counts |
| Donor collision regression re-enters via future selector edits | Isolation expressed as disjoint registries plus the committed adversarial two-sided test in the aggregate compute suite (runs on every regression) |
| Governed paths quietly manufacture acceptance | Exercisers deleted, not deprecated; tests assert provisional/blocked via public routes; review packet labels unavailable stages |
| Stub-provider coverage overclaimed as live proof | Packet separates stub-provider production-path evidence from the single live DeepSeek record |
| sqlite lock returns under load ordering changes | Telemetry drain hook + busy_timeout committed with a 3× consecutive-run gate, not a one-off pass |
| Cost/retry overrun on the live check | One-call guard, no auto-retry, worst-case spend preflight vs. cumulative ledger |
| Cross-language dependency drift (`0.80.10`) | Pin exact versions in `pi-runtime/package.json` + lockfile; validate lab and runtime import the same version |

## 8. Rollback

- Commits split per phase (P1 bridge/registry; P2 chat; P3 seams; P4 isolation/determinism; P5 docs/evidence) — revert the smallest offending commit; never reset the shared worktree.
- Runtime rollback is configuration: Pi header absent/engine disabled ⇒ legacy path with zero Pi code executed; `ApiEndpointRegistry` empty ⇒ Pi fails closed without touching `ComputeRegistry`. Killing the sidecar (or it never spawning) degrades to the typed unavailable error, never to silent fallback.
- Deleting `pi-runtime/` and the `backend/app/core/pi_runtime/` package restores the pre-plan surface; donation, relay, channels, and research code are untouched by design, so no rollback there.
- Live-evidence failure ⇒ retain sanitized failure metadata only, mark the criterion blocked, no retry, no substitute provider.
- Confirm rollback with: non-Pi chat regression, fail-closed Pi tests, aggregate compute suite, security benchmark, feature-doc check, CF after-gate.

## 9. Handoff

Implementation starts only after cross-judge consensus and owner approval. Done means: the acceptance list in §5 is evidenced at real boundaries, both isolation directions hold adversarially, the review packet states exactly what stub-provider evidence proves versus the one live record, and `Review_pi_test` is locally review-ready with no push, no `origin` mutation, and protected folders untouched.
