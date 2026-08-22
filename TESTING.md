# Istara Testing Guide

This is the developer entry point for Istara verification. Use it first when
you need to understand what tests exist, which commands are CI-safe, which
commands require live services, and how project-scoped test data should be
handled.

The deeper files are still important, but they are not competing front doors:

| File | Owns |
| --- | --- |
| `TESTING.md` | Developer navigation, command matrix, suite topology, CI map, project-scoping rules, artifact policy. |
| `testing/TESTING_STRATEGY.md` | Release-governance strategy, test layer contracts, live LLM contract, eval metrics. |
| `testing/AI_EVALS_STRATEGY.md` | Academic and industry eval design for RAG, Prompt RAG, LLMLingua, DAG/ReAct, ReasoningBank, Memento Skills, Meta Hyperagents, and voice contracts. |
| `testing/TEST_HISTORY.md` | Curated release-relevant verification history. Raw run dumps do not belong here. |
| `tests/evals/README.md` | Versioned AI eval runner usage and output rules. |
| `tests/real_user_benchmark/README.md` | Long-form real UX researcher benchmark, sandbox, donated compute, and comparison scorecards. |
| `security/SECURITY_BENCHMARK.md` | Security control matrix, required security benchmark, and standards mapping. |

## Safety Model

Treat the suite as two families:

| Family | Meaning | Examples |
| --- | --- | --- |
| CI-safe deterministic checks | Do not require live servers, private LLMs, or manual credentials. These are the default for normal development and PRs. | Pytest contract tests, governance scripts, frontend unit/type/lint/build checks, mutation/property gates, static eval runner. |
| Live or environment-bound checks | Require a running Istara app, browser automation, Docker/Colima, private LLM profile, donated compute, third-party credentials, or explicit operator intent. | `tests/e2e_test.py`, `tests/simulation/run.mjs`, marathon cycles, real-user benchmark probe/full, live LLM evals. |

Repository policy still applies while testing:

- Do not start backend/frontend servers, send live chat probes, or trigger model
  loading without explicit permission for that run.
- Do not probe broad local-network LLM endpoints. Live LLM tests use one
  gitignored OpenAI-compatible profile.
- Never commit private server URLs, tokens, connection strings, or endpoint
  fingerprints.
- Raw artifacts stay in ignored result roots. Curated summaries go in
  `testing/TEST_HISTORY.md` only when they become useful release evidence.
- `LLMs/` and `Model_Finetuning/` are protected local artifact folders. Do not
  delete, prune, move, or clean them during testing work.

## Quick Command Matrix

Run commands from the repository root unless the command says otherwise.

