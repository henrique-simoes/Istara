# Implementation Ledger

Run: `20260719T125756-0300-full-replacement-candidate`
Updated: `2026-07-19T13:21:48-03:00`

## Architecture Map

Pi remains isolated under `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement` on branch `comparison/pi-replacement-core`. Main Istara app code was not edited outside `comparison-Istara-pi/` artifacts.

The candidate path is now:

```text
Istara harness scenario family
  -> scenario catalog sourced from Istara tests/evals
  -> IstaraPiAdapter
  -> @earendil-works/pi-agent-core Agent event loop
  -> CanonicalToolFacade
  -> Istara-shaped task/document/finding/memory/skill/A2A/channel/eval envelopes
```

## Implementation Plan

1. Keep the sidecar removable and version-pinned.
2. Expand canonical tools from task/finding smoke to representative Istara surfaces.
3. Run each scenario through both a deterministic Istara contract baseline and the Pi-owned Agent loop.
4. Record traces, outputs, scores, raw live call records, coverage, gaps, storage, and cleanup.
5. After the owner clarification, record Build Stream Conductor compliance truthfully instead of implying the generic subagent lane was a literal conductor pipeline.

## Implementation

Changed candidate code in the isolated worktree:

- `src/canonical-tool-facade.mjs`: added document, plan, lifecycle, memory write, skill, A2A report, channel, structured-eval, and telemetry envelopes.
- `src/scenario-catalog.mjs`: added eight Istara-derived scenario definitions with Pi faux-provider responses and expected canonical tool sequences.
- `src/istara-pi-adapter.mjs`: added generic `runNoModelScenario`, all-scenario execution, telemetry summaries, and `IstaraContractBaseline` for paired deterministic contract comparison.
- `scenarios/chat-tool-loop.mjs`: added `--scenario all` and `--engine baseline|pi|both`.
- `scenarios/collect-replacement-artifacts.mjs`: writes `traces.jsonl.gz`, `outputs.jsonl.gz`, `scores.json`, and `paired-run-summary.json`.
- `test/adapter.test.mjs`: verifies all representative surfaces run through Pi Agent loops and the baseline contract runner.
- `package.json`: added `smoke:all-no-model`, `paired:no-model`, and `collect:artifacts` scripts.

## Self-Review

The candidate is materially stronger than the prior thin smoke because the Pi-owned loop now covers eight scenario families instead of one. It still intentionally uses in-memory envelopes, so it is not a production route replacement.

Build Stream Conductor self-review: the earlier implementation used separated manual lanes inside one OpenClaw subagent, not a literal conductor watcher/cast. This is now recorded as a process limitation in `build-stream-conductor-compliance.md` and `build-stream-lifecycle.md`.

## Remediation

The previous key-cleanup remediation remains in place. This run added raw LLM prompt/output capture for the one DeepSeek smoke and avoided logging secrets. No local model path was invoked.

## Benchmark Execution

- Baseline native harness slice: `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/test_agentic_eval_contract.py tests/test_istara_eval_runner.py` -> 12 passed.
- Baseline orchestration benchmark: `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/benchmarks/test_orchestration.py -q` -> 5 passed.
- Candidate adapter tests: `npm run validate` -> 4 passed.
- Candidate/baseline paired deterministic contract run: `npm run collect:artifacts -- --out ...` -> baseline 8/8, candidate 8/8.
- Pi ai live provider smoke: `npm run smoke:deepseek` -> passed, 47 tokens, USD 0.00003654 provider-reported cost.

## Final Synthesis

The run supports a robust isolated candidate for representative harness slices, not full replacement. The exact missing adapters are listed in `adapter-coverage-matrix.md` and `final-outlook.md`.

Conductor synthesis: partial compliance only. CF orientation/impact/test-impact and Build Stream ledger artifacts were added after the clarification, but no conductor-owned S2-S4 worker pipeline, stage attribution rows, review verdicts, or model-diverse convergence occurred in this run.
