# Istara Test History

This file is the curated, tracked verification history. Raw eval outputs,
simulation reports, screenshots, local database snapshots, and security
scorecards remain in gitignored artifact directories. Add a compact entry here
when a run becomes a release baseline or materially changes confidence in the
system.

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
