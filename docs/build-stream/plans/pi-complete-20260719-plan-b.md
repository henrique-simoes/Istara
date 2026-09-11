# Plan B — Complete the opt-in Pi-to-Istara adaptation

## 1. Outcome and boundaries

Complete the existing Pi candidate as a reversible, explicitly selected execution mode that reuses Istara's production application boundaries. The normal Istara path must remain byte-for-byte equivalent at the request contract and behavior level when Pi is not selected. A Pi-selected request must either use the registered `pi-deepseek-candidate` DeepSeek node or fail closed before any model transport call; model-name substitution alone is not sufficient proof of routing.

This plan covers:

- `/api/chat` request handling, Prompt-RAG preparation, native/text tool loops, SSE events, persistence, and transport selection;
- A2A `tasks/send` authorization and accepted execution;
- the local-only `pi_local` channel lifecycle through channel routes/services and inbound processing;
- public research-validity, task/report, memory/RAG, reasoning-memory, steering, and autoresearch boundaries;
- benchmark header propagation, one bounded DeepSeek request, redacted evidence, feature docs, security/regression checks, and the local review handoff.

Non-goals are external messaging providers, webhooks, live backend/frontend servers, broad model loading, global conductor configuration, the main Istara checkout, `LLMs/`, `Model_Finetuning/`, `origin`, and claims that local-only channel coverage proves third-party delivery. No test may create an accepted research artifact by directly constructing accepted coding, reconciliation, review, skill-stat, or report rows.

## 2. Design

### D1 — One typed Pi selection and target-resolution contract

Keep Pi selection explicit through the configured `x-istara-agent-engine` header (and the already documented opt-in environment switch). Resolve that selection once at the chat route boundary into a small immutable execution context containing the configured model and the exact `pi-deepseek-candidate` node identity. Normal requests receive no Pi context and continue through the existing provider/model path.

Target resolution performs the complete preflight before either native or text tool transport:

1. read the Keychain-backed secret through the existing settings resolver without logging or persisting it;
2. register or validate the DeepSeek node;
3. confirm its provider type, configured base URL, exact model capability, health/availability state, and in-memory credential;
4. return the pinned target, or raise a typed unavailable error with a stable, non-secret reason.

Do not merely pass the DeepSeek model name to the generic `ollama.chat_stream` selector. Extend the narrow compute invocation boundary, if needed, so the Pi context pins the server/node id and disallows failover. Both native-tools and text-fallback loops must consume the same resolved context. A failure to register, a missing credential, an unhealthy/mismatched node, a tools rejection, or an empty response may change tool strategy only within the pinned DeepSeek node; it may never fall back to Ollama, LM Studio, the default model, or another node.

For an unavailable Pi target, emit a deterministic route/SSE error contract (or an HTTP error if the route can reject before constructing `StreamingResponse`) and do not persist an assistant success message. Record content-free failure telemetry only after authorization and project scoping. The telemetry route id must identify the selected node without including endpoint fingerprints or credentials.

### D2 — Boundary tests observe transports, not helper success

Use the FastAPI ASGI application and authenticated requests for chat, A2A, research, memory, steering, and autoresearch tests. Patch only true external boundaries—Keychain resolution and the final network transport—and use strict spies that fail on any unexpected provider/node. Avoid patching route authorization, project-scope helpers, Pi decision helpers, or persistence services in the tests intended as acceptance evidence.

Use unique projects and users with real membership roles. For every denial case, assert both the response and absence of downstream effects: zero DeepSeek/Ollama calls, zero Pi telemetry spans, zero A2A messages, zero channel messages, or zero background loop creation as applicable. Clear router/adapter/steering state in fixture teardown so tests prove ownership and do not leak state into later cases.

### D3 — A2A instrumentation occurs only after real authorization and persistence

