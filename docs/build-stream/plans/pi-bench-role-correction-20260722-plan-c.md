# Plan C r1 — Pi benchmark role correction: two-document role-language reconciliation

- **Task:** `PI-BENCH-ROLE-CORRECTION-20260722-REPLAN-C-r1` (consensus architect slot C,
  revision r1 — supersedes r0 authored under `PI-BENCH-ROLE-CORRECTION-20260722-PLAN-C`)
- **Role:** `pi-bench-role-correction-20260722-architect-c` · **Pipeline:** `PI-BENCH-ROLE-CORRECTION-20260722`
- **Spec:** CF-SPEC-8 · **Branch:** `Review_pi_test` · **Grounded at:** `1ff29c48`, 2026-07-22
- **Canon brief (verbatim source):** `docs/build-stream/conductor-instructions/pi-benchmark-role-correction.md`
- **Documents under correction:** `docs/build-stream/2026-07-22-pi-benchmark.md` (lifecycle)
  and `docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md` (work-order)

**Mission:** make the lifecycle and the work-order speak one role language — Istara is the
DUT, DeepSeek serves the DUT calls through Istara's API/dispatcher under one `$1.00`
ledger, Kimi is the post-run artifact-only judge, BSC workers are orchestration — without
touching the master plan, production routing, benchmark code, or any backend/frontend
production file.

---

## 1. Verified current state (fresh audit @ `1ff29c48`, 2026-07-22)

Every citation below was re-verified by direct read/grep during this planning stage. The
lifecycle tail is append-only and grows (L-1…L-29 at audit time); all stale regions sit
above the append point and their line numbers are stable.

### 1.1 Already role-correct — keep, do not rewrite

- Lifecycle **Goals** (`2026-07-22-pi-benchmark.md:26-30`): both arms' live calls "routed
  through the configured DeepSeek API"; "Kimi is the intended judge" in a separate session.
- Lifecycle **wave/provider contract** (`:35-62`): DeepSeek-only evaluation through
  Istara's API/dispatcher (`:50-52`); Kimi and every other evaluation provider disabled
  (`:52`); "Post-run judging is a separate BSC session using the intended Kimi judging
  harness" (`:53`); judging "is artifact-based and does not consume evaluation budget"
  (`:59-60`); one cumulative `budget_cap_usd=1.00` envelope (`:56-60`).
- **Work-order** (`pi-benchmark-deepseek-moa-execution.md`): DUT = Istara's two arms
  (`:24-25`); `deepseek-v4-pro` the only live provider behind Istara (`:26-28`); separate
  BSC judging session, Kimi the intended judge (`:28-31`, `:74-77`); judging off the
  evaluation ledger (`:37-38`); no DUT rerun, no new provider calls (`:79-82`).
- **Code already enforces the target state:** `tests/pi_benchmark/runner.py:78-79`
  (`ONLY_PROVIDER="deepseek"`, `ONLY_MODEL="deepseek-v4-pro"`), defaults at `:541-542`,
  and `parser.error` rejection of any other provider/model at `:551-554` (citing DEC-5).
  **The lifecycle's stale `--provider kimi` commands would be rejected by the runner
  today — the docs lag the code, not vice versa.**

### 1.2 Contradictory active text — the correction surface (16 stale regions)

All inside the embedded **winning consensus plan** (`:110-468`), the lifecycle's active
execution authority — corrected in place, because it is living plan text, not history:

