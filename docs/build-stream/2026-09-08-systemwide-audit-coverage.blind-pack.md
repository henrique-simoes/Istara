# Blind Review Pack — Systemwide Audit Coverage fix pass

**Role:** you are an INDEPENDENT reviewer. You have NOT seen the implementer's
claims, ledger, or evidence rows. Do not open the lifecycle file
(`2026-09-08-systemwide-audit-coverage.md`), CF task evidence, or chat history
until your measurement sheet is written and frozen.

**Scope under review:** the working tree's uncommitted changes to exactly these
files (other dirty files in the worktree belong to other agents — ignore them):
- `backend/app/api/routes/files.py`
- `backend/app/api/routes/chat.py`
- `tests/test_files.py`
- `tests/test_websocket.py`
- `tests/test_project_scope_contracts.py`
- `frontend/src/lib/navigation.test.ts`

## Open questions (answer by running, not by reading claims)

1. How many tests pass/fail in `tests/test_files.py`? Run it.
2. How many tests pass/fail in `tests/test_websocket.py`? Run it.
3. How many tests pass/fail in `tests/test_project_scope_contracts.py` (+ harness + agent scope files)? Run all three.
4. How many tests pass/fail in `tests/test_pi_replacement_candidate.py`? Run it.
5. How many tests pass/fail in `tests/test_chat.py`? Run it.
6. What does `python scripts/security_benchmark.py --fail-on-threshold` report (status/counts)?
7. Does `backend/app/api/routes/files.py` refuse quarantined documents on BOTH
   the serve path and the content path? Grep for `QUARANTINED` and read the
   surrounding control flow. What HTTP status is returned?
8. Does `backend/app/api/routes/chat.py` queue a `content`-type display event
   inside its tool executors? Grep for `result_display` / `"type": "content"`.
   In how many tool-executor copies? Does any copy append the display directly
   to `all_text_parts` (a duplication hazard)?
9. Do the new tests `test_quarantined_files_are_not_servable`,
   `test_file_serve_denies_stranger_and_anonymous`,
   `test_ws_rejects_missing_and_invalid_token`,
   `test_ws_denies_nonmember_project_with_4003`,
   `test_relay_rejects_unauthenticated_and_accepts_network_token` exist, and
   does each pass in isolation?
10. Does `ruff check` on the six files report anything attributable to the
    uncommitted hunks (compare `git stash` / `git stash pop`, or reason from
    `git diff` line numbers)?
11. `git diff --check`: clean or not?
12. For each source-text assertion in `tests/test_project_scope_contracts.py`
    that mentions `get_active_project_or_404`, `source_ids`, `project_id`,
    or the kanban advisory copy: does the asserted literal match the current
    implementation file? List any mismatch.
13. Adversarial: try to REFUTE these statements with a targeted run or grep:
    a. "quarantined files are served to viewers"
    b. "tool-result displays are absent from persisted transcripts"
    c. "a stranger can fetch another project's file via serve"
    d. "unauthenticated /ws/relay connects successfully"

## Procedure

1. Run every command yourself in `<REPO_ROOT>`.
   Do NOT start servers, touch the network, or load models. pytest, vitest
   (frontend navigation test only), ruff, git, and grep are allowed.
2. Write your answers to `docs/build-stream/2026-09-08-systemwide-audit-coverage.measurement.md`
   as a numbered sheet: `M-1 … M-13`, each with the exact command and the
   observed result. No verdicts about the implementer — only observations.
3. When the sheet is complete, append the line `FROZEN: <ISO time>` and stop.
   Only then may implementation artifacts be opened for comparison.
