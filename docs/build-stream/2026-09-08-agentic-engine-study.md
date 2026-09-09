# Build Stream — Agentic Engine Deep Study (read-only, no behavior change)

<!-- STATUS BLOCK -->
```yaml
item: agentic-engine-study
branch: testing
phase: "Study + teaching page (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: opencode, at: 2026-09-08T00:00:00Z, ledger: L-002 }
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
