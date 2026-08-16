# Storage And Cleanup Runbook

Status: required for durable OpenClaw job
Date: 2026-07-19

## Storage Budget

Default local budget for this comparison folder:

- Planning/docs: under 10 MB.
- Dry-run artifacts: under 25 MB.
- Smoke-test artifacts: under 25 MB.
- First paired benchmark batch: ask before exceeding 250 MB.
- Screenshots/video traces: disabled by default; ask before enabling.

## Artifact Policy

Keep:

- `manifest.json`
- `scenarios.jsonl`
- `trace.jsonl.gz`
- `outputs.jsonl.gz` with capped text fields
- `scores.json`
- `feature-matrix.json`
- `article-tables/*.csv` or `*.json`
- Article Markdown files
- `cleanup-report.md`

Delete or compress after each run:

- Raw server logs unless they contain a cited failure.
- Temporary dependency caches inside the comparison folder.
- Uncapped prompt/output dumps.
- Browser traces/screenshots not cited by a failure.
- Duplicate Pi package clones or build outputs.

Never store:

- API keys.
- Authorization headers.
- Production data.
- Unredacted private prompts or outputs.
- Local model weights.

## Cleanup Procedure

After each run:

1. Record `du -sh comparison-Istara-pi`.
2. Record top-level sizes with `du -sh comparison-Istara-pi/*`.
3. Gzip JSONL traces and outputs.
4. Delete temp folders named `tmp`, `.cache`, `node_modules`, `dist`, `coverage`, or
   browser trace folders unless explicitly retained in `manifest.json`.
5. Write `cleanup-report.md` with retained artifacts, deleted artifacts, and final size.

## Future Run Instructions

Before a new run:

- Read `deepseek-test-config.md`.
- Read `article-collaboration-protocol.md`.
- Read this runbook.
- Verify `DEEPSEEK_API_KEY` is available without printing it.
- Verify no previous run artifacts exceed the storage budget.
- Prefer simulated channels and fake tools before real channel credentials.
