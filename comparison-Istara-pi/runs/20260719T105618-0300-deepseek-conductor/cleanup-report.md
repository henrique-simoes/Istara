# Cleanup Report

Run: `20260719T105618-0300-deepseek-conductor`

Status: complete

## Size

- Final comparison folder size: 340K.
- Run folder size: 184K.

Top-level sizes:

| Path | Size |
|---|---:|
| `comparison-Istara-pi/README.md` | 8.0K |
| `comparison-Istara-pi/architects` | 36K |
| `comparison-Istara-pi/article` | 48K |
| `comparison-Istara-pi/evaluation-lab-plan.md` | 24K |
| `comparison-Istara-pi/evidence-log.md` | 12K |
| `comparison-Istara-pi/runs` | 184K |

## Retained Artifacts

- `manifest.json`
- `status.md`
- `article.md`
- `architect-lanes.md`
- `specs/engine-adapter-spec.md`
- `specs/first-run-scenarios.jsonl`
- `feature-matrix.json`
- `full-replacement-coverage-matrix.md`
- `article-tables/feature-matrix-summary.csv`
- `logs/no-model-validation.json`
- `logs/deepseek-openai-compatible-smoke.json`
- `logs/pi-provider-static-probe.json`
- `trace.jsonl.gz`
- `outputs.jsonl.gz`
- `scores.json`

## Deleted Artifacts

None. No `node_modules`, `dist`, `coverage`, `.cache`, or `tmp` directories were present
under `comparison-Istara-pi/`.

## Policy Checks

- JSONL traces and outputs are gzip-compressed.
- Output text is capped in smoke artifacts.
- No screenshots or browser traces were created.
- No local model weights, package installs, build output, or dependency caches were retained.
- Secret value was not written to artifacts.
