# Istara Test History

This file is the curated, tracked verification history. Raw eval outputs,
simulation reports, screenshots, local database snapshots, and security
scorecards remain in gitignored artifact directories. Add a compact entry here
when a run becomes a release baseline or materially changes confidence in the
system.

## 2026-09-11 — CI backend-test pi diff-proof environment (ci-green F-CI-R1-2)

Scope: `.github/workflows/ci.yml` `backend-test` now installs both bundled pi
surfaces (`npm ci` in `pi-runtime` + `labs/pi-replacement`) before the full
suite. `tests/pi_compat/test_bump_diff_proof.py::test_verify_accepts_current_repository_state`
runs `scripts/pi_bump_diff_proof.py verify`, which fails closed when either
surface has no installed `@earendil-works` packages; the previous
pi-runtime-only install left the full-suite step red in CI-shaped checkouts
(CI run 34564927746 stopped before that step). The no-skip contract is pinned
by `scripts/check_workflow_contracts.py` + `tests/test_workflow_contracts.py`.

| Area | Result |
| --- | --- |
| CI-shape reproduce | Clean worktree at `f4a873f5`, `npm ci` pi-runtime only → `1 failed, 19 passed` (`gate-failed: labs/pi-replacement has no installed @earendil-works/pi-ai (surface not built)`) |
| CI-shape fixed | + `npm ci` labs/pi-replacement → `20 passed`; full CI command `pytest ../tests/ -v --tb=short -m "not live_llm"` → `2369 passed / 5 skipped / 1 deselected, 0 failed` (270.81 s) |
| Governance | `check_ci_governance`, `check_workflow_contracts`, `check_required_checks` (17 contexts), `check_integrity`, `check_test_harness`, `security_benchmark --fail-on-threshold` (triggered ci.yml), `git diff --check` — all PASS |


## 2026-09-11 — readiness5 certification (W5) on 3b4b881d: full matrix + browser lane + live ensemble + long-horizon

Scope: Wave W5 certification per `docs/build-stream/plans/readiness5-20260910-plan-a.md` on frozen SHA `3b4b881de23f60e8b58d8a84a907b33c0e105f21` (`conductor/readiness5-20260910`, baseline `abc9da92`). Dossier rewritten at `docs/promotion/2026-09-09-promotion-certification.md` (W5 header + historical appendix); topology counts refreshed in `TESTING.md` (this checkpoint). No push/PR/merge/settings — manager pushes after verifying SHA.

| Area | Result |
| --- | --- |
| Governance | `check_integrity`, `check_ci_governance`, `check_test_harness`, `check_required_checks` (17 contexts), `check_workflow_contracts`, `check_qa_capabilities`, `security_release_readiness`, `public_repo_quality_audit --check`, `check_feature_obligations --base origin/main` (0 unknown), `production_rehearsal --json` (ROOT venv) — all PASS; `git diff --check` clean |
| Security | `security_benchmark --fail-on-threshold` PASS 28/28 100.0 triggered []; changed-paths (`abc9da92..HEAD`) PASS 28/28 triggered [PiModelManagement, authStore, ci.yml, check_ci_governance] |
| Backend | Full suite `2330 passed / 5 skipped / 1 deselected, 0 failed`; mutmut exit 0 (252 killed / 97 survived / 0 no-cov, 349 mutants); backend-dir `ruff==0.16.6 format --check` clean (371 files) + `ruff check F821/F811/F822` clean |
| Frontend | `tsc` clean; `eslint` 0 errors / 41 warnings; unit 23 files / 121 tests; `next build` green; Stryker node v24.20.0 `90.77` (118/12/0) ≥75 |
| Contracts | Compose renders contract/ui/synthetic/audit exit 0; lifecycle verifiers OK; simulation `test:static` 41/41 + 82/83/84 `node --check` + real-user `check` + relay `test` green; CF `gate after --new-only` 0 new issues (full 420 pre-existing cycles); index v21 fresh |
| Browser lane (W2) | 15 PASS + 1 SKIP, 248/0 checks; 82 15/15, 83 17/17, 84 13/13; axe 0, Nielsen 4.3/5, perf 12/12; artifacts `tests/simulation/.results/runs/2026-09-11T01-35-10-892Z` |
| Live ensemble (W3) | Stages A–E true; 3-model coding k=-0.102/a=0.493 reconciled; adversarial/debate + 5 probes; artifacts `qa/runs/w3-live-ensemble-2026-09-11T02-32-09Z-97dbb2ce`; no Petals |
| Long-horizon (W4) | 151 turns/engine, 302/302 success; pi 18.7s $0.31 / legacy 21.3s unmetered; telemetry + docs + UI; artifacts `qa/runs/w4-long-horizon-20260911-zai-glm` (`run-both.json` 618e4c8e); CareNav only; no Petals |
| Protection | `testing/required-checks.json` 17 contexts == `docs/promotion/branch-protection/gh-api-body.json` incl `desktop-check`; package prepared, application + CI observation owner-gated |

