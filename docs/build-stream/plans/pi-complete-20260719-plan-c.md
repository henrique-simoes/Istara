# Plan C — Complete the opt-in Pi-to-Istara adaptation (consensus slot C)

Spec: CF-SPEC-6 · Task: pi-complete-20260719-REPLAN-C-r3 · Slot: C · Branch: `Review_pi_test`
Scope: `<repo-root>-pi-replacement` only. No push, no `origin`, no
mutation of `<repo-root>`, `defaults.json`, `LLMs/`, or `Model_Finetuning/`.

This is an independent architect plan. It is buildable as written and is scoped to remedy the
five known defects while proving behavior at authentic in-process route/service boundaries, not
at fixture/helper success. It respects the Research Spine and Self-Improvement Governance
contracts in `AGENTS.md`: no manufactured "accepted" governance, no silent transport fallback,
no fabricated authorization.

---

## 1. Design

### 1.1 Problem framing

The reversible Pi candidate already threads an opt-in engine selection (`x-istara-agent-engine`
header / `pi_replacement_enabled` / metadata) through chat, A2A, the local channel, autoresearch,
and a production-readiness probe (`backend/app/core/pi_replacement.py`). Five behaviors are wrong
or unproven:

- **D1 — Chat does not fail closed.** In `_generate_native_tools` (chat.py) a missing DeepSeek
  registration only logs a warning and continues; `_generate_text_fallback` performs **no**
  registration check at all. Both then call `ollama.chat_stream(model=pi_chat_model(...))`, which
  the `llm_router` serves through the **default** provider because the `pi-deepseek-candidate`
  node was never registered. Result: Pi-selected traffic silently reaches Ollama/default. It must
  fail closed **before** transport when Keychain registration is unavailable.
- **D2 — A2A tests are permissive.** `test_pi_a2a_route_persists_candidate_telemetry` monkeypatches
  both `_authorize_a2a_request` and `_authorize_project_scope` to succeed, so denial paths and the
  "zero Pi work on denial" invariant are unproven.
- **D3 — Channel coverage is positive-only.** `test_pi_local_channel_adapter_routes_through_inbound_processor`
  only proves the happy inject. Paused/stopped, cross-project denial, and cleanup/ownership are
  untested.
