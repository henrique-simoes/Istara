# Istara AI Evals

This directory contains tracked eval definitions. Raw eval outputs are written
to `tests/evals/.results/`, which is gitignored.

Run all current Istara AI evals against the configured local live LLM profile:

```bash
python scripts/run_istara_evals.py --suite all --require-live-llm
```

Run static-only checks:

```bash
python scripts/run_istara_evals.py --suite static
```

The runner records `manifest.json`, `summary.json`, `results.jsonl`, and
`report.md` for each run. The manifest identifies the git and Compass state
without storing the private LLM endpoint or token.

Live evals load only the shared live-LLM keys from gitignored `.env*` files or
the local environment, then route through `compute_registry.chat` so retry,
model-readiness, thinking-mode, and visible-output behavior match Istara user
serving. Custom `--output-dir` values must stay under `tests/evals/.results/`
unless `--allow-unignored-output` is supplied explicitly for scratch/debug runs.
