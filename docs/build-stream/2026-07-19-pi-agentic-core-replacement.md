# Pi Agentic Core Replacement

```yaml
item: pi-agentic-core-replacement
branch: comparison/pi-replacement-core
cf: { specs: [CF-SPEC-1, CF-SPEC-2], tasks: [CF-1, CF-2, CF-3, CF-4, CF-5, CF-6, CF-7, CF-8, CF-9, CF-10, CF-11, CF-12, CF-13, CF-14, CF-15, CF-16, CF-17, CF-23, CF-24, CF-25, CF-26, CF-27, CF-28, CF-29, CF-30, CF-31, CF-32, CF-33, CF-34, CF-35, CF-36] }
phase: "pi-complete-20260719 - delta re-review round 2"
stage: S3-review
status: review_passed
blocked_on: null
last: { agent: fable.5-medium, at: "2026-07-20T00:57:00Z", ledger: L-18 }
next_action: "Conductor advances the pi-complete-20260719 pipeline past S3-review; all review findings (F1-F6, RF1) are resolved with verified command evidence."
```

## Plan Overview

Build a real, isolated Pi-backed replacement candidate for Istara's agentic management
core so the existing Istara harness can run against both the native baseline and the
Pi-wired candidate.

The candidate lives only in `<repo-root>-pi-replacement` on branch
`comparison/pi-replacement-core`. The main Istara worktree remains untouched except for
comparison artifacts under `comparison-Istara-pi/`.

## Owner Bar

- Use the actual Build Stream Conductor process, not a generic one-agent imitation.
- Route work through Compass Forge, model routing, role-separated rounds, review, and
  remediation.
- Use the prior findings and candidate skeleton as the starting point.
- Implement the missing Pi candidate gaps enough for full scenario testing to proceed.
- Save raw prompts and raw LLM outputs for every LLM call.
- Keep DeepSeek live spend under the existing hard USD 0.50 cap.
- Use no local models.
- Do not write or print secrets.
- Do not commit unless the owner asks.

## Non-Goals

- No production deployment.
- No merge to main.
- No mutation of the main Istara application worktree.
- No real channel credentials or production data.
- No local LLM/model usage.

## Phases

### Phase 1 - Adapter Gap Implementation

Implement missing candidate adapter surfaces in the isolated worktree:

- plan lifecycle and review-state representative adapter
- document/tool interaction representative adapter
- persistent memory/RAG boundary simulation with future real adapter seams
- A2A representative adapter
- channel lifecycle simulated adapter
- trace/raw LLM capture layer
- scenario runner that maps Istara harness categories to Pi candidate runs

Verification:

- `npm run validate` in `labs/pi-replacement`
- `npm run smoke:no-model` in `labs/pi-replacement`
- targeted scenario runner commands added by the conductor

### Phase 2 - Paired Harness Benchmarks

Run conservative representative slices from the Istara harness against native baseline and
Pi candidate, under the USD 0.50 cap.

Verification:

- JSON/gzip artifact validation
- secret scan
- scenario coverage matrix
- score table with prompt/output files

## Decision Log

DEC-1 | 2026-07-19 | S0-frame | owner
Context: Prior rounds built a thin Pi candidate and benchmark inventory but did not use the
literal Build Stream Conductor or implement enough adapter code for robust replacement
testing.
Decision: Run a new implementation round using the Build Stream Conductor method, with
Compass Forge, model routing, role-separated planning/implementation/review/remediation,
and ten-minute owner reporting.
Why: The owner needs evidence from a real replacement candidate, not standalone Pi or a
single adapter smoke.

DEC-2 | 2026-07-19 | S2-plan | openclaw-conductor
Context: The follow-up bridge round needed broader real Istara-loop surface coverage, but
the literal local Build Stream Conductor daemon was still down and the old cast remained
unsuitable for DeepSeek-only convergence inside OpenClaw.
Decision: Create `CF-SPEC-2` for the lab-only real-loop bridge, use OpenClaw durable
role lanes for the live review path, and explicitly record the daemon limitation instead
of claiming literal BSC convergence.
Why: This preserved the Build Stream/Compass Forge method while staying within the
owner's safety constraints: no main app mutations, no local models, no commits, bounded
DeepSeek spend, and no production credentials.

## Ledger