| Scope | Command | Use when | Live services |
| --- | --- | --- | --- |
| Pytest inventory | `pytest --collect-only -q` | You need a cheap suite map or want to verify collection after moving tests. | No |
| Targeted Python test | `pytest tests/test_project_scope_contracts.py -q` | You touched a specific backend, frontend contract, governance, or security surface. | No |
| Full Python suite | `cd backend` then `pytest ../tests/ -v --tb=short` | You want the same broad backend test shape CI uses. | No, except tests explicitly gated by env/markers |
| Harness smoke | `pytest tests/test_harness_config.py tests/test_agentic_eval_contract.py -q` | You changed eval, simulation, mutation, or harness wiring. | No |
| Project scope guards | `pytest tests/test_harness_project_scope_contracts.py tests/test_simulation_project_scope_contracts.py tests/test_integration_simulation_scope.py tests/test_project_scope_contracts.py -q` | You touched project isolation, active-project behavior, simulations, agents, chat, voice, tasks, files, or shared API clients. | No |
| Governance | `python scripts/check_integrity.py` | You changed architecture-sensitive files or want broad repo integrity feedback. | No |
| CI governance | `python scripts/check_ci_governance.py` | You changed CI, release checks, or governance scripts. | No |
| Harness governance | `python scripts/check_test_harness.py` | You changed tests, evals, simulation, live LLM wiring, or mutation/property gates. | No |
| Production rehearsal | `python scripts/production_rehearsal.py --json` | You need release-critical governed-evolution, compute, rollback, and dependency checks. | No live model by default |
| Security benchmark | `python scripts/security_benchmark.py --fail-on-threshold` | Auth, authorization, sessions, WebAuthn, connection strings, pooled compute, MCP, webhook, LLM-provider, autoresearch, self-evolution, or agentic-memory changes. | No |
| Security benchmark tests | `pytest tests/test_security_benchmark.py -q` | You changed the control matrix, evidence paths, or trigger patterns. | No |
| Feature-obligation classifier | `python scripts/check_feature_obligations.py --base origin/testing --head HEAD --json-out artifacts/feature-obligations.json` | You changed product behavior and need the fail-closed obligation report. | No |
| QA capabilities check | `python scripts/check_qa_capabilities.py` | You changed `qa/runtime_capabilities.json` or the QA capability contract. | No |
| Workflow contract check | `python scripts/check_workflow_contracts.py` | You changed public CI/promotion workflows. | No |
| QA compose render | `docker compose -f docker-compose.qa.yml --profile contract config --quiet` | You changed the disposable QA stack contract. | No (render only) |
| QA developer entrypoint | `./scripts/istara-qa.sh render` | You want the documented QA lifecycle (render/up/wait/seed/qa/collect/reset/down). | `up` needs Docker |
| Feature docs | `python scripts/feature_docs.py --seed-missing --generate-site --check` | UI/menu/route/store/agent/skill/model/test behavior changed. | No |
| Feature docs tests | `pytest tests/test_feature_docs.py -q` | You changed feature docs inventory, source pages, glossary, generator, or generated site expectations. | No |
| Frontend unit tests | `cd frontend` then `npm run test:unit` | You changed frontend logic covered by Vitest. | No |
| Frontend type check | `cd frontend` then `npx tsc --noEmit` | You changed TypeScript types, API clients, components, stores, or config. | No |
| Frontend lint | `cd frontend` then `npm run lint` | You changed frontend source. | No |
| Frontend mutation | `cd frontend` then `npm run test:mutation` | You changed `src/lib/runtimeConfig.ts` or mutation harness config. | No |
| Frontend build | `cd frontend` then `npm run build` | You need the full Next build gate. | No live backend |
| Pi runtime contract tests | `cd pi-runtime` then `npm ci && npm test` | You changed Pi provider binding, protocol, model identity, budgets, or secret-flow behavior. | No live provider; uses deterministic and loopback fixtures |
| Pi replacement lab tests | `cd labs/pi-replacement` then `npm ci && npm run validate` | You changed the standalone-Pi compatibility adapter or its contract fixtures. | No live provider |
| Relay unit tests | `cd relay` then `npm test` | You changed relay connection strings, heartbeats, LLM proxying, or compute donation client code. | No |
| Simulation static checks | `cd tests/simulation` then `npm run test:static` | You changed simulation runner, scenario, evaluator, or helper JavaScript and want syntax plus pure harness smoke coverage. | No |
| Marathon config integrity | `pytest tests/test_marathon_config_integrity.py -q` | You changed `scripts/marathon/config.json`, scenario registration, or custom-check wiring. | No |
| Backend mutation | `python scripts/run_backend_mutation.py` | You changed compute-capacity mutation targets or property gates. | No |
| Backend mutation properties | `cd backend` then `pytest tests/test_compute_capacity_properties.py -q` | You need the mutmut-compatible property selection from backend cwd. | No |
| Simulation full suite | `cd tests/simulation` then `npm test` | You have explicit permission to target a running app and want all browser/API scenarios. | Yes, running app |
| Simulation one scenario | `cd tests/simulation` then `node run.mjs --scenario 77` | You are validating one user-facing path, such as voice transcription. | Yes, running app |
| E2E script | `ISTARA_ADMIN_USER=<user> ISTARA_ADMIN_PASSWORD=<pass> python tests/e2e_test.py` | You have explicit permission to test a live Istara instance with real auth. | Yes, running app |
| Marathon cycle | `./scripts/marathon/start-marathon.sh --cycle A` | You are running a planned long-form cycle against prepared services. | Usually yes |
| Marathon all cycles | `./scripts/marathon/start-marathon.sh --all` | You are doing a deliberate pre-release marathon. | Yes |
| Static AI evals | `python scripts/run_istara_evals.py --suite static` | You need eval registry/static behavior without live LLM calls. | No |
| Live AI evals | `python scripts/run_istara_evals.py --suite all --require-live-llm` | You have explicit permission and the private live LLM profile configured. | Yes, live LLM |
| Live LLM orchestration | `ISTARA_RUN_REAL_LLM_BENCHMARK=1 pytest tests/integration/test_llm_orchestration_real.py -q` | You have explicit permission to run the one configured live LLM profile. | Yes, live LLM |
| Real-user plan | `npm --prefix tests/real_user_benchmark run plan` | You want a credential-free benchmark plan/corpus/scaffold. | No |
| Real-user syntax | `npm --prefix tests/real_user_benchmark run check` | You changed the benchmark harness and want JS syntax coverage. | No |
| Real-user probe | `npm --prefix tests/real_user_benchmark run probe` | You have running services and want a bounded realistic UX researcher run. | Yes |
| Real-user deep probe | `npm --prefix tests/real_user_benchmark run probe:deep` | You want video/demo material plus full canonical corpus upload, Research Spine traceability, telemetry, donation, and governed self-improvement evidence. | Yes |
| Real-user three-model deep probe | `npm --prefix tests/real_user_benchmark run probe:deep:three-model` | You want the validated Mac Studio LM Studio donor plus two Colima llama.cpp donors, two researchers, canonical corpus upload, Research Spine traceability, telemetry, donation, and governed self-improvement evidence. | Yes |
| Real-user full | `npm --prefix tests/real_user_benchmark run full` | You are deliberately running the sandboxed comparison benchmark. | Yes, Docker/Colima and often live LLM |

