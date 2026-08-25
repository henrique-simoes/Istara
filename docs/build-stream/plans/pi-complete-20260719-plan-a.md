# Plan A — Complete opt-in Pi-to-Istara adaptation (consensus slot A)

```yaml
plan: pi-complete-20260719-plan-a
task: pi-complete-20260719-PLAN-A
spec: CF-SPEC-6
author: fable.5-medium (pi-complete-20260719-architect-a)
date: 2026-07-19
branch: Review_pi_test (local only; never push origin)
```

## 1. Design

### 1.1 Problem framing

The worktree already contains an opt-in Pi candidate (`backend/app/core/pi_replacement.py`,
`backend/app/channels/pi_local.py`, hooks in chat/A2A/autoresearch/channel routes). Five
defects block a credible handoff:

- **D1 fail-open routing** — `chat.py:158-162`: when Pi is selected but
  `ensure_pi_deepseek_registered()` returns `(False, "missing_keychain_secret")`, the code
  logs a warning and proceeds into `ollama.chat_stream(...)` with the DeepSeek model name —
  i.e. silent fallback to the default provider/transport.
- **D2 helper-level tests** — `tests/test_pi_replacement_candidate.py` calls helpers with
  permissive mocks; no adversarial route-boundary coverage (notably A2A denial with proof of
  zero Pi spans/work).
- **D3 channel adapter one-sided** — `PiLocalAdapter` only has positive injection coverage;
  no paused, cross-project-denial, cleanup/ownership tests.
- **D4 manufactured governance acceptance** — `write_pi_source_evidence_chain` /
  `exercise_pi_done_report_gate` / `record_pi_memory_governance_fanout` construct ORM rows
  with pre-accepted outcomes (`kappa=1.0`, `promotion_status="accepted"`,
  `review_status="approved"`, fixed 0.92/0.93 scores) instead of going through the governed
  public services — this fabricates acceptance and would let the benchmark "prove" readiness
  by fiat.
- **D5 benchmark client / live path** — header propagation (`x-istara-agent-engine`) exists in
  `tests/real_user_benchmark/lib/api-client.mjs` but must be proven on every chat-path request
  (JSON + SSE), and the single bounded DeepSeek run must capture redacted evidence.

### 1.2 Design decisions

**DD-1: Fail closed at the routing seam, before transport.**
Introduce an explicit exception type `PiRoutingUnavailableError` in
`backend/app/core/pi_replacement.py`. In both chat generators (`_generate_native_tools` and
the text-fallback path at `chat.py:338`), when `pi_candidate` is true:

- call `ensure_pi_deepseek_registered()` **before any transport call**;
- on failure: record an error Pi span (`status="error"`,
  `error_message="missing_keychain_secret"`), yield exactly one SSE `error` event with a
  stable machine-readable code (`pi_registration_unavailable`) and a `done` event, then
  `return` — never enter `ollama.chat_stream`. For the non-streaming path raise
  `HTTPException(503, detail={"code": "pi_registration_unavailable"})`.
- Pi-selected requests always use the pinned model from `pi_chat_model()` and the
  `pi-deepseek-candidate` node; they must never rewrite `effective_model` back to the caller
  model on failure (that is the fallback we are eliminating).

Non-Pi requests are untouched: the `pi_candidate` flag remains the only switch, preserving
default Istara behavior.

