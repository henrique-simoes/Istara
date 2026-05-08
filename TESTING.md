# Istara Testing, Evals, and Benchmarking

This is the top-level verification guide. It points to the active strategy docs,
defines where test history lives, and keeps release verification aligned with
Compass Forge.

## Active Docs

| File | Purpose |
| --- | --- |
| `testing/TESTING_STRATEGY.md` | Active release-governance strategy for test layers, live LLM contracts, eval contracts, mutation/property gates, and agentic metrics. |
| `testing/AI_EVALS_STRATEGY.md` | Academic and industry evaluation plan for RAG, Prompt RAG, LLMLingua, DAG/ReAct, memory, ReasoningBank, Memento Skills, Meta Hyperagents, and voice contracts. |
| `testing/TEST_HISTORY.md` | Curated tracked baseline history. Raw artifacts stay gitignored. |
| `tests/evals/registry.json` | Machine-readable eval registry. |
| `tests/agentic_eval_contract.json` | Agentic workflow evidence and metric contract. |

## Quick Verification Matrix

```bash
# Backend
pytest -q

# Frontend
(cd frontend && npm run test:unit && npx tsc --noEmit && npm run lint && npm run build)

# Relay
(cd relay && npm test)

# Static governance
python scripts/check_integrity.py
python scripts/check_test_harness.py
python scripts/check_ci_governance.py

# Security release gate
python scripts/security_benchmark.py --fail-on-threshold
python scripts/security_release_readiness.py

# Production rehearsal
python scripts/production_rehearsal.py --json
```

## Simulation and E2E

The simulation harness exercises authenticated UI/backend workflows without
requiring raw browser output to be tracked.

```bash
# Full non-live simulation matrix
node tests/simulation/run.mjs

# Scenario 20 with a bounded random skill subset
ISTARA_SCENARIO20_SKILL_LIMIT=3 node tests/simulation/run.mjs --scenario 20
```

For live or long-running scenarios, keep run output under
`tests/simulation/.results/` and summarize only release-relevant baselines in
`testing/TEST_HISTORY.md`.

## Live LLM Contract

Live tests use one private OpenAI-compatible profile and the shared gitignored
environment loader. This mirrors production serving through `compute_registry`
without broad endpoint probing or multiple heavy model autoloads.

| Setting | Value |
| --- | --- |
| Base URL | `ISTARA_LIVE_LLM_BASE_URL` from gitignored env, process env, or keychain |
| Chat endpoint | `/v1/chat/completions` |
| Model | `google/gemma-4-e4b` |
| Retry budget | `PRIMARY_LIVE_LLM_MAX_ATTEMPTS = 5` |
| Secret source | `ISTARA_LIVE_LLM_API_KEY`, `ISTARA_LLM_TEST_API_KEY`, or macOS Keychain service `istara-live-openai-compatible-tests` |

Do not commit live API keys, private endpoint values, or endpoint fingerprints
that identify a private server. Do not add tests that discover Ollama, LM
Studio, OpenAI-compatible, or other endpoints by probing the local network.
Production-like live tests must register the one configured profile and call the
same serving path user requests use.

```bash
ISTARA_RUN_REAL_LLM_BENCHMARK=1 pytest tests/integration/test_llm_orchestration_real.py -q
python scripts/run_istara_evals.py --suite all --require-live-llm
```

## Eval and Benchmark Artifacts

`scripts/run_istara_evals.py` writes versioned artifacts under
`tests/evals/.results/`:

- `manifest.json`
- `summary.json`
- `results.jsonl`
- `report.md`

The runner covers classic LLM behavior, RAG, Prompt RAG, LLMLingua compression,
DAG/ReAct planning, ReasoningBank, Memento Skills, Meta Hyperagent,
thinking-output controls, and voice transcription contracts. Custom output
directories outside `tests/evals/.results/` require the explicit
`--allow-unignored-output` safety flag.

Orchestration benchmarks remain mocked and provider-independent by default:

```bash
python tests/benchmarks/run_benchmarks.py
pytest tests/benchmarks/test_orchestration.py -v
```

The benchmark suite validates long-horizon DAG decomposition, tool-calling
accuracy and resilience, A2A mathematical consensus, and async steering
responsiveness.

## Artifact History Rules

Raw run output should not become scattered Markdown. Use this policy:

- Keep raw eval outputs under `tests/evals/.results/`.
- Keep simulation screenshots/reports/traces under `tests/simulation/.results/`.
- Keep local data-integrity findings in ignored runtime output unless they are
  summarized for a release.
- Keep security scorecards in `security/security_scorecard.json` locally or CI
  artifacts.
- Add only compact, release-relevant summaries to `testing/TEST_HISTORY.md`.
- Include date, scope, git SHA when available, dirty/clean state, commands or
  artifact paths, pass/fail counts, and residual risks.

## Security Benchmark Gate

Auth, authorization, session, WebAuthn, connection string, pooled compute, MCP,
webhook, LLM-provider, autoresearch, self-evolution, and agentic-memory changes
must run:

```bash
python scripts/security_benchmark.py --fail-on-threshold
pytest tests/test_security_benchmark.py -q
```

When controls, standards, evidence paths, or trigger patterns change, update
`security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and
`tests/test_security_benchmark.py` together.

## Dataset Generator Validation

The Istara SFT dataset generator is a local, credential-free generation path by
default:

```bash
python -m py_compile Model_Finetuning/dataset-json-generator.py
python Model_Finetuning/dataset-json-generator.py --out-dir /tmp/istara_dataset_check --samples-per-skill 2
python scripts/check_integrity.py
```

Expected result:

- live skill definitions under `backend/app/skills/definitions/*.json` are
  discovered
- generated JSONL files parse
- `dataset_info.json` reports no omitted live skills
- upload is skipped unless `--upload` is explicitly passed
