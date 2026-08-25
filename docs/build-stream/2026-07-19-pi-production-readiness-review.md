# Pi Production-Test Readiness Review

```yaml
item: pi-production-readiness-review
branch: comparison/pi-replacement-core
cf: { spec: CF-SPEC-5, tasks: [] }
phase: "Phase 1 — literal BSC review and production-test readiness"
stage: S3-review
status: in-progress
blocked_on: null
last: { agent: gpt-5.6-terra, at: "2026-07-19T20:55:43Z", ledger: L-8 }
next_action: "Conductor: tally consensus plan votes and select the winning plan for execution."
```

## Plan overview

Review the existing opt-in Pi replacement candidate in the isolated replacement worktree,
prove the real route/service boundaries that can be exercised without production
credentials, remediate any findings through a role-separated Build Stream Conductor cast,
and leave an evidence-backed readiness classification.

Non-goals: production deployment, external channel sends, production data mutation, live
model loading without explicit authorization, commits, or claims of deployment readiness.


<!-- consensus-winning-plan -->
## Winning consensus plan

# Plan A — Pi replacement credential-free production-test readiness

## Outcome and boundaries

Review and complete the existing Pi candidate as an **explicit, reversible, credential-free test overlay**. The deliverable is an evidence-backed classification of the code paths that are ready for production-style tests without secrets or a live model; it is not a production-deployment or provider-readiness claim.

Pi selection must remain default-off (`PI_REPLACEMENT_ENABLED=false`) and require the supported request header or metadata. The work must preserve Istara's normal chat, A2A, channel, project/auth/replay, raw-capture, metric, and report behavior when Pi is absent. It must not start a backend/frontend server, load a model, contact Keychain/a provider, send an external message, change credentials, commit, or push.

Record three disjoint outcomes throughout: (1) reproducible implementation defects, (2) insufficient boundary proof, and (3) credential/runtime blockers (Keychain secret, authorized provider/network, or a user-authorized single-target live probe). Only the first two are implementation work in this stream.

## Design and load-bearing decisions

The Pi code should remain a narrow overlay across existing public boundaries:

- `pi_replacement_requested()` is the sole selection predicate; flag/header/metadata parsing must not broaden default selection.
- `/api/chat` retains its established SSE/tool-loop and persistence envelopes. A selected Pi run may use a transport stub in tests, but a missing Keychain credential must be classified before any outbound transport attempt and must never cause a silent fallback to the ordinary model.
- A2A `tasks/send` retains authentication, body/rate/replay, participant, and project checks before Pi telemetry or work. Spans must be project-scoped and content-free: no secret, base URL, prompt, response, or raw source span in telemetry IDs.
- `pi_local` is local/test-only but uses the ordinary channel registry, lifecycle, router, inbound persistence, paused-project protections, and cleanup. It cannot affect external adapters.
- Research readiness must enter the governed spine: Sources → Evidence Units → independent coding/reliability/reconciliation → accepted atoms/facts → human-approved Done → report routing. A convenience helper must not directly mint `accepted` nuggets/edges or reportable evidence merely to satisfy a test.
- ReasoningBank, Memento, and model-skill stats are project-scoped process/governance records, not raw tool-success promotions or report evidence. Pi Autoresearch remains dry-run only; steering interruption remains scoped to the selected agent/project.

## Phased task graph

### Phase 1 — Baseline, seam map, and evidence classification

1. Inspect the candidate diff and the real owners: `chat.py`, `a2a.py`, `autoresearch.py`, `pi_replacement.py`, `pi_local.py`, channel service/inbound processor, configuration/keychain resolver, telemetry recorder, research-validity/report/Done services, ReasoningBank/Memento/skill-stat services, and benchmark API client.
2. Classify current tests as route-boundary, service-boundary, or helper/mock-only. Preserve the focused passing baseline as evidence, but do not treat it as conclusive where it directly constructs final research artifacts.
3. Build a readiness matrix listing each in-scope contract, its focused proof, and either an implementation finding or named runtime blocker. Open separate remediation tasks for each Blocker/Major finding; do not fold unrelated debt into Pi work.

