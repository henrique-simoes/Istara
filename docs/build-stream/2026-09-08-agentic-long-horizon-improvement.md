# Build Stream — Agentic Long-Horizon Reasoning Improvement (planning only)

<!-- STATUS BLOCK -->
```yaml
item: agentic-long-horizon-improvement
branch: testing
cf: { spec: CF-SPEC-19, tasks: [CF-193, CF-194, CF-195, CF-196, CF-197, CF-198, CF-199, CF-200, CF-201, CF-202] }
phase: "Phase 0 — Research & improvement plan (complete; implementation open)"
stage: S1-plan
status: in_progress
blocked_on: null
last: { agent: opencode, at: 2026-09-08T01:20:00Z, ledger: L-003 }
next_action: "Future agent: pick Phase 1 (budget-aware continuation), run work-order + gate before on its CF task, implement, verify, evidence."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### S0 Frame — PRFAQ / one-pager (owner-approved, DEC-1)

**Press release.** Istara's chat agents now work a question until it is done:
complex inquiries get planned, executed step by step with mid-run self-checks,
and honest budget accounting — while every existing guarantee (fail-closed
errors, project scoping, content-free telemetry, Pi model authority, no silent
fallbacks) holds unchanged.

**Problem.** Complex questions receive single-pass ReAct answers: one loop, no
plan, no critic, stop at the first quiet turn. Measured live 2026-09-08: a
3-part tool question on Pi/zai-glm used **3 turns, 4 sequential tool calls,
`stop_reason: "stop"`** of a 24-turn budget — breadth without depth, no
verification. Legacy chat is capped at **8 tool iterations**
(`chat.py:84,690`); skill tasks at **5** (`agent_research.py:95,183`).

**Outcome.** A complex question observably receives multi-step treatment:
planned subgoals, chained execution in one session, mid-run critique, visible
budget with continuation — proven by a depth-eval harness, not by anecdote.

**Goal.** Research, specify, and queue 12 philosophy-preserving upgrades;
extend the teaching page; leave implementation tasks open with exact
verification for a later agent.

**Non-goals (hard boundary).** No changes to engine runtime code in this
initiative (`agentic/legacy.py`, `pi_runtime/*`, `dispatcher.py`,
`pi-runtime/src/worker.mjs`), catalogs, auth, telemetry schemas, or
research-spine gates. No merges. No raw budget hikes without orchestration.

**Appetite.** Research + plan + teaching page now (this file); implementation
phased later, one proposal per phase, each independently verifiable and
feature-flaggable.

### Acceptance criteria (for the future implementer)
- `Given` a proposal phase is implemented `When` its verification commands run
  `Then` they pass and CF `gate after` shows 0 new drift
  (verify: `gate after --task CF-n --summary`, `pytest -q <named tests>`,
  Playwright proof script per UI phase).
- `Given` any long-horizon run `When` it exceeds budget or fails
  `Then` it ends with a typed reason (`turn_budget_exceeded`, cost cap,
  honest `not_runnable`) — never a confident hallucination and never a silent
  fallback (verify: scenario suite asserts terminal frames).
- `Given` the depth-eval harness `When` run against pre/post builds
  `Then` turns-used, tools-used, and completeness deltas are reported
  (verify: `node tests/simulation/<depth-suite>.mjs`).

### Doc impact
`docs/architecture/agentic-engine-deep-dive.html` (extended Phase 10 → 12
proposals + references appendix — done in L-002); feature docs only when a
phase ships UI.

### Rollback
Each phase ships behind its own flag/default-off path; revert = flag off or
file-scoped revert. Engine defaults (8/24/5 budgets) never change silently.

### Top risks
1. Planner/critic loops multiply cost — mitigated by per-run cost caps that
   already exist (`max_cost_usd`, unpriced-spend fail-closed).
2. Extra passes could launder ungrounded content — mitigated: all new passes
   are provisional until existing spine validation accepts them.
3. Scope creep into engine rewrites — mitigated: phase task graphs name exact
   files; anything else becomes a new CF task.

## Hard evidence (measured, not claimed)
- **E1 — live single-pass probe (2026-09-08, QA stack, session `3673fc34`,
  Pi `glm-5.3-flash` via `pi-zai-glm`):** 3-part tool question →
  `turns: 3`, 4 sequential tool calls (`search_memory`, `list_project_files`,
  `list_tasks`, `search_documents`), `stop_reason: "stop"`, usage exact
  (`estimate: false`). Session override restored to `gpt-5.6-luna` after.
  Rate limits observed honestly on luna/dashscope during probing (typed
  provider errors, no silent substitution).
- **E2 — accepted benchmark bundle
  (`comparison-Istara-pi/reports/20260801T010602Z/scorecard.json`,
  verdict `no_significant_difference`):** Tool Calling pi 0.8077 vs legacy
  0.8312 (delta −0.026, CI [−0.1429, 0.0909]); Output Quality 6.75 vs 6.6364;
  Research Spine pi 1.0 vs legacy 0.8095; Skills/A2A tied 1.00. Planes are at
  parity — depth work must preserve both, not pick a winner.
- **E3 — budget constants (grep-verified):** legacy chat 8 / Pi chat 24 /
  skill tasks 5; `range(budget+1)` loop (`legacy.py:357`); run timeout 120 s,
  handshake 15 s, cost cap $1.00, pool 2, sessions 10/8, history 200.
- **E4 — existing seams reused (no new machinery):** session revision rehydrate
  (`worker.mjs:143–150`), steering pump 50 ms (`engine.py:392–421`),
  `validation.judge` structured verb, `resolve_distinct` fail-closed,
  chat→task binding (`chat.py:924`), compaction + window guard.

## Literature grounding (why these designs, mapped to seams)
External results inform — repo evidence decides. Each mapping names the seam reused:
- **ReAct (Yao et al., 2022)** — the loop Istara already runs; proposals extend
  orchestration *around* it, never replace it.
- **Reflexion / verbal reinforcement (Shinn et al., 2023)** → Proposal 3
  (mid-run critic): self-reflective text fed back as observations improves
  multi-step success without weight updates; seam: `validation.judge` +
  history-append (`legacy.py:474–487`).
- **Plan-and-Solve / Plan-and-Execute** → Proposal 2: decoupling planning from
  execution beats single-pass ReAct on multi-step tasks; seam: structured
  output + chained turns in one session revision.
- **ReWOO (Xu et al., 2023)** → Proposal 10 (new): full tool-call plan upfront,
  then execution without per-step LLM calls — fewer tokens, same tools; seam:
  tool catalog + `execute_with_idempotency`.
- **Self-Refine (Madaan et al., 2023)** → Proposal 3 variant: iterative
  feedback-refine on the draft answer before `done`; bounded to 1 repair like
  structured output already is (`engine.py:742`).
- **Self-Consistency (Wang et al., 2022)** → Proposal 8: sample-and-vote for
  high-stakes answers; seam: `run_ensemble` + `resolve_distinct`.
- **Multi-agent debate (Du et al., 2023)** → already Istara's `debate_rounds`
  validation; Proposal 3 may use it as the critic engine.
- **Process supervision ("Let's Verify Step by Step", OpenAI 2023)** →
  Proposal 9 (new): reward/verify intermediate steps, not just outcomes; seam:
  existing reliability metrics + per-turn telemetry spans.
- **Tool-parallelism / fan-out-barrier** → Proposal 4: independent calls
  concurrently; mirrors the repo's own multi-agent orchestration discipline.
- **Complexity routing (adaptive compute)** → Proposal 11 (new): classify
  question depth first, then spend budget by tier; evidence E1 shows simple
  questions waste nothing while complex ones starve at fixed budgets.
- **Long-horizon evals (SWE-bench, τ-bench, BFCL ethos)** → Proposal 12
  (new): depth scenario suite turning today's manual probe (E1) into an
  automated, asserted harness.

## Phased task graph (for the future implementer)
| Phase | Proposal | Acceptance | Verification |
|---|---|---|---|
| 1 | Budget-aware continuation | stop_reason surfaced + Continue resumes same revision | Playwright: exhaust budget, Continue, assert revision continuity; `pytest -q tests/test_chat.py` |
| 2 | Plan-then-execute | complex questions emit subgoal plans; chained turns; synthesis | scenario suite; gate after 0 new drift |
| 3 | Mid-run critic | off-track runs get judge verdict as observation | unit tests on verdict injection; scenario deltas |
| 4 | Parallel fan-out | independent calls concurrent, joined | timing + correctness tests; idempotency tests |
| 5 | Plan state in sessions | plan ledger persists/compacts with history | session revision tests |
| 6 | Promote-to-task | budget-exhausted chats continue as tasks | e2e Playwright; task validation green |
| 7 | Budget UX | live budget display + per-question budget choice | screenshots light/dark/375px; a11y check |
| 8 | Ensemble spot-checks | low-confidence answers second-passed or honest `not_runnable` | ensemble tests; single-endpoint honesty test |
| 9 | Complexity routing (new) | tiered budgets by predicted depth; simple stays snappy | tier tests; E1-style probe per tier |
| 10 | ReWOO planner (new) | upfront tool plan; fewer LLM calls, same tools | token-count + correctness deltas |
| 11 | Plan memory (new) | revision payload carries goal/steps/open-questions | compaction tests |
| 12 | Depth eval harness (new) | automated turns/tools/completeness deltas pre/post | `node <suite>.mjs` green in CI lane |

## Decision log
- **DEC-1 | 2026-09-08 | S0 | owner** — Context: owner ordered long-horizon
  work with care, no engine changes yet. Decision: planning-only initiative;
  implementation queued as phased tasks for a later agent. Why: protects the
  working engine while making the improvement path concrete and reviewable.
  Alternatives rejected: immediate implementation (blast radius too high
  without this plan).

## Append-Only Ledger
- **L-001 | 2026-09-08 | S0-frame/S1-plan | opencode | —**
  Did: CF-SPEC-19 created, clarified (planning-only scope), planned, tasked
  (CF-193…CF-202); gathered E1–E4; wrote this file.
  Result: durable improvement contract exists; 0 app-code files touched.
  Verified: `spec tasks CF-SPEC-19` lists CF-193…CF-202 open; `git diff --check` clean
  (this file + HTML only at close).
  Next: extend HTML with proposals 9–12 + references appendix (L-002).
- **L-002 | 2026-09-08 | S1-plan | opencode | —**
  Did: extended `docs/architecture/agentic-engine-deep-dive.html` with
  proposals 9–12, literature appendix, and evidence appendix (E1–E4);
  render-verified in headless Chromium (0 page errors, no h-scroll);
  synced to QA checkout for reference.
  Result: teaching page now carries the full 12-proposal plan with
  why-per-proposal and seam-per-proposal.
  Verified: HTML parses; screenshots reviewed; `git diff --check` clean.
  Next: Plan B audit file, then close both ledgers with evidence rows.
- **L-003 | 2026-09-08 | S1-plan | opencode | —**
  Did: extended render-verification to anchors (14 h2, 12 h3, all TOC links
  resolve) + appendix screenshot review; synced final HTML to QA checkout.
  No engine, app, or test code touched in this initiative —
  `git status` shows only the two plan files + the HTML (+ pre-existing
  worktree state).
  Result: Plan A complete and handed off; CF-SPEC-19 tasks CF-193…CF-202
  stay OPEN for the future implementer by design (no premature finish).
  Verified: `python3 html.parser` OK; Chromium JSON
  `{h2count:14,h3count:12,noscroll:true,missing:[],errs:[]}`;
  appendix screenshot shows Appendix B table rendered correctly;
  `git diff --check` clean.
  Next: stage exit — Plan A stays at S1-plan/in_progress as a living handoff;
  future agent starts at its `next_action`.
