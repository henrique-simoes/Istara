# Implementation Ledger

## Scope

Lab-only implementation in
`/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`.

## Code Changes

- Expanded `src/canonical-tool-facade.mjs` with document search/read, research-spine
  step recording, model-route, and telemetry metric tools while retaining tasks,
  findings, memory, skills, A2A, channels, and structured evals.
- Extended `src/scenario-catalog.mjs` to 10 representative Istara harness-backed
  scenarios covering tools, documents, memory/RAG, skills, A2A, channels, research spine,
  plan/review state, model routing, telemetry, and structured evals.
- Added `src/raw-llm-capture.mjs` for gzipped JSONL prompt/output capture with token,
  latency, cost, stop reason, raw text, raw tool-call blocks, and redaction summaries.
- Added `scenarios/deepseek-role-rounds.mjs` and updated the DeepSeek smoke to write
  direct raw LLM records under the run folder.
- Expanded `scenarios/collect-replacement-artifacts.mjs` to generate
  `scenario-inventory.jsonl`, `coverage-matrix.json`, `scores.json`,
  `tool-call-metrics.json`, `research-spine-step-quality.json`,
  `feature-adherence.json`, `benchmark-results.md`, `cleanup-report.md`,
  `final-outlook.md`, and `article-notes.md`.
- Updated tests and README for the expanded lab contract.

## Verification

- `npm run validate`: pass, 4/4 tests.
- `npm run smoke:no-model`: pass.
- `npm run paired:no-model`: pass, 10 baseline deterministic and 10 Pi candidate
  scenarios.
- `npm run smoke:deepseek -- --out <run-folder>`: pass, `deepseek-v4-pro`, estimated
  cost $0.00002958.
- DeepSeek role lanes: planner, architect, plan-reviewer, code-reviewer, remediator, and
  final re-review captured under `raw-llm-calls/`.
- `npm run collect:artifacts -- --out <run-folder>`: pass.
- Raw gzip validation and secret scan: pass, 35 prompt records, 35 output records, no
  Keychain secret or bearer-token leak.
- `compass-forge gate after --task CF-8 --summary`: no new failures; inherited
  `unexpected_large_files` remain.
- `compass-forge spec accept CF-SPEC-1 --actor openclaw-conductor`: accepted with
  `CF-1` through `CF-17` done.

## Outcome

The candidate is now a real Pi-owned lab replacement harness: Pi owns the agent loop,
provider/model path, canonical tool execution envelope, and trace emission for
representative Istara surfaces. It remains lab-only and does not claim production parity.
Added DeepSeek spend is estimated at $0.01086299, leaving an estimated $0.40903701 under
the $0.50 cap after prior conservative spend.