Definition of ready: exact route/service owners and negative seams are identified, and no test has been mistaken for a live-provider check.

### Phase 2 — Route and lifecycle boundary remediation

1. Add/repair in-process credential-free chat tests at the actual FastAPI handler/ASGI boundary. Stub only the model transport and assert default-off behavior, selected model resolution, tool/chunk/done SSE ordering, persistence, content-free telemetry, and zero outbound calls when Pi registration/keychain resolution fails.
2. Exercise the A2A JSON-RPC entry boundary with Pi-marked payloads. Assert malformed, unauthenticated, unauthorized, cross-project, oversized/rate-limited, and replayed requests create neither Pi spans nor Pi work; assert an accepted `tasks/send` writes one redacted project-scoped span only after the existing gates.
3. Exercise `pi_local` through create/start/inject/stop and the actual router/inbound processor. Assert project isolation, paused-project rejection, normal persistence/cleanup, Pi-only response metadata, and no Pi response for an ordinary adapter/message.
4. Call the Pi-selected Autoresearch dry-run and steering contracts at their route/service seam. Assert no runner/background task, global policy mutation, production mutation, or quality promotion; assert interruption clears only its scoped queued work.

Definition of done: every claim is proved through a route or service boundary, with adversarial negative tests at the gate ordering seams.

### Phase 3 — Research-spine and governed-learning remediation

1. Replace or constrain `exercise_pi_production_readiness()` / `write_pi_source_evidence_chain()` wherever it directly creates final `Nugget`, coding, accepted edge, task, or report-ready state. Fixture setup may create provisional test data, but acceptance and reportability must be driven by the existing governed service/API contracts.
2. Add a deterministic credential-free fixture proving source-span preservation, evidence-unit creation, independent coding/reliability/reconciliation, approved Done-task gating, traceability, and report routing. Include the inverse assertion: incomplete/single-coder/provisional artifacts never appear as reportable findings.
3. Assert ReasoningBank/Memento/model-skill fanout carries project scope, evidence/governance state, and content-free references. Assert Autoresearch dry-run results remain proposal/process-memory only and cannot promote report evidence or a positive quality signal from raw success.

Definition of done: no Pi-specific shortcut bypasses the Research Validity or Self-Improvement Governance contracts, and both accept/reject paths are proven.

### Phase 4 — Benchmark propagation and living documentation

1. Test `IstaraApiClient` constructor and per-call header precedence for Pi selection on chat and every implemented candidate request constructor. Explicit selection must propagate `x-istara-agent-engine: pi`; absence must leave default headers untouched. Decide and test whether explicit call headers can override configured engine, documenting the compatibility decision.
2. If behavior changes, update the existing living feature pages for chat overview, A2A, messaging, and compute pool. State opt-in semantics, post-gate telemetry ordering, local-only channel scope, and credential-free—not deployment—readiness.
3. Regenerate feature docs/site/manifests with the repository command; generated outputs must come from that command, not manual editing.

Definition of done: benchmark tests capture the actual request headers and living documentation matches the final behavior.

### Phase 5 — Verification, independent review, and readiness classification

1. Run focused suites first, then impacted route/security suites, then the full credential-free backend suite. Treat optional dependency or inherited failures as evidence to classify, not as a reason to force green.
2. Because A2A/keychain/model-routing/autoresearch/memory controls are security-sensitive, run the tracked security benchmark and update its control artifacts only if controls/triggers/evidence change.
3. Run Compass Forge before/after gates around the implementation task and attach all command/gate evidence. Independently re-review the changed surface; Blocker/Major findings require separate remediation tasks and a delta re-review.
4. Publish the readiness matrix with two explicit verdicts: verified credential-free contracts and unverified runtime/credential dependencies. A live check remains blocked pending explicit owner authorization for one configured target.

## Acceptance criteria and proof