Keep Pi A2A work after request authentication, replay/rate checks, project membership/role enforcement, input validation, and successful `a2a_svc.send_message`. Accepted Pi `tasks/send` records one Pi span tied to the persisted message. Missing authentication, insufficient role, foreign project, malformed scope, replay, and rate denial record no Pi span and perform no Pi work. Existing generic security audit events may still record denials under their current contract.

### D4 — `pi_local` is a credential-free local adapter with normal ownership rules

Expose `pi_local` only through the existing channel CRUD/start/stop/health/send and inbound service contracts; it must not acquire or accept external-provider credentials. Test these lifecycles:

- create and start in an active owned project, inject locally through the registered adapter, persist the inbound message, generate the local Pi response, and persist/send it through the same adapter;
- paused project refuses start and drops inbound work without a Pi span or messages;
- a user from another project cannot read, start, stop, send through, delete, or inject into the instance;
- stop/delete/project cleanup unregisters the adapter, marks the database instance inactive, and makes later injection impossible;
- non-Pi metadata follows the existing no-deployment behavior and does not manufacture a Pi response.

The test harness calls no Slack, Telegram, WhatsApp, Google Chat, webhook, or external channel transport.

### D5 — Research and self-improvement paths remain governed or visibly unavailable

Remove or quarantine the current readiness helpers that directly synthesize a `Nugget`, accepted `CodingRun`, approved `CodeApplication`, human approval, production `ModelSkillStats`, and success memory. Those records falsely claim independent coding, reconciliation, human review, and production quality.

Drive credential-free coverage through public application boundaries instead:

- create source/document and task inputs through their API routes;
- inspect evidence units, coding runs, reconciliation state, traceability, task atomic path, and report eligibility through `/research-validity`, task, finding, and report routes;
- if authorized independent coders are unavailable without model loading, assert that coding/report promotion remains pending or blocked and state that limitation in the review packet—never seed acceptance;
- exercise project-scoped hybrid RAG through `/memory/{project_id}/search` and the chat Prompt-RAG path, and prove a foreign project cannot retrieve the source;
- exercise manual ReasoningBank create/retrieve through its authorized routes only as process memory, never research evidence or a positive model-quality signal;
- exercise steering queue/status/abort through `/steering` routes, including foreign-project denial and cleanup;
- exercise Pi autoresearch `dry_run` through `/autoresearch/start`, after real project authorization, and prove no runner, background task, proposal promotion, filesystem mutation, or report evidence is created.

Every response and review note must distinguish `candidate`, `blocked/pending`, and `accepted`. Telemetry, ReasoningBank items, RAG hits, tool success, and autoresearch dry-run results are process evidence only and cannot satisfy the Research Spine.

### D6 — One bounded production-path DeepSeek request with evidence-before-retention

Extend the benchmark client so `sendChat` merges the configured Pi header with authorization/network headers on the actual request, including override/absence tests. Add a dedicated bounded runner that invokes the same in-process chat route and pinned transport used by the application; it is not a direct DeepSeek SDK smoke test and it does not start a server.

The live step is gated on all credential-free tests, docs check, security benchmark, secret-scanner self-test, Keychain availability, and a spend preflight. It performs exactly one DeepSeek request—no automatic retry—with fixed deterministic input, temperature, timeout, and a small `max_tokens`. Before dispatch, compute the maximum possible added cost and refuse if the cumulative ledger plus that maximum could reach USD 0.50.

Capture only the approved raw prompt/output and minimal audit metadata (timestamp, model, route id, token counts, estimated cost, status, and hashes) into the local review packet. Run redaction in memory before writing; reject rather than retain evidence if it contains the resolved credential, authorization/network tokens, private endpoint/host fingerprints, common secret patterns, or unrelated environment values. Console/log output contains only hashes/counts/status and never raw content or endpoint details. If Keychain or the target is unavailable, record the live criterion as blocked; do not substitute a mock, another provider, or a second request.

### D7 — Documentation and handoff are evidence artifacts

