# Cleanup Report

Run: `20260719T124322-0300-50c-paired-benchmarks`

## Retained

- Manifest, status, scenario inventory, paired plan, coverage matrix/summary, scores, and CF notes.
- Gzipped `trace.jsonl.gz` and `outputs.jsonl.gz` only; no raw uncapped traces retained.
- Istara deterministic result summaries under `istara-orchestration-benchmarks.json` and `istara-static-evals/` with runtime data removed.
- Run-local Pi live evaluator script under comparison artifacts; Pi dependencies remain only in the isolated replacement worktree.
- Real-user benchmark plan-only artifacts retained under `real-user-plan/`; no screenshots, browser traces, local models, or live service outputs were generated.
- Article notes and CSV tables under `comparison-Istara-pi/article/`.

## Deleted

- Static eval `runtime_data/` after summary/results/report generation.

## Storage Measurements

- Run folder: `720K	comparison-Istara-pi/runs/20260719T124322-0300-50c-paired-benchmarks`
- Comparison folder: `1.2M	/Users/user/Documents/Istara-main/comparison-Istara-pi`

No local model files, screenshots, browser traces, dist, coverage, cache, tmp, or node_modules were retained inside this run folder.

## Cost Update

- Conservative live spend after Pi live rerun and baseline retries: USD $0.0800.
- Owner clarification extension spend delta: USD $0.0000.