| # | Line(s) | Stale text |
|---|---------|-----------|
| 1 | `:202` | diagram: "disjoint, resumable **Kimi-evaluation** slices under one $1.00 cap" |
| 2 | `:307` | B0-3 row: "**Kimi-only evaluation** adapter/preflight" |
| 3 | `:312` | B1…B_N row: `--provider kimi --model <configured-kimi-model>` |
| 4 | `:327-329` | A3: "proves the **Kimi evaluation credential** and exact configured model" |
| 5 | `:330-332` | A4: "the configured **Kimi evaluation provider/model**" |
| 6 | `:339-340` | A7: "uses **Kimi only**" |
| 7 | `:357` | gate preamble: "until the **Kimi evaluation preflight** and owner gate" |
| 8 | `:374`,`:377` | `--provider kimi --model <configured-kimi-model>` plan-only/gate commands |
| 9 | `:380` | heading "**Kimi evaluation preflight**" |
| 10 | `:385` | `--preflight-only --provider kimi` |
| 11 | `:393` | `--provider kimi --model <configured-kimi-model> --budget-usd 1.00` |
| 12 | `:422` | risk row: "**Kimi evaluation API** quota/latency" |
| 13 | `:424` | risk row: "validates the **Kimi evaluation provider/model**; the runner rejects **non-Kimi** evaluation configuration" |
| 14 | `:449-451` | G0: "authorizes **Kimi-only** benchmark evaluation" |
| 15 | `:452-453` | G1: "**Kimi provider/model identity**" (plus doubled-word typo "runtime credential credential presence") |
| 16 | `:465-467` | non-goal: "**non-Kimi** evaluation provider routing … single **Kimi evaluation** `$1.00` envelope" |

### 1.3 Decision log state

- **DEC-5** (`:484-493`): "Route every live evaluation **and judge call** through DeepSeek
  `deepseek-v4-pro`" and one ledger "across all waves, retries, **and judges**" — makes
  DeepSeek the judge and puts judging on the evaluation ledger, contradicting the same
  file's contract (`:53`, `:59-60`). Its DeepSeek-only provider isolation is **correct and
  load-bearing** (the runner cites it at `runner.py:552,554`).
- **DEC-6** (`:495-503`): routes evaluation "through the configured **Kimi** route/model"
  (Kimi as DUT provider) and leaves the judge open — "Claude, Codex, Kimi, or another
  configured judging harness". Wrong provider, ambiguous judge.
- The log is append-only; DEC-5/DEC-6 are **superseded, never rewritten** (§2.4).
- Historical `### L-*` entries mention stale roles (e.g. L-17's "judges" ledger mention) —
  they are evidence of what agents believed and stay **byte-preserved**; DEC-7 covers them.

### 1.4 Adjacent executable debt — out of scope, becomes a NEW CF task

`tests/pi_benchmark/deepseek_judge.py` (`:6`, `:84-89`), `judge_config.json`,
`deepseek_provider.py:95` ("judge calls"), `judge.py` (`allow_dut_model` docstring),
`test_deepseek_judge.py`, and the module's README paragraph
(`tests/pi_benchmark/README.md:73-76`) encode the DEC-5-era "DeepSeek as in-wave judge,
judging on the shared evaluation ledger" policy. Reconciling that apparatus (deprecate vs
rewire as a post-run artifact scorer) changes benchmark **code, config, and tests** —
beyond a docs reconciliation. This plan bars the apparatus from satisfying the corrected
judge contract (DEC-7 wording) and tracks its reconciliation as a follow-up CF task
(RC-7). r0 of this plan proposed editing the README pointer inside this change; r1 rejects
that — the brief names exactly two documents, and the README text travels with the code it
documents, so both belong to the same follow-up task.

### 1.5 Concurrency and baseline facts

- Findings register: **F-3…F-7 all `fixed`** (F-6 L-22, F-7 L-25, F-5 L-26); a delta
  re-review may still append. The correction touches only plan/contract/decision sections
  — never the Findings register or any `L-*` row.
- The lifecycle tail is actively appended by concurrent workers (grew L-28→L-29 during
  this planning stage). All ledger/status/commit work happens inside
  `repo_lock.completion_lock`, re-reading numbers inside the lock.
- Dirty-path baseline at audit time (never stage these): `plan-b.md` (M — sibling
  architect), `recipes/istara-main-pi-replacement/recipe.toml` (M), the work-order file
  and the canon brief (?? — conductor-created, not yet committed), this plan file (??).

## 2. Design

