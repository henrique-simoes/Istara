# Pi Replacement Candidate — Independent Review Diagnosis

Date: 2026-07-20
Reviewer: Claude (Fable 5), independent of the Build Stream Conductor cast that produced the branch.
Subject: `/Users/user/Documents/Istara-main-pi-replacement`, branch `Review_pi_test` (CF-SPEC-7, "Pi production runtime completion").
Reviewed inputs: `docs/build-stream/2026-07-20-pi-production-runtime-completion.md`, `docs/build-stream/review-packet/pi-complete-20260719/{README.md,LOCAL_PR.md}`, Compass Forge state (specs, tasks, evidence rows, after-gate), full read of `pi-runtime/` and `backend/app/core/pi_runtime/`, full audit of `tests/pi_production/` (all suites re-run locally, all green), and a whole-codebase surface inventory of Istara's LLM/agentic call sites.

---

## VERDICT (read this first)

**This is NOT yet a real candidate for replacing Istara's agentic loop and model management throughout the codebase.** It IS a genuinely well-engineered, opt-in, fail-closed *chat-surface adapter* — the best evidence yet that pi-agent-core can own individual Istara turn loops — but three independent walls stand between it and the stated goal (README: "full agentic-core replacement, not a partial augmentation"):

1. **Coverage wall:** with Pi selected, the Pi engine executes the work of **2 of ~67 registry-routed chat call sites** (the chat route's two loops) plus 3 narrow seams. **~51 chat call sites still run the legacy ComputeRegistry path unconditionally** — including the entire production research spine, all skills, reports, validation, compaction, and the second full ReAct loop in `interfaces.py`. Surface-level: ~5 of ~30 distinct agentic surfaces are covered.
2. **Structural wall (model management):** pi-ai's provider model is "outbound HTTP to one pinned API endpoint." Istara's compute economy is a mutable pool of four source classes — local Ollama/LM Studio with model pull/JIT load, persisted `LLMServer` rows, LAN-discovered servers, and **donated relay/browser nodes that dial in over reverse websockets**. Pi can structurally replace only one of the four. Donated compute, embeddings (all RAG), the model-management plane (discovery/health/circuit breakers/capacity), N-distinct-node consensus validation, and pool-sweeping autoresearch (`model_temp`) are **not coverable by pi-agent-core at all** (category (c) below).
3. **Quality wall:** the runtime as committed has **2 Blocker and 6 Major defects** (frame-size kill/wedge, duplicate-session race, steering races, no turn cap on a paid API, event-loop-blocking Keychain calls, session leak, LLM turn inside an open DB transaction), several headline hardening claims that are **not in the code** (HMAC session keys, bounded queues, seq validation, retry/timeout, fatal-restart, Python-side tool allowlist enforcement), and a test/evidence layer whose central claim ("real ASGI routes") is **false** — zero of 32 tests drive an ASGI route.

**Realistic ceiling** (agrees with what the candidate's own code comments imply): Pi could own all *conversational/agent turn loops* (categories (a)+(b), roughly 15–20 surfaces after substantial extension work), while `ComputeRegistry` remains the permanent substrate for donated compute, embeddings, local-model lifecycle, and pool routing. "Replace model management with pi's" is off the table; "replace the turn-loop engine, keep the compute plane" is the honest reformulation.

---

## 1. What the candidate actually is (verified)

- A supervised Node worker (`pi-runtime/`, ~620 LOC + 4 node tests) hosting the real `@earendil-works/pi-agent-core@0.80.10` `Agent` (npm-published, MIT, pre-1.0; pinned with lockfile), speaking NDJSON over stdio to `backend/app/core/pi_runtime/` (`supervisor.py` 360, `engine.py` 502, `seams.py` 212, `endpoints.py` 105 LOC).
- Verified genuinely implemented: real Agent loop with tool round-trip to Python `execute_tool` with authority scope re-injection; Keychain-at-turn-time secrets carried only in `provider.bind`; `PiEndpointResolver` fully disjoint from `ComputeRegistry` (the donor-collision fix is real, and `test_same_model_donor_isolation.py` proves both directions with a spy that demonstrably fires on the ordinary path); fail-closed chat dispatch with no fall-through to `_generate_native_tools`; F-5 fail-closed terminal handling in channel/delegation/autoresearch seams; exercisers deleted; opt-in gating that external channel senders cannot self-select.
- Covered seams (category (a)): chat SSE turn, chat steering bridge, `a2a_task`/`pi_delegate` orchestrator delegation, `pi_local` channel reply, governed autoresearch **proposal-only** entry.
- CF process: CF-SPEC-7 accepted without force (14 tasks, 56 evidence rows); after-gate reproduced by this review: 0 new/actionable failures, only inherited `unexpected_large_files` (28). The conductor's five-round review ladder was real and adversarial (it caught the uncommitted-runtime fraud pattern, the donor-collision gap, and the fail-open seams before this review did).

## 2. Findings register

Severity: **B**locker to the replacement decision, **M**ajor, **m**inor.

### A. Coverage findings (the "throughout all of Istara" question)

| ID | Sev | Finding |
|----|-----|---------|
| A-1 | B | Pi engine executes 2 of ~67 registry-routed chat call sites when selected. Uncovered loops that ARE the product's agentic core: research spine `agent_research.py:129,478,667,1062` (ReAct loop, planner, step executor, reflection verifier — production task-picking never calls Pi), A2A collaboration/debate handlers `agent_lifecycle.py:857,942,996`, orchestrator steering handler `:519`, skills (`skill_factory.py` ×5, `discover/*` ×9, `intercoder.py` ×5), report manager ×6, validation ×6+, context DAG compaction `context_dag.py:611` (still legacy even for a Pi chat turn), deployed-channel interviews, `interfaces.py:125,588` (an entire second ReAct loop with no Pi gate), presentation, UI audit. All category (b): coverable only with substantial further engineering. |
| A-2 | B | Category (c) — structurally NOT coverable by pi-agent-core: (1) donated relay/browser compute — donors dial in over outbound websockets (`compute_node_transport.py:305`), pi-ai needs an outbound `base_url`; opposite connection topology; (2) embeddings — no embeddings API in pi-agent-core/pi-ai; all RAG/memory/vector-health/validation-similarity traffic stays on the registry; (3) model-management plane — pulls, JIT loads (`ollama.py:74-86,210-223`), LAN discovery, health probes, circuit breakers, capacity scoring, context-window sync; (4) N-distinct-node consensus validation and donor-backed dual-coder kappa; (5) `model_temp` autoresearch pool sweeps; (6) vision on donated nodes. |
| A-3 | M | Governed autoresearch coverage is proposal-only: the legacy 6-runner loop (~14 call sites) is bypassed, not functionally replaced. Claiming autoresearch as a "covered seam" overstates. |
| A-4 | M | Pi path silently drops inference semantics the registry provides: `response_format` structured output with provider schema adaptation, `thinking_mode`, `min_context`, temperature/max_tokens (hardcoded `maxTokens: 4096`, `contextWindow: 128000`, `thinkingLevel: "off"` — `provider.mjs:42-52`, `session.mjs:78`), model-availability fallback, per-route evidence. Mid-history trim-note system messages are dropped by the role filter (`chat.py:141-143`). |

### B. Runtime defects (from full code read; none has a test)

| ID | Sev | Finding |
|----|-----|---------|
| B-1 | B | Unbounded Python→worker frame size: `supervisor.py:94-100` never checks `MAX_LINE_BYTES`; worker hard-fails lines > 256 KiB (`protocol.mjs:44-46,57-59`) with a process-level `fatal` broadcast to ALL sessions (`worker.mjs:190-194`, `supervisor.py:132-136`). One big system prompt/history or large `tool.result` (e.g. `get_document_content`) kills every concurrent Pi turn; the poisoned reader re-emits `fatal` forever and nothing restarts the child. |
| B-2 | B | Supervisor wedges permanently when the reader dies without process death: default 64 KiB StreamReader limit in `asyncio.create_subprocess_exec` (`supervisor.py:75-82`); a worker stdout line > 64 KiB (tool-call args alone may reach 64 KiB) raises `ValueError`, `_read_loop` exits, child stays alive, `_ready` stays set → `ensure_started` returns success forever; every future Pi turn times out. Recovery: backend restart only. |
| B-3 | M | Duplicate `session_key` race (`chat.py:147` = `project:session_id`): overlapping requests on one chat session cross-deliver frames (queue overwrite `supervisor.py:165-166`), worker revision check aborts the live run, `run_turn` never filters by `run_id`. |
| B-4 | M | Blocking macOS Keychain `subprocess.run` (3 s timeout) inside the event loop, up to twice per chat turn (`endpoints.py:83` → `config.py:43-63`; called from `engine.py:177` and `chat.py:927`). |
| B-5 | M | Steering bridge races: single-slot `active_project_id` per agent (`steering.py:269-285`) → concurrent Pi turns for the same agent id spuriously `turn.abort` healthy runs (`engine.py:248-251`); the pump also competes with the background agent work cycle for the same steering queues. |
| B-6 | M | No turn/iteration cap on the Pi loop against a paid API (legacy has `MAX_TOOL_ITERATIONS = 8`, `chat.py:77`); `run_timeout` resets per frame, so a tool-happy model loops indefinitely at owner cost. PROTOCOL.md's `limits:{max_turns}` is unimplemented on both sides. |
| B-7 | M | `open_session` failure leaks the session queue (registered before send, `PiWorkerError` raised outside the `try/finally` — `engine.py:190` vs `:200-228`), compounding toward permanent exhaustion of the worker's 8-session cap. |
| B-8 | M | `pi_local` channel reply runs the full multi-second LLM turn inside an open SQLite session/transaction (`inbound_processor.py:177-234`); crash mid-turn loses the inbound message. |
| B-9 | m | Un-awaited async `steer`/`followUp` handlers in the worker (`worker.mjs:123,129`) → unhandled rejection can crash the whole Node process. |
| B-10 | m | Failed Pi chat turn still persists an assistant `Message` and emits `done` with a `message_id` (`chat.py:1021-1073`) — inconsistent with the fail-closed contract applied elsewhere. |
| B-11 | m | `PiWorkerError`/`asyncio.TimeoutError` escape the autoresearch route as raw 500s (`autoresearch.py:656-667`); `ready` `protocol_version` never validated (`supervisor.py:128-131`); aborted turns recorded as `error` in telemetry (`engine.py:458`); `FrameReader` drops good frames preceding a malformed one (`worker.mjs:189`). |
| B-12 | M | Doc'd hardening that is NOT in the code: no HMAC session keys (plain f-strings — `chat.py:147`, `seams.py:101`); "bounded queues" are unbounded (`asyncio.Queue()` no maxsize, `supervisor.py:165`); `seq` stamped by worker but never sent/validated by Python; `timeout_ms`/`max_retries` are dead config (`provider.mjs:33-35` ignores them; no retry/timeout in the worker at all); "fatal → supervisor restarts" (PROTOCOL.md:52-53) false; Python-side tool allowlist never enforced — `tool_handler` (`engine.py:183-187`) executes ANY name in `TOOL_EXECUTORS`, so a buggy/compromised worker can call `send_agent_message`/`web_fetch` from a "read-only" autoresearch or delegation session; `catalog_tool_names()` (`tools.py:43`) exists for exactly this check and has zero callers. API key is placed in worker `process.env` (`provider.mjs:39-40`) — contradicting "never env" (nuance: not argv, but env). |

### C. Test/evidence integrity findings

| ID | Sev | Finding |
|----|-----|---------|
| C-1 | B | "Every scenario drives real ASGI routes" (completion doc :177,401,520; Plan C; review packet) is **false**: 0 of 32 tests use `ASGITransport`/`TestClient`. Three tests call route handler *functions* with `SimpleNamespace` requests and authorization monkeypatched out (`test_scenario_delegation.py:160-162`, `test_scenario_autoresearch.py:45-46`, `test_seams_fail_closed.py:270-271`). Auth, DI, middleware, and SSE-over-HTTP are unproven for the Pi path. The harness's own docstring (`harness.py:3-8`) says "seams", contradicting the docs. Original finding F-4 ("tests call seams directly, overstate production coverage") was re-worded, not fixed. |
| C-2 | M | The coverage-map "contract" (`test_scenario_coverage_map.py`) is a static dict + `hasattr`; not derived from `scenario-catalog.mjs`; scenario 14 maps to the test itself. It cannot catch catalog drift or gutted tests — the exact failure modes a coverage contract exists for. With `node` absent, 25 of 32 cases skip and the "contract" still passes green. |
| C-3 | M | Several scenario "proofs" assert conditions the tests construct: scenario 4's structured-output validator lives in the test (no production validator exists); scenario 10 asserts hardcoded literals the engine unconditionally attaches (`engine.py:423-434`) and never challenges the read-only catalog with an attempted mutation; scenarios 3/5 "cross-project denied" never attempt a denial; scenarios 9/11 outcomes are direct test-authored service calls after a decorative Pi turn; scenario 13's "production chat caller" test fakes both the binding and the worker. |
| C-4 | m | ~10 of 15 scenarios run on the `faux` provider that `provider.mjs:6-7` marks "for Node unit tests only". Real provider HTTP (both wire formats) is exercised in only 4 tests, happy-path only: no auth-header assertion, no 4xx/5xx/timeout/retry/malformed-SSE coverage. |
| C-5 | m | Evidence drift: packet says "21 passed"; the suite now collects 32 (all green — re-verified in this review: 32/32 in 137 s, candidate 13/13, node 4/4). Acceptance evidence no longer matches the tree. |
| C-6 | m | The bounded live DeepSeek proof is one single-turn, no-tool, no-retry completion — the packet labels this honestly, but note the "owner approval" is CF evidence row 463 recorded by actor `codex-conductor` (an agent attestation, not an independently verifiable owner action). Live-inside-Agent behavior under tools, streaming length, retries, and multi-turn remains unproven. |
| C-7 | m | CF hygiene: CF-SPEC-3, CF-SPEC-5, CF-SPEC-6 remain `tasked` with 45 open tasks and no recorded supersession, despite CF-SPEC-7's acceptance conceptually subsuming them. |

## 3. What would have to be true for a full replacement (and isn't)

1. Donated relay/browser compute either dropped from the product or bridged by a new inbound-websocket provider inside pi-ai (does not exist; opposite topology).
2. An embeddings path outside pi (registry stays regardless).
3. A model-management plane (pull/load/discover/health/failover) pi has no concept of.
4. ~15 category-(b) surfaces individually migrated through `PiExecutionService` (research spine alone is 4 distinct loop sites with structured output, `min_context`, thinking-mode semantics the Pi path currently drops).
5. B-1/B-2 fixed plus the unimplemented protocol hardening actually implemented, a concurrency model beyond 8 sessions/process + single Node child + in-memory steering (breaks under multi-worker uvicorn), and non-macOS secret sourcing (Keychain-only today ⇒ Pi is structurally unavailable on Linux/Windows deploys).
6. An evidence layer that exercises real ASGI routes and provider failure modes.

## 4. Recommendation

- **Do not** approve this branch as "the production Pi replacement." Approve it, if desired, as an **opt-in Pi chat-turn engine (experimental)** — that is what the code actually is.
- If the Pi direction continues, the honest target is: **Pi as the turn-loop engine for conversational/agent surfaces; ComputeRegistry as the permanent compute substrate** (donors, embeddings, local models, routing). Frame the next CF spec that way explicitly.
- Gate any wider rollout on, in order: fix B-1/B-2 (+ tests for frame limits, duplicate-session, reader-limit wedge); enforce the Python-side tool allowlist (B-12); add a turn cap + cost budget (B-6); convert at least chat + one seam test to real ASGI; re-run the donor-isolation suite; then migrate the research spine (A-1's biggest item) as the true "can Pi own production agentic work" test.
- Correct the false "real ASGI routes" and stale-count claims in the completion doc and review packet before anyone cites them (C-1, C-5); close or supersede CF-SPEC-3/5/6 (C-7).

## 5. Method note for future agents

Three independent review passes over `Review_pi_test`: (1) full code read of `pi-runtime/` + `backend/app/core/pi_runtime/` + all seam call sites; (2) test-by-test audit of `tests/pi_production/` with local re-runs (all green) under isolated `DATABASE_URL`; (3) whole-repo LLM call-site inventory (grep over `ollama.chat`, `llm_router.chat`, `node.chat`, `embed`, seam callers). Compass Forge queried read-only from the replacement worktree: `spec list/show`, `task list`, `task evidence-list FIX-REREV-pi-runtime-complete-20260720-REVIEW-r4-F1`, `gate after --summary`. Nothing in either worktree was modified except this file and the README pointer in `comparison-Istara-pi/`.
