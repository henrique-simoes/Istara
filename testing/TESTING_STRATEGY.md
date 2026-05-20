# Istara Testing Strategy

This file is active release governance. For developer navigation, command
selection, suite topology, CI coverage, and project-scoped testing rules, start
with `../TESTING.md`. This file defines the durable test contracts that must
stay aligned with Compass Forge, CI, and the production behavior described in
`Tech.md`.

## Official Reference Baseline

- Pytest markers are registered in `pytest.ini` with `addopts = --strict-markers`,
  following the pytest custom marker guidance:
  https://docs.pytest.org/en/stable/how-to/mark.html
- Browser acceptance tests follow Playwright's authenticated-state model:
  https://playwright.dev/docs/auth
- Live LLM tests use one private OpenAI-compatible profile configured through
  gitignored environment only. The checked-in contract fixes the model id but
  never stores the endpoint or token.
- Backend mutation testing is staged around mutmut:
  https://mutmut.readthedocs.io/en/latest/
- Frontend and relay mutation testing are staged around StrykerJS:
  https://stryker-mutator.io/docs/stryker-js/introduction/
- Property-based tests should use Hypothesis where deterministic invariants can
  be generated safely:
  https://hypothesis.readthedocs.io/
- Agentic eval design is aligned with OpenAI Evals, Inspect AI, HELM, Ragas,
  TruLens, BFCL, tau-bench, GAIA, WebArena, SWE-bench, LLMLingua, RULER,
  LoCoMo, and Memento Skills. See `testing/AI_EVALS_STRATEGY.md`.
- Tool-calling evals should track BFCL-style function-call correctness:
  https://sky.cs.berkeley.edu/project/berkeley-function-calling-leaderboard/

## Test Layers

1. Static governance: `scripts/check_integrity.py`,
   `scripts/check_ci_governance.py`, `scripts/check_change_obligations.py`,
   `scripts/check_test_harness.py`, and `scripts/security_benchmark.py`.
2. Unit and contract tests: `pytest` over `tests/`, with explicit markers for
   `contract`, `security`, `benchmark`, `agentic_eval`, `live_llm`, `e2e`,
   `simulation`, `acceptance`, `mutation`, and `ui`.
3. Production rehearsal: `scripts/production_rehearsal.py --json` verifies the
   release-critical governed evolution, ReasoningBank, compute, rollback, and
   dependency surfaces before the full suite.
4. Simulation acceptance: `tests/simulation/run.mjs` exercises menus,
   submenus, auth, data flows, agentic features, voice/transcription, and UI
   acceptance with authenticated API and browser state.
5. Deterministic JS harness static checks: `tests/simulation/lib/static-check.mjs`,
   `tests/simulation/lib/project-selection.test.mjs`, relay `npm test`, and
   real-user benchmark `npm run check` keep CI coverage over Node harnesses
   without starting live services. The real-user benchmark check includes
   per-donor model sandbox config tests so Colima/Docker donor setup can evolve
   without silently weakening the live multi-donor contract.
6. Marathon config integrity: `tests/test_marathon_config_integrity.py` keeps
   marathon cycle scenario references, custom-check names, and environment
   requirements aligned with the simulation runner and `scripts/marathon/custom-checks.mjs`.
   Marathon auth follows the same test-token contract as simulation: a supplied
   `ISTARA_TEST_AUTH_TOKEN` wins, and `ISTARA_E2E_ALLOW_LOCAL_TOKEN=1` permits a
   local signed admin token for bounded local runs.
7. Live LLM evals: `scripts/test_llm_integration.py`,
   `tests/integration/test_llm_orchestration_real.py`, and
   `scripts/run_istara_evals.py` use the same single private
   OpenAI-compatible profile. There is no secondary model probing in tests.
   Secrets must come from gitignored environment files, environment variables,
   or macOS Keychain only.
8. Agentic eval contract: `tests/agentic_eval_contract.json` maps autoresearch,
   ReasoningBank, Memento skill/agent creation, Hyperagent, DGM-H, ensemble
   orchestration, ReAct tool-calling, and acceptance UI to test evidence and
   quantifiable metrics.
9. Versioned AI eval registry: `tests/evals/registry.json` and
   `tests/evals/cases/core_eval_cases.json` define repeatable subsystem evals.
   Raw run outputs go under gitignored `tests/evals/.results/`.

## LLM Test Contract