### L-1 | 2026-07-19T13:33:58-03:00 | S0-frame | codex-main | framer | Phase 1
Did: Created the lifecycle file for the literal Build Stream Conductor round.
Result: Owner bar, non-goals, phases, and first decision are recorded.
Verified: `date +%Y%m%dT%H%M%S%z` produced `20260719T133358-0300`.
Next: Create CF spec/tasks and Build Stream Conductor cast/routing artifacts.

### L-2 | 2026-07-19T13:40:02-03:00 | S1-plan | codex-main | planner | Phase 1
Did: Revised `CF-SPEC-1` with owner-specific Pi replacement requirements, replanned it,
and generated linked Compass Forge tasks `CF-1` through `CF-17`.
Result: The task graph now covers scenario-runner contract, Pi-owned loop/model/tool
execution, expanded canonical tools, metrics, raw LLM prompt/output capture,
baseline-vs-candidate distinction, article/build-stream docs, conductor compliance,
spend cap, and validation evidence.
Verified: `compass-forge spec revise CF-SPEC-1 --from .compass-forge/spec-revision-pi-replacement.json --actor codex-main`,
`compass-forge spec plan CF-SPEC-1 --force --reason "replan after owner-specific Pi replacement gap requirements"`,
and `compass-forge spec tasks CF-SPEC-1 --force --reason "derive implementation tasks from revised owner requirements despite broad acceptance wording"`
completed.
Next: Create Build Stream Conductor pipeline/cast and run preflight.

### L-3 | 2026-07-19T13:54:00-03:00 | S1-plan | openclaw-conductor | conductor | Phase 1
Did: Loaded Build Stream Conductor, Build Stream, and Compass Forge instructions; ran
`compass-forge status`, `compass-forge agent-brief`, and `conductor.py status --brief`.
Result: Literal BSC state was inspectable but not runnable as a daemon from this session:
`open=5 ready=3 active=[] pi-repl-20260719t133814-code-reviewer=-- converged=False
daemon=down`. The cast routes to Codex CLI `gpt-5.6-*` workers, while this round is
DeepSeek-only after the parent preflight observed Codex CLI probes hanging.
Verified: `.compass-forge/conductor/cast.json` and
`comparison-Istara-pi/runs/20260719T133814-0300-literal-bsc-gap-implementation/conductor-compliance.md`
record the exact limitation.
Next: Continue as an OpenClaw durable conductor using CF tasks and DeepSeek role lanes.

### L-4 | 2026-07-19T14:04:00-03:00 | S3-build | openclaw-conductor | implementer | Phase 1
Did: Expanded the lab-only Pi replacement candidate under `labs/pi-replacement` with
canonical document tools, research-spine step recording, telemetry/model-route tools,
scenario catalog coverage, raw LLM capture, and a DeepSeek role-round runner.
Result: The candidate now owns representative agent loop, model/tool execution envelope,
trace emission, plan/review state, documents, memory/RAG boundary, A2A, channels,
skills/memento adherence, research-spine tracking, model routing, and telemetry slices.
Verified: Changes stayed within `labs/pi-replacement` plus build-stream/comparison
artifacts; no main Istara app code was modified.
Next: Run deterministic, live DeepSeek, and artifact validations.

### L-5 | 2026-07-19T14:06:00-03:00 | S4-verify | openclaw-conductor | verifier | Phase 1
Did: Ran candidate validation and paired scenario commands.
Result: `npm run validate`, `npm run smoke:no-model`, `npm run paired:no-model`,
`npm run smoke:deepseek -- --out <run-folder>`, DeepSeek role rounds, final DeepSeek
re-review, and `npm run collect:artifacts -- --out <run-folder>` passed.
Verified: `scores.json` reports 10/10 baseline scenarios and 10/10 Pi candidate
scenarios passing, with 36/36 successful candidate tool calls.
Next: Validate raw prompt/output capture and spend accounting.

### L-6 | 2026-07-19T14:07:00-03:00 | S4-verify | openclaw-conductor | reviewer | Phase 1
Did: Ran role-separated DeepSeek lanes for planner, architect, plan-reviewer/judge,
code-reviewer, remediator, and re-reviewer.
Result: Early code review and re-review failures identified under-evidenced prompts and
missing concrete artifact proof; remediation updated prompts/artifacts and the final
DeepSeek re-review returned PASS with no remaining blockers.
Verified: Raw captures include all live calls, including a recovered record for an
overwritten failed re-review caused by an earlier fixed call id collision.
Next: Attach CF evidence and close the spec.

