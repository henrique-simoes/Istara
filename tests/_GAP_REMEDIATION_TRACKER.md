# Istara Gap Remediation Tracker

**Created:** 2026-04-13
**Purpose:** Track all system gaps, their remediation status, and agent coordination for fixes.
**Relationship to _CHANGE_LOG.md:** This file tracks *what* needs fixing and *why*. The `_CHANGE_LOG.md` tracks *exactly what code changed* for each fix. This file references change log entries by gap number.

---

## HOW TO USE THIS FILE (Agent Instructions)

1. **Read the current gap** you're working on. Check its status.
2. **If PENDING:** Execute the fix plan. Follow the steps exactly.
3. **If IN PROGRESS:** Continue from where the last agent left off. Update the status log.
4. **If BLOCKED:** Add a blocker note explaining why. Do NOT skip to the next gap.
5. **When COMPLETE:**
   - Update status to `✅ COMPLETE`
   - Add evidence (test output, what changed)
   - Reference the `_CHANGE_LOG.md` entries
   - Run `python scripts/check_integrity.py` — must pass
   - Run full test suite — must pass
   - Move to the NEXT gap in sequence
6. **NEVER skip a gap.** Sequential order is mandatory. Gaps 1-3 are bugs (HIGH/MEDIUM), 4-10 are architectural/testing debt.
7. **Compass compliance:** Before each change, read relevant Compass sections. After each fix, verify integrity.

---

## EXECUTION RULES

- **Sequential:** Gap 1 → Gap 2 → ... → Gap 10. No parallel work.
- **Block on failure:** If a fix doesn't pass tests, stay on the gap. Debug, fix, re-test.
- **Evidence required:** Each gap completion must include passing test output and integrity check.
- **No regressions:** Full test suite must pass after every gap fix.

---

## GAP INVENTORY

| # | Gap | Severity | Status | Tests Added | Files Changed | Change Log Ref |
|---|-----|----------|--------|-------------|---------------|----------------|
| 1 | AutoresearchEngine.get_current_experiment missing | HIGH | ✅ COMPLETE | 1 | 2 | Entry G1.1, G1.2 |
| 2 | AutoresearchEngine.get_leaderboard unawaited coroutine | HIGH | ✅ COMPLETE | 1 | 2 | Entry G2.1, G2.2 |
| 3 | FastMCP(description=...) constructor TypeError | MEDIUM | ✅ COMPLETE | 1 | 2 | Entry G3.1 |
| 4 | API response inconsistency (mixed wrapper/raw) | MEDIUM | ⏳ PENDING | 0 | 0 | — |
| 5 | No service layer — routes query DB directly | LOW | ⏳ PENDING | 0 | 0 | — |
| 6 | No route-level business logic tests | MEDIUM | ⏳ PENDING | 0 | 0 | — |
| 7 | No data transformation tests (RAG, summarization, Prompt RAG) | MEDIUM | ⏳ PENDING | 0 | 0 | — |
| 8 | No error handling path tests | MEDIUM | ⏳ PENDING | 0 | 0 | — |
| 9 | No WebSocket flow tests | LOW | ⏳ PENDING | 0 | 0 | — |
| 10 | E2E coverage only ~30% | MEDIUM | ⏳ PENDING | 0 | 0 | — |

**Baseline:** 260 passed, 6 xfailed, 0 unexpected failures (as of 2026-04-13)
**Current:** 266 passed, 0 xfailed, 0 unexpected failures (Gaps 1-3 fixed)
**Target:** 380+ passed, 0 xfailed, 0 unexpected failures

---

## GAP STATUS LOGS

### GAP 1: AutoresearchEngine.get_current_experiment missing

**Severity:** HIGH
**Status:** ✅ COMPLETE
**Started:** 2026-04-13
**Completed:** 2026-04-13
**Agent:** Qwen Code

**Problem:**
`GET /api/autoresearch/status` calls `engine.get_current_experiment()` but the method doesn't exist.

**Fix Applied:**
1. Added `get_current_experiment()` method to `AutoresearchEngine` (returns `self._current_experiment`)
2. Fixed `engine.is_running()` → `engine.is_running` (property, not method)
3. Fixed `await engine.get_experiments()` in list_experiments endpoint
4. Removed xfail markers, fixed integration test assertions for empty test DB

**Evidence of completion:**
- `test_autoresearch_status_returns_response` PASSED (was xfailed)
- `test_autoresearch_leaderboard_returns_response` PASSED (was xfailed)
- `test_agent_work_cycle_integration` PASSED (was xfailed)
- Full suite: 263 passed, 2 xfailed, 0 unexpected failures
- Integrity check: "All tracked architecture docs are in sync"