## Current Suite Topology

This is the shape developers should expect when navigating the suite:

| Area | Location | Current span | Notes |
| --- | --- | --- | --- |
| Python pytest suite | `tests/` | 1020 collected tests across 118 collected files at this checkpoint. There are 121 `test_*.py` files on disk because some files are splitters/pointers and `tests/e2e_test.py` is a standalone live script. | Default deterministic contract, security, governance, backend, and cross-surface coverage. |
| Backend mutation properties | `backend/tests/test_compute_capacity_properties.py` | 6 property tests for the mutmut backend cwd. | Wrapped by `scripts/run_backend_mutation.py`. |
| Frontend unit tests | `frontend/src/**/*.test.ts` | Vitest tests for runtime config and model provider behavior. | Run with `npm run test:unit`. |
| Frontend mutation | `frontend/stryker.config.json` | Stryker target for `src/lib/runtimeConfig.ts`. | Thresholds are defined in the config. |
| Relay unit tests | `relay/lib/**/*.test.mjs` | Node test runner coverage for relay connection strings, heartbeat payloads, and LLM proxy request behavior. | Run with `cd relay` then `npm test`. |
| Simulation scenarios | `tests/simulation/scenarios/*.mjs` | 76 scenario files plus static helper tests under `tests/simulation/lib/*.test.mjs`. | Browser/API scenarios against a running app, registered through `tests/simulation/run.mjs`; `npm run test:static` is the PR-safe syntax/project-selection smoke layer. |
| E2E script | `tests/e2e_test.py` | One phase-based live script. | Uses `ISTARA_ADMIN_USER` and `ISTARA_ADMIN_PASSWORD` when provided. Run with `python`, not `pytest`. |
| AI eval registry | `tests/evals/registry.json`, `tests/evals/cases/` | Versioned subsystem evals. | Static mode is safe by default; live mode uses the configured private profile. |
| Real-user benchmark | `tests/real_user_benchmark/` | Plan, probe, and full modes. | Longitudinal UX researcher benchmark with JSONL logs, scorecards, screenshots, and traces. |
| Marathon cycles | `scripts/marathon/config.json` | 13 cycles, A through M, over the simulation and custom-check surface. | Long-running pre-release harness, not a default PR check. |
| Security benchmark | `scripts/security_benchmark.py`, `security/control_matrix.json`, `tests/test_security_benchmark.py` | Standards-backed control matrix and scorecard. | Required for security-sensitive surfaces. |
| Feature docs checks | `scripts/feature_docs.py`, `tests/test_feature_docs.py` | Source docs, generated site, manifests, local-link validation. | Required when product behavior or test behavior changes. |