### L-7 | 2026-07-19T14:09:00-03:00 | S4-verify | openclaw-conductor | evidence | Phase 1
Did: Validated gzipped raw LLM capture and secret redaction.
Result: `raw-llm-calls/prompts.jsonl.gz` and `raw-llm-calls/outputs.jsonl.gz` each parse
with 35 records, include 8 DeepSeek output records, and contain no persisted Keychain
secret or bearer-token leak.
Verified: Added DeepSeek spend is estimated at USD 0.01086299; with prior conservative
spend of USD 0.0801, remaining budget is estimated at USD 0.40903701.
Next: Finish CF tasks and accept the spec.

### L-8 | 2026-07-19T14:11:19-03:00 | S5-ship | openclaw-conductor | acceptor | Phase 1
Did: Attached shared implementation/validation evidence across `CF-1` through `CF-17`,
marked all linked tasks done, ran `compass-forge gate after`, and accepted `CF-SPEC-1`.
Result: Compass Forge records `CF-SPEC-1` as accepted with 17 tasks complete and 35
evidence records. The final gate has no new failures; inherited `unexpected_large_files`
remain from existing docs/assets and `frontend/package-lock.json`.
Verified: `compass-forge spec accept CF-SPEC-1 --actor openclaw-conductor` completed.
Next: Use the run folder artifacts to decide whether to fund broader live fanout and real
Istara service integration.

### L-9 | 2026-07-19T14:55:00-03:00 | S1-plan | openclaw-conductor | conductor | Phase 2
Did: Loaded Build Stream Conductor, Build Stream, and Compass Forge instructions for the
real Istara-loop bridge round; read the new run instructions/status, prior final outlook,
coverage matrix, replacement explainer, and this lifecycle file.
Result: The run was grounded in the prior lab candidate and the new requirement that Pi
be tested as a replacement engine against Istara's actual agentic-loop touchpoints.
Verified: Required run files under
`comparison-Istara-pi/runs/20260719T145107-0300-real-istara-loop-bridge/` were read
before edits.
Next: Map real surfaces through Compass Forge and source inspection.

### L-10 | 2026-07-19T15:04:00-03:00 | S2-plan | openclaw-conductor | planner | Phase 2
Did: Ran `compass-forge status`, `refresh`, `agent-brief`, `classify`, impact analysis,
test-impact, created and clarified `CF-SPEC-2`, planned it, generated tasks `CF-23`
through `CF-36`, claimed work order `CF-34`, and ran `compass-forge gate before`.
Result: Scope was locked to lab-only code plus run/build-stream artifacts, with main
Istara app code protected. Literal BSC status remained daemon down, so OpenClaw durable
role lanes were used.
Verified: `compass-forge gate before --task CF-34 --summary` reported no new failures;
the inherited failure class was only `unexpected_large_files`.
Next: Implement bridge surfaces in the isolated lab candidate.

### L-11 | 2026-07-19T15:10:00-03:00 | S3-build | openclaw-conductor | implementer | Phase 2
Did: Added `istara-surface-map.mjs` and `istara-service-bridge.mjs`; extended the
canonical facade, adapter, scenario catalog, artifact collector, role-lane prompts,
README, and tests.
Result: The lab candidate now maps and exercises chat/tool loop, Autoresearch
governance, plan/review state, tasks/findings/documents, memory/RAG/ReasoningBank/
Memento/skills, A2A/reports, channels/webhooks/Telegram-like lifecycle,
steering/system-prompt, telemetry/tokens/tool metrics, and benchmark/eval/real-user
contracts.
Verified: Edits remained under `labs/pi-replacement`, `.compass-forge` spec answer
context, this lifecycle file, and comparison run artifacts; main Istara app code was not
modified.
Next: Validate deterministic, live DeepSeek, raw capture, and artifact generation.

