# Istara Testing Strategy

This file is active release governance. It defines the test contracts that must
stay aligned with Compass Forge, CI, and the production behavior described in
`Tech.md`.

## Official Reference Baseline

- Pytest markers are registered in `pytest.ini` with `addopts = --strict-markers`,
  following the pytest custom marker guidance:
  https://docs.pytest.org/en/stable/how-to/mark.html
- Browser acceptance tests follow Playwright's authenticated-state model:
  https://playwright.dev/docs/auth
- Primary live LLM tests use Gemini's OpenAI-compatible base URL:
  https://ai.google.dev/gemini-api/docs/openai
- Secondary live LLM fallback tests use LM Studio's OpenAI-compatible chat
  completions endpoint:
  https://lmstudio.ai/docs/developer/openai-compat/chat-completions
- Backend mutation testing is staged around mutmut:
  https://mutmut.readthedocs.io/en/latest/
- Frontend and relay mutation testing are staged around StrykerJS:
  https://stryker-mutator.io/docs/stryker-js/introduction/
- Property-based tests should use Hypothesis where deterministic invariants can
  be generated safely:
  https://hypothesis.readthedocs.io/
- Agentic eval design is aligned with OpenAI Evals and Inspect AI concepts:
  https://github.com/openai/evals and https://inspect.aisi.org.uk/
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
5. Live LLM evals: `scripts/test_llm_integration.py` and
   `tests/integration/test_llm_orchestration_real.py` use Gemini as primary and
   the LM Studio/OpenAI-compatible server as optional fallback. Every live test
   must spend exactly five Gemini chat-completion attempts before falling back.
   Secrets must come from environment variables or macOS Keychain only.
6. Agentic eval contract: `tests/agentic_eval_contract.json` maps autoresearch,
   ReasoningBank, Memento skill/agent creation, Hyperagent, DGM-H, ensemble
   orchestration, ReAct tool-calling, and acceptance UI to test evidence and
   quantifiable metrics.

## LLM Test Contract

Live tests must never infer provider endpoints from browser probes, Ollama
paths, or generic discovery URLs. Gemini calls use:

- Base URL: `https://generativelanguage.googleapis.com/v1beta/openai/`
- Chat endpoint: `/chat/completions`
- Model: `gemini-3.1-flash-lite-preview`

The secondary fallback server uses:

- Base URL: `http://10.0.10.142:1234`
- Chat endpoint: `/v1/chat/completions`
- Model: `qwen3.6-35b-a3b@q5_k_xl`

The profile helper in `tests/llm_test_config.py` is the only source of truth for
test endpoint construction and retry/fallback behavior. `PRIMARY_LIVE_LLM_MAX_ATTEMPTS`
is fixed at `5`; `post_live_llm_chat_completion()` is the shared helper for
live test probes. `scripts/check_test_harness.py` blocks stale `/api/tags` and
`/output_schema` references in LLM test wiring.

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
