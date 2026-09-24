# Build Stream — minimal public QA governance correction

<!-- STATUS BLOCK -->
```yaml
item: istara-qa-governance-minimal-20260818
branch: conductor/istara-public-ci-testing-20260818
# not addressable here: the Compass Forge database that held these records was replaced; kept as history. was> cf: { spec: CF-SPEC-57, tasks: [ISTARA-QA-GOV-MIN-IMPL, ISTARA-QA-GOV-MIN-REVIEW] }
phase: "S2–S4 — minimal deterministic governance correction"
stage: closed
status: closed-superseded
blocked_on: null
last: { agent: claude-opus-5-5, at: 2026-09-24T03:39:14Z, ledger: L-2 }
next_action: "Closed 2026-09-12 (post-promotion closeout): superseded: minimal governance correction merged into the public CI/testing train (CI run 34637179724)."
```
<!-- /STATUS BLOCK -->

## Scope

Only update `testing/feature_coverage.yml` and `scripts/check_change_obligations.py` to close the three known deterministic failures. No other source, documentation, provider, Docker, SSH, or deployment action is authorized in this run.

## Ledger <!-- append-only -->

### L-0 | 2026-08-18T12:00:00Z | S0-frame | pi | planner | S0
Did: Created one implementation task and one dependent review task in local Compass Forge state and prepared a fresh bounded cast.
Result: The implementation is limited to `qa/Dockerfile` ownership, `backend/app/api/routes/documents.py` ownership, and removal of the false governed-evolution trigger for `scripts/check_test_harness.py`.
Verified: `compass-forge task import` (2 tasks, 1 blocking edge); cast inspection confirmed Codex Spark implementer, Pi Luna reviewer, DeepSeek fixer, 600-second worker timeout, zero retries, and `ship.auto_pr=false`.
Next: Run passive preflight, then dispatch the implementer once.

### L-1 | 2026-08-18T11:59:09Z | S2-execute | gpt-5.3-codex-spark | executor | istara-testing-remote-qa-20260817-implementer <!-- bsc-ledger:ISTARA-QA-GOV-MIN-IMPL -->
Did: istara-testing-remote-qa-20260817-implementer stage on task ISTARA-QA-GOV-MIN-IMPL (harness fallback entry; the model did not append one).
Result: task ISTARA-QA-GOV-MIN-IMPL finished; worktree head 36ea8f0c.
Verified: see Compass Forge evidence rows on ISTARA-QA-GOV-MIN-IMPL (command + self_report + stage_attribution).
Next: conductor advances the pipeline on evidence.

### L-2 | 2026-09-24T03:39:14Z | S5-ship | claude-opus-5-5 | executor | —
Did: record correction found by Ainulindalë's truth reconciler. Its Compass Forge references are not addressable: that database was replaced (the current one starts at CF-SPEC-1, 2026-08-24).
Result: the Status Block says what is true today.
Verified: `git merge-base --is-ancestor 2f106b57 origin/main` (the squash of testing); `git diff --stat 2f106b57 9620e5d8` empty; `compass-forge spec show` for each named spec.
Next: as the block says.
