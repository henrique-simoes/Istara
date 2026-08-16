# Cleanup Report

## Retained

- Run folder: `/Users/user/Documents/Istara-main/comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate`.
- Gzipped trace/output artifacts: `traces.jsonl.gz`, `outputs.jsonl.gz`.
- Raw prompt/output records and manifest: `raw-llm-calls/prompts.jsonl.gz`, `raw-llm-calls/outputs.jsonl.gz`, and `raw-llm-calls/manifest.json`.
- Scores and compact JSON summaries.
- Candidate dependencies retained only in isolated worktree for repeatability: `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement/node_modules` (~130 MB).

## Not Retained

- No `dist/`, coverage, cache, tmp, screenshots, local model files, or generated frontend/backend build output were retained in comparison artifacts.
- No DeepSeek API key or private endpoint was written.
- No auth headers, bearer tokens, production/private data, or binary artifacts were retained in raw LLM evidence.

## Size Notes

- `comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate` remains small; artifacts are gzipped where trace-like.
- `labs/pi-replacement` is ~131 MB because Pi npm dependencies remain in the isolated replacement worktree.
- Raw LLM evidence remains small: 22 prompt records and 22 output records, no capping needed.