Caveats (non-blocking, in dossier §7): ROOT-scope ruff notes outside CI scope (42 md fences + 6 F811 pre-readiness5) disclosed; 2 untracked docs excluded from SHA; full-tree 420 cycles + 41 warnings pre-existing; telemetry gaps + small-n labels operational only. Minors F-R5-W2-R1-2, F-R5-W3-R1-2/R1-3/R1-4, F-R5-W4-R1-1/R1-2 + registerPasskey residual ride as follow-ups.



## 2026-09-09 — CI failure-domain independence + required-check contract (W4 ci-enforcement)

Scope: `.github/workflows/ci.yml` redesigned into failure-domain jobs with a
fail-closed `release-gate` aggregator; required-checks manifest
(`testing/required-checks.json`) + contract checker
(`scripts/check_required_checks.py`); read-only CI (`badge-sync.yml` split out,
M-13); repo-wide correctness lint classes blocking; `qa-contract-stack` →
`qa-contract-render` rename with QA contract tests moved to `backend-test`;
container-first `ui-journeys` lane defined (executed in W5) with honest
`not_runnable` handling and SHA-keyed artifacts; `desktop-check` honest status
(M-18 owner decision pending); frontend mutation `related: false` + advisory
wide scope; owner-gated branch-protection package prepared unapplied in
`docs/promotion/branch-protection/`. Suite topology change: new
`tests/test_required_checks.py` (15 tests), new `badge-sync.yml` contract tests
in `tests/test_workflow_contracts.py` (now 14).

| Area | Result |
| --- | --- |
| Contract battery | `check_required_checks.py`, `check_workflow_contracts.py`, `check_ci_governance.py`, `check_test_harness.py`, `check_integrity.py`, `check_qa_capabilities.py`, `public_repo_quality_audit.py --check` — all passed; `security_benchmark.py --fail-on-threshold` — pass, exit 0 |
| Contract test suites | `pytest tests/test_required_checks.py tests/test_workflow_contracts.py tests/test_feature_obligations.py tests/test_public_repo_quality.py tests/test_qa_capabilities.py -q` → 52 passed; QA contract set (now in backend-test) → 69 passed; harness/property/governance/compute CI contract set → 100 passed |
| Workflow YAML | `ci.yml` + `badge-sync.yml` parse clean (yaml.safe_load); 17 jobs parsed, single retained edge `ui-journeys → qa-contract-render`, release-gate needs ≡ 16 required contexts − itself |
| M-06 acceptance (local demonstration) | Injected format violation into `backend/app/core/compute_capacity.py` → `ruff format --check` exit 1 (backend-format red) while `pytest tests/test_data_transformations.py tests/test_workflow_contracts.py` → 35 passed (backend-test green, independent domain); file restored, worktree clean |
| ui-journeys lane | Docker daemon unavailable locally → stack execution NOT run locally (CI/W5 evidence); selection + `not_runnable` recording verified by execution: scope=full → 79 registered, 7 proven selected, 72 explicitly recorded not-runnable; journey ids validated against the scenario registry; compose render (`--profile contract`, `--profile ui`) passed without a daemon |
| Frontend | `npx vitest run` → 108 passed after `stryker.config.json` `related:false` + new `stryker.wide.config.json`; stryker thresholds unchanged (break 75) |

