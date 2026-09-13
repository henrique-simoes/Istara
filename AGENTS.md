# Istara — Agent Contract

Canonical instructions for every coding agent (Claude, Codex, pi, others). Claude-specific
operating rules live in `CLAUDE.md`. Keep this file short: facts here must be verifiable in
the repo; move narrative to `Tech.md` or `docs/architecture/`.

Reference map (read on demand, not up front):

| Need | Source of truth |
|---|---|
| Architecture narrative | `Tech.md` (CI enforces updates via `scripts/check_change_obligations.py`) |
| Research spine | `docs/architecture/research-validity-contract.md` |
| Self-improvement governance | `docs/architecture/self-improvement-governance-contract.md` |
| Test commands, CI coverage, live-LLM rules | `TESTING.md`, `testing/TESTING_STRATEGY.md` |
| UI tokens and interface contract | `DESIGN.md` |
| pi upgrade runbook | `docs/architecture/pi-compatibility-authority.md` §3 |
| Promotion dossier / branch protection | `docs/promotion/` |
| Delivery ledgers | `docs/build-stream/*.md` (validate with `python scripts/verify_build_stream_status.py`) |
| Open post-promotion work | `todo.md` |

## 1. Istara Research Spine Contract

Istara is a research system. Every product feature that ingests, creates,
processes, retrieves, summarizes, validates, visualizes, routes, promotes, or
reports user research data is an extension of the same research-validity spine:

`Sources -> Evidence Units -> Independent Multi-Model Atomic Extraction + Open Coding -> Reliability + Grounding -> Reconciliation -> Accepted Atoms/Nuggets -> Facts -> Insights -> Recommendations -> In Review -> Human-Approved Done -> Reports`.

Atomic Research is not a pre-validation summary layer. Model output may create
candidate/provisional artifacts only; nothing is reportable until source-grounded
coding, reliability, reconciliation, and Done-task gates accept it. Evidence units come
from raw source spans, never synthesized prose.

The spine applies to skills, task creation and execution, ReAct/tool calls, chat, documents, interviews, surveys, AURA-style research, integrations, deployments, interfaces,
autoresearch, self-evolution, RAG/GraphRAG, compute donation, benchmarks, simulations, and
any future feature that touches research data.

Code markers to preserve: `research_spine_eligible: False` (transcription, file processor,
validation) and `can_bypass_research_spine: False` (`autoresearch_engine.py`,
`self_improvement_policy.py`). Guard tests: `tests/test_research_validity_contract.py`,
`tests/pi_production/test_w3_research_spine.py`, `test_scenario_research_spine.py`,
`test_research_spine_donor_routing.py`.

If a feature currently bypasses the spine, classify it as architecture debt and either fix
it in scope or report it. Never describe the system as fully aligned while any
research-data path bypasses evidence units, coding, reliability, reconciliation, human
review, route evidence, or Done/report gates.

Self-improvement (telemetry, ReasoningBank, Memento skills, Autoresearch, Meta-Hyperagent,
Self-Evolution, RAG/GraphRAG, LLMLingua) exists only to improve the spine. It may never
create report evidence, rewrite protected methodology, weaken authorization, or promote
project-scoped evidence to global state.

## 2. Blast-radius protocol (Compass Forge CLI)

Use the CLI (`compass-forge`); the MCP server is optional and often unavailable. Graph
queries are `intelligence code-graph|graph-query|impact` — there is no `graph` command.
Spec ids in old docs are unreliable; confirm with `compass-forge spec`.

```bash
# before editing
compass-forge status
compass-forge index status            # stale -> compass-forge index refresh
compass-forge agent-brief "<request>"
compass-forge intelligence impact --path <file> [--symbol <name>]
compass-forge intelligence test-impact --path <file>
compass-forge gate before
# after editing
compass-forge index refresh && compass-forge gate after
```

Impact output is the starting map, not the answer. Follow dependencies until you know
whether the change touches the spine, auth, or a cross-surface contract. Attach command,
gate, and test evidence to the CF task before finishing. Security-sensitive paths are
listed in `recipes/istara-main/recipe.toml`.

Cross-surface coupling to check on every change:

| If you change | Also check |
|---|---|
| Model fields / route payloads | `frontend/src/lib/types.ts`, `api.ts`, stores, views, alembic, simulation scenarios |
| Auth, RBAC, sessions, WebAuthn, connection strings | `security_middleware.py`, `permissions.py`, login/join UI, `python scripts/security_benchmark.py --fail-on-threshold`, `security/control_matrix.json` |
| Sidebar / view IDs / menus | `HomeClient.tsx`, `MobileNav.tsx`, search + shortcuts, `docs/features/inventory.json`, scenario 09 |
| WebSocket events | `frontend/src/hooks/useWebSocket.ts`, notification store, StatusBar |
| Agent loop, personas, skills | `backend/app/agents/personas/` (CI requires persona updates), chat engines (pi + legacy) |
| Compute / LLM routing / relay | compute pool, `relay/`, pi catalog, donor routing tests, `tests/petals_bridge/` |
| Architecture, process, release files | `Tech.md` (CI gate) |
| UI/menu/route/skill/model behavior | `python scripts/feature_docs.py --seed-missing --generate-site --check` |

## 3. Branches, CI, promotion

- **Work lands on `testing`** (feature/conductor branches → PR into `testing`). `ci.yml` runs
  on push/PR to `main`, `staging`, `testing`; `release-gate` aggregates all jobs;
  `qa-artifact.yml` builds the QA image on `testing` pushes.
- **`main` only via `promote-testing.yml`** (manual, `testing-promotion` environment,
  `source_sha` must equal `origin/testing` HEAD, green checks + QA artifact evidence, never
  auto-merges). Promotions are squash merges, so commit counts between `main` and `testing`
  are not meaningful — compare trees (`git diff --stat main origin/testing`).
- `main` protection: 17 required contexts (`testing/required-checks.json`, checked by
  `scripts/check_required_checks.py`), linear history, no force-push.
- Pushes to `main` trigger `sync-staging.yml` (force-syncs `staging`), `pages.yml`
  (docs site), `build-installers.yml` (releases), `badge-sync.yml`, `scorecard.yml`.
- Never push to `main`, force-push, delete remote branches, or run `git gc --prune=now`
  without the owner (unreferenced certification SHAs must survive).

## 4. Releases, packages, website

- Release: `scripts/prepare-release.sh [--bump|<ver>]` (integrity, CI governance, harness,
  security readiness, security benchmark, production rehearsal, then `set-version.sh`).
  `build-installers.yml` builds macOS/Linux/Windows Tauri installers, `latest.json` for the
  updater, and a `v<CalVer>` GitHub Release.
- Known drift (fix when touching releases): `VERSION` lags the latest tag; `homebrew/istara.rb`
  has no automated update; no GHCR images are published; `wiki/` is not deployed.
- Website: `docs/features/` → `python scripts/feature_docs.py --seed-missing --generate-site --check`
  and `pytest tests/test_feature_docs.py -q` → GitHub Pages via `pages.yml`.

## 5. Containers

| Compose file | Use |
|---|---|
| `docker-compose.yml` (+ `docker-compose.gpu.yml`) | dev/prod stack; profile `observability` adds otel-collector + Jaeger |
| `docker-compose.qa.yml` | disposable QA stack, standalone (never merge with base); drive via `scripts/istara-qa.sh <render\|up\|wait\|seed\|qa\|collect\|reset\|down> --run-id <id> --profile contract\|ui\|live` |
| `docker-compose.vps.yml` | VPS test deploy (provider stub, optional donor) |
| `tests/real_user_benchmark/docker-compose.benchmark.yml` | long-form benchmark |

### Protected QA containers and databases (never delete)

Mac Studio QA host containers prefixed `never-delete-official-`
(`istara-qa-readiness5-20260910-qa-backend`, `w3-live-backend`, `w3-live-backend-fix`,
`w4-live-pi`, `w4-live-legacy`) hold research results.

1. Never `docker rm`, `docker container prune`, or `docker system prune` them; never delete their DBs or images.
2. Their data is **tmpfs**: before stopping one, snapshot `/app/data` and `/tmp/*.db*` to
   `~/never-delete-official-data/<container>/<UTC-timestamp>/`. Snapshots are permanent.
3. Updates = new QA run from HEAD (`QA_RUN_ID=<branch>-<date>`, unique compose project); a
   redeploy never erases prior run data.
4. `~/w4-scratch-20260910/data` (W4 pi/legacy DBs, run logs), `LLMs/`, and
   `Model_Finetuning/` are protected: never delete, move, or prune.

## 6. Testing contract

Every feature change ships with user-journey coverage. Details and commands: `TESTING.md`.