**DD-2: Boundary tests drive the real ASGI app.**
All new tests build the FastAPI app and use `httpx.AsyncClient(transport=ASGITransport(app))`
(or the repo's existing app-level test fixture if one exists — reuse before invent) so the
real route → service → core seams execute. Mocks are permitted **only** at the outermost
transport edge (the HTTP client inside the OpenAI-compat/ollama transport) and at the
Keychain resolver; never at Istara service functions. Every denial test asserts both the
denial response **and** the absence side: zero Pi telemetry spans recorded and zero
work-product rows created (query the telemetry recorder / DB after the call).

**DD-3: Governance honesty — use governed paths or return "unavailable".**
Rework the D4 helpers so acceptance is *earned or absent*:

- `write_pi_source_evidence_chain`: keep document + nugget creation (legitimate public
  models), but derive evidence-unit persistence and coding outcomes only through the
  governed services (`persist_task_nugget_evidence_units`, the real coding/reliability
  service entry points). Where a governed outcome genuinely requires a live rater/model
  (e.g. inter-rater reliability), do **not** hardcode `kappa=1.0`/`accepted`; run the
  governed path with its real inputs and accept whatever status it returns, or return a
  structured `{"available": False, "reason": ...}` result. The readiness probe result must
  distinguish `exercised` vs `unavailable` per surface and must not report
  `production_test_ready: True` unless every exercised surface used a governed path.
- `exercise_pi_done_report_gate`: drive the review through `record_task_review_event` with
  inputs the gate actually evaluates; assert the gate's own outcome rather than presetting
  statuses.
- Autoresearch stays dry-run-only via its existing governed dry-run path
  (`backend/app/api/routes/autoresearch.py`), asserted through the route.

**DD-4: Channel coverage is local-only by construction.**
All channel tests go through `channel_service` / `inbound_processor` with `PiLocalAdapter`
registered in-process. No provider startup, webhook, or credential is ever configured; a
test-level guard asserts the adapter registry contains only `pi_local` during these tests.

**DD-5: One bounded live DeepSeek run, evidence-first.**
A single script/marker (`tests/pi_live/test_deepseek_bounded.py`, `-m pi_live`, skipped unless
`PI_DEEPSEEK_LIVE=1`) performs one chat request through the real route with the Pi header,
Keychain-resolved key, `max_tokens<=256`, one retry max. It writes
`docs/build-stream/review-packet/pi-complete-20260719/deepseek-evidence.json` containing the
raw prompt, raw output, token counts, and cost estimate — after passing a redaction filter
(reject any string matching the Keychain value or `sk-`-style patterns). Cumulative spend
check: prior ledger shows ≈ USD 0.091 spent; this run must keep the running total < 0.50
(expected add ≈ < 0.01). It runs **only after** all credential-free suites are green.

### 1.3 Touched surfaces

| Surface | Files |
|---|---|
| Fail-closed routing | `backend/app/core/pi_replacement.py`, `backend/app/api/routes/chat.py` |
| Governance honesty | `backend/app/core/pi_replacement.py` |
| Channel lifecycle | `backend/app/channels/pi_local.py`, `backend/app/services/channel_service.py`, `backend/app/services/inbound_processor.py` (tests may need small seams only if a behavior is untestable — prefer zero prod changes) |
| Boundary tests | `tests/test_pi_replacement_boundaries.py` (new), rework `tests/test_pi_replacement_candidate.py`, `tests/pi_live/test_deepseek_bounded.py` (new) |
| Benchmark client | `tests/real_user_benchmark/lib/api-client.mjs`, `api-client.test.mjs` |
| Docs | `docs/features/content/{chat/overview,agents/a2a,compute/pool,integrations/messaging}/architecture.md` + generated site |
| Handoff | `docs/build-stream/review-packet/pi-complete-20260719/` (review packet), lifecycle file |

## 2. Task breakdown

Ordered; each task lists its acceptance and verification. T1–T6 are credential-free; T7 is
the only live task; T8 closes out.

### T1 — Fail-closed Pi routing in chat (D1)
Implement DD-1 in `pi_replacement.py` + both chat generation paths.
**Acceptance:** with Pi selected and Keychain resolver returning empty: SSE stream yields one
`error` event with code `pi_registration_unavailable` then `done`; a spy on
`ollama.chat_stream` (and any router transport entry) records **zero** calls; an error Pi
span is recorded. With registration available (mocked key), the stream proceeds and
`effective_model == settings.pi_replacement_deepseek_model`. Non-Pi requests: behavior
byte-identical to before (existing chat tests stay green).
**Verify:** `python -m pytest tests/test_pi_replacement_boundaries.py -k fail_closed -q` plus
the existing chat suite.

### T2 — Adversarial A2A boundary tests (D2)
Through the real `/api/a2a` route: (a) accepted case with Pi header → task accepted and Pi
span recorded with correct route id; (b) cross-project denial, bad/missing scope, and
unknown-agent cases → denial status **and** zero Pi spans, zero tasks/messages persisted.
**Acceptance:** all four cases pass at the route boundary; denial assertions include the
zero-side checks.
**Verify:** `python -m pytest tests/test_pi_replacement_boundaries.py -k a2a -q`

### T3 — Local channel lifecycle tests (D3)
Via `channel_service`/`inbound_processor` with `PiLocalAdapter`: normal inbound→outbound
round trip; paused channel → no processing and no outbound; cross-project injection →
denied with zero spans/rows; stop/cleanup → adapter stopped, ownership released, no
dangling registry entry. Guard asserts only `pi_local` is registered.
**Acceptance:** all four behaviors proven without any external provider/credential.
**Verify:** `python -m pytest tests/test_pi_replacement_boundaries.py -k channel -q`

### T4 — Governance honesty rework (D4)
Implement DD-3. Remove every hardcoded accepted/approved status and fixed score from the
Pi helpers; results carry `exercised`/`unavailable` per surface. Update
`exercise_pi_production_readiness` so `production_test_ready` is computed, not asserted.
Memory/RAG (`reasoning_bank.record_memory`), steering (`steering_manager`), and
autoresearch dry-run are exercised through their governed public paths at the route/service
boundary.
**Acceptance:** `grep -n '"accepted"\|approved\|kappa=1.0' backend/app/core/pi_replacement.py`
shows no preset acceptance; boundary tests show governed outcomes (or explicit
`unavailable`) end-to-end; autoresearch dry-run test proves no production mutation.
**Verify:** `python -m pytest tests/test_pi_replacement_boundaries.py -k "governance or memory or steering or autoresearch" -q`

### T5 — Benchmark client header propagation (D5a)
Extend `api-client.mjs` tests: `x-istara-agent-engine` present on chat JSON **and** SSE
requests (and absent when no engine configured); header value passed through verbatim.
**Acceptance:** node test asserts header on every chat-path fetch.
**Verify:** `node --test tests/real_user_benchmark/lib/api-client.test.mjs`

### T6 — Feature docs
Update the four architecture docs (chat, A2A, compute/pool routing, messaging) to describe
the opt-in Pi path, fail-closed behavior, and local-only channel adapter; regenerate site.
**Acceptance/Verify:** `python scripts/feature_docs.py --seed-missing --generate-site --check`
exits 0; diffs reviewed for accuracy (no production-ready claims).

### T7 — Bounded DeepSeek production-path run (D5b)
Implement DD-5. Precondition: T1–T6 green. Exactly one bounded run; evidence file written
and redaction-checked; spend accounting appended to the review packet.
**Acceptance:** evidence file exists with raw prompt/output, no secret material (automated
scan + manual check); response provably came via the `pi-deepseek-candidate` node
(model/route id in span); cumulative spend < USD 0.50.
**Verify:** `PI_DEEPSEEK_LIVE=1 python -m pytest tests/pi_live -m pi_live -q` once, then
secret scan over the evidence file.

### T8 — Security benchmark, regressions, review packet
Run `python scripts/security_benchmark.py --fail-on-threshold`; run focused regression
suites (existing chat/A2A/channel/research-validity tests touched by the diff, discovered
via `compass-forge intelligence test-impact` plus targeted pytest selection); assemble
`docs/build-stream/review-packet/pi-complete-20260719/` (summary, exact commands + outcomes,
evidence file, spend ledger, known limitations — explicitly: local-only channels and
credential-free suites do **not** demonstrate production readiness); commit on
`Review_pi_test` only; no push.
**Verify:** commands above recorded with exit codes; `git log`/`git status` show only scoped
commits on the branch.

## 3. Acceptance criteria (spec-level)

1. Pi-selected chat with missing Keychain registration fails closed **before transport**
   with a structured error; a spy proves zero transport/fallback calls (D1, SC-001).
2. Pi-selected chat with registration uses the DeepSeek model and node; default (non-Pi)
   requests are behaviorally unchanged (existing suites green).
3. A2A accepted + ≥3 denial cases pass at the route boundary with zero-side assertions.
4. Channel normal/paused/cross-project-denial/cleanup pass, provably local-only.
5. No manufactured governance acceptance remains; readiness result distinguishes
   exercised vs unavailable; autoresearch is dry-run-safe at the route.
6. Benchmark client header propagation proven for JSON + SSE chat.
7. Exactly one bounded DeepSeek run with redacted raw prompt/output evidence; cumulative
   spend < USD 0.50.
8. `feature_docs.py --check` and `security_benchmark.py --fail-on-threshold` pass; review
   packet complete; no push/origin/defaults mutation; no unrelated files committed.

## 4. Verification plan (full-run order)

```bash
# credential-free gate (T1–T5)
python -m pytest tests/test_pi_replacement_boundaries.py tests/test_pi_replacement_candidate.py -q
python -m pytest <impacted chat/A2A/channel/research suites> -q     # from test-impact
node --test tests/real_user_benchmark/lib/api-client.test.mjs
# docs (T6)
python scripts/feature_docs.py --seed-missing --generate-site --check
# live bounded (T7, once, after all above green)
PI_DEEPSEEK_LIVE=1 python -m pytest tests/pi_live -m pi_live -q
# security + gate (T8)
python scripts/security_benchmark.py --fail-on-threshold
( cd <root> && compass-forge gate after --task <task> --summary )
```

Each command's exact invocation and result is recorded as CF `command` evidence and in the
review packet.

## 5. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Governed research-validity paths can't produce accepted outcomes without a live rater | Medium | DD-3 allows honest `unavailable`; acceptance criterion 5 forbids faking it — reviewer standard explicitly rejects fabricated acceptance |
| SSE error contract change breaks frontend expectations | Low | Error emitted as standard SSE `error` event shape already used by chat error paths; existing chat tests must stay green |
| Live DeepSeek run flakes or leaks secrets | Low | Single bounded run, retry≤1, redaction filter + automated secret scan before the file is kept; abort keeps credential-free evidence valid |
| Hidden Pi fallback path beyond chat (e.g. text-fallback branch at `chat.py:338`) | Medium | T1 covers both generators; grep audit for `pi_chat_model(`/`pi_candidate` call sites; spy asserts on the shared transport seam |
| Channel tests accidentally require live infra | Low | DD-4 registry guard; CI-safe with no env credentials present |
| Spend cap breach | Very low | max_tokens cap + one run; prior spend ≈0.091, headroom ≈0.41 |
| Security benchmark regression from new error path | Low | Run benchmark in T8 before handoff; treat any regression as blocking |

## 6. Rollback

- The entire feature is opt-in behind `pi_replacement_requested()` (settings flag, header,
  metadata). Operational rollback = do not select Pi; default paths are untouched by design
  and proven by the existing suites.
- Code rollback: work is confined to local commits on `Review_pi_test`; revert with
  `git revert <range>` or reset the branch — `origin` and the main worktree are never
  mutated, so no remote rollback exists or is needed.
- The live-run evidence file and review packet are additive artifacts; deleting the packet
  directory fully unwinds T7/T8 outputs.
- If T4's governance rework proves a governed path cannot run credential-free, the rollback
  within scope is to report that surface `unavailable` (honest degradation), not to restore
  the fabricated-acceptance code.

## 7. Out of scope

Production deployment, merge/push, external channel providers or credentials, local model
loading, changes to `<repo-root>`, `LLMs/`, `Model_Finetuning/`, or
conductor defaults. Out-of-scope defects found during implementation become new CF tasks.
