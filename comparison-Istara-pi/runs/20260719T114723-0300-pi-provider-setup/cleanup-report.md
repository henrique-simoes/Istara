# Cleanup Report

Run: `20260719T114723-0300-pi-provider-setup`

## Retained Artifacts

- `manifest.json`
- `status.md`
- `logs/pi-provider-deepseek-smoke.json`
- `logs/dependency-setup.json`
- `scripts/pi_deepseek_smoke.mjs`
- `trace.jsonl.gz`
- `outputs.jsonl.gz`
- `cleanup-report.md`

## Deleted Artifacts

- `tmp-pi-deps/`: temporary npm package folder used for `@earendil-works/pi-ai@0.80.10`.

## Storage

- Temporary dependency size before cleanup: 128M.
- Pi package size inside temporary install: 7.6M.
- Final run folder size: 36K.
- Final `comparison-Istara-pi` size: 380K.

No `node_modules`, `dist`, `coverage`, `.cache`, `tmp`, or `tmp-pi-deps` folder is retained
under `comparison-Istara-pi/`.
