# Plan A — Pi benchmark role correction (DUT / evaluation backend / post-run judge)

- **Task:** `PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-A-r2` (consensus architect slot A,
  revision r2 — supersedes r1 (`…-REPLAN-A-r1`) and r0 (`…-PLAN-A`);
  pipeline `PI-BENCH-ROLE-CORRECTION-20260722`)
- **Spec:** CF-SPEC-8 · **Lifecycle:** `docs/build-stream/2026-07-22-pi-benchmark.md`
- **Authored:** 2026-07-22, against branch `Review_pi_test` @ `1777753c` (post-L-29 state)
- **Scope:** documentation-only correction of the Pi benchmark lifecycle file and the
  Pi benchmark Conductor work-order. No backend/frontend production file, no
  `tests/pi_benchmark/` code, no master-plan edit, no production routing change.

> **r2 revision note.** Every §1/§3 citation was re-verified by fresh grep on
> @ `1777753c` (command evidence on the CF task `…-REPLAN-A-r2`): all lifecycle
> Kimi-as-evaluation regions, DEC-5's judge clause (:488-489), DEC-6 (:497-500), the
> wave-contract slice list (:42-43), and the work-order role text (:24-31, :36-38 no
> ledger draw, :71-73 pack list, :76-77 Kimi judge, :79 must-not-rerun-DUT, :82
> route/MoA judge-scoring dimension) all hold unchanged at HEAD. Drift folded in at r2:
> (a) ledger has advanced to **L-29** (L-27 = this plan's r1; L-28/L-29 are harness
> fallback entries for sibling architect slots C and B), and the committed Status Block
> carries a dangling `ledger: L-30` reference — the next real appended entry becomes
> L-30, so implementers must re-read the last `### L-<n>` under the completion lock and
> never trust the Status Block for numbering; (b) `tests/pi_benchmark/deepseek_judge.py`'s
> module docstring was **rewritten** since r1 and now *explicitly declares* the policy the
> correction supersedes — ":3-8: 'the judge IS the DUT model (`deepseek-v4-pro`) but never
> the DUT *role*' … 'a shared budget ledger so judge spend and benchmark spend draw from
> the same owner-approved cap', citing `judge_config.json`'s `separation_note`" — with
> `make_deepseek_judge_fn` (:84-90) still sharing the evaluation `ledger` via
> `kind="judge"` calls; the §7 code/doc-mismatch row is upgraded accordingly (the code
> now asserts a *decided policy*, not just an implementation detail, so the follow-up CF
> task must also supersede that docstring/`separation_note` text); (c) findings F-3…F-7
> all read `fixed` in the lifecycle register (F-5 at L-26, F-7 at L-25); the pending
> sibling work sharing this worktree is now the delta re-review plus the r2 consensus
> round itself (replan-b-r2 and judges a/b/c active), keeping §7's race mitigation
> (completion lock + path-scoped commits) load-bearing.
>
> **r1 revision note (retained).** Every §1 citation was re-verified by fresh grep on
> @ `b13b238c` (command evidence on the CF task): all 14 Kimi-as-evaluation regions,
> DEC-5's "and judge call through DeepSeek" clause (:488-489), and DEC-6's Kimi
> evaluation route + open judge cast (:497-500) sit at the cited lines; the execution
> work-order's correct role text is confirmed at :26-27 (DeepSeek-only DUT backend),
> :30-31 and :76-77 (Kimi intended judge), :78-79 (judge must not rerun the DUT or make
> new provider calls). r1 closes the r0 residual imprecisions: (a) the lifecycle wave
> contract is at lines **42-43** (not 43-44) and lists canonical/breadth/depth/feature/
> spine/A2A/probe as *slice categories* — §3 now separates "the brief's seven evaluation
> packs must be enumerated in both documents" from "the slice list gains the two missing
> coverage categories" so the pack arithmetic is exact; (b) the judge-does-not-consume-
> the-ledger rule is already **explicit** in the work-order at :38 (not merely implied) —
> RC-4 now only moves it into the role list; (c) the code/doc judge mismatch is pinned:
> `tests/pi_benchmark/deepseek_judge.py:6` ("shared budget ledger so judge spend and
> benchmark spend draw from the same envelope") and `:84-89` (`make_deepseek_judge_fn`
> passes the shared `ledger`, `kind="judge"`), plus `tests/pi_benchmark/judge_config.json`
> — directly contradicting the corrected role model AND the work-order's own :38;
> (d) findings-register drift since r0: **all of F-3…F-7 are now `fixed`** (F-7 at
> L-25, F-5 at L-26, landing while this revision was in flight); the remaining sibling
> activity is the one delta re-review, which still shares the worktree — §7's race
> mitigation (completion lock + path-scoped commits) stays in force.