## CI Coverage

GitHub Actions lives in `.github/workflows/ci.yml`. It runs on `main`, `staging`,
and the long-lived public `testing` integration branch. In addition to the
classic jobs below, CI now includes:

| Job | What it runs |
| --- | --- |
| `feature-obligations` | `scripts/check_feature_obligations.py --base --head --json-out` (fail-closed classifier), `scripts/check_qa_capabilities.py`, `scripts/check_workflow_contracts.py`. Gates unknown paths before expensive jobs. |
| `qa-artifact` | Builds a disposable QA image with immutable digest + provenance/SBOM and records `qa-artifact-manifest.json` on `testing` pushes. |
| `qa-contract-stack` | Renders QA Compose profiles and runs the QA contract tests. |

The dedicated `qa-artifact.yml` workflow builds the disposable QA image; the
`promote-testing.yml` workflow is the ONLY path that may create a promotion PR
to `main`, and only after a protected-environment human approval that binds the
exact source SHA. Nothing auto-merges.

Before creating the PR, the promotion workflow verifies required checks are
green for the exact SHA via `gh api .../actions/runs`; the workflow token binds
`actions: read` (plus `contents`/`pull-requests` write) so that check is
authorized on a normal runner (`scripts/check_workflow_contracts.py` enforces
this permission contract).

The `governance` job's README version-badge sync is restricted to `main` (the
release branch): CI never pushes a generated commit to `testing` or `staging`,
so `testing` HEAD stays the exact, reproducible SHA the promotion gate verifies
(`scripts/check_workflow_contracts.py` enforces this writeback contract).

The original five jobs:

| Job | What it runs |
| --- | --- |
| `governance` | `scripts/check_integrity.py`, `scripts/check_ci_governance.py`, `scripts/check_test_harness.py`, `scripts/security_release_readiness.py`, `scripts/security_benchmark.py --fail-on-threshold`, PR change obligations, and PR security benchmark trigger checks. |
| `backend` | Python install, compileall for governed surfaces, production rehearsal, harness contract smoke tests, property-based contract tests, backend mutation gate, governed evolution regressions, changed-file ruff gate, non-blocking full ruff/format checks, and `pytest ../tests/ -v --tb=short`. |
| `frontend` | `npm ci`, `npm run lint`, `npx tsc --noEmit`, `npm run test:unit`, `npm run test:mutation`, and `npm run build`. |
| `test-harness-js` | Relay dependencies plus `npm test`, simulation `npm run test:static`, and real-user benchmark `npm run check`. |
| `desktop` | Rust toolchain setup and `cargo check` for `desktop/src-tauri`, currently continue-on-error for system dependency drift. |

CI does not run the full simulation suite, marathon, real-user probe/full, or
live LLM evals by default. Those need deliberate operator setup.

## Project-Scoped Testing Rules

Project isolation is now a first-class testing contract. This matters
especially for admin users with many existing projects: tests must not
accidentally pass by reading or mutating the first visible project.

Rules for new or changed tests:

- Keep the active project explicit. Use the project created or selected by the
  current test context.
- Treat paused projects as inactive for test selection. Harnesses may report a
  paused project as evidence, but they must not reuse it for active-work tests.
- In JavaScript simulation code, use `ctx.projectId` or another explicit
  scenario project id. If it is missing, fail or skip clearly instead of
  inventing a fallback.
- Do not use fake fallback ids such as `sim-project-001`.
- Do not use patterns such as `ctx.projectId ||`, `projectId ||`, or
  `project_id: projectId ||` for scoped requests.
- By-id routes for tasks, agents, documents, deployments, sessions,
  notifications, loops, skill proposals, improvement governance, and similar
  project-owned resources should carry `project_id` unless the route is already
  path-scoped by project.
- Creation payloads should include `project_id` when the created object belongs
  to a project.