Update the living architecture docs for chat, A2A, compute/model routing, and messaging with the opt-in contract, fail-closed behavior, local-only limitation, authorization ordering, Research Spine classification, and the exact evidence boundary. Regenerate the site/manifest with the mandated feature-doc command.

Create a local review packet under `docs/build-stream/review-packet/pi-complete-20260719/` containing a manifest, command matrix, credential-free boundary results, one-live-request record or explicit blocked record, redaction/secret-scan result, cumulative spend ledger, changed-surface summary, known limitations, and rollback instructions. Update the initiative lifecycle in the implementation/review stages, not in this consensus-plan stage. The final branch is local `Review_pi_test`; never push or mutate `origin`.

## 3. Implementation task breakdown

### T1 — Baseline, gates, and transport contract

- Capture `git status`, current branch/origin refs, protected-folder existence, Compass Forge status/impact, and `compass-forge gate before` without cleaning the shared worktree.
- Map `ollama.chat_stream` through `compute_registry` selection and add the smallest server-pinning/failover-denial contract needed by D1.
- Add unit tests for exact-node selection and unchanged generic selection when no server id is supplied.

Acceptance: a caller can request an exact node; mismatched/unavailable exact nodes fail without trying another node; existing callers retain their current routing behavior.

### T2 — Fail-closed chat and authentic SSE coverage

- Introduce the typed Pi context/unavailable error and resolve it once for `/api/chat`.
- Thread the context through native tools and text fallback; ensure both pin `pi-deepseek-candidate` and preserve existing tool/SSE envelopes.
- Add ASGI tests for non-Pi baseline, missing Keychain, registered Pi success, native-to-text fallback on the same node, tool event/done persistence, and foreign-project/auth denial.

Acceptance: missing registration causes a deterministic error with zero calls to every transport spy and no assistant success record; registered Pi calls only the pinned DeepSeek node/model; non-Pi results and provider selection are unchanged.

### T3 — A2A accepted and denial matrix

- Keep Pi recording after real `tasks/send` persistence.
- Add authenticated ASGI cases for accepted researcher membership, unauthenticated request, viewer/insufficient role, foreign project, missing/mismatched scope, replay, and malformed payload.

Acceptance: exactly one message and one Pi span for the accepted case; every denied case has zero Pi spans and zero persisted A2A work.

### T4 — Local channel route/service lifecycle

- Complete `pi_local` configuration validation, registration, start/stop, health, send/inject, and cleanup semantics through the existing channel router/service.
- Add API/service tests for normal, paused, cross-project, non-Pi metadata, stop/delete, and project cleanup behavior.

Acceptance: all activity is in memory/local database; ownership and pause gates precede Pi work; teardown leaves no registered adapter or active instance.

### T5 — Governed source/evidence, memory/RAG, steering, and autoresearch

- Delete or make unreachable the synthetic acceptance/readiness fan-out.
- Add boundary scenarios using document/task/research-validity/report, memory/reasoning-bank, steering, and autoresearch routes with real authorization.
- Assert provisional/blocked states when independent coding or human approval is unavailable and prove cross-project isolation.

Acceptance: no test writes accepted coding/reconciliation/human-review/model-quality outcomes directly; report creation remains blocked until the real gates pass; dry-run and process memory cannot be reported as research evidence.

### T6 — Benchmark propagation and safe evidence writer

- Verify `IstaraApiClient.sendChat` carries Pi selection together with standard headers on the real request and does not leak headers through logs.
- Implement the one-request in-process runner, spend preflight, raw evidence schema, in-memory redaction, atomic write-after-validation, and secret scan.
- Unit-test header merging, spend refusal, one-call enforcement, timeout/no-retry behavior, redaction rejection, and console sanitization without live network activity.

Acceptance: deterministic tests prove the runner cannot make more than one call or write unsafe evidence; the application route—not a provider helper—is the live entry point.

### T7 — Docs, credential-free gate, then the single live request