---

## 1. Problem statement (verified audit)

The lifecycle file contains two mutually contradictory role assignments, verified by
direct grep on 2026-07-22, re-verified at r1 on @ `b13b238c`, and **re-verified at r2 on
@ `1777753c`** (all line numbers below re-checked at HEAD):

**Defect class 1 — Kimi mislabeled as the evaluation (DUT-serving) provider.**
The embedded "Winning consensus plan" (Plan C, lifecycle lines ~110–505) was authored
before DEC-5 switched the evaluation backend to DeepSeek, and still says "Kimi-only
evaluation" throughout. Verified occurrences (lifecycle line numbers at audit time):

| Region | Lines | Wrong text |
|---|---|---|
| §2.1 program-shape diagram | 202 | "resumable Kimi-evaluation slices" |
| §3 task table B0-3, B0-7, B1…B_N | 307, 311, 312 | "Kimi-only evaluation adapter", "Kimi credential/model preflight", `--provider kimi --model <configured-kimi-model>` |
| §4 acceptance A3, A4, A7 | 327, 330, 339 | "Kimi evaluation credential", "configured Kimi evaluation provider/model", "uses Kimi only" |
| §5 verification commands | 357, 374, 377, 380–386, 393 | `--provider kimi` in runner/ledger/preflight commands |
| §6 risk rows | 422, 424 | "Kimi evaluation API quota", "rejects non-Kimi evaluation configuration" |
| §8 gates G0, G1 | 449, 452 | "authorizes Kimi-only benchmark evaluation", "Kimi provider/model identity" |
| §9 non-goals | 465–466 | "non-Kimi evaluation provider routing", "Kimi evaluation `$1.00` envelope" |
| Decision log DEC-6 | 497 | "route every live benchmark evaluation call through the configured Kimi route/model" |

**Defect class 2 — DeepSeek mislabeled as (or permitted to be) the judge.**

| Region | Lines | Wrong text |
|---|---|---|
| Decision log DEC-5 | 488–489 | "Route every live evaluation **and judge** call through DeepSeek `deepseek-v4-pro`" |
| Decision log DEC-6 | 497–500 | evaluation routed "through the configured Kimi route/model" (:497) and judging cast "may use Claude, Codex, Kimi, or another configured judging harness" (:499-500) — leaves the judge open instead of naming Kimi as the intended judge harness/model |

**Already correct (do not churn):** the Goals (line 30), the "Wave and provider
contract" section (lines 50–55), and §2.2 design principle 5 (line 236) already state
DeepSeek-served evaluation and a separate Kimi BSC judging session. The execution
work-order `docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`
already carries the correct separation (DeepSeek DUT backend at lines 26–27, Kimi judge
at lines 30–31 and 76–77, judge-must-not-rerun-DUT-or-call-providers at 78–79, judging
does not consume the evaluation ledger at 38) and the evaluation matrix (packs at
71–73: canonical 15-scenario contract coverage, feature/breadth criteria, Research Spine
lifecycle, A2A collaboration, prompt/injection probes, token/usage accounting) — it
needs only a consistency audit and two small additions ("MoA route/downgrade evidence"
as a seventh named pack — today route/MoA evidence appears only in the judge-scoring
list at :81, not the wave-coverage list — and an explicit pointer to the role-correction
brief `docs/build-stream/conductor-instructions/pi-benchmark-role-correction.md` as the
authoritative role statement).