- **D4 — Governance acceptance is fabricated.** `write_pi_source_evidence_chain`,
  `exercise_pi_done_report_gate`, and `record_pi_memory_governance_fanout` hard-code
  `promotion_status="accepted"`, `reliability_status/reconciliation_status="accepted"`,
  `review_status="approved"`, `kappa=1.0`, `alpha=1.0`. This manufactures spine acceptance
  instead of letting the governed reliability/reconciliation/report gates compute it — a direct
  violation of the Research Spine contract ("no feature may treat … as reportable until … gates
  have accepted them").
- **D5 — Benchmark propagation and bounded live evidence.** The benchmark client now forwards the
  engine header, but end-to-end propagation and the single bounded DeepSeek production-path run
  (secret-redacted, spend < USD 0.50, fail-closed) are not yet proven.

### 1.2 Design decisions

**DD1 — One authoritative transport resolver; fail closed before `chat_stream`.**
Add `resolve_pi_chat_transport()` to `pi_replacement.py` returning a small typed result
(`registered: bool`, `status: str`, `model: str`, `node_id: str`). It calls
`ensure_pi_deepseek_registered()` and, on `(False, reason)`, does **not** return a usable model.
In `chat.py`, both `_generate_native_tools` and `_generate_text_fallback` call this resolver first
when `pi_candidate` is true. On unavailability they **yield a terminal SSE error event**
(`{"type": "error", "error": "pi_transport_unavailable", "detail": <reason>}` followed by the
existing `done` framing) and `return` **without ever calling `ollama.chat_stream`**. The `chat()`
orchestration must treat a Pi-unavailable native path as terminal — it must **not** fall through
to `_generate_text_fallback` with the default model (today the `except native_err` branch would do
exactly that). Prove-out: with `ensure_pi_deepseek_registered` stubbed to
`(False, "missing_keychain_secret")`, a fake `ollama.chat_stream` records **zero** calls and the
SSE stream contains the typed error, not a model answer.

Non-Pi traffic is untouched: the resolver is only consulted when `pi_replacement_requested(...)`
is true, so default Istara behavior is byte-for-byte preserved.

**DD2 — A2A instrumentation is strictly post-authorization; denial does zero Pi work.**
No code change is required to ordering (`record_pi_a2a_event` at a2a.py:471 already runs only
after `_authorize_a2a_request` at :309 and `_authorize_project_scope` at :439 pass, and after the
message is persisted). The gap is test honesty. Add adversarial boundary tests that drive **real**
denial without stubbing the authorizers to success, and assert the `pi_candidate_a2a_tasks_send`
telemetry span is **absent** and no A2A message row was created. If the audit shows any Pi span
emitted on a denial path, that becomes a code fix (move/guard the call) — but current reading says
ordering is correct, so the deliverable is the negative proof.

**DD3 — `pi_local` is a first-class local adapter with real ownership/lifecycle.**
Exercise the real `channel_service` + `channel_router` + `inbound_processor` contract for: normal
inject (kept), paused/stopped instance (inject rejected — no dispatch, no `ChannelMessage`),
cross-project inbound (denied — message scoped to a different project must not be accepted/answered),
and cleanup (`stop_project_channel_instances` removes the adapter from the router, is idempotent on
a second call, and leaves another project's instance untouched). Local-only: never start an
external provider, send a webhook, or read external-channel credentials.

**DD4 — Governance flows through governed public paths or is honestly unavailable.**
Replace hard-coded acceptance with the spine's own computation:
- Evidence units are created via `persist_task_nugget_evidence_units(..., candidate_only=True)`
  and remain provisional until the real reliability/reconciliation path rules on them. Do not set
  `reliability_status`/`reconciliation_status`/`promotion_status` to `"accepted"` by hand, and do
  not set `kappa=1.0`/`alpha=1.0` as literals.
- Report routing continues through the **real** `report_manager.route_approved_task_findings`,
  whose `_filter_reportable_finding_ids` decides reportability. The probe records **whatever count
  the gate returns**; it never asserts a forced `>= 1`.
- Task done/review flows through the real `record_task_review_event` gate; the probe does not
  short-circuit it.
- Where credential-free single-rater conditions cannot satisfy multi-model reliability, the probe
  returns an explicit `governance_available: false` / `reason` and the artifacts stay provisional.
  The result object gains `governance_source: "computed"` (never `"asserted"`).
This keeps `exercise_pi_production_readiness` a *contract exerciser*, not an acceptance forger, and
aligns `test_pi_production_readiness_*` to assert the governed outcome rather than a manufactured
one.

**DD5 — Benchmark propagation proven end-to-end; exactly one bounded DeepSeek live run.**
Confirm the persona/runner passes `agentEngine: "pi"` so `sendChat` emits `x-istara-agent-engine`
on the real outgoing request (the api-client boundary test inspects the actual request headers).
The bounded live run is a single, explicitly-gated task executed **only after** every
credential-free check is green: it resolves the DeepSeek key from Keychain, performs one bounded
request against the registered node, redacts all secrets/URLs/tokens from captured evidence,
retains only the approved raw prompt/output, keeps cumulative spend < USD 0.50, and — proving D1 in
production — fails closed if Keychain registration is unavailable.

### 1.3 Touched surfaces

| Surface | File | Change |
|---|---|---|
| Fail-closed resolver | `backend/app/core/pi_replacement.py` | Add `resolve_pi_chat_transport()`; make governance probes route through governed paths (DD4) |
| Chat routing | `backend/app/api/routes/chat.py` | Consult resolver first in both generators; terminal SSE error; no fallthrough to default model |
| Tests (boundary) | `tests/test_pi_replacement_candidate.py` | Add fail-closed, A2A-denial, channel-lifecycle, governance-honest tests |
| Benchmark client | `tests/real_user_benchmark/lib/api-client*.mjs`, `lib/persona.mjs` (if needed) | Prove engine header propagation |
| Feature docs | `docs/features/content/{chat/overview,agents/a2a,compute/pool,integrations/messaging}/architecture.md` + regenerated site | Document opt-in Pi behavior + fail-closed |
| Review packet | `docs/build-stream/2026-07-19-pi-agentic-core-replacement.md` (or handoff note) | Commands, outcomes, redacted live evidence |

A2A/autoresearch/channel_service/inbound_processor code is **not** expected to change beyond what
D1–D4 require; if a denial/ownership audit surfaces a real gap, fix it in scope with a test.

---

## 2. Task breakdown

Dependencies: T1 → (T2, T3, T4, T5) → T6 → T7 → T8. T7 (live) runs once, only after T1–T6 green.

### T0 — Baseline & runner pinning
- Establish exact invocations: backend pytest rootdir/`PYTHONPATH` (`cd backend && python -m pytest
  ../tests/test_pi_replacement_candidate.py -q` or the repo's configured runner) and
  `node --test tests/real_user_benchmark/lib/api-client.test.mjs`. Record baseline results before
  changes. No functional edits.

### T1 — Fail-closed Pi chat routing (D1) — **blocking**
- Add `resolve_pi_chat_transport()` to `pi_replacement.py`.
- In `_generate_native_tools` and `_generate_text_fallback`, when `pi_candidate`: resolve first;
  on unavailable, yield terminal `{"type":"error","error":"pi_transport_unavailable",...}` + done
  and `return` before any `ollama.chat_stream`.
- In `chat()`, ensure a Pi-unavailable native failure does **not** fall through to the text
  fallback default-model path.
- Tests: (a) native path, registration `(False, …)` → fake `chat_stream` `calls == []`, stream
  carries the typed error; (b) same for text-fallback path; (c) registration `(True,"registered")`
  → model is `settings.pi_replacement_deepseek_model` and the SSE tool contract is preserved.

### T2 — Adversarial A2A boundary tests (D2)
- Add: (a) `_authorize_a2a_request` yields 401 JSONResponse → response is the denial and **no**
  `pi_candidate_a2a_tasks_send` span exists; (b) authenticated but `_authorize_project_scope`
  denies (cross-project / below `researcher`) → `-32043` scope error, **no** Pi span, **no** A2A
  message row. Do not stub authorizers to success on the denial cases. Keep one accepted-case test
  for the positive telemetry assertion.

### T3 — Local channel lifecycle tests (D3)
- Add: paused/stopped instance rejects inject (no dispatch, no `ChannelMessage`); cross-project
  inbound denied (no accepted response); `stop_project_channel_instances` removes the adapter from
  `channel_router`, is idempotent, and leaves another project's instance intact. Local-only.

### T4 — Governance-honesty rework (D4)
- Route evidence units through `persist_task_nugget_evidence_units(candidate_only=True)`; remove
  literal `accepted`/`approved`/`kappa=1.0`/`alpha=1.0`; let reliability/reconciliation/report/review
  gates compute status. Add `governance_source: "computed"` and `governance_available`/`reason`.
- Retarget `test_pi_production_readiness_*` to assert the **governed** outcome (no forced
  `report_finding_count >= 1`; assert either genuine gate acceptance under valid multi-rater inputs
  or explicit unavailability).

### T5 — Benchmark client header propagation (D5a)
- Confirm/adjust persona/runner to pass `agentEngine: "pi"`; keep the api-client boundary test that
  asserts `x-istara-agent-engine: pi` on the real outgoing chat request. No live network.

### T6 — Feature docs
- Update chat, A2A, compute/pool, messaging architecture docs to describe opt-in Pi selection,
  fail-closed routing, post-auth A2A instrumentation, local channel, and governed evidence.
- Regenerate/check: `python scripts/feature_docs.py --seed-missing --generate-site --check`; attach
  output as evidence.

### T7 — Bounded DeepSeek production-path run (D5b) — **once, gated, after T1–T6 green**
- One bounded live request via the registered node; redact secrets/URLs/tokens; retain only approved
  raw prompt/output; cumulative spend < USD 0.50; fail closed if Keychain missing. Capture redacted
  evidence to the review packet.

### T8 — Security benchmark, focused regressions, review packet
- `python scripts/security_benchmark.py --fail-on-threshold`; update `security/control_matrix.json`,
  `security/SECURITY_BENCHMARK.md`, `tests/test_security_benchmark.py` if a control/trigger changed.
- Re-run the focused pytest + node suites; run `compass-forge gate before/after`.
- Assemble the local review packet (commands, outcomes, redacted live evidence) and leave the
  handoff note. No push, no `origin`.

---

## 3. Acceptance criteria (spec-level)

| # | Criterion | Bound to |
|---|---|---|
| A1 | Pi-selected chat with missing Keychain registration emits a typed fail-closed error and makes **zero** `ollama.chat_stream` calls; no fallthrough to default model | D1 / T1 |
| A2 | Pi-selected chat with valid registration uses `settings.pi_replacement_deepseek_model` and preserves the SSE + tool-call contract | D1 / T1 |
| A3 | A2A denial (auth **and** scope) returns the correct error and records **no** Pi span and **no** message row | D2 / T2 |
| A4 | Local channel: normal keeps, paused/stopped rejects, cross-project denies, cleanup removes+idempotent+isolates — all without contacting a real channel | D3 / T3 |
| A5 | Governance probes carry no hard-coded acceptance; status is computed by real gates or honestly unavailable (`governance_source: "computed"`) | D4 / T4 |
| A6 | Benchmark `sendChat` emits `x-istara-agent-engine: pi` on the real outgoing request | D5a / T5 |
| A7 | Exactly one bounded DeepSeek live run; secrets redacted; spend < USD 0.50; fails closed on missing Keychain | D5b / T7 |
| A8 | Feature docs updated and `feature_docs.py … --check` passes; security benchmark passes; focused suites green; evidence attached | T6 / T8 |
| A9 | No push/`origin` mutation; no edits to protected paths; no unrelated files committed | Safety |

---

## 4. Verification plan (full-run order)

```bash
# Credential-free gate (T1–T5) — no live network, no model loading
cd backend && python -m pytest ../tests/test_pi_replacement_candidate.py -q
node --test tests/real_user_benchmark/lib/api-client.test.mjs
# Adversarial proof points (must observe transport, not helper success):
#  - fail-closed: fake chat_stream call-count == 0 on missing registration
#  - A2A denial: pi_candidate_a2a_tasks_send span absent; no message row
#  - channel: no ChannelMessage on paused/cross-project inject
#  - governance: asserted-acceptance literals absent; status computed

# Docs (T6)
python scripts/feature_docs.py --seed-missing --generate-site --check

# Live bounded (T7) — once, only after everything above is green
#   resolve DeepSeek key from Keychain, one bounded request, redact, spend < USD 0.50

# Security + gate (T8)
python scripts/security_benchmark.py --fail-on-threshold
compass-forge gate before && compass-forge gate after
```

Each command is recorded as `compass-forge task evidence --type command`. The live run's captured
prompt/output is stored **redacted** in the review packet.

---

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Fail-closed change leaks into non-Pi chat | Resolver consulted only when `pi_replacement_requested` is true; add a regression asserting default chat is unchanged |
| Native Pi failure silently falls through to text fallback (default model) | Make Pi-unavailable terminal in `chat()`; test both generators independently for zero `chat_stream` |
| A2A "denial" test accidentally re-mocks auth to success | Denial tests must not stub authorizers to success; assert span/message **absence** as the invariant |
| Removing forced acceptance breaks `report_finding_count >= 1` assumption | Retarget tests to the governed outcome; document credential-free reliability limits honestly |
| Live run exceeds spend or leaks a secret | Single bounded request, hard spend ceiling < USD 0.50, redaction before persistence, fail-closed on missing key |
| Docs check drift | Run `feature_docs.py … --check` in the same task that edits docs; attach output |
| Out-of-scope defect discovered | File a new CF task (`task import` with the right role); do not expand this stage |

---

## 6. Rollback

- All changes are additive and opt-in; reverting is `git checkout -- <file>` on the touched files
  or `git revert` of the branch commits. Pi remains off by default
  (`pi_replacement_enabled=False`), so rollback restores exact prior Istara behavior.
- The registered `pi-deepseek-candidate` node is created only at runtime on explicit Pi selection
  and holds the key in memory only; nothing is persisted to disk or committed. No migration or
  schema change is introduced, so there is no data rollback.
- The bounded live run mutates nothing beyond telemetry/evidence rows in the local test DB; drop the
  local DB / discard the branch to fully unwind.
- No `origin` push occurs, so rollback is entirely local.

---

## 7. Out of scope

- Any change to `<repo-root>`, `defaults.json`, `LLMs/`, `Model_Finetuning/`,
  or `origin`.
- Starting live backend/frontend servers, external channel providers, webhooks, or loading multiple
  heavy models.
- Broad refactors of chat/A2A/channel/autoresearch beyond the D1–D4 remedies.
- Production-readiness claims derived from mocks or local-only channels — explicitly disallowed.