### 2.1 Role canon (target language, applied verbatim)

1. **DUT/evaluation:** the benchmark runs Istara's original agentic loop and the Pi
   adaptation against the same scenario inputs and compares their captured behavior.
2. **Evaluation backend:** live model calls made by either Istara arm use the configured
   DeepSeek API route (`deepseek` / `deepseek-v4-pro`) under the existing cumulative
   `$1.00` cap, exercised **through Istara's API/dispatcher** — never a direct DeepSeek
   call substituting for Istara.
3. **MoA:** `self_moa` and `full_ensemble` are properties of Istara's existing
   dispatcher/validation path. The benchmark records requested versus served route
   identity and marks downgrades as degraded/blocked, without changing production
   defaults. (This documents enforced post-F-4/F-5 behavior, not an aspiration.)
4. **Judging:** after B0 and B1…B_N are terminal, a **separate Build Stream Conductor
   session** scores frozen durable artifacts. **Kimi is the intended judge harness/model.**
   The judge produces `report.md`, `report.html`, `scorecard.json`, and per-judgment
   outputs; it must not rerun the DUT, make new benchmark-provider calls, or consume
   evaluation-ledger spend.
5. **BSC implementation/review/remediation workers** are orchestration infrastructure,
   not DUT or judge evidence, unless explicitly cast in the post-run judging session.

### 2.2 Seven evaluation packs (explicit list in BOTH documents)

canonical 15-scenario contract coverage · feature breadth · Research Spine lifecycle ·
A2A collaboration · prompt/injection probes · usage/cost accounting · MoA route/downgrade
evidence. The lifecycle's existing slice vocabulary (`:42-43` "canonical, breadth, depth,
feature, spine, A2A, and probe work") stays as the internal shard mapping — `depth` is a
mapped legacy label, not an eighth pack; the seven-pack list is the external coverage
contract and is not permission to drop mapped work.

### 2.3 Edit strategy (five rules)

1. **Correct active text in place.** Every §1.2 instance moves to DeepSeek role language:
   "Kimi evaluation credential/provider/model" → "configured DeepSeek evaluation
   credential/provider/model"; `--provider kimi --model <configured-kimi-model>` →
   `--provider deepseek --model deepseek-v4-pro` (exactly what `runner.py:78-79,541-554`
   enforces); "Kimi-only evaluation" → "DeepSeek-only evaluation through Istara's
   API/dispatcher"; "rejects non-Kimi" → "rejects non-DeepSeek". Kimi text that is
   judge-only (`:30`,`:53`, and the corrected DEC-7) stays Kimi.
2. **History is superseded, not rewritten.** Append supersession annotation lines to
   DEC-5 (in part) and DEC-6 (in full); append DEC-7 (§2.4). No edit to any `L-*` entry
   or Findings-register row.
3. **Insert the seven-pack enumeration** into the winning plan's wave section (near the
   B1…B_N row, `:312`) and the wave/provider contract (after `:47`), per §2.2.
4. **Add canon point 5** to both documents (lifecycle contract section; work-order
   provider/safety contract), so every future worker prompt inherits it.