### L-12 | 2026-07-19T15:17:00-03:00 | S4-verify | openclaw-conductor | verifier | Phase 2
Did: Ran deterministic validation and scenario commands, DeepSeek provider smoke,
DeepSeek code-review/re-review role lanes, artifact collection, raw capture counts, and
secret scan.
Result: `npm run validate` passed 5/5 tests. The artifact collector reports 15/15
baseline scenarios and 15/15 Pi candidate scenarios passing, 56/56 candidate canonical
tool calls, all 10 mandatory mapped surfaces covered, 29 canonical bridge tools, and 44
prompt/output raw LLM records.
Verified: `npm run smoke:deepseek -- --out <run-folder>` passed; `npm run
role-rounds:deepseek -- --max-calls 2 --roles code-reviewer,code-reviewer-rereview`
passed with final re-review `{"status":"pass","remaining_blockers":[]}`; the Keychain
secret scan found no key persisted in run artifacts.
Next: Record final artifacts, attach CF evidence, and close the follow-up spec.

### L-13 | 2026-07-19T15:19:11-03:00 | S5-ship | openclaw-conductor | evidence | Phase 2
Did: Wrote the required run artifacts including `surface-map.md`,
`implementation-ledger.md`, `conductor-compliance.md`, `scenario-inventory.jsonl`,
`coverage-matrix.json`, `scores.json`, `tool-call-metrics.json`,
`research-spine-step-quality.json`, `feature-adherence.json`,
`raw-llm-calls/prompts.jsonl.gz`, `raw-llm-calls/outputs.jsonl.gz`,
`benchmark-readiness.md`, `cleanup-report.md`, and `final-outlook.md`.
Result: Added DeepSeek spend is estimated at USD 0.00339262; with prior conservative
spend of USD 0.09096299, remaining cap is USD 0.40564439. The Compass Forge after-gate
reported no new failures and only inherited `unexpected_large_files`.
Verified: `compass-forge intelligence test-impact` identified
`labs/pi-replacement/test/adapter.test.mjs` as the key direct lab test; `compass-forge
gate after --task CF-34 --summary` reported `new_failures: 0`.
Next: Finish `CF-SPEC-2` evidence/tasks and decide whether to authorize production
service integration or broader full-harness live benchmarking.

### L-14 | 2026-07-19T15:21:49-03:00 | S5-ship | openclaw-conductor | acceptor | Phase 2
Did: Attached artifact, command, gate, and DeepSeek review evidence across `CF-23`
through `CF-36`, marked all linked tasks done, and accepted `CF-SPEC-2`.
Result: Compass Forge records `CF-SPEC-2` as accepted with 14 tasks complete and 50
evidence records. The real-loop bridge round is complete under the OpenClaw fallback
because literal BSC daemon convergence remained unavailable.
Verified: `compass-forge spec accept CF-SPEC-2 --actor openclaw-conductor` completed
with all linked tasks in `done` status.
Next: Use the run folder to decide whether to fund broader live benchmark fanout or
authorize production Istara service adapters.

### L-15 | 2026-07-19T15:24:00-03:00 | S5-ship | openclaw-conductor | verifier | Phase 2
Did: Ran the tracked security benchmark because the lab bridge added webhook,
LLM-provider, Autoresearch, and agentic-memory representative surfaces.
Result: The benchmark passed at 100.0 percent with 28/28 controls passing and no
triggered production security paths.
Verified: `python scripts/security_benchmark.py --fail-on-threshold` completed, and the
result was attached as Compass Forge evidence to `CF-35` and `CF-36`.
Next: Use the completed artifacts for benchmark or production-integration decisions.

### L-16 | 2026-07-19T15:25:00-03:00 | S5-ship | openclaw-conductor | gate | Phase 2
Did: Re-ran the Compass Forge after-gate after the final lifecycle and comparison
evidence-log updates.
Result: Gate status still reports no new failures or new warnings. The only failure class
remains inherited `unexpected_large_files`.
Verified: `compass-forge gate after --task CF-34 --summary` completed with
`new_failures: 0`, `security: 0`, and all drift counters at zero.
Next: Report completion to the requesting main agent.

