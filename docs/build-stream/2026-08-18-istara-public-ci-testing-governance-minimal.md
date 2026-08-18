# Build Stream — minimal public QA governance correction

<!-- STATUS BLOCK -->
```yaml
item: istara-qa-governance-minimal-20260818
branch: conductor/istara-public-ci-testing-20260818
cf: { spec: CF-SPEC-57, tasks: [ISTARA-QA-GOV-MIN-IMPL, ISTARA-QA-GOV-MIN-REVIEW] }
phase: "S2–S4 — minimal deterministic governance correction"
stage: S2-execute
status: in-progress
blocked_on: "Bounded Conductor implementation and independent review"
last: { agent: pi, at: 2026-08-18T12:00:00Z, ledger: L-0 }
next_action: "Run the implementer once, then report before review."
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