- List, detail, update, delete, approve, reject, analytics, and health requests
  must stay scoped to the active project.
- Voice and microphone paths must pass explicit `project_id`; UI and harnesses
  should refuse transcription when no active project exists.
- Static guard tests are intentionally strict. If a guard fails, fix the scoped
  test or product path rather than weakening the guard.

Marathon and simulation auth should mirror the app's current security contract:
use `ISTARA_TEST_AUTH_TOKEN` when a bounded test JWT is supplied, or set
`ISTARA_E2E_ALLOW_LOCAL_TOKEN=1` to allow the harness to mint a local signed
admin token from backend code. LM Studio API keys are provider credentials, not
Istara admin JWTs.

The main guard files are:

| Guard | Purpose |
| --- | --- |
| `tests/test_harness_project_scope_contracts.py` | Blocks fake/first-project harness fallbacks and checks voice/microphone project id wiring. |
| `tests/test_simulation_project_scope_contracts.py` | Checks simulation API client and scenario project scoping. |
| `tests/test_integration_simulation_scope.py` | Checks simulation creation/list/update API boundaries align with UI project scope. |
| `tests/test_project_scope_contracts.py` | Broad static contract coverage for project-scoped backend, frontend, agent, governance, chat, files, sessions, and integration surfaces. |

## Choosing Tests For A Change

Use the smallest set that covers the changed behavior, then broaden when the
blast radius is shared or security-sensitive.

| Change type | Minimum useful checks |
| --- | --- |
| Documentation-only change | Link/path sanity, relevant docs grep, and Compass Forge gates if the change is meaningful. |
| Backend API route or service | Targeted pytest for the route/service, auth failure coverage, project-scope guard if project-owned, then relevant governance script. |
| Frontend API client/store/component | `npm run test:unit`, `npx tsc --noEmit`, targeted project-scope guard if project-owned, and simulation scenario only with permission to run live app. |
| Auth, session, WebAuthn, roles, secrets, connection strings | Targeted security pytest, `python scripts/security_benchmark.py --fail-on-threshold`, `pytest tests/test_security_benchmark.py -q` if controls changed. |
| Project isolation | The project-scope guard command from the quick matrix, plus any targeted unit/API tests for the changed surface. |
| Voice/microphone/transcription | `tests/test_harness_project_scope_contracts.py`, relevant transcription tests, and scenario `77` only with explicit live-app permission. |
| LLM provider or compute routing | Deterministic provider/compute tests first; live LLM checks only with explicit permission and one configured profile. |
| Feature docs inventory/source/generator | `python scripts/feature_docs.py --seed-missing --generate-site --check` and `pytest tests/test_feature_docs.py -q`. |
| CI, test runner, eval registry, mutation config | Harness governance, affected runner syntax/collection checks, and the changed job command locally when feasible. |
| User-facing workflow | Targeted backend/frontend tests first, then the relevant simulation scenario with a running app if approved. |

## Simulation, E2E, Marathon, And Benchmark Layers

These layers are easy to confuse, so use this split:

| Layer | Purpose | Default command |
| --- | --- | --- |
| `tests/e2e_test.py` | Phase-based live API and system path script. It is a Python script, not a normal pytest module. | `python tests/e2e_test.py` |
| `tests/simulation/run.mjs` | Browser/API behavioral scenarios with authenticated app state, accessibility checks, and user-facing flows. | `cd tests/simulation` then `npm test` |
| `scripts/marathon/` | Long-running pre-release cycle orchestration over simulation scenarios plus custom checks. | `./scripts/marathon/start-marathon.sh --cycle A` |
| `tests/real_user_benchmark/` | Realistic UX researcher journey with canonical corpus materialization, onboarding, chat, task review, integrations, reports, donated compute, and scorecards. | `npm --prefix tests/real_user_benchmark run plan` |

Use `tests/simulation/package.json` for the supported simulation scripts:

```bash
npm test
npm run test:static
npm run test:headed
npm run test:scenario -- 77
```

