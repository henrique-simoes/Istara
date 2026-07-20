# Build Stream — Pi production runtime completion

<!-- STATUS BLOCK -->
```yaml
item: pi-production-runtime-completion
branch: Review_pi_test
cf: { spec: CF-SPEC-7, tasks: [pi-runtime-complete-20260720-PLAN-A, pi-runtime-complete-20260720-PLAN-B, pi-runtime-complete-20260720-PLAN-C, pi-runtime-complete-20260720-IMPL, pi-runtime-complete-20260720-REVIEW, CF-120..CF-133] }
phase: "Phase 0 — architecture and production boundary"
stage: S1-plan
status: in-progress
blocked_on: "planning-enabled conductor consensus and owner approval"
last: { agent: kimi-code/k3, at: 2026-07-20T02:46:40Z, ledger: L-10 }
next_action: "Collect the remaining cross-judge vote, record consensus_result, then pause for owner approval."
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

## Decision log

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
