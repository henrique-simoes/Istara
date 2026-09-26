# Build Stream — public testing CI governance closure

<!-- STATUS BLOCK -->
```yaml
item: istara-public-ci-testing-governance-closure
branch: conductor/istara-public-ci-testing-20260818
# not addressable here: the Compass Forge database that held these records was replaced; kept as history. was> cf: { spec: CF-SPEC-57, tasks: [CF-761, CF-762, CF-763, CF-764, CF-765] }
phase: "S2–S4 — close final feature-obligation and change-governance gaps"
stage: closed
status: closed-superseded
blocked_on: null
last: { agent: claude-opus-5-5, at: 2026-09-24T03:39:14Z, ledger: L-2 }
next_action: "Closed 2026-09-12 (post-promotion closeout): superseded: governance gaps closed across promotion runs 1-3 (obligations 486->0; ledger L-1..L-80)."
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

### L-2 | 2026-09-24T03:39:14Z | S5-ship | claude-opus-5-5 | executor | —
Did: record correction found by Ainulindalë's truth reconciler. Its Compass Forge references are not addressable: that database was replaced (the current one starts at CF-SPEC-1, 2026-08-24).
Result: the Status Block says what is true today.
Verified: `git merge-base --is-ancestor 2f106b57 origin/main` (the squash of testing); `git diff --stat 2f106b57 9620e5d8` empty; `compass-forge spec show` for each named spec.
Next: as the block says.
