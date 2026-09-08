# Istara Test History

This file is the curated, tracked verification history. Raw eval outputs,
simulation reports, screenshots, local database snapshots, and security
scorecards remain in gitignored artifact directories. Add a compact entry here
when a run becomes a release baseline or materially changes confidence in the
system.

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