Caveats recorded honestly: the deliberate format-error-red/backend-test-green
proof was demonstrated locally at the command level plus structurally in
`tests/test_required_checks.py`; the same-run GitHub Actions proof lands when
CI next executes on the pushed candidate. Local Docker was not started (no
permission), so `ui-journeys` has no local green run — its CI/W5 evidence is
the release proof.

## 2026-09-08 - Pi Upstream Lockstep Bump 0.84.3→0.85.1 + Release Acceptance (update-and-release-proof wave)

Scope: lockstep pi-ai/pi-agent-core pin 0.84.3 → 0.85.1 across `pi-runtime` and
`labs/pi-replacement` (package.json exact pins, regenerated lockfiles, installed
node_modules, labs adapter manifest); catalog projection regenerated from the 0.85.1
registry; routine-bump diff-proof gate (`scripts/pi_bump_diff_proof.py` + 13 offline
tests in `tests/pi_compat/test_bump_diff_proof.py`); installed-vs-pin provenance test
in `tests/pi_migration/test_version_provenance.py`; AC-6 unpriced-admission proof moved
to `zai/glm-5.3-highspeed` (upstream priced `zai/glm-5.3` in 0.85.1 — intended-upstream,
classified in `docs/build-stream/pi-compat-20260908-0851-diff-proof.json`); UI journeys
W5.4 (effort badge, scenario 10) and W5.5 (effort persistence, scenario 05).
Suite topology change: new `tests/pi_compat/test_bump_diff_proof.py`; scenario 05/10
extended.

| Area | Result |
| --- | --- |
| Diff-proof gate | `python scripts/pi_bump_diff_proof.py proof 0.85.1 --report docs/build-stream/pi-compat-20260908-0851-diff-proof.json` — 36 changed surfaces + 73 registry removals, all classified `intended-upstream`, gate PASSED; `zai/glm-5.3-flash` + `zai/glm-5.3` present in candidate (expect-models) |
| pi-runtime suite | `cd pi-runtime && npm test` passed with `100 pass / 0 fail` against 0.85.1 — AC-1 fallback fixtures byte-identical, inherited wire fixtures unchanged (API diffs are response-side assembly) |
| Conformance + provenance | `pytest tests/pi_compat tests/pi_migration -q` passed with `74 passed` (projection ≡ resolver over all 1,394 records, provenance ≡ pin 0.85.1, pin/lockfile/installed lockstep) |
| Backend pi suites | `pytest tests/pi_production -q` → `475 passed`; `pytest tests/pi_benchmark -q` → `245 passed, 5 skipped` |
| Second surface | `cd labs/pi-replacement && npm install && npm run validate` → `5 pass / 0 fail` on 0.85.1 |
| Frontend | `npx vitest run src/lib/modelCatalog.test.ts src/lib/modelProviders.test.ts` → `24 passed`; `npx tsc --noEmit` clean |
| Governance | `check_test_harness.py`, `check_integrity.py`, `check_qa_capabilities.py` passed; `feature_docs.py --check` passed (86 features); `security_benchmark.py --fail-on-threshold` 100.0 pass; `docker compose --profile contract config --quiet` ok |
| UI container lane | `not_runnable` — Docker daemon unreachable (`unix:///Users/user/.docker/run/docker.sock`); resume: start Docker, then `docker compose -f docker-compose.qa.yml --profile ui up -d` (loopback only) and `node tests/simulation/run.mjs --scenario 10-settings-models,05-chat-interaction`; scenario static checks `npm run test:static` → 17 pass |
| Live acceptance (W7.1–7.3) | `not_runnable` — owner authorization required (AGENTS.md Live LLM and Model Loading Safety; DEC-O6); no live probe, model load, or benchmark spend was performed |
| Residual risks | live reconciliation evidence (receipt → captured body → served identity) pending owner-authorized run; scenarios authored but not yet executed in a container |

Scope: pi-ai registry becomes the capability authority (worker resolver +
generated catalog projection); routine-bump conformance machinery; deterministic
wire fixtures. Suite topology change: new `pi-runtime/test/capability-inheritance.test.mjs`
(33 tests) and `tests/pi_compat/test_catalog_conformance.py` (5 tests); two
defect-pinning assertions in `pi-runtime/test/provider-params.test.mjs` flipped
with in-file evidence (codex xhigh clamp, zai missing reasoning_effort).

