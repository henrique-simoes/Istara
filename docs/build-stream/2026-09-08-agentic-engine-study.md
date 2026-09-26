# Build Stream — Agentic Engine Deep Study (read-only, no behavior change)

<!-- STATUS BLOCK -->
```yaml
item: agentic-engine-study
branch: main   # testing was promoted to main by squash merge (PR #34, 2f106b57), so its commits are not ancestors of main
phase: "Study + teaching page (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: claude-opus-5-5, at: 2026-09-24T03:39:14Z, ledger: L-1 }
next_action: "Owner picks long-horizon proposals from Phase 10 of the page; no code changes pending."
```
<!-- /STATUS BLOCK -->

## Objective
Understand the Istara agentic engine end to end (ReAct core, dispatcher,
Pi/legacy planes, tools, secrets, budgets, telemetry) and explain why turns
feel short; propose longer-horizon upgrades without breaking philosophy.
No behavior changes in this initiative.

## Append-Only Ledger
- **L-001**: Fanned out 2 explore lenses (ReAct core; Pi vs legacy) + verified
  budget constants and line citations directly (legacy.py:271/357/458/488,
  chat.py:84/90/419/690, supervisor.py:75-79, types.py:19, session.mjs
  effectiveMaxTurns/budget frames, config.py:400/427).
- **L-002**: Wrote `docs/architecture/agentic-engine-deep-dive.html` (12 phases,
  self-contained, no external deps). Verified: HTML parses, all cited lines
  spot-checked, render-proven in headless Chromium (h1 + 12 h2, no h-scroll,
  zero page errors, light-on-dark screenshots reviewed). Synced to QA
  checkout for reference. No app code touched; no tests affected; no rebuild
  needed.

### L-1 | 2026-09-24T03:39:14Z | S5-ship | claude-opus-5-5 | executor | —
Did: record correction found by Ainulindalë's truth reconciler. Its work reached main through the squash merge of testing (PR #34, 2f106b57); the block named `testing`, whose commits a squash leaves off main's history.
Result: the Status Block says what is true today.
Verified: `git merge-base --is-ancestor 2f106b57 origin/main` (the squash of testing); `git diff --stat 2f106b57 9620e5d8` empty; `compass-forge spec show` for each named spec.
Next: as the block says.
