# Istara Feature Integration Audit & Execution Plan

**Date:** 2026-04-13
**Status:** Phase A-C COMPLETE, Phase D-E remaining

## EXECUTION STATUS

| Phase | Planned | Done | Remaining |
|-------|---------|------|-----------|
| A: Critical Fixes | 2 tasks | 2 tasks | 0 |
| B: Per-Menu Tests | 29 files, ~86 tests | 29 files, 86 tests | 0 |
| C: Integration Tests | 4 files, ~12 tests | 4 files, 12 tests | 0 |
| D: E2E Expansion | ~30 tests | 0 | ~30 tests |
| E: Compass | Regenerate + verify | 0 | Full regeneration |

## TEST RESULTS
- **260 passed, 6 xfailed, 0 unexpected failures**
- 6 xfail: 3 known backend bugs (autoresearch methods, FastMCP constructor)

## COMPLETED TEST FILES
Phase B (29 files): chat, findings, projects, tasks, documents, files, sessions,
skills, agents, memory, context DAG, UX Laws, interfaces, loops, channels, surveys,
MCP, LLM servers, settings, backup, meta-agent, compute, autoresearch, notifications,
codebooks, code apps, codebook versions, connections, webauthn

Phase C (4 files): agent_work_cycle, chat_flow, interview, integration

## REMAINING
Phase D: E2E expansion (extend e2e_test.py phases to cover all menus)
Phase E: Compass regeneration (update_agent_md.py + check_integrity.py)

## 3 BACKEND BUGS FLAGGED
1. `AutoresearchEngine.get_current_experiment` — AttributeError: method missing
2. `AutoresearchEngine.get_leaderboard` — ValueError: unawaited coroutine
3. `FastMCP(description=...)` — TypeError: unexpected keyword argument