- Update the four required feature docs and regenerate generated pages/manifest.
- Run the complete credential-free verification ladder in section 5 and attach Compass Forge evidence.
- Only if every prerequisite passes, run the dedicated bounded DeepSeek command once. Validate/redact its retained evidence and update cumulative spend.

Acceptance: all credential-free checks are green before the live command; either one validated request exists under the cap or the packet truthfully records a blocker with zero substitute calls.

### T8 — Review packet, post-change gate, and local handoff

- Run focused regressions, the security benchmark, feature-doc check, secret scan, `compass-forge gate after`, and spec coverage/evidence checks.
- Record inherited gate debt separately from new drift; do not claim a pre-existing repository gate failure as introduced or silently waive new failures.
- Commit only scoped code, tests, generated docs, lifecycle updates, and the review packet on `Review_pi_test`. Confirm no changes to protected paths, global defaults, main checkout, remote refs, or origin.

Acceptance: the packet contains exact commands/outcomes and limitations, every actionable reviewer finding is fixed and re-reviewed, no new gate drift remains, and the branch is ready for local review without push.

## 4. Acceptance matrix

1. Pi is opt-in; an equivalent request without Pi selection follows the existing model/provider behavior.
2. Missing Keychain registration or invalid pinned-node state fails before model transport with zero default/Ollama/LM Studio fallback.
3. Registered Pi chat uses only `pi-deepseek-candidate` and preserves authenticated project scope, Prompt-RAG, SSE chunk/tool/error/done contracts, and message persistence.
4. Native tool fallback, if exercised, remains on the pinned node; it cannot become provider fallback.
5. A2A accepted work records one persisted message and one Pi span only after authorization; all denial cases produce neither.
6. Local channel normal, paused, cross-project, non-Pi, and cleanup cases pass without external credentials or traffic.
7. Research artifacts remain provisional/blocked unless the real evidence-unit, independent coding, reliability, reconciliation, human-review, Done, and report gates accept them.
8. Memory/RAG/ReasoningBank/steering are project-scoped; their outputs are not promoted to research evidence or model-quality success merely because a tool call worked.
9. Pi autoresearch dry-run starts no background work and mutates no experiment, proposal, protected methodology, report evidence, or filesystem state.
10. The benchmark client propagates Pi selection on the actual chat request while retaining auth headers and suppressing secret logging.
11. At most one bounded live DeepSeek request is attempted, with no retry; retained prompt/output is approved and redaction-scanned; cumulative estimated spend stays below USD 0.50.
12. Required feature docs/site are current, the security benchmark and focused regressions pass, and any inherited Compass Forge gate debt is explicitly separated from new drift.
13. The local review packet and lifecycle state are accurate; `Review_pi_test` is not pushed and `origin`, global defaults, the main checkout, `LLMs/`, and `Model_Finetuning/` are untouched.

## 5. Verification ladder

The implementer should refine test selectors to the files created, but must retain this order and record every exact command as Compass Forge evidence.

### Credential-free checks

```bash
pytest -q tests/test_pi_replacement_candidate.py tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_channels.py tests/test_channel_inbound.py tests/test_channel_resilience.py
pytest -q tests/test_project_scope_contracts.py tests/test_research_validity_contract.py tests/test_research_integrity_validation.py tests/test_reasoning_bank.py tests/test_steering.py tests/test_autoresearch_api.py
node --test tests/real_user_benchmark/lib/api-client.test.mjs
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
```

Add the focused compute-registry/router suite selected by `compass-forge intelligence test-impact` for the exact pinning change. Run Python lint/type checks and Node checks required by the repository for touched files. Do not invoke a live-provider integration test as part of these commands.

### Adversarial proof points