5. **Work-order gets minimal touch-ups only** (its roles are already right): add the
   "MoA route/downgrade evidence" pack to the evaluation matrix (`:71-73`), rename
   "token/usage accounting" → "usage/cost accounting" (the brief's exact vocabulary), add
   canon point 5. Fix the G1 doubled-word typo while rewriting `:452-453`.

**Scope fence:** task-commit paths ⊆ {`docs/build-stream/2026-07-22-pi-benchmark.md`,
`docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md`}.
Nothing else — no master plan, no code/tests/README under `tests/pi_benchmark/`, no
backend/frontend/desktop path, no secret surface.

### 2.4 DEC-7 — full specification (the implementer transcribes, does not invent)

Append to DEC-5 (after `:493`):
> Superseded in part by DEC-7 (2026-07-22): the judge-call routing and judge-spend clauses
> are withdrawn; the DeepSeek-only provider isolation and the cumulative `$1.00`
> evaluation ledger stand.

Append to DEC-6 (after `:503`):
> Superseded by DEC-7 (2026-07-22): evaluation runs through the configured DeepSeek route
> behind Istara's API/dispatcher, and the post-run judge is the separate BSC session with
> Kimi the intended judge harness/model.

Append as a new entry:

```
DEC-7 | 2026-07-22 | S1-plan-repair | owner + build-stream-conductor
Context: the lifecycle accumulated three generations of role language — the Kimi-
evaluation winning-plan text; DEC-5's DeepSeek-only replan that also routed judge calls
through DeepSeek and put judging on the evaluation ledger; DEC-6's Kimi-evaluation /
ambiguous-judge correction. The runner (tests/pi_benchmark/runner.py:78-79,541-554) and
the remaining-wave work-order already enforce DeepSeek-behind-Istara evaluation and a
separate post-run Kimi judging session; the lifecycle text disagreed with itself and with
the enforced code path.
Decision: the five-point role canon (§2.1 of the correcting plan) is authoritative for
this lifecycle: (1) the DUT is Istara — original agentic loop vs Pi adaptation on
identical scenario inputs; (2) every live DUT call traverses Istara's API/dispatcher over
the configured DeepSeek route (deepseek / deepseek-v4-pro) under the one cumulative
budget_cap_usd=1.00 evaluation ledger — no direct DeepSeek call substitutes for Istara;
(3) self_moa/full_ensemble are properties of Istara's dispatcher/validation path —
requested versus served route identity is recorded and any downgrade is
degraded/blocked, production defaults unchanged; (4) judging is a separate post-run BSC
session over frozen durable artifacts with Kimi the intended judge harness/model,
emitting report.md, report.html, scorecard.json, and per-judgment outputs — it never
reruns the DUT, makes no benchmark-provider calls, and consumes no evaluation-ledger
spend; (5) BSC implementation/review/remediation workers are orchestration
infrastructure, not DUT or judge evidence. The seven evaluation packs are: canonical
15-scenario contract coverage, feature breadth, Research Spine lifecycle, A2A
collaboration, prompt/injection probes, usage/cost accounting, MoA route/downgrade
evidence. DEC-5's judge-call and judge-ledger clauses and DEC-6 in full are superseded;
DEC-5's DeepSeek-only provider isolation stands (the runner cites it). The DEC-5-era
in-wave DeepSeek judge apparatus under tests/pi_benchmark/ does not satisfy this judge
contract; its reconciliation is tracked as a separate CF task. Production Istara model
selection is unchanged.
Why: documentation must match the enforced code path and the owner's role intent before
any live B1…B_N wave; ambiguity about DUT provider or judge identity contaminates route
evidence, the budget ledger, and the final scorecard.
```

## 3. Task breakdown

One implementation task (RC-1…RC-7, two files, one path-scoped commit) plus one
independent review task (RC-8). Estimates: S (< half agent-day) each. No executor lanes,
no live calls, no spend.

| # | Task | Files | Depends on |
|---|------|-------|-----------|
| RC-1 | Pre-edit baseline: capture `git status --porcelain` dirty-path baseline; re-run §1.2 greps to confirm every instance line; snapshot current DEC/ledger tail numbers | none | — |
| RC-2 | Correct all 16 §1.2 instances in the embedded winning plan to DeepSeek role language; fix the G1 doubled-word typo | lifecycle | RC-1 |
| RC-3 | Insert the seven-pack enumeration (§2.2) and canon point 5 into the wave/provider contract section | lifecycle | RC-1 |
| RC-4 | Decision log: supersession annotations on DEC-5 (in part) / DEC-6 (full); append DEC-7 per §2.4 | lifecycle | RC-2, RC-3 (same file, one commit) |
| RC-5 | Work-order: add seventh pack, rename to "usage/cost accounting", add canon point 5 | work-order | RC-1 |
| RC-6 | Run the §5 verification battery; record every command as CF `command` evidence | none | RC-2…RC-5 |
| RC-7 | Import the follow-up CF task for the `tests/pi_benchmark/` DeepSeek-judge apparatus (code + config + README + tests); under `repo_lock.completion_lock` re-read tail, append the implementer ledger entry (task-marked), refresh only status `last`, commit the two paths with `repo_lock.commit_paths` | CF state + lifecycle tail | RC-6 |
| RC-8 | Independent review of the doc diff: re-run §5 audits, check the decision log line-by-line against §2.4, confirm no register/`L-*` hunk | none | RC-7 |

Suggested CF roles: one implementer (`pi-bench-role-correction-20260722-implementer`),
one reviewer. If conductor remediation lands concurrently, the implementer rebases on the
latest lifecycle inside the lock and still touches only plan/contract/decision sections.

## 4. Acceptance criteria

- **AC-1 (roles unambiguous):** the lifecycle states, in its contract section and plan
  body, what is evaluated (Istara original loop vs Pi adaptation on identical scenario
  inputs), what serves the DUT calls (configured DeepSeek route through Istara's
  API/dispatcher), and what the post-run judge does (separate BSC session, Kimi intended
  judge, artifact-based, off-ledger, no DUT rerun, no new benchmark-provider calls).
- **AC-2 (no stale role language):** the §5 battery finds zero Kimi-as-evaluation-provider
  or DeepSeek-as-judge text outside (a) the quoted DEC-5/DEC-6 supersession context,
  (b) byte-preserved `L-*` history, (c) DEC-7's explicit debt reference to the
  `tests/pi_benchmark/` apparatus.
- **AC-3 (work-order parity):** the work-order carries the same five-point separation,
  including canon point 5, and names all seven packs with the brief's exact vocabulary.
- **AC-4 (packs listed):** the lifecycle enumerates all seven packs: canonical
  15-scenario contract coverage, feature breadth, Research Spine lifecycle, A2A
  collaboration, prompt/injection probes, usage/cost accounting, MoA route/downgrade
  evidence.
- **AC-5 (preservation):** `$1.00` cumulative ledger, `max_processes=N`, immutable
  manifest, resumable B1…B_N waves, and unchanged production model-selection behavior all
  survive the diff.
- **AC-6 (scope):** `git diff --check` clean; `git diff-tree` of the task commit shows
  exactly the two permitted paths; no master plan, production file, code/test/README under
  `tests/pi_benchmark/`, Findings-register row, or `L-*` entry is touched.
- **AC-7 (traceability):** DEC-7 and the implementer's ledger entry explain the
  correction; the follow-up apparatus task exists in CF.

## 5. Verification (exact commands)

Docs-only change — no test suite, no model, no spend is required or permitted. Run from
`<repo-root>-pi-replacement`; compare against the RC-1 baseline so
concurrent worker changes are never attributed to this task.

```bash
# whitespace/patch hygiene (brief-mandated), scoped to the two documents
git diff --check -- \
  docs/build-stream/2026-07-22-pi-benchmark.md \
  docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md

# stale-role battery on the lifecycle — expect NO matches outside L-* history / DEC quotes:
grep -n "provider kimi\|Kimi-only evaluation\|Kimi evaluation\|non-Kimi" \
  docs/build-stream/2026-07-22-pi-benchmark.md
grep -n "judge call through DeepSeek\|retries, and judges" \
  docs/build-stream/2026-07-22-pi-benchmark.md   # only inside DEC-5's quoted context

# enforced route appears in the corrected examples:
grep -n -- "--provider deepseek --model deepseek-v4-pro" \
  docs/build-stream/2026-07-22-pi-benchmark.md

# role-canon + all seven packs present in BOTH documents:
for f in docs/build-stream/2026-07-22-pi-benchmark.md \
         docs/build-stream/conductor-instructions/pi-benchmark-deepseek-moa-execution.md; do
  for t in "original agentic loop" "Pi adaptation" "API/dispatcher" "Kimi is the intended judge" \
           "orchestration" "canonical 15-scenario" "feature breadth" "Research Spine lifecycle" \
           "A2A collaboration" "prompt/injection probes" "usage/cost accounting" \
           "MoA route/downgrade evidence"; do
    grep -q "$t" "$f" || { echo "MISSING: $t in $f"; exit 1; }
  done
done

# preservation invariants still stated:
grep -n "budget_cap_usd=1.00\|\$1.00" docs/build-stream/2026-07-22-pi-benchmark.md
grep -n "max_processes\|immutable\|resumable" docs/build-stream/2026-07-22-pi-benchmark.md

# decision log: supersession annotations + DEC-7 present, DEC-5/6 text otherwise intact:
grep -n "DEC-7\|Superseded" docs/build-stream/2026-07-22-pi-benchmark.md

# cross-check against enforced code behavior (read-only):
grep -n "ONLY_PROVIDER\|ONLY_MODEL" tests/pi_benchmark/runner.py

# scope audit — the task commit contains exactly the two documents:
git diff --cached --name-only            # before commit
git diff-tree --no-commit-id --name-only -r <task-commit>   # after commit
```

Every executed command is recorded as CF `command` evidence on the implementer's task; the
reviewer re-runs the same battery independently (RC-8). Any match in a "expect NO matches"
block is a finding, not a judgement call.

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Under-edit: a stale Kimi-evaluation instance survives | Medium | §1.2 enumerates all 16 regions by line; §5 greps are mechanical and reviewer-repeated; any match is a finding. |
| Over-edit: DEC-5/DEC-6 or an `L-*`/register row is rewritten | Medium | Plan forbids it; DEC edits limited to appended annotation lines; reviewer checks the decision-log diff line-by-line against §2.4. |
| Scope creep into the `deepseek_judge.py` apparatus or README | Medium | Explicit non-goal + follow-up CF task (RC-7); path audit rejects anything beyond the two documents. |
| Concurrent append shifts DEC/ledger numbering or collides on the index | Medium | Re-read tail numbers inside `repo_lock.completion_lock`; `commit_paths` stages only the two named paths; RC-1 baseline separates foreign dirty paths. |
| Corrected commands drift from what the runner accepts | Low | §5 cross-checks `runner.py:78-79,541-554`; the substitution is exactly what the code enforces — docs align TO the code. |
| Judge identity re-ambiguified later | Low | DEC-7 names Kimi as the intended judge harness/model; canon point 5 + the five-point block must appear in every future worker prompt for this lifecycle. |
| Reader treats `deepseek_judge.py` as satisfying the judge contract | Low | DEC-7 explicitly bars it; the follow-up task owns code-side reconciliation. |

## 7. Rollback

- The change is doc-only across two files: **one `git revert` of the task commit**
  restores the previous text exactly. No code, config, schema, data, or state migration.
- DEC-7 is additive; reverting returns DEC-5/DEC-6 to sole authority (the pre-correction,
  self-contradictory state — undesirable but harmless to code, since `runner.py:551-554`
  enforces DeepSeek-only regardless of doc text).
- The RC-7 follow-up CF task is cancelled with one CF status change; it has no repo
  footprint. Per Build Stream convention, any later rollback of the decision itself is
  recorded as a new superseding decision/ledger entry, never by deleting history.

## 8. Explicit non-goals

- No edit to `docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md`.
- No backend/frontend/desktop production file change; no production routing or
  model-selection behavior change.
- No change under `tests/pi_benchmark/` (code, config, README, tests) — that apparatus
  reconciliation is the RC-7 follow-up task with its own tests and gates.
- No edit to any `L-*` ledger entry or Findings-register row; no rework of the completed
  F-3…F-7 remediation.
- No live model call, no spend, no DUT execution, no judging — this correction is
  documentation reconciliation only.
- No re-litigation of the DeepSeek-only provider choice (DEC-5's provider isolation
  stands; only its judge clauses are superseded).