| Area | Result |
| --- | --- |
| pi-runtime suite | `cd pi-runtime && npm test` passed with `87 passed / 0 fail` (54 baseline + 33 conformance) |
| Catalog conformance | `pytest tests/pi_compat -q` passed with `5 passed` (round-trip byte identity, provenance ≡ pin, overlay preservation, registry parity, authority equivalence over 1,312 models) |
| Backend pi suites | `pytest tests/pi_production tests/pi_migration/test_version_provenance.py tests/test_model_source.py tests/test_pi_replacement_candidate.py -q` passed (475 + 66 + provenance) |
| Pi benchmark | `pytest tests/pi_benchmark -q` passed with `245 passed, 5 skipped` |
| Governance | `check_test_harness.py`, `check_integrity.py` passed; `security_benchmark.py --fail-on-threshold` 100.0 pass |
| Residual risks | W3 carry-through (settings API/frontend/pricing preflight), W5 observability/UI scenarios, and W6 (0.85.1 bump) are later waves; UI-suite effort-journey coverage lands with W5.4–5.5 |

## 2026-09-04 - Empirical Three-Model Research Spine Baseline

Scope: end-to-end live validation of Istara's Research Spine and Scenario 76 long-horizon trajectory using three frontier models: Luna (`gpt-5.6-luna`), Qwen 3.7 Max (`qwen3.7-max-2026-06-08`), and GLM 5.2 (`glm-5.2`). Ingested canonical CareNav transcript, performed independent qualitative coding, Fleiss' Kappa / Krippendorff's Alpha reliability evaluation, human reconciliation, atomic DAG promotion, task execution, steering injection, Done approval gate, and Minto SCQA report synthesis.

| Area | Result |
| --- | --- |
| Research Spine multi-model coding | 14 code applications generated across 3 distinct frontier LLMs with cryptographic route receipts |
| Reliability evaluation | Nominal Fleiss' $\kappa = -0.125$, Krippendorff's $\alpha = 0.488$; correctly triggered fail-closed `needs_reconciliation` gate |
| Human reconciliation gate | 26 durable reconciliation decisions recorded; un-reconciled applications verified to block task Done approval with HTTP 409 |
| Atomic Research DAG | 3 Nuggets, 2 Facts, 1 Insight, 1 Recommendation, 64 evidence edges constructed |
| Strategic report synthesis | Generated Barbara Minto SCQA executive summary with 100% MECE categories and full backward traceability |
| Tool execution telemetry | OpenTelemetry GenAI-compliant tool call spans with model attribution and steering queue event logging |
| Detailed scientific audit | `docs/scientific_audit/three-model-research-spine-audit.md` |

## 2026-05-20 - Testing Suite Governance Refresh

Scope: deterministic testing-suite alignment after project-isolation hardening,
including relay CI coverage, simulation/real-user static checks, marathon
config integrity, and admin-many-project simulation project selection.

| Area | Result |
| --- | --- |
| Harness governance | `python scripts/check_test_harness.py` passed |
| CI governance | `python scripts/check_ci_governance.py` passed |
| Marathon integrity and project-scope smoke | `pytest tests/test_harness_project_scope_contracts.py tests/test_marathon_config_integrity.py -q` passed with `7 passed` |
| Relay tests | `npm --prefix relay test` passed with `17 passed` |
| Simulation static checks | `npm --prefix tests/simulation run test:static` passed with `99` files syntax-checked and `4` helper tests passed |
| Real-user benchmark syntax | `npm --prefix tests/real_user_benchmark run check` passed |
| Feature docs | `python scripts/feature_docs.py --seed-missing --generate-site --check` passed for `86` features |
| Compass Forge after-gate | `compass-forge gate after CF-SPEC-115 --report-format json` returned `status: warn`, `failures: []`, `unexpected_large_files: []`, and `new_issues: []` |
| Compass Forge test suggestions | `compass-forge suggest-tests "testing suite project_id simulation marathon relay real-user"` returned no `node_modules` or `.results` paths |

Residual notes:
- This checkpoint deliberately did not start backend/frontend servers, run live
  simulation scenarios, run marathon cycles, or load/probe live LLM models.