| ID | Given / When / Then | Required proof |
| --- | --- | --- |
| AC-1 | Given Pi is absent, when chat/A2A/channel/autoresearch/benchmark flows run, then baseline routing, headers, and telemetry behavior remain unchanged. | Negative route/service/client tests. |
| AC-2 | Given Pi is selected, when chat invokes tool/SSE processing with a stubbed transport, then normal chunks, tool events, `done`, and persistence survive and telemetry is redacted. | In-process chat route/body-iterator test plus telemetry assertions. |
| AC-3 | Given Pi is selected without a credential, when chat starts, then no provider transport is called and the outcome is a named runtime blocker with no secret persistence/logging. | Transport spy plus missing-keychain fixture. |
| AC-4 | Given a rejected Pi-marked A2A request, when any auth/project/size/rate/replay gate rejects it, then no Pi work/span exists; accepted `tasks/send` emits one post-gate redacted span. | JSON-RPC boundary deny/accept matrix. |
| AC-5 | Given `pi_local` starts, injects, and stops, then it follows normal lifecycle/inbound persistence and project isolation; non-Pi traffic receives no Pi response. | Channel service/router/inbound integration test. |
| AC-6 | Given readiness research data is incomplete, when report routing is attempted, then it is non-reportable; given the governed spine and human Done approval, report routing and source-span traceability succeed. | Positive and negative governed-service tests. |
| AC-7 | Given Pi dry-run/steering or governed-memory fanout runs, then no background/global/production mutation or raw-success promotion occurs and records remain scoped/redacted. | Route/service assertions and database checks. |
| AC-8 | Given the benchmark client is explicitly configured for Pi, when it sends supported requests, then the opt-in header propagates; without configuration, it does not. | Captured-fetch Node tests. |
| AC-9 | Given all credential-free checks pass, when readiness is reported, then implementation evidence and runtime blockers are explicitly separated and no live/deployment claim is made. | Review matrix, CF evidence, gate, and independent verdict. |

## Exact verification sequence

Run from the repository root without launching services or loading a model. First capture the currently passing focused baseline:

```bash
python -m pytest tests/test_pi_replacement_candidate.py -q
node --test tests/real_user_benchmark/lib/api-client.test.mjs
```

After remediation, run the focused boundary tests selected from the inspected owners, then:

```bash
python -m pytest tests/test_chat.py tests/test_a2a_security.py tests/test_a2a_project_claims.py tests/test_channel_inbound.py tests/test_project_scope_contracts.py -q
python -m pytest tests/test_security_benchmark.py tests/test_validation_project_scope.py tests/test_transport_headers.py -q
python scripts/security_benchmark.py --fail-on-threshold
python scripts/feature_docs.py --seed-missing --generate-site --check
python -m pytest tests/ -q
compass-forge gate before --task <implementation-task>
compass-forge gate after --task <implementation-task> --summary
```

Record every command in Compass Forge. If documentation or security-control artifacts are unchanged, record the targeted checks rather than editing them. If the full suite is environment-blocked, preserve its exact failure and retain the independently passing focused proof; do not label it a passed full suite.

## Risks and rollback

- **Research-spine bypass:** Direct fixture construction can falsely prove reportability. Mitigation: negative pre-approval assertions and public governed-service paths. Rollback: revert only Pi probe changes while retaining an equivalent fail-closed report gate.
- **Security-gate ordering:** Instrumentation might occur before A2A rejection. Mitigation: each denial test asserts zero telemetry/work. Rollback: remove Pi instrumentation, not existing authorization/replay checks.
- **Default-path regression:** Broad selection parsing can divert ordinary traffic. Mitigation: explicit absent-header/metadata tests. Rollback: set the flag false/remove header or surgically revert Pi-only selection hooks.
- **Side effects/flaky fixtures:** Local channel or dry-run tests can leave adapters/tasks/session state. Mitigation: actual stop/teardown and scoped queue assertions. Rollback: remove test-only adapter registration without touching external adapters.
- **Runtime ambiguity:** Credentials/provider authorization cannot be inferred from mocks. Mitigation: report those as unexercised blockers; a later owner-authorized one-target probe is separate work.