Scenario 20 verifies the full registered skill catalog, canonical coverage, and
skill-health surface, then executes a bounded live subset of 3 skills by default
(`ISTARA_SCENARIO20_DEFAULT_SKILL_LIMIT`, default `3`). When live LLM execution
is available, Scenario 20 may ask Istara to choose a coherent 3-skill test plan
from the registered catalog and canonical skill-coverage map; otherwise it uses
seeded logical random selection (`ISTARA_SCENARIO20_SKILL_SEED`) that preserves
phase diversity. Set `ISTARA_SCENARIO20_AGENTIC_SELECTION=0` to force the seeded
fallback. For a deliberate full live skill sweep, set
`ISTARA_SCENARIO20_SKILL_LIMIT` to the current registered skill count; the
default full simulation suite should not spend its entire timeout budget
executing every skill when the registration contract has already been checked.

Document-heavy product tests should use the canonical synthetic UX research
corpus in `tests/document_corpus/canonical/` through
`tests/document_corpus/shared-corpus.mjs`. Use named manifest slices for focused
checks, including `coding-reliability`, `graph-synthesis`, and
`low-consensus-review`, and reserve tiny ad hoc files for parser/unit tests
that are explicitly labeled as such.

The canonical corpus is intentionally deep enough for realistic research
evaluation rather than fixture-only parsing. The manifest records 174 long-form
synthetic upload-compatible sources and more than 2.5 million words/row-word
equivalents across extended interview transcripts, diary studies, usability
tests, surveys, support tickets, analytics, accessibility audits, competitor
benchmarks, stakeholder memos, multilingual/privacy material, and
report-readiness sources. Raw sources must not be pre-digested candidate
evidence blocks or canned report prose. Use selectors for speed; do not replace
representative product tests with tiny 10-20 source fallbacks.

The canonical corpus is also an upload contract. Manifest sources must use
Istara upload-processable file types, currently text/markdown, PDF, DOCX, CSV,
and supported audio. If a new corpus method needs an archive/export format that
Istara cannot ingest, add product support or mark it as a narrow parser fixture
instead of putting it in the product-level canonical upload path.

Use `scripts/reset_test_environment.py` when a live harness needs a clean local
test server. The script is destructive, local SQLite only by default, and
requires `ISTARA_DESTRUCTIVE_TEST_RESET=1` plus
`--confirm DELETE-ISTARA-LOCAL-TEST-DATA`. It deletes users, admins, projects,
local app artifacts, marathon outputs, simulation outputs, and real-user
benchmark outputs, then seeds admin `admin` / `istara123` and an on-demand count
of `researcher_N` users with password `istara123`. It leaves zero projects so
E2E, simulation, marathon, Colima/Docker, and benchmark runs create clearly
named per-suite projects. It never touches `LLMs/` or `Model_Finetuning/`.

Example:

```bash
ISTARA_DESTRUCTIVE_TEST_RESET=1 python scripts/reset_test_environment.py \
  --confirm DELETE-ISTARA-LOCAL-TEST-DATA --researchers 2
```

Research-validity tests must follow the architecture contract in
`docs/architecture/research-validity-contract.md`: source material becomes
stable evidence units, independent coders apply a governed codebook, reliability
is computed on evidence-unit matrices, low agreement goes to reconciliation or
human review, and reports draw only from accepted evidence attached to approved
Done tasks. Tests must keep Hybrid RAG exact-evidence behavior separate from
Evidence Graph / GraphRAG synthesis, and compression tests must prove protected
methodology/codebook/evidence/reliability blocks survive trimming.

Self-improvement tests must follow
`docs/architecture/self-improvement-governance-contract.md`: autoresearch
mutations are sandboxed and reverted before proposals, Meta-Hyperagent variants
are project-scoped read-time overrides, Memento learns from verified/spine-valid
outcomes rather than raw tool success, ReasoningBank remains process memory,
model/skill rankings are project-scoped, BM25 fallback preserves provenance or
marks hits non-promotional, and GraphRAG fails closed when Done-task or evidence
gates are missing.

Use `tests/real_user_benchmark/package.json` for benchmark modes:

