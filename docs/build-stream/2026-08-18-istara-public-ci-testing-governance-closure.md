# Build Stream — public testing CI governance closure

<!-- STATUS BLOCK -->
```yaml
item: istara-public-ci-testing-governance-closure
branch: conductor/istara-public-ci-testing-20260818
cf: { spec: CF-SPEC-57, tasks: [CF-761, CF-762, CF-763, CF-764, CF-765] }
phase: "S2–S4 — close final feature-obligation and change-governance gaps"
stage: S2-execute
status: in-progress
blocked_on: "Conductor implementation/review convergence; no ship actions authorized"
last: { agent: gpt-5.3-codex-spark, at: 2026-08-18T11:48:00Z, ledger: L-1 }
next_action: "Forward CF-761 impact findings to the remediation owner and continue with implementation tasks."
```
<!-- /STATUS BLOCK -->

## Scope

Close only the final deterministic governance failures discovered after the public provider-agnostic testing run: classify `qa/Dockerfile` and `backend/app/api/routes/documents.py` in `testing/feature_coverage.yml`, and keep `scripts/check_test_harness.py` out of the governed-evolution trigger set while preserving its harness/test obligations. Do not touch unrelated target-branch work, private artifacts, providers, Docker services, `multivac`, push, PR, merge, promotion, or deployment.

## Findings register

| ID | Sev | Where | Finding | Status |
|---|---|---|---|---|
| G-1 | Blocker | `testing/feature_coverage.yml` | `qa/Dockerfile` is not owned by the executable feature-obligation registry. | open |
| G-2 | Blocker | `testing/feature_coverage.yml` | `backend/app/api/routes/documents.py` is not owned by the executable feature-obligation registry. | open |
| G-3 | Major | `scripts/check_change_obligations.py` | Test-harness governance is incorrectly included in governed-evolution triggers, causing a false dedicated-evolution-test failure. | open |

## Ledger <!-- append-only -->

### L-0 | 2026-08-18T11:25:00Z | S0-frame | pi | planner | S0
Did: Created CF-SPEC-57, clarified the scope boundary, generated its plan/tasks, mapped impacted relationships for the registry and classifier, and prepared a fresh remediation cast without mutating the active legacy cast.
Result: The remediation is limited to two registry ownership entries and one classifier trigger correction; all public testing, Research Spine, security, and fail-closed contracts remain in scope for verification.
Verified: `compass-forge spec clarify CF-SPEC-57`; `compass-forge spec plan CF-SPEC-57`; `compass-forge spec tasks CF-SPEC-57`; `compass-forge intelligence impact --path testing/feature_coverage.yml`; `compass-forge intelligence why testing/feature_coverage.yml`; `python scripts/check_feature_obligations.py --base origin/testing --head HEAD` (identified exactly two unknown paths); `python scripts/check_change_obligations.py --base origin/testing --head HEAD` (identified the false governed-evolution trigger).
Next: Conductor implementer, then independent code reviewer.

### L-1 | 2026-08-18T11:48:00Z | S2-execute | gpt-5.3-codex-spark | executor | implementer <!-- bsc-ledger:CF-761 -->
Did: Inspected impact for `qa/Dockerfile`, `backend/app/api/routes/documents.py`, and `scripts/check_test_harness.py` via `intelligence impact` + `intelligence why` for CF-761.
Result: Confirmed the three impact findings needed for remediation: `qa/Dockerfile` lacks feature-obligation ownership, `backend/app/api/routes/documents.py` maps to document-ingestion feature surface, and `scripts/check_test_harness.py` is harness-governance-only rather than governed-evolution behavior.
Verified: `compass-forge intelligence impact --path qa/Dockerfile --request "Close final public testing CI governance gaps: classify qa/Dockerfile and backend/app/api/routes/documents.py in the feature-obligation registry, and ensure the change-obligation classifier does not misclassify the test-harness governance script as governed-evolution behavior. Preserve fail-closed ownership, Research Spine synthetic provisional gates, and all existing security and test obligations. Implement and verify only on the public testing feature branch worktree; do not push, merge, deploy, or mutate multivac."`; `compass-forge intelligence why qa/Dockerfile`; `compass-forge intelligence impact --path backend/app/api/routes/documents.py --request "Close final public testing CI governance gaps: classify qa/Dockerfile and backend/app/api/routes/documents.py in the feature-obligation registry, and ensure the change-obligation classifier does not misclassify the test-harness governance script as governed-evolution behavior. Preserve fail-closed ownership, Research Spine synthetic provisional gates, and all existing security and test obligations. Implement and verify only on the public testing feature branch worktree; do not push, merge, deploy, or mutate multivac."`; `compass-forge intelligence why backend/app/api/routes/documents.py`; `compass-forge intelligence impact --path scripts/check_test_harness.py --request "Close final public testing CI governance gaps: classify qa/Dockerfile and backend/app/api/routes/documents.py in the feature-obligation registry, and ensure the change-obligation classifier does not misclassify the test-harness governance script as governed-evolution behavior. Preserve fail-closed ownership, Research Spine synthetic provisional gates, and all existing security and test obligations. Implement and verify only on the public testing feature branch worktree; do not push, merge, deploy, or mutate multivac."`; `compass-forge intelligence why scripts/check_test_harness.py`.
Next: Open CF-762 and CF-763 with the impact findings; stage in-progress handoff.