Live tests must never infer provider endpoints from browser probes, Ollama
paths, or generic discovery URLs. They use one OpenAI-compatible profile:

- Base URL: `ISTARA_LIVE_LLM_BASE_URL` from a gitignored local env file
- Chat endpoint: `/v1/chat/completions`
- Model: `google/gemma-4-e4b`

The profile helper in `tests/llm_test_config.py` is the only source of truth for
test endpoint construction and retry behavior. `PRIMARY_LIVE_LLM_MAX_ATTEMPTS`
is fixed at `5`; `post_live_llm_chat_completion()` is the shared helper for
live test probes. `scripts/run_istara_evals.py` uses the same profile and writes
only boolean configuration flags plus a private endpoint fingerprint. It must
not write the endpoint or token. `scripts/check_test_harness.py` blocks stale
`/api/tags` and `/output_schema` references plus committed private server
addresses in LLM test wiring.

## Versioned AI Eval Runner

Use the eval runner whenever Compass Forge or the user asks to run, extend, or
compare AI evaluations:

```bash
python scripts/run_istara_evals.py --suite all --require-live-llm
```

The runner currently covers classic LLM behavior, RAG, Prompt RAG, LLMLingua
compression, DAG/ReAct planning, ReasoningBank, Memento Skills, Meta
Hyperagent, thinking-output controls, and voice transcription contracts. It
writes `manifest.json`, `summary.json`, `results.jsonl`, and `report.md` under
`tests/evals/.results/` for later comparison.

## Artifact History and Retention

Tracked docs should contain curated summaries, not raw run dumps. Store raw
outputs under the gitignored result roots:

- `tests/evals/.results/` for eval manifests, summaries, JSONL results, and
  reports.
- `tests/simulation/.results/` for scenario reports, screenshots, and traces.
- `tests/real_user_benchmark/.results/` for benchmark logs, generated corpus,
  screenshots, traces, and scorecards.
- `security/security_scorecard.json` locally or CI artifacts for benchmark
  scorecards.
- ignored benchmark output directories for transient JSON reports.

When a run becomes a release baseline, add a compact entry to
`testing/TEST_HISTORY.md` with date, scope, git SHA when available, dirty/clean
state, command evidence or artifact paths, pass/fail counts, and residual risks.

## Mutation and Property Testing Gates

Mutation testing is now executable in CI for scoped, deterministic targets:

- Backend: `backend/pyproject.toml` configures `mutmut` with `paths_to_mutate`
  against
  `app/core/compute_capacity.py`. The normal CI property gate runs
  `tests/test_property_contracts.py`; mutmut uses the equivalent
  `backend/tests/test_compute_capacity_properties.py` selection because its
  isolated mutant workspace runs from the backend directory. CI runs
  `scripts/run_backend_mutation.py`, which wraps mutmut, disables its
  fork-child process-title update on macOS, and keeps worker concurrency
  bounded.
- Frontend: `frontend/stryker.config.json` configures StrykerJS with the Vitest
  runner against `src/lib/runtimeConfig.ts`, backed by
  `frontend/src/lib/runtimeConfig.test.ts`. CI runs `npm run test:unit` and
  `npm run test:mutation`.
- Governance: `scripts/check_test_harness.py` verifies mutmut, Hypothesis,
  Vitest, Stryker, CI commands, and harness files stay wired.

Property-based tests should cover deterministic invariants rather than live
model behavior: URI normalization, connection-string parsing, RBAC permission
sets, route/type contracts, statistical ensemble calculations, ReasoningBank
ranking invariants, and sandbox proposal validation.

## Agentic Evaluation Metrics

Agentic tests must report product-relevant metrics, not only pass/fail:

- Tool Selection Quality: selected tool and argument schema correctness.
- DAG Success: plan decomposition and dependency-ready execution.
- Evidence Chain Completeness: generated output traces back to sources,
  reasoning memories, proposal evidence, or task artifacts.
- Sandbox Pass Rate: proposals have approval state, rollback, risk class, and
  test evidence before apply.
- Rollback Availability: every mutable system change has visible rollback
  lineage.
- Retrieval Precision: ReasoningBank, BM25, vector/RAG, prompt-RAG, and
  LLMLingua-protected context keep decision-critical evidence.
- Latency and Capacity: LLM routing, fallback, and pooled compute stay inside
  the current capacity envelope.