1. **UI simulation as a real user**: extend `tests/simulation/scenarios/*.mjs` (registered in
   `lib/scenario-registry.mjs`) with real browser acts — navigate, click, fill, upload, send.
   API-behind-browser steps must be labeled. Cover roles (admin/researcher/viewer/stranger),
   light/dark, 375px, keyboard focus, loading/error/empty states. Synthetic data only.
2. **Broad suites** (run the ones your change touches; `--engine pi|legacy` where chat is involved):
   all menus/views (09 plus `test_phase9_broad_24view_sweep.mjs`), agentic chat and real work
   (05, 12, 17, 21, 48, 70–71, 76, 79), model ensemble (35, 37), research spine (07, 16, 47, 58),
   security/auth/2FA (32, 42, 56, 64, 67, 68, 74), compute donation (34 + `tests/petals_bridge/`),
   voice (77, 78), long-form (`npm --prefix tests/real_user_benchmark run probe:deep`).
3. **CI lane is credential-free**: `ui-journeys` runs only `testing/ui-journeys.smoke.json` +
   `proven-extra.json` against the QA `ui` profile with the provider stub. Scenarios needing
   live models/donors declare it and fail closed with `not_runnable` — never skip or fabricate.
4. **Desktop**: CI only runs `cargo check` in `desktop/src-tauri`; there are no desktop UI tests.
   State that gap rather than claiming desktop coverage.
5. Attach scenario command + verdict as CF evidence; update `testing/TEST_HISTORY.md` when
   release-relevant results change. A scenario broken by your change is part of your change.

## 7. Telemetry and benchmarks

- Current state: custom spans (`backend/app/core/telemetry.py`, `telemetry_export.py` →
  `telemetry_spans`, `agentic_usage_rows`, `<base>_spans.jsonl`); run aggregation via
  `qa/scripts/w4_aggregate_telemetry.py` (per-turn/tool/model latency, tokens, cost, errors;
  prompts stored as sha12 + length only). No OTLP export and no `gen_ai.*` attributes yet.
- New or changed LLM/agent instrumentation must follow the **OpenTelemetry GenAI semantic
  conventions**: spans `chat`/`invoke_agent`/`execute_tool`; attributes
  `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`,
  `gen_ai.response.model`, `gen_ai.usage.input_tokens`/`output_tokens`,
  `gen_ai.response.finish_reasons`, `gen_ai.conversation.id`; eval results as
  `gen_ai.evaluation.*`. Map onto the existing span tables rather than forking a second store,
  propagate trace context across pi-runtime ↔ backend ↔ relay, and pin collector images.
- Benchmark results are the engine scorecard: refresh and commit them after agentic engine
  changes (`comparison-Istara-pi/`, `qa/runs/<run-id>`, `artifacts/`, `testing/TEST_HISTORY.md`),
  always keyed by commit SHA, engine, and model.

## 8. pi (earendil) runtime

- `pi-runtime/` (Node worker; wire contract `pi-runtime/PROTOCOL.md`) wraps
  `@earendil-works/pi-ai` + `@earendil-works/pi-agent-core`, **exact-pinned** and kept in
  lockstep with `labs/pi-replacement`. Backend adapter: `backend/app/core/pi_runtime/`.
- Upgrade routinely with the runbook: `python scripts/pi_bump_diff_proof.py proof <X> --report ...`
  → install both surfaces with exact pins → `python scripts/generate_pi_catalog.py` → classify
  every changed surface `intended-upstream` or `istara-fix` → `pi_bump_diff_proof.py verify`
  → update `EXPECTED_PINS` in `tests/pi_migration/test_version_provenance.py`.
- Verify: `cd pi-runtime && npm ci && npm test`, `pytest tests/pi_compat tests/pi_migration -q`,
  then a pi-engine UI chat scenario. New pi capabilities go through the adapter seams
  (`seams.py`, `tools.py`), never around the spine or tool-authority checks.

## 9. Safety rules

- No live backend/frontend servers, chat-completion probes, or model loading without explicit
  owner permission; at most one configured model target at a time.
- Secrets and private LLM endpoints live in gitignored env files or macOS Keychain — never in
  commits, logs, or prompts.
- Auth/security/pooled-compute/MCP/webhook/LLM-provider/self-evolution changes run
  `python scripts/security_benchmark.py --fail-on-threshold` and attach the scorecard.
- Never commit the literal checkout path (`scripts/public_repo_quality_audit.py`).