- transport spies are wired to every registered provider and fail the test if missing-Keychain Pi reaches any of them;
- authorization denials assert database and telemetry counts before/after;
- channel tests assert router membership and database active state before/after cleanup;
- research tests query public summaries/traceability/report endpoints and assert no accepted artifacts were seeded;
- memory/RAG and steering tests use two projects and prove no cross-project read/queue mutation;
- autoresearch tests spy on runner construction, task scheduling, proposal persistence, and filesystem writes;
- evidence-writer tests inject known sentinel secrets and require rejection/no file.

### Live check, once only

Run the dedicated in-process bounded command produced by T6 only after the credential-free evidence manifest is green. The command must enforce one request, no retry, fixed timeout/temperature/max tokens, spend headroom, and write-after-redaction. Immediately run the packet validator/secret scan. Do not print the prompt, output, credential, token, base URL, or endpoint fingerprint.

### Final process checks

```bash
compass-forge gate after --task <implementation-task> --summary
compass-forge spec coverage CF-SPEC-6
git status --short
git diff --check
git diff --name-only <baseline>...HEAD
git remote -v
```

Compare remote refs captured before/after without fetching or pushing. The reviewer must inspect the actual route/service tests, the single-call audit record, redaction result, spend total, living-doc output, security scorecard, and protected-path diff—not only green summaries.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Generic model routing silently chooses a non-DeepSeek node | Pin exact node id at the compute invocation boundary and adversarially register competing nodes in tests. |
| Missing credential returns an SSE/HTTP error after partial success state | Resolve target before transport and assistant persistence; test zero transport and zero success record. |
| Text-tool fallback becomes provider fallback | Carry the immutable Pi context into both loops and disallow target reselection. |
| Permissive mocks hide authorization regressions | Use authenticated ASGI requests and real membership records; patch only Keychain/network edges. |
| Synthetic fixtures are mistaken for Research Spine acceptance | Remove direct accepted-row helpers; assert provisional/blocked public-route results and label unavailable stages. |
| Telemetry or memory creates a positive learning signal | Keep telemetry content-free and process-only; do not update production skill/model stats from boundary success. |
| Local adapter leaks across tests/projects | Project-scope every service lookup and assert router/database cleanup in teardown. |
| Live evidence leaks credentials or private endpoint details | Redact in memory, validate before atomic write, reject unsafe records, log only hashes/counts. |
| Cost exceeds cap or a retry creates a second request | Preflight worst-case spend, one-call guard, no automatic retry, and cumulative ledger validation. |
| Existing dirty work or generated docs are overwritten | Preserve the shared worktree, use scoped patches/commits, and inspect path lists before each commit. |
| Existing Compass Forge gate failures obscure new drift | Record the baseline, compare after-gate output, and reject any new unsuppressed failure. |

## 7. Rollback

- Keep commits split by contract: compute pinning/chat, boundary tests and governed-path cleanup, benchmark/evidence writer, then docs/review packet. Revert the smallest local commit that introduced a regression; never reset the shared worktree or discard unrelated changes.
- The runtime rollback is to remove/disable Pi selection and unregister the transient `pi-deepseek-candidate` node; normal Istara routing must remain intact because non-Pi callers never receive a Pi execution context.
- Stop/delete all `pi_local` instances and unregister their adapters; no external state requires cleanup.
- If the live request fails or evidence validation rejects its output, retain only the sanitized failure metadata, record the live criterion as blocked, and do not retry.
- Review-packet evidence is local and additive. Remove unsafe temporary output immediately before it is staged; safe packet removal does not alter application state.
- Confirm rollback with the non-Pi chat regression, zero-provider missing-Keychain test, A2A/channel isolation tests, security benchmark, feature-doc check, and Compass Forge after-gate.

## 8. Handoff criteria

Implementation may start only after owner approval of the selected consensus plan. It is complete only when the acceptance matrix is evidenced at real application boundaries, every review finding is closed by a delta re-review, the one-request rule and spend cap are independently auditable, and the local `Review_pi_test` packet states exactly what is proven and what remains unavailable. Local-only and credential-free evidence must never be presented as universal production readiness.
