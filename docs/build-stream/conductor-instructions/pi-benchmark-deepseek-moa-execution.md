# Pi benchmark remaining-wave work order

Work only in the Pi benchmark lifecycle initiative. Do not edit the master plan
`docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`.

## Objective

Complete the remaining benchmark apparatus and execution path described by
`docs/build-stream/2026-07-22-pi-benchmark.md`:

- B0 offline scheduling, explicit `max_processes`, immutable shard manifest, and a
  crash-safe cumulative budget ledger with a hard `$1.00` cap;
- B1…B_N resumable process waves;
- live benchmark evaluation calls through Istara's API/dispatcher path using DeepSeek;
- real output/usage/provenance capture rather than the current synthetic T2/T3 records;
- Research Spine routing validation for both `self_moa` (same model, temperature samples)
  and `full_ensemble` (distinct route slots), without falsely treating a downgrade to
  one endpoint as a successful ensemble;
- post-run judging and report generation as a separate Build Stream Conductor session;
- final report generation from durable wave artifacts.

## Provider and safety contract

The benchmark DUT is Istara itself: run the original agentic loop and the Pi adaptation
against the same scenarios and compare their captured behavior. The only live provider
allowed behind those Istara evaluation calls is the configured DeepSeek API model
`deepseek-v4-pro`. Do not dispatch DUT evaluation to Kimi, Claude, Codex, local models,
LM Studio, Ollama, Petals, or any other provider. After B1…B_N are terminal, a separate
Build Stream Conductor session judges the durable artifacts and generates HTML, Markdown,
JSON, and scorecard output. Kimi is the intended judging model/harness for that session;
the judge is not the DUT and must not rerun it.

Read the DeepSeek evaluation credential only from its existing runtime secret path; never
write it to files, prompts, logs, manifests, or reports. Every evaluation call must reserve
worst-case cost before dispatch, record provider usage and actual/estimated cost after
completion, and reject the call if the shared cumulative ledger would exceed `$1.00`.
Retries, MoA samples, and evaluation preflight calls share the ledger. Post-run judging
is artifact-based and does not consume the evaluation ledger. Unknown usage or uncertain
evaluation cost fails closed.

## MoA contract

The benchmark must exercise Istara through its API so the dispatcher, endpoint resolution,
route counters, output processing, consensus, and Research Spine evidence are measured.
Do not call DeepSeek directly as a substitute for the Istara DUT path.

1. `self_moa`: same DeepSeek model/endpoint, multiple temperature samples; record the
   requested sample count, temperatures, response count, consensus, and endpoint ID.
2. `full_ensemble`: logical ensemble slots all use DeepSeek, but route resolution must
   preserve and report the requested distinct endpoint/model slots. A dry-run or fake
   route test may validate topology without spend; a live run must never claim full
   ensemble success if Istara resolves fewer distinct served routes.
3. Research Spine coding/reconciliation must record source-unit IDs, coder count,
   served route IDs, reconciliation status, and any downgrade (`full_ensemble` to
   `self_moa`, `dual_run`, or single coder) as a blocked/degraded result, not success.
4. Keep `max_processes` (scheduler concurrency), `moa_n` (samples/coders), and
   `repeats` as separate parameters and manifest fields.

## Required verification

Use the repository's configured Python environment if the system interpreter lacks
dependencies. Add unit tests for ledger locking/reservation, provider rejection,
resume/idempotency, exact-vs-estimated usage, MoA downgrade detection, and budget
exhaustion. Run the focused benchmark tests, the migration ratchet, the Research Spine
route/coverage tests, `git diff --check`, and the security benchmark if provider or
telemetry product code is touched. Do not claim live completion unless the artifact
manifest contains redacted route evidence and a closed cumulative spend ledger.

## Evaluation matrix

The B1…B_N evaluation waves must cover the existing benchmark packs: canonical
15-scenario contract coverage, feature/breadth criteria, Research Spine lifecycle,
A2A collaboration, prompt/injection probes, and token/usage accounting. Every live DUT
call uses the configured DeepSeek route through Istara. After all waves finish, a
separate BSC judging session evaluates the durable records and produces `report.md`,
`report.html`, `scorecard.json`, and per-judgment outputs. Kimi is the intended judge
model/harness for that session.

The judging session must not rerun the DUT or make new benchmark-provider calls. It
scores captured output quality, deterministic scenario success, Research Spine phase and
grounding adherence, tool/A2A behavior, prompt/injection resistance, route/MoA evidence,
and exact-versus-estimated usage/cost integrity.

## Finish contract

The worker must append its Build Stream ledger entry to
`docs/build-stream/2026-07-22-pi-benchmark.md`, record exact verification commands and
remaining blockers, and finish only its assigned CF task. Do not fabricate live results.