### L-17 | 2026-07-20T00:46:00Z | S3-review | claude-fable-5 | reviewer | pi-complete-20260719 delta re-review r1 <!-- bsc-ledger:REREV-pi-complete-20260719-REVIEW-r1 -->
Did: Delta re-review of the four fix tasks for pi-complete-20260719-REVIEW findings
F1-F6: verified the review packet's bounded DeepSeek runtime evidence, the strict
fail-closed Pi routing in chat.py/compute_registry, the unconditional autoresearch
dry_run handling, text-fallback PiChatRunMetrics parity, and the new A2A/pi_local
negative boundary tests; re-ran the focused suites locally.
Result: FAIL. Five of six findings verify (F1, F2, F4, F5, F6, and the stopped-injection
half of F3), but the delivered cross-project test
`test_pi_local_channel_inbound_cannot_cross_project_boundary` fails deterministically:
it asserts 2 persisted project-A ChannelMessages while the no-deployment path persists
only the inbound row (the Pi response goes to `adapter.send()` without outbound
persistence), so 1 != 2. The source fix task's evidence claiming the suite passed does
not reproduce. Created finding task
FIX-REREV-pi-complete-20260719-REVIEW-r1-cross-project-channel-test (owner
pi-complete-20260719-fixer) and recorded verdict fail with one Major finding (RF1).
Verified: `python3 -m pytest tests/test_pi_replacement_candidate.py -q` -> 1 failed /
11 passed (reproduced in isolation); `python3 -m pytest tests/test_autoresearch.py -q`
-> 16 passed; `python3 -m pytest tests/test_compute.py -k
strict_model_stream_does_not_fallback_after_pinned_node_fails -q` -> 1 passed. Command
evidence, review_verdict, and self_report recorded on
REREV-pi-complete-20260719-REVIEW-r1.
Next: Fixer resolves RF1 (correct the assertion to the persisted-inbound +
adapter.sent_messages contract, or persist the Pi outbound on the no-deployment path),
re-runs the full file to 12/12, and re-records evidence; conductor creates re-review
round 2 after all siblings settle.

### L-18 | 2026-07-20T00:57:00Z | S3-review | claude-fable-5 | reviewer | pi-complete-20260719 delta re-review r2 <!-- bsc-ledger:REREV-pi-complete-20260719-REVIEW-r2 -->
Did: Delta re-review of FIX-REREV-pi-complete-20260719-REVIEW-r1-cross-project-channel-test
(RF1). Verified the corrected test contract in
tests/test_pi_replacement_candidate.py: it now asserts exactly 1 persisted project-A
inbound ChannelMessage (option a from the finding) and additionally checks the Pi
OutgoingMessage on adapter.sent_messages with pi_replacement metadata whose
inbound_message_id resolves to the project-A inbound row. Inspected the immediate seam:
the no-deployment path in backend/app/services/inbound_processor.py now returns
build_pi_channel_response(...) instead of None; confirmed it is gated by
pi_replacement_requested (only PiLocalAdapter injects pi_candidate=True), project_id is
taken from instance.project_id so the spoofed metadata project_id cannot leak
persistence or telemetry into project B.
Result: PASS. RF1 resolved; fix evidence reproduces honestly this time. Zero
corrections made.
Verified: `python3 -m pytest
tests/test_pi_replacement_candidate.py::test_pi_local_channel_inbound_cannot_cross_project_boundary
-q` -> 1 passed; `python3 -m pytest tests/test_pi_replacement_candidate.py -q` -> 12
passed; seam check `python3 -m pytest tests/test_channel_inbound.py -q` -> 4 passed.
Command evidence, review_verdict (pass), and self_report recorded on
REREV-pi-complete-20260719-REVIEW-r2.
Next: Conductor advances the pipeline past S3-review; no open findings remain. Noted
residual (non-blocking) risk: the no-deployment Pi response is delivered via
adapter.send() without a persisted outbound ChannelMessage row, so the outbound audit
trail differs from the deployment path.

## Findings

| ID | Severity | Status | Owner | Summary |
| --- | --- | --- | --- | --- |
| RF1 | Major | resolved (REREV-pi-complete-20260719-REVIEW-r2, L-18) | pi-complete-20260719-fixer | Delivered test `test_pi_local_channel_inbound_cannot_cross_project_boundary` fails deterministically (asserts 2 persisted project-A messages; no-deployment path persists only the inbound, Pi response is sent but not persisted); source fix evidence claiming a passing suite does not reproduce. Fixed via option (a): assertion corrected to 1 persisted inbound + adapter.sent_messages contract; full file 12/12 verified by re-review r2. |