```bash
npm --prefix tests/real_user_benchmark run plan
npm --prefix tests/real_user_benchmark run check
npm --prefix tests/real_user_benchmark run probe
npm --prefix tests/real_user_benchmark run probe:deep:three-model
npm --prefix tests/real_user_benchmark run full
```

Probe and full benchmark modes require prepared services and, by default,
donated compute plus non-empty live chat. For harness debugging only, the README
documents explicit opt-out variables.

For real multi-donor compute validation, each required donor must resolve to a
distinct provider/host endpoint. The canonical three-model probe is
host-managed: Mac Studio runs Istara, the admin session, and the LM Studio
donor; Colima runs only two researcher/client simulations plus their Qwen/Gemma
llama.cpp donor endpoints. It skips the Istara server sandbox, starts disposable
client/donor containers, removes benchmark-owned containers, and stops Colima
after the run unless keep/debug flags are set. This mode is for deliberate live
benchmark runs only and does not download models unless explicitly configured
to do so.

## Live LLM Contract

Live tests use one private OpenAI-compatible profile and the shared gitignored
environment loader. This mirrors production serving through `compute_registry`
without broad endpoint probing or multiple heavy model autoloads.

| Setting | Value |
| --- | --- |
| Base URL | `ISTARA_LIVE_LLM_BASE_URL` from gitignored env, process env, or macOS Keychain |
| Chat endpoint | `/v1/chat/completions` |
| Model | `google/gemma-4-e4b` |
| Retry budget | `PRIMARY_LIVE_LLM_MAX_ATTEMPTS = 5` |
| Secret source | `ISTARA_LIVE_LLM_API_KEY`, `ISTARA_LLM_TEST_API_KEY`, or macOS Keychain service `istara-live-openai-compatible-tests` |

Do not commit live API keys, private endpoint values, or endpoint fingerprints
that identify a private server. Do not add tests that discover Ollama, LM
Studio, OpenAI-compatible, or other endpoints by probing the local network.
Production-like live tests must register the one configured profile and call the
same serving path user requests use.

## Eval And Benchmark Artifacts

Raw run output should not become scattered Markdown. Use this policy:

- `tests/evals/.results/` for eval manifests, summaries, JSONL results, and
  reports.
- `tests/simulation/.results/` for simulation scenario reports, screenshots,
  and traces.
- `tests/real_user_benchmark/.results/` for benchmark logs, screenshots,
  generated corpus copies, traces, and scorecards.
- `security/security_scorecard.json` locally or CI artifacts for security
  scorecards.
- Ignored benchmark output directories for transient JSON reports.

When a run becomes a release baseline, add a compact entry to
`testing/TEST_HISTORY.md` with:

- date
- scope
- git SHA when available
- dirty or clean state
- command evidence or artifact paths
- pass/fail counts
- residual risks

## Security Benchmark Gate

Auth, authorization, session, WebAuthn, connection string, pooled compute, MCP,
webhook, LLM-provider, autoresearch, self-evolution, and agentic-memory changes
must run:

```bash
python scripts/security_benchmark.py --fail-on-threshold
pytest tests/test_security_benchmark.py -q
```

When a security control, evidence path, standards mapping, or trigger pattern
changes, update these together:

- `security/control_matrix.json`
- `security/SECURITY_BENCHMARK.md`
- `tests/test_security_benchmark.py`

## Documentation Update Rules

Testing docs should have one clear architecture:

- Put developer-facing navigation, command choices, and suite topology here.
- Put durable strategic rationale in `testing/TESTING_STRATEGY.md`.
- Put historical run outcomes in `testing/TEST_HISTORY.md`.
- Put AI eval methodology in `testing/AI_EVALS_STRATEGY.md`.
- Put real-user benchmark operational details in
  `tests/real_user_benchmark/README.md`.
- Put raw logs, screenshots, traces, generated reports, and benchmark dumps in
  ignored result folders.

When UI/menu/route/store/agent/skill/model/test behavior changes, also update
the relevant living feature docs under `docs/features/`, regenerate the site
and manifests, and run:

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q
```

Docs-only navigation changes do not need to regenerate the feature site unless
they change feature source pages, inventory, glossary, generated site files, or
test behavior.

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