**Append-only history containing stale language (must NOT be edited):** ledger entries
L-2…L-21 and the L-18 phrase "role-separated DeepSeek judge on the shared ledger" are
historical narrative. The correction supersedes them via new forward-looking text
(DEC-7 + ledger entry), never by rewriting them.

## 2. Authoritative role model (target state, verbatim intent)

1. **DUT/evaluation:** the benchmark runs Istara's original agentic loop and the Pi
   adaptation against the same scenario inputs and compares captured behavior. Istara
   itself is the device under test.
2. **Evaluation backend:** live model calls made by either Istara arm use the configured
   DeepSeek API route (`deepseek-v4-pro`) under the one cumulative `$1.00` cap. The
   runner exercises Istara's API/dispatcher; it never calls DeepSeek directly as a
   substitute for Istara.
3. **MoA:** self-MoA and full-ensemble are properties of Istara's existing
   dispatcher/validation path; the benchmark records requested-vs-served route identity
   and marks downgrades degraded/blocked. Production defaults unchanged.
4. **Judging:** after B0 and B1…B_N are terminal, a separate Build Stream Conductor
   session over durable artifacts; **Kimi is the intended judge harness/model**. It
   produces `report.md`, `report.html`, `scorecard.json`, and per-judgment outputs; it
   must not rerun the DUT or make new benchmark-provider calls, and it does not consume
   the evaluation ledger.
5. **BSC implementation/review workers** are orchestration infrastructure, not DUT or
   judge evidence, unless explicitly assigned to the post-run judging session.

## 3. Design of the correction

Three editable surfaces; one append-only surface:

