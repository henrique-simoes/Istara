# System Audit & Integration Check

## Branch
`feat/system-audit-and-integration-check` (branched from `staging`)

## Context
Security branch `feat/security-remediation-2fa-passkey` already pushed (contains 2FA, WebAuthn, field encryption, headers). This audit branch must verify integration and find dead/broken/unintegrated code without conflicting with security work.

## Executor Verdict (Evaluator)

Following the Evaluator verdict for the audit plan, the Executor must:
1. Run evidence-first audit for dead/broken/unintegrated code
2. Check cross-branch compatibility with `feat/security-remediation-2fa-passkey`
3. Fix proven issues only (no speculative optimization)

## Active Issues

- **`test_business_logic.py::test_task_create_and_list` fails with HTTP 500**: Test expects status in (200, 201, 404, 422) but gets 500. Needs root cause investigation.
- **Naive import graph too noisy**: AST-based import scan flagged all route files as "orphans" because they're dynamically registered in `main.py`. Audit pivoted to lint/type/wiring checks first.
- **`ruff` unavailable**: Cannot run `ruff check` for lint gate; relying on `pytest` and `tsc --noEmit` instead.

## Audit Surface (Do NOT modify security branch files in conflicting ways)

Overlapping files with security branch:
- `auth.py`, `user.py`, `LoginScreen.tsx`, `authStore.ts`, `types.ts`, `api.ts`
- `field_encryption.py`, `main.py`

## Test Layers

- Layer 1 = pytest
- Layer 2 = `e2e_test.py`
- Layer 3 = Playwright simulation scenarios

## Integrity Checks Required Before Shipping

```bash
python scripts/update_agent_md.py
python scripts/check_integrity.py
```

## Pre-push Hook

Rewrites authorship to `henrique-simoes <simoeshz@gmail.com>` and strips `Co-authored-by` trailers.

## Status

- [x] HTTP 500 root cause identified: SQLite AsyncAdaptedQueuePool connections outliving pytest-asyncio event loops
- [x] Fix applied: `NullPool` for SQLite + `engine.dispose()` autouse fixture
- [x] All 354 tests pass (353 unit + 1 integration)
- [x] `scripts/check_integrity.py` passes
- [x] Compass docs resynced (`AGENT.md`, `AGENT_ENTRYPOINT.md`, `COMPLETE_SYSTEM.md`)
- [x] `TESTING.md` updated with audit entry
- [x] Pushed to `origin/feat/system-audit-and-integration-check`

## Notes

Frontend `tsc --noEmit` passes cleanly.
Backend import scan: 0 broken imports across all app modules.

---

completion::: [2026-04-21 21:35:00]

Executor Phase 3 complete. Branch `feat/system-audit-and-integration-check` pushed to origin.
- Proven fix: `NullPool` + `engine.dispose()` resolves SQLite locking across pytest-asyncio tests.
- All 354 tests pass (353 unit + 1 integration).
- Integrity check passes.
- Compass docs regenerated and in sync.
- No conflicts with `feat/security-remediation-2fa-passkey`.
- Awaiting Phase 4 Review.