- Compass Forge `CF-SPEC-115` clarified and planned cleanly, but task creation
  hung before producing linked tasks; implementation evidence stayed attached
  to the explicit eight-item scope instead of a generated task graph.

## 2026-05-08 - Release Security Hardening Baseline

Scope: auth/security release hardening, LLM-provider endpoint safety, upload
quarantine, A2A replay/rate controls, webhook replay protection, MCP endpoint
validation, backup exclusions, ReasoningBank untrusted-memory wrappers, and log
redaction.

| Area | Result |
| --- | --- |
| Backend pytest | `762 passed, 1 skipped` |
| Frontend typecheck | `npx tsc --noEmit` passed |
| Frontend lint | `npm run lint` passed |
| Frontend build | `npm run build` passed |
| Frontend unit tests | Passed |
| Relay tests | `17 passed` |
| Security benchmark | `28/28`, score `100%`, threshold gate passed |
| Release readiness | `python scripts/security_release_readiness.py` passed |
| Compass gate after | Passed |

Notes:
- No private LLM endpoint, token, connection string, or user data was committed.
- The security assessment for this baseline is
  `security/ISTARA_SECURITY_ASSESSMENT_2026-05-08.md`.

## 2026-05-08 - Stabilization and Full Regression Baseline

Scope: nine-item stabilization pass after LLM serving, thinking controls,
provider-aware schemas, ReAct skill routing, monolith decomposition, eval
harness hardening, RBAC/onboarding, resource-manager, data-integrity, and
migration work.

| Area | Result |
| --- | --- |
| Backend pytest | `726 passed, 1 skipped in 391.23s` |
| Targeted backend tests | `59 passed` for settings, surveys, interfaces, research reports, and prompt-RAG transformations |
| Frontend typecheck | `npx tsc --noEmit` passed |
| Frontend lint | `npm run lint` passed |
| Frontend build | `npm run build` passed |
| Frontend unit tests | `2 files, 8 tests passed` |
| Relay tests | `17 passed` |
| Integrity/harness governance | `scripts/check_integrity.py` and `scripts/check_test_harness.py` passed |
| Security benchmark | Passed, score `93.75`, with maturity warnings for `SUPPLY-001`, `TEST-001`, and `OPS-001` |
| Orchestration benchmark | `4/4` benchmark checks passed |
| Istara eval suite | `11/11` passed using the gitignored live profile and fixed test model id |
| Live LLM integration | Single configured live profile passed; no broad multi-model loading path was used |
| Non-live simulation matrix | `75` scenarios, `1073/1073` checks, `0` failures |
| Scenario 20 | Fixed-seed 5-skill run passed `29/29`; selected skills were affinity mapping, A/B test analysis, competitive analysis, survey AI detection, and journey mapping |
| Focused simulation reruns | Scenarios `19`, `22`, `47`, `48`, `55`, `59`, `69`, and `73` passed after targeted fixes |
| Migrations | Existing DB and fresh temp DB both reached `015_permission_requests (head)` |
| Compass refresh | Snapshot `104` created |
| Compass gate after | Passed; no route drift, type drift, contract drift, import cycles, layer violations, security issues, or complexity issues |

Residual notes:
- Scenario 20 was behaviorally green but slow; the 5-skill live run took about
  21 minutes 45 seconds. Future comparisons should preserve per-skill timing so
  slow paths are easy to diagnose.
- The eval suite reported embedding retrieval unavailable and fell back to
  keyword retrieval while still passing thresholds. Keep that visible in future
  baseline comparisons.
- Local data warnings should continue through the admin-visible
  integrity/quarantine workflow. Do not silently delete runtime artifacts.

## Artifact Logging Rules

- Eval runner artifacts: `tests/evals/.results/<run-id>/manifest.json`,
  `summary.json`, `results.jsonl`, and `report.md`.
- Simulation artifacts: `tests/simulation/.results/<run-id>/` with scenario
  reports, screenshots, and browser traces when enabled.
- Security artifacts: `security/security_scorecard.json` locally or the
  `istara-security-scorecard` CI artifact.
- Benchmark artifacts: keep JSON/report outputs under ignored result roots
  unless a compact release summary is added here.
- Each curated entry should include date, scope, git SHA when available,
  dirty/clean state, commands or artifact paths, pass/fail counts, and residual
  risks.