1. **Lifecycle winning-plan section (living planning artifact — edit in place).**
   Replace every "Kimi evaluation" role usage listed in §1 with the DeepSeek evaluation
   route (`--provider deepseek --model deepseek-v4-pro`, "DeepSeek evaluation
   credential", etc.), and keep all judge references pointing at the separate post-run
   Kimi BSC session over durable artifacts. The `$1.00` cap, `max_processes=N`,
   immutable manifest, resumable waves, fail-closed rules, and gate structure are
   preserved verbatim — only the provider/judge identities change.
2. **Decision log (append + annotate, never silently rewrite).** Append **DEC-7**
   stating the authoritative five-role separation above and explicitly superseding
   (a) DEC-5's "and judge call through DeepSeek" clause and (b) DEC-6's "Kimi
   route/model" evaluation clause and open judge cast. Add a one-line
   `(superseded by DEC-7 for provider/judge identity)` annotation under DEC-5 and
   DEC-6 so no future worker can follow the stale language.
3. **Work-order (`pi-benchmark-deepseek-moa-execution.md`) — audit + tighten.** Verify
   the five roles read identically to §2; add "MoA route/downgrade evidence" explicitly
   to the evaluation-matrix pack list at :71-73 (it is currently only a judge-scoring
   dimension at :81); add one line naming
   `docs/build-stream/conductor-instructions/pi-benchmark-role-correction.md` as the
   authoritative role statement for every future Conductor worker; repeat the
   judging-does-not-consume-the-evaluation-ledger rule (already explicit at :38) inside
   the role list so a worker reading only the roles cannot miss it.
4. **Ledger (append-only).** The implementer appends its own `### L-<n+1>` entry
   describing the correction (what changed, why, evidence commands) with its task
   marker, and refreshes the Status Block `last:` line. Historical entries untouched.

**Evaluation packs (must appear in the corrected lifecycle and work-order, per
acceptance):** the brief's seven packs are canonical 15-scenario contract coverage,
feature breadth, Research Spine lifecycle, A2A collaboration, prompt/injection probes,
usage/cost accounting, and MoA route/downgrade evidence. Current state: the work-order
pack list (:71-73) has six of the seven (missing MoA route/downgrade evidence); the
lifecycle wave contract (:42-43) lists the slice categories
canonical/breadth/depth/feature/spine/A2A/probe (missing usage/cost accounting and MoA
route/downgrade evidence). The correction adds the missing coverage categories to each
list so both documents enumerate all seven brief packs; "depth" remains in the lifecycle
slice list as a legacy work-package label the B0 scheduler maps (removing it would
silently drop accounted work, violating the no-silent-skip rule at :46-47).

## 4. Task breakdown

| # | Task | Files | Depends | Est |
|---|------|-------|---------|-----|
| RC-1 | Rewrite the winning-plan Kimi-evaluation occurrences (all rows of §1 table 1) to the DeepSeek evaluation route; keep judge text pointed at the post-run Kimi BSC session | `docs/build-stream/2026-07-22-pi-benchmark.md` (lines ~200–470 region) | — | S |
| RC-2 | Append DEC-7 (authoritative role separation, supersedes the stale DEC-5/DEC-6 clauses); annotate DEC-5/DEC-6 as superseded for provider/judge identity | same file, Decision log | RC-1 | S |
| RC-3 | Extend the wave-contract slice list with usage/cost accounting + MoA route/downgrade evidence so all seven brief packs are enumerated (depth kept as a mapped legacy label) | same file, lines ~42–43 | — | S |
| RC-4 | Work-order audit + tighten: identical five-role list, add MoA route/downgrade evidence to the :71-73 pack list, pointer to the role-correction brief, repeat judge-does-not-consume-ledger (:38) in the role list | `docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md` | — | S |
| RC-5 | Ledger entry + Status Block `last:` refresh (under `repo_lock.completion_lock`, path-scoped commit) | lifecycle file | RC-1..RC-4 | S |
| RC-6 | Verification battery (§6) recorded as CF command evidence | — | RC-1..RC-5 | S |

One implementer task can carry RC-1…RC-6; a delta reviewer then verifies with the same
§6 battery.

## 5. Acceptance criteria

- **AC-1** The lifecycle states in one place (wave/provider contract + DEC-7): Istara
  (original loop and Pi adaptation) is what is evaluated; DeepSeek `deepseek-v4-pro`
  through Istara's API/dispatcher is the only provider serving live DUT calls; the
  post-run judge is a separate Kimi BSC session over durable artifacts that emits
  report.md/report.html/scorecard.json/per-judgment outputs and never reruns the DUT.
- **AC-2** Zero remaining occurrences of Kimi in an *evaluation-provider* role and zero
  occurrences of DeepSeek in a *judge* role anywhere outside the append-only ledger
  entries and the annotated historical decisions (machine check in §6).
- **AC-3** The work-order gives every future Conductor worker the identical five-role
  separation and names the role-correction brief as authoritative.
- **AC-4** Both documents enumerate the seven evaluation packs: canonical 15-scenario
  contract coverage, feature breadth, Research Spine lifecycle, A2A collaboration,
  prompt/injection probes, usage/cost accounting, MoA route/downgrade evidence.
- **AC-5** `$1.00` cumulative evaluation ledger, `max_processes=N`, immutable manifest,
  resumable B1…B_N waves, fail-closed rules, owner gates, and production Istara
  model-selection behavior are textually preserved (no semantic change beyond
  provider/judge identity).
- **AC-6** The diff touches only `docs/build-stream/` files — no backend/, frontend/,
  tests/, recipes/, or any production path.
- **AC-7** A DEC-7 decision entry and an L-<n+1> ledger entry explain the correction.

## 6. Verification (exact commands)

```bash
# hygiene
git diff --check

# scoped diff/path audit (AC-6): every changed path must be under docs/build-stream/
git diff --name-only | grep -v '^docs/build-stream/' && echo "SCOPE VIOLATION" || echo "scope ok"
git status --porcelain -- backend frontend tests recipes   # expected: no rows from this change

# AC-2 residual-ambiguity audit on the editable regions
# (a) no Kimi-as-evaluation-provider phrasing anywhere:
grep -n -iE 'provider kimi|--provider kimi|kimi[- ]only (benchmark )?evaluation|kimi evaluation (credential|provider|api|envelope|adapter)|non-kimi evaluation|configured-kimi-model' \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md \
  && echo "RESIDUAL KIMI-EVAL" || echo "kimi-eval clean"
# (b) no DeepSeek-as-judge phrasing outside append-only ledger history (### L-*) —
#     check the decision log + plan sections after annotation:
grep -n -iE 'judge call through deepseek|deepseek .*(is|as) the judge' \
  docs/build-stream/2026-07-22-pi-benchmark.md && echo "check hits are annotated-history only"

# AC-4 pack enumeration present in both documents
for f in docs/build-stream/2026-07-22-pi-benchmark.md \
         docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md; do
  for p in canonical feature "Research Spine" A2A probe "usage" "downgrade"; do
    grep -qi "$p" "$f" || echo "MISSING pack '$p' in $f"; done; done

# AC-5 invariants still present
grep -n 'budget_cap_usd=1.00\|max_processes\|immutable' docs/build-stream/2026-07-22-pi-benchmark.md | head

# docs-only change ⇒ no code behavior to re-verify, but prove the suite is undisturbed:
backend/.venv/bin/python -m pytest tests/pi_benchmark/ -q   # expected: unchanged pass count
```

## 7. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Accidental edit of append-only ledger entries (L-2…L-21) while rewriting the winning-plan section | Medium | RC-1 edits are bounded to the winning-plan region and decision log; reviewer diffs against `### L-` headings — any hunk inside a historical ledger entry is a finding. |
| Shared-worktree race with sibling workers — all findings F-3…F-7 are `fixed` as of L-20…L-26, but the pending delta re-review (and any resulting fixers) still edits tests/ and appends lifecycle ledger entries, and the r2 consensus round itself (replan-b-r2, judges a/b/c) runs concurrently in this worktree; harness fallback entries (L-28, L-29) and a dangling Status Block `ledger: L-30` reference show numbering races are real, not theoretical | Medium | Acquire `repo_lock.completion_lock` for the read-append-commit critical section; re-read the last `### L-<n>` heading (never the Status Block) for numbering; commit only the two doc paths via `repo_lock.commit_paths`; never `git add -A`. |
| Over-correction: rewriting text that is already correct (Goals, wave contract, §2.2 p5) creates review churn and merge conflicts | Low | §1 "already correct" list is explicit; RC-1 touches only the audited line regions. |
| grep audit false positives from historical ledger text (e.g. L-18 "DeepSeek judge") | Medium | AC-2 command (b) is scoped to non-`### L-` regions by manual hunk inspection; the plan explicitly declares history exempt. |
| Semantic drift: changing budget/gate/wave wording while swapping provider names | Low | AC-5 grep battery pins the invariants; reviewer checks the diff is identity-swap only. |
| Code/doc mismatch remains — and hardened at r2: `tests/pi_benchmark/deepseek_judge.py`'s docstring now *explicitly declares* "the judge IS the DUT model (`deepseek-v4-pro`) but never the DUT *role*" with "a shared budget ledger so judge spend and benchmark spend draw from the same owner-approved cap" (`:3-8`, referencing `judge_config.json`'s `separation_note`), and `make_deepseek_judge_fn` (`:84-90`) shares the evaluation `ledger` via `kind="judge"` — contradicting the corrected roles (Kimi judge, artifact-only, no evaluation-ledger draw) AND the work-order's own :36-38 | High | Out of scope here (no code edits). Record as an explicit residual risk in the ledger entry and raise a NEW CF task for the follow-up (rename/re-scope the judge preflight apparatus or gate it out of the judging path, AND supersede the docstring/`separation_note` policy text) — do not silently leave the contradiction unlisted. |

## 8. Rollback

Documentation-only: the whole correction is one commit touching two files under
`docs/build-stream/`. `git revert <sha>` restores the prior text exactly; no code,
schema, config, or routing state is involved. The appended ledger entry and DEC-7
remain in history post-revert (append-only discipline), which is acceptable — a revert
would itself be recorded as a further decision entry.

## 9. Non-goals

- No edit to `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`.
- No change to Istara production routing, model selection, or defaults.
- No code changes — `tests/pi_benchmark/` (including `deepseek_judge.py`) untouched;
  the code/doc judge mismatch becomes a new CF task (§7 last row).
- No rewriting of historical ledger entries or verbatim deletion of DEC-5/DEC-6 —
  supersession only.
- No live model calls, no spend, no benchmark execution.
