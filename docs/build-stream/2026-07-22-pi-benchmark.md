# Build Stream Lifecycle — Pi Benchmark Experimentation

<!-- STATUS BLOCK -->
```yaml
item: pi-benchmark
branch: Review_pi_test
cf: { spec: CF-SPEC-8 }
phase: "Planning phase"
stage: S1-plan
status: in-progress
blocked_on: "none"
authored_by: henrique-simoes
grounding: "Based on 2026-07-20-pi-full-replacement-master-plan.md Section 10"
last: {agent: claude-fable-5, at: 2026-07-22T13:38:20Z, ledger: L-4}
next_action: "Consensus judges vote on architect plans a/b/c"
```
<!-- /STATUS BLOCK -->

## Context
We have completed all 9 waves of the Pi candidate replacement (W0 through W9). The next and final step is to conduct a professional, industry-class paired experiment (B1 through B4) evaluating the Pi candidate against the original Istara React and agentic loops.

## Goals
1. Execute the B1 contract tests.
2. Execute the B2 breadth tier 2 tests.
3. Execute the B3 depth tier 2 and tier 3 tests.
4. Generate the final B4 report in comparison-Istara-pi/reports/.
5. Ensure exact or estimated tokens are flagged properly.

## Instructions
Review Section 10 of docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md for the exact benchmark rules.
Create a step-by-step plan for running all benchmarks, collecting the results, and generating the report.

### L-1 | 2026-07-22T10:25:00Z | S1-plan | human | creator
Did: created lifecycle file   Result: ok   Verified: N/A   Next: architects plan

### L-2 | 2026-07-22T13:33:17Z | S1-plan | claude-fable-5 | architect | Planning phase <!-- bsc-ledger:pi-eval-PLAN-A -->
Did: authored independent consensus plan A at docs/build-stream/plans/pi-eval-plan-a.md (design, E0 asset-build wave, E1-E4 = B1-B4 execution waves, acceptance A1-A5 + per-phase, exact verification commands, risks R1-R9, layered rollback)
Result: plan slot A ready for consensus judging; key finding: S10.3 assets (tests/pi_benchmark/, metrics-schema.json, pi_benchmark_report.py, comparison-Istara-pi/, --engine plumbing) do not exist yet, so plan front-loads build wave E0; pi-eval-PLAN-A
Verified: ls/grep gap audit (tests/pi_benchmark absent, --engine unplumbed in both run.mjs, header support present api-client.mjs:31,244); evidence rows 1222-1224 on CF task
Next: consensus judges vote on plan slots a/b/c

### L-3 | 2026-07-22T13:33:48Z | S1-plan | gpt-5.6-sol | planner | pi-eval-architect-b <!-- bsc-ledger:pi-eval-PLAN-B -->
Did: pi-eval-architect-b stage on task pi-eval-PLAN-B (harness fallback entry; the model did not append one).
Result: task pi-eval-PLAN-B finished; worktree head ccf1680e.
Verified: see Compass Forge evidence rows on pi-eval-PLAN-B (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-4 | 2026-07-22T13:38:20Z | S1-plan | claude-fable-5 | architect | Planning phase <!-- bsc-ledger:pi-eval-REPLAN-A-r1 -->
Did: repaired consensus plan A (revision r1) at docs/build-stream/plans/pi-eval-plan-a.md — closed all three r0 residual risks with verified evidence; extended ground-truth table (axis-1 vocab in tests/agentic_eval_contract.json; pricing table labs/pi-replacement/src/raw-llm-capture.mjs:5-10; chunk-count tokens bug tests/benchmarks/long_horizon_runner.py:138); E0.8/E3.2 now cite exact file:line
Result: plan slot A ready for consensus judging (r1); metrics-schema.json confirmed absent repo-wide so E0.1 is definitively an authoring task; pi-eval-REPLAN-A-r1
Verified: ls/find/grep grounding audit (assets absent, vocab present, bug located at :138, engine header intact api-client.mjs:31,244); wc -l plan = 253 lines; CF evidence rows 1233,1235,1236
Next: consensus judges vote on plan slots a/b/c