## Handoff

Give the implementer the seam inventory, the direct-artifact governance concern, the acceptance table, and baseline evidence. Give the reviewer the final diff, route/service proof, full-suite/security/gate output, feature-doc output if behavior changed, and the two-column readiness matrix. No phase may claim production deployment or live-model readiness without a separately authorized bounded probe.

## Decision log

<!-- consensus-winner-decision -->
DEC-consensus-winner | 2026-07-19 | S1-plan | conductor
Context: three planner cross-votes completed
Decision: slot a selected from pi-prod-readiness-20260719t173836-REPLAN-A-r1
Why: votes={"a": {"task": "pi-prod-readiness-20260719t173836-JUDGE-A", "vote": "c"}, "b": {"task": "pi-prod-readiness-20260719t173836-JUDGE-B", "vote": "a"}, "c": {"task": "pi-prod-readiness-20260719t173836-JUDGE-C", "vote": "a"}}; tiebreak_used=False; plan_file=docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-a.md



DEC-1 | 2026-07-19 | S1-plan | codex-main
Context: The prior round used an OpenClaw fallback because the conductor was launched from
the wrong nested runtime and its daemon was down.
Decision: Re-run the literal conductor from a clean login-shell path using a visible
Terminal.app watcher, after real one-shot CLI preflight and harness-symlink checks.
Why: This directly tests the documented failure mode before any fallback is considered.

## Ledger

### L-1 | 2026-07-19T17:38:36-03:00 | S1-plan | codex-main | planner | Phase 1
Did: Created CF-SPEC-5, clarified it with the isolated-worktree and credential-free
production-test boundary, planned it, and created the continuation lifecycle/run folder.
Verified: `compass-forge spec show CF-SPEC-5` reports `status: planned`; direct Codex
preflight probes for `gpt-5.6-terra` and `gpt-5.6-sol` exited 0; conductor preflight cache
reports `ok: true`.
Next: Generate a fresh run-scoped pipeline/cast and launch the visible conductor.

## Phase 1

### Frame and plan

Acceptance: the literal BSC cast starts from Terminal.app, reaches convergence or records
the exact command-level failure, and the final run preserves review findings, remediation,
tests, gates, raw-capture state, and credential/runtime blockers separately.

### Findings register

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|