**Files changed:**
- `backend/app/core/autoresearch_engine.py` — added `get_current_experiment()` method
- `backend/app/api/routes/autoresearch.py` — fixed `is_running()` → `is_running`, added `await` to `get_experiments()` and `get_leaderboard()`
- `tests/test_autoresearch.py` — removed xfail markers
- `tests/test_integration_agent_work_cycle.py` — fixed assertions for empty test DB

---

### GAP 2: AutoresearchEngine.get_leaderboard returns unawaited coroutine

**Severity:** HIGH
**Status:** ✅ COMPLETE (fixed alongside Gap 1 — same file)
**Started:** 2026-04-13
**Completed:** 2026-04-13
**Agent:** Qwen Code

**Problem:**
`GET /api/autoresearch/leaderboard` calls `engine.get_leaderboard()` without `await`.

**Fix Applied:**
Added `await` to `engine.get_leaderboard()` call in autoresearch.py line 217.
Also fixed same bug in `get_experiments()` call (line 113).

**Evidence of completion:** (see Gap 1 above — same test results)

**Files changed:** `backend/app/api/routes/autoresearch.py`

---

### GAP 3: FastMCP(description=...) constructor TypeError

**Severity:** MEDIUM
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Problem:**
MCP server route passes `description` to `FastMCP()` constructor but the installed version doesn't accept this parameter.

**Error:**
```
TypeError: FastMCP() got unexpected keyword argument(s): 'description'
```

**Affected files:**
- `backend/app/api/routes/mcp.py` — FastMCP instantiation
- `tests/test_mcp.py` — has xfail marker to remove

**Fix Plan:**
1. Read `backend/app/api/routes/mcp.py` to find the FastMCP instantiation
2. Run `pip show fastmcp` to check installed version and supported params
3. Remove `description` param or use correct param name for the installed version
4. Remove xfail from `tests/test_mcp.py::test_mcp_server_status_returns_response`
5. Run: `python -m pytest tests/test_mcp.py -v` — must pass
6. Run full suite — no regressions
7. Update `_CHANGE_LOG.md`
8. Run: `python scripts/check_integrity.py`

**Evidence of completion:**
- [ ] Test passes without xfail
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

### GAP 4: API response inconsistency

**Severity:** MEDIUM
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Fix Plan:** (See full plan in audit document)

**Evidence of completion:**
- [ ] All endpoints use consistent response format
- [ ] Frontend still works
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

### GAP 5: No service layer

**Severity:** LOW (architectural debt)
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Fix Plan:** (See full plan in audit document)

**Evidence of completion:**
- [ ] Service modules created for high-frequency models
- [ ] Routes updated to use services
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

### GAP 6: No route-level business logic tests

**Severity:** MEDIUM
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Fix Plan:** (See full plan in audit document)

**Evidence of completion:**
- [ ] 30+ business logic tests created
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

### GAP 7: No data transformation tests

**Severity:** MEDIUM
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Fix Plan:** (See full plan in audit document)

**Evidence of completion:**
- [ ] RAG, summarization, Prompt RAG, budget tests created
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

### GAP 8: No error handling path tests

**Severity:** MEDIUM
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Fix Plan:** (See full plan in audit document)

**Evidence of completion:**
- [ ] 10+ error handling tests created
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

### GAP 9: No WebSocket flow tests

**Severity:** LOW
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Fix Plan:** (See full plan in audit document)

**Evidence of completion:**
- [ ] 8+ WebSocket tests created
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

### GAP 10: E2E coverage only ~30%

**Severity:** MEDIUM
**Status:** ⏳ PENDING
**Started:** —
**Completed:** —
**Agent:** —

**Fix Plan:** (See full plan in audit document)

**Evidence of completion:**
- [ ] 12 new E2E phases created
- [ ] E2E suite passes against live server
- [ ] Full suite passes
- [ ] Integrity check passes
- [ ] Change log updated

---

## COMPASS REFERENCE

After all gaps are closed:
1. `python scripts/update_agent_md.py` — regenerate Compass docs
2. `python scripts/check_integrity.py` — verify integrity + Tech.md freshness
3. Commit with clean message
4. Push to main + staging
5. Verify CI passes

---

## AGENT NOTES

*Agent coordination notes go here. Leave status updates for other agents.*

---

### 2026-04-13 — Gap 1 & 2 Complete
- Added `get_current_experiment()` method to AutoresearchEngine
- Fixed `is_running()` → `is_running` (property access)
- Added `await` to `get_experiments()` and `get_leaderboard()` calls
- Removed 3 xfail markers, fixed integration test assertions
- **Result:** 263 passed, 2 xfailed, 0 unexpected failures (was 260 passed, 6 xfailed)
- **Next gap:** Gap 3 — FastMCP constructor TypeError