### L-2 | 2026-07-19T20:48:39Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-b <!-- bsc-ledger:pi-prod-readiness-20260719t173836-PLAN-B -->
Did: pi-prod-readiness-20260719t173836-planner-b stage on task pi-prod-readiness-20260719t173836-PLAN-B (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-PLAN-B finished; worktree head fa6a1a39.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-10 | 2026-07-19T21:00:00Z | S1-plan | codex-main | owner-gate
Did: Observed the literal Build Stream Conductor after planning repair and judge completion.
Result: Plan A won 2–1 (`winner_task=pi-prod-readiness-20260719t173836-REPLAN-A-r1`); the conductor state is `awaiting-owner-approval`, with implementation and review still open and `converged=false`.
Verified: `conductor.py status --project-root <repo-root>-pi-replacement --brief`; `.compass-forge/conductor/consensus.json`; Compass Forge task/evidence listings for tasks 81–86.
Next: obtain explicit owner approval before dispatching `pi-prod-readiness-20260719t173836-IMPL`.

### L-3 | 2026-07-19T20:48:57Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-a <!-- bsc-ledger:pi-prod-readiness-20260719t173836-PLAN-A -->
Did: pi-prod-readiness-20260719t173836-planner-a stage on task pi-prod-readiness-20260719t173836-PLAN-A (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-PLAN-A finished; worktree head 1fad745a.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-PLAN-A (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-4 | 2026-07-19T20:50:38Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-c <!-- bsc-ledger:pi-prod-readiness-20260719t173836-PLAN-C -->
Did: pi-prod-readiness-20260719t173836-planner-c stage on task pi-prod-readiness-20260719t173836-PLAN-C (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-PLAN-C finished; worktree head ece54640.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-PLAN-C (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-5 | 2026-07-19T20:53:22Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-a <!-- bsc-ledger:pi-prod-readiness-20260719t173836-REPLAN-A-r1 -->
Did: pi-prod-readiness-20260719t173836-planner-a stage on task pi-prod-readiness-20260719t173836-REPLAN-A-r1 (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-REPLAN-A-r1 finished; worktree head 437b9831.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-REPLAN-A-r1 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-6 | 2026-07-19T20:54:00Z | S3-review | gpt-5.6-terra | reviewer | Phase 1 <!-- bsc-ledger:pi-prod-readiness-20260719t173836-JUDGE-A -->
Did: Compared the assigned Plan B and Plan C candidates without editing either plan.
Result: Voted for Plan C; it explicitly remediates direct accepted-artifact creation in the readiness probe and better preserves the governed Research Spine. Task pi-prod-readiness-20260719t173836-JUDGE-A.
Verified: `sed -n` review of `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-b.md` and `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-c.md` completed; Compass Forge command, plan_vote, and self_report evidence recorded.
Next: conductor tallies consensus votes and selects the execution plan; stage exit: consensus vote recorded.

### L-7 | 2026-07-19T20:56:00Z | S3-review | gpt-5.6-terra | reviewer | Phase 1 <!-- bsc-ledger:pi-prod-readiness-20260719t173836-JUDGE-C -->
Did: Compared the assigned Plan A and Plan B candidates without editing either plan.
Result: Voted for Plan A; it defines one selection predicate, a more explicit post-gate A2A telemetry matrix, and a concrete governed-research remediation path that distinguishes provisional fixtures from accepted/reportable artifacts. Task pi-prod-readiness-20260719t173836-JUDGE-C.
Verified: `sed -n` review of `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-a.md` and `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-b.md` completed; Compass Forge command, plan_vote, and self_report evidence recorded.
Next: conductor tallies consensus votes and selects the execution plan; stage exit: consensus vote recorded.

### L-8 | 2026-07-19T20:55:43Z | S3-review | gpt-5.6-terra | reviewer | Phase 1 <!-- bsc-ledger:pi-prod-readiness-20260719t173836-JUDGE-B -->
Did: Compared the assigned Plan A and Plan C candidates without editing either plan.
Result: Voted for Plan A because its phased task graph, acceptance-to-proof matrix, and security, feature-documentation, and gate verification sequence provide the stronger executable readiness contract. Task pi-prod-readiness-20260719t173836-JUDGE-B.
Verified: `sed -n` review of `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-a.md` and `docs/build-stream/plans/pi-prod-readiness-20260719t173836-plan-c.md` completed; Compass Forge command, plan_vote, and self_report evidence recorded.
Next: conductor tallies consensus votes and selects the execution plan; stage exit: consensus vote recorded.

### L-9 | 2026-07-19T20:55:07Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-c <!-- bsc-ledger:pi-prod-readiness-20260719t173836-REPLAN-C-r1 -->
Did: pi-prod-readiness-20260719t173836-planner-c stage on task pi-prod-readiness-20260719t173836-REPLAN-C-r1 (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-REPLAN-C-r1 finished; worktree head 05fc1f72.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-REPLAN-C-r1 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-11 | 2026-07-19T20:59:49Z | S1-plan | gpt-5.6-terra | planner | pi-prod-readiness-20260719t173836-planner-c <!-- bsc-ledger:pi-prod-readiness-20260719t173836-REPLAN-C-r2 -->
Did: pi-prod-readiness-20260719t173836-planner-c stage on task pi-prod-readiness-20260719t173836-REPLAN-C-r2 (harness fallback entry; the model did not append one).
Result: task pi-prod-readiness-20260719t173836-REPLAN-C-r2 finished; worktree head 99bf106e.
Verified: see Compass Forge evidence rows on pi-prod-readiness-20260719t173836-REPLAN-C-r2 (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.
