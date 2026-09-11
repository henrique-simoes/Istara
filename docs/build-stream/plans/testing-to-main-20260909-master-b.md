# Master Plan B — MECE synthesis: testing → main promotion

Consensus synthesis · slot `b` · pipeline run `testing-to-main-20260909` · spec `CF-SPEC-30`
Task: `testing-to-main-20260909-MASTER-B` · round `b35539f4f7bdabc5be5f`
Phase: `synthesize`. Status: **proposal only**. No implementation, promotion, or merge is authorized by this document.

> **Path hygiene notice (load-bearing, see M-02).** `scripts/public_repo_quality_audit.py` fails the
> build when the owner's literal absolute checkout path appears in any *tracked* text file. This plan
> writes `<REPO_ROOT>` wherever that path would appear, and every implementer must do the same in
> every committed artifact — ledger entries included. This file is committed, so it obeys its own rule.

---

## 0. Synthesis method and what changed versus the drafts

Three independent drafts were synthesized:

| Slot | Author | Model / settings | Draft |
|---|---|---|---|
| a | `gpt-5.6-sol-low` (codex) | `gpt-5.6-sol`, effort=low | `docs/build-stream/plans/testing-to-main-20260909-plan-a.md` |
| b | `opus.5-high` (claude) | `claude-opus-5`, effort=high | `docs/build-stream/plans/testing-to-main-20260909-plan-b.md` |
| c | `zai/glm-5.3-flash-max` (pi) | `zai/glm-5.3-flash`, effort=max | `docs/build-stream/plans/testing-to-main-20260909-plan-c.md` |

All three were read from their immutable snapshots under
`.compass-forge/conductor/consensus-snapshots/`. This is not a concatenation. The drafts **disagreed
on four material facts**, and a plan that averaged them would have shipped at least two unexecutable
waves. Each conflict was re-measured read-only during this synthesis session; the adjudications
below are the synthesis's primary contribution and are carried into the register as M-01, M-10 and
M-16.

### 0.1 Conflict adjudication (re-measured 2026-09-09, this session)

| # | Conflict | Draft positions | Measured verdict | Consequence for the plan |
|---|---|---|---|---|
| K-1 | Is local committed `testing` (surface B) a viable candidate base? | A: build "Candidate D" rooted at B. C: B is internally broken — modified tracked files import untracked modules. B(b): silent. | **C is right, and understated it.** `git grep tokenStore HEAD -- frontend/src` → empty; `frontend/src/lib/tokenStore.ts` is `??` untracked; **22** tracked-modified files import `@/lib/tokenStore`, plus 3 importing `SeeMoreList` and 3 importing `ToolAuditTrailTable` (both untracked). | The candidate **must** include classified untracked files. A "commit only what is already committed" base cannot typecheck or build. Dependency-closure proof becomes a W1 acceptance test (M-01). |
| K-2 | How many frontend lint errors are there? | A: **233 errors, 82 warnings** (release-blocking, "materially wider than briefed"). B(b) and C: exactly **1** (`ChatModelControls.tsx:20`). | **Both are literally right; A's is an artifact.** `npm run lint` → 315 problems (233 errors). **232 of 233 are inside `frontend/.stryker-tmp/sandbox-2OnHq3/`**, a leftover Stryker sandbox created 2026-09-09 11:12. Real product errors outside it: **1**. `.stryker-tmp/` is gitignored (`.gitignore:64`) but **not** eslint-ignored, and CI checks out clean, which is why CI's blocking `eslint .` passed at `9961fa3d`. | W3 fixes **one** lint error, not 233 — a ~200× scoping correction. And the trap itself becomes a finding (M-16): a gitignored-but-not-lint-ignored artifact directory made a principal architect misreport a release blocker. |
| K-3 | Is the Compass Forge graph usable, and what is the impact command? | A: refresh index to "schema 21", then `compass-forge impact`. C: `impact`/`graph` are `not_yet_native`; run a refresh until usable. B(b): the brief is wrong — `intelligence impact --path` works today. | **B(b) is right.** Bare `impact` → `{"code":"not_yet_native"}`. `intelligence impact --path <p>` → `confidence.level: "high"`, `corpus: {graph_version 2, kernel "rust", source "tree-sitter"}`. `index status` → `index_version: 12`, `kernel: "rust"`, `warnings: []`, built `2026-09-09T14:48:19Z`. | The brief's blocker #4 is **false**. There is no schema-21 target and no `graph_usable` field; the capability was renamed, not lost. A and C would each have burned a wave chasing a refresh that cannot change `index_version`. Waves call `intelligence impact --path` (M-10). |
| K-4 | Why does the public-quality audit fail when the phrase is not in the files? | A: "literal `rg` does not see the token — scanner/input discrepancy requires diagnosis." B(b): `machine_checkout_path` is the **rule name**; the forbidden text is the absolute path. C: identified both leak sites. | **B(b) supplies the root cause, C supplies the locations.** They compose exactly. | The highest-risk misdirection in the brief is neutralized: an implementer following A would have "diagnosed the scanner" and risked disabling a working gate (M-02). |

### 0.2 Two facts that moved during planning

- **The candidate base moved.** The brief and all three drafts measured local `testing` HEAD as
  `85f64e4d…`. It is now **`50c4d493fcd0b9aef8df8277e5c766822f65d0aa`** — the three draft-plan commits
  landed during the planning phase. The dirty overlay is unchanged (155 files, +4712/−977, 119
  untracked), so the *work* did not move, but the *base* did. This is B(b)'s F-B11 confirmed in the
  act (M-19), and it is why W1 freezes before it measures.
- **Draft insertion/untracked counts (4712 / 119) still hold**, against the brief's 4706 / 118.

---

## A. Candidate definition

### A.1 Measured state

| Fact | Measured value | Command | Source |
|---|---|---|---|
| Local branch | `testing` | `git rev-parse --abbrev-ref HEAD` | a,b,c |
| Local `testing` HEAD **(moved)** | `50c4d493fcd0b9aef8df8277e5c766822f65d0aa` | `git rev-parse HEAD` | **this synthesis** |
| `origin/testing` | `9961fa3dbd2ce03a6e1d8cc3e303478edaf17a79` | `git rev-parse origin/testing` | a,b,c |
| `origin/main` | `fa6a1a391b5a1089690eb8fed5d179ce146ec9e9` | `git rev-parse origin/main` | a,b,c |
| Merge base with `main` | `fa6a1a39…` — `main` is a **strict ancestor** | `git merge-base` | b |
| `origin/testing` vs `origin/main` | 994 ahead, 0 behind (fast-forwardable) | `git rev-list --left-right --count` | a,b,c |
| Local vs `origin/testing` | 64 ahead, 0 behind; 59 of 64 touch `docs/build-stream`; code commits are the pi-ai 0.85.1 lockstep bump and five review-fix commits | `git log --oneline origin/testing..HEAD` | c |
| Tracked modifications | 155 files, **4712** insertions, 977 deletions | `git diff --shortstat` | b,c |
| Untracked (excl. ignored) | **119** files | `git ls-files --others --exclude-standard` | b,c |
| Untracked composition | 71 `tests/document_corpus/rich/**`, 17 `docs/build-stream`, 13 `tests/simulation`, 4 `frontend/src` | grouping | b |
| **Import closure gap** | 22 tracked-modified files import untracked `@/lib/tokenStore`; 3 import `SeeMoreList`; 3 import `ToolAuditTrailTable` | `git grep HEAD` + `grep -rl` | **this synthesis** (extends c) |
| Full `origin/main..C` size | ~1,400 files, ~264,900 insertions, ~14,976 deletions | `git diff --stat` | a |

`main` being a strict ancestor is the single most favourable fact in this release: the promotion has
no rebase or conflict surface.

### A.2 Verdict on the three surfaces

| Surface | Contents | Verdict | Reason |
|---|---|---|---|
| A — `origin/testing` `9961fa3d` | 994 commits over main | **rejected** | CI red on it (mutation 73.08, format); missing all 64 local commits and every working-tree change. |
| B — local committed `testing` | A + 64 commits | **rejected** | **Import closure fails** (K-1): 22 modified tracked files import modules that exist in no commit. This surface cannot typecheck or build. |
| **C — local commits + classified working tree** | B + classified tracked edits + classified untracked files | **SELECTED** | The only surface whose import graph closes and that contains the recent Build Stream work. Every known-green result was measured on it. |

The candidate is C, produced by *deliberate classification*, never by bulk staging. A's "Candidate D"
framing is preserved in substance — a fourth, constructed surface — but rooted per C's evidence at
`local HEAD + classified working tree` rather than at bare B.

### A.3 Reconciliation algorithm

Nothing is ever deleted, reset, cleaned, stashed-away, or pruned. `LLMs/` and `Model_Finetuning/`
are never touched, moved, listed-into, or cleaned at any step.

**Step 0 — recovery substrate that does not depend on any later step (from a, hardened by b).**

```
git bundle create ../istara-recovery-<UTC>.bundle --all
git stash list                     > ../istara-stashlist-<UTC>.txt   # record only, never drop
git status --porcelain=v2 -z       > ../istara-status-<UTC>.txt
git diff --binary HEAD             > ../istara-tracked-<UTC>.patch
tar -czf ../istara-untracked-<UTC>.tar.gz $(git ls-files --others --exclude-standard)
compass-forge state backup                                          # native binary, from repo root
```
Stored **outside** the repository. Verify by restoring into a scratch clone and comparing hashes
*before* any wave commits. `git check-ignore LLMs Model_Finetuning` confirms protection; their
contents are never enumerated.

**Step 1 — classify every path into exactly one bucket.** Produce
`docs/promotion/2026-09-09-candidate-classification.tsv` (tracked), one row per modified and
untracked path: `path · bucket · evidence citation · owning lifecycle/CF ref · sha256`.

| Bucket | Meaning | Default |
|---|---|---|
| `INCLUDE-PRODUCT` | Product/test/fixture code traceable to a named initiative or CF task | include |
| `INCLUDE-LIFECYCLE` | `docs/build-stream/**` narrative and plan records | include, after §A.5 truth pass |
| `INCLUDE-HYGIENE` | Repair produced by this release effort | include |
| `EXCLUDE-GENERATED` | Reproducible from source (`node_modules`, `.stryker-tmp`, `.results`, build output, scorecards) | exclude, never delete |
| `EXCLUDE-PROTECTED` | `LLMs/`, `Model_Finetuning/`, `.compass-forge/`, `.env*`, keys | exclude, never touch |
| `QUARANTINE` | Ambient/unattributable local work | **exclude**, preserved in place **and** on branch `quarantine/ambient-20260909` |
| `UNDECIDED` | Cannot be traced by evidence | **exclude and escalate to owner** |

`UNDECIDED` and `QUARANTINE` default to *exclude*: accidentally shipping unreviewed local work is a
worse failure than deferring a file to the next release. Nothing enters the candidate because it
happened to be sitting in the tree. Directory-level `??` entries are expanded to leaf files (a).

**Step 2 — evidence rule.** A path is `INCLUDE-*` only if at least one holds: it appears in a
lifecycle ledger `Did:` line; it is named by an open or accepted CF task/spec; it is a test/fixture
required by an included source change; or it is required to make a blocking check pass. Otherwise
`UNDECIDED`. Classification is recorded as CF evidence so the reviewer audits it rather than
re-deriving it.

**Step 3 — dependency-closure proof (mandatory acceptance test, from K-1).** For every
`INCLUDE-PRODUCT` untracked file, at least one included importer must exist; and — the direction that
actually bit here — **for every included tracked file, every module it imports must resolve within the
candidate**. Mechanically: `npx tsc --noEmit` on the staged candidate must resolve every specifier.
A file with no importer and no importee is demoted to `QUARANTINE`. This test is what distinguishes a
buildable candidate from surface B.

**Step 4 — hunk granularity where a file mixes concerns (from a).** If one file contains both release
and ambient edits, reproduce the release unit in an isolated candidate worktree rather than editing or
staging the shared file.

**Step 5 — stage by explicit path list only.** `git add --pathspec-from-file` exclusively.
**Never `git add -A`, never a pathless commit.** This is the single most important mechanical rule in
the plan: `git add -A` here sweeps 119 untracked files, including unclassified ones, into a release.

**Step 6 — the untracked lifecycle problem.** The 17 untracked lifecycle files are resolved *before*
freeze, because a lifecycle record outside the candidate cannot be evidence about the candidate. The
conductor's own convergence file is among them and is committed in W1.

**Step 7 — owner ratification.** The manifest is presented in the lifecycle file. The same owner
approval that authorizes implementation ratifies it. Any path the owner does not rule on defaults to
`QUARANTINE`, never to silent inclusion.

### A.4 Freeze

W1 produces the **Candidate Base SHA**. W6 produces the **Promotion SHA** (Base + repair commits),
and the dossier binds to the Promotion SHA. From the freeze instant:

- the SHA is written into the CF spec, the lifecycle status block, and the dossier;
- every verification records the SHA it ran against; pre-freeze results are diagnostics, never
  certification;
- any commit after the freeze **invalidates** the dossier and forces re-freeze at a new SHA. There is
  no "small amendment" path; W6's dossier check enforces it, not convention;
- `git log --oneline <Base>..<Promotion>` is published as the audit trail of everything added after
  the freeze (c);
- CI evidence binds by `headSha`: `gh run list --commit <Promotion SHA>` must show the green run (c).

`origin/testing` is only ever updated by a fast-forward push of the frozen commit — never
force-pushed — so its history stays append-only and the existing anti-replay check in
`.github/workflows/promote-testing.yml` (which verifies the promoted SHA equals current `testing`
HEAD) keeps working (b).

### A.5 Rollback and recovery

| Failure | Recovery |
|---|---|
| Wrong file included | `git revert` the specific commit; re-freeze at a new SHA |
| Wrong file excluded | It is still in the worktree and on the quarantine branch — include next release |
| Local work appears lost | Restore from Step-0 bundle + untracked tarball + tracked patch |
| Candidate unshippable | Abandon the SHA; `origin/testing` intact; `main` never moved |
| Lifecycle record wrong | Ledgers are append-only — append a correction, never rewrite |
| CF state damaged | Restore from the native `state backup`; never a Python fallback |

Backup branch `backup/pre-candidate-20260909` is created at the pre-W1 HEAD (c). No rollback path
uses `reset --hard`, `clean`, broad `checkout`, or deletion of protected/ignored directories.
`main` is never touched by any wave, so the worst case is always "the release does not happen",
never "the release branch is damaged".

### A.6 Rules preventing silent basis change

1. Every wave records start and end SHA as CF `command` evidence.
2. No wave commits a path outside its declared scope; the supervisor compares
   `git diff --name-only <start>..<end>` against the wave's scope list. New ambient edits appearing
   mid-stream go to `QUARANTINE`, never into the wave (c).
3. `git add -A`, `git checkout -- .`, `git reset --hard`, `git clean`, `git stash drop`, amend,
   rebase, and force-push are forbidden in every wave (§G).
4. Evidence without a SHA is rejected by the supervisor (b).
5. W6 re-verifies `git rev-parse testing == PROMOTION_SHA` before any promotion evidence counts.

---

## B. Findings register (unified, MECE)

Severity: **S1** blocks promotion · **S2** blocks unless the owner accepts with written rationale ·
**S3** fix in this release · **S4** record and defer.
`Src` cites the draft(s) that found it; **`syn`** marks a synthesis-only finding or correction.

| ID | Sev | Surface | Evidence (measured) | Root cause | Consequence | Correction | Verification | Wave | Disposition | Src |
|---|---|---|---|---|---|---|---|---|---|---|
| **M-01** | S1 | Candidate custody | 3 divergent surfaces; 155 modified + 119 untracked; **22 tracked-modified files import untracked `@/lib/tokenStore`**; base moved `85f64e4d`→`50c4d493` mid-planning | Work accumulated across remote, local commits, and worktree with no freeze ritual | Any "green" claim is unfalsifiable; risk of shipping *or losing* ambient work; surface B cannot build | §A.3 classify → dependency-closure proof → Base SHA + manifest + backup/quarantine branches | Manifest committed; `tsc --noEmit` resolves every specifier; `git status` residue is only EXCLUDE/QUARANTINE | W1 | blocking | a,c,**syn** |
| **M-02** | S1 | Public-artifact audit | `pytest tests/test_public_repo_quality.py` → 1 failed; `audit()` → 2 findings. `grep machine_checkout_path AGENTS.md` → **nothing**: it is the *rule name*, mapped in `GLOBAL_FORBIDDEN` to the literal absolute path. Leaks: `AGENTS.md:142`; `docs/build-stream/2026-09-08-pi-capability-inheritance.md:1722` | Absolute machine path written into tracked docs; **and the conductor protocol hands every worker that path and tells it to write ledgers into the scanned directory — the leak regenerates every wave** | Owner's filesystem layout published; a correct gate is at risk of being disabled to obtain green | Rewrite both to repo-relative — **never edit the audit**; pre-commit hook + fast CI step running the audit; protocol rule mandating `<REPO_ROOT>` in lifecycle entries | `pytest tests/test_public_repo_quality.py` on the frozen SHA + a negative test that re-introducing the path fails; **re-run *after* W1 commits, since the audit scans `git ls-files` (tracked only) and the scan surface grows** | W1 (hook+protocol), W3 (text), W6 (re-verify) | blocking | b(root cause), c(sites), a(symptom) |
| **M-03** | S1 | Backend correctness escaping lint | `ruff check backend/ --select F821` → 2 errors: `BudgetAllocation` (`token_counter.py:105`), `ComputeNode` (`compute_registry_helpers.py:253`). Proven real: `typing.get_type_hints(m._hydrate_local_resources)` → `NameError` | Changed-file strict lint is **blocking** but sees only the diff; repo-wide `ruff check .` is **`continue-on-error: true`** (`ci.yml:181`); neither file is in the changed set | **Answer to the brief's question: yes — release-critical correctness findings demonstrably escape protection, with two live specimens.** Latent `NameError` on any `get_type_hints`/Pydantic-rebuild/FastAPI-response-model resolution | Import both under `if TYPE_CHECKING:`; then split ruff policy **by severity class, not by changed-ness**: `F821,F811,F822,E999` blocking repo-wide; the 378 style errors stay advisory with their burn-down note | `ruff check backend/ --select F821,F811,F822,E999` → 0 **and** the `get_type_hints` probe returns a dict for both | W3 (fix), W4 (policy) | blocking | b |
| **M-04** | S1 | Frontend mutation | CI: score **73.08** < break 75; 130 mutants = 95 killed / 21 survived / 14 no-coverage. Config mutates **exactly one file**, `src/lib/runtimeConfig.ts` (82 lines), **not modified by this candidate**; `"vitest": {"related": true}` | Two conflated problems: **hollowness** (a release gate whose scope is one unmodified 82-line file, while `frontend/src/lib/` has 12 modified files in this very candidate) and **brittleness** (3 mutants = 2.3 points; `related:true` makes no-coverage a test-*selection* artifact) | Release blocked by a gate measuring almost nothing; passing it would create false confidence about the frontend | **Never lower the threshold.** (1) Strengthen `runtimeConfig.test.ts` to kill the 21 and cover the 14, targeting ≥90 not the bare 75 (only 3 kills clear it — restore margin). (2) `related:false` for the mutated set. (3) Widen `mutate` to changed `src/lib/*Api.ts` **advisory-first**, blocking next release by owner decision | `npm run test:mutation` ≥75 in the node-24 lane, with the killed/survived/no-coverage **triple** recorded from the raw report, not the summary line | W3 (1), W4 (2,3) | blocking | b(scope analysis), a, c |
| **M-05** | S1 | UI acceptance | `qa-contract-stack`'s only container step is `docker compose … config --quiet`, which **parses and validates; it starts nothing**. No Playwright, no browser, no container runtime anywhere in CI. `qa-artifact.yml` builds artifacts without proving journeys | Compose-rendering was adopted as a proxy for stack health, then treated as evidence of user-journey health — a syntax check wearing a stack check's name | The repository has **zero** automated evidence that any user journey works in a browser, while carrying a Full UI Acceptance Contract demanding exactly that. Promoting today certifies behaviour never executed | Add a `ui-journeys` job that actually starts the QA stack (loopback-only), waits for health, and runs container-first Playwright suites; **rename `qa-contract-stack` → `qa-contract-render`** so its name states what it proves | Journeys on the frozen SHA across role × theme × 375px × keyboard × states, dated verdicts, deterministic screenshot/HAR paths, explicit `not_runnable` | W4 (define), W5 (execute) | blocking for changed surfaces | b, a, c |
| **M-06** | S1 | CI failure domains | `backend`: … → `Format check` → `Test`. `frontend`: `Lint` → `Type check` → `Unit` → `Mutation` → `Build`. One job per technology, not per failure domain | A step failure aborts every later step in the same job | **Actively costing information right now**: because format precedes test, *nobody knows whether the 2,329-test backend suite passes on the pushed SHA*. Each red run yields one datum instead of six; the release converges by serialised guessing | Split into independent jobs, none `needs:`-chained on a sibling quality gate (§D.1) | A deliberately injected format error yields red `backend-format` **and** green `backend-test` in the same run | W4 | blocking | b, a, c |
| **M-07** | S1 | Branch protection | `gh api …/branches/main/protection`: contexts `["governance"]`, `strict: true`, approvals **0**, code-owner **false**, `enforce_admins` **false**, `allow_force_pushes` **true**, linear history **false**. `ci.yml` defines 7 jobs — **6 of 7 are advisory at the merge gate** | Protection configured when `governance` was the only gate; never grew with the workflow | `main` is mergeable with a red backend, red frontend, failed mutation and failed QA — and force-pushable by an admin with zero reviews. Every other finding is unenforced at the boundary that matters | Owner applies the §D.2 context set, ≥1 approving review, code-owner review, `enforce_admins`, force-push off, linear history on, `strict` retained. **In-repo `ci.yml` edits cannot do this** | API read-back attached to the dossier + a negative test: a PR with a failing required context must be un-mergeable | W4 (prepare) / owner (apply) | blocking, owner-gated | a,b,c |
| **M-08** | S1 | Lifecycle truth | Of the 4 contradictory files, **3 are untracked**; **19** lifecycle files under `docs/build-stream/` are untracked (17 when the drafts were written — the count grew *during planning*). This initiative's own lifecycle file was untracked at draft time and was **committed mid-planning** (`3bdea267`), so it is now tracked but still carries `cf.tasks: []` while CF-SPEC-30 has live tasks. Contradictions: pi-capability-inheritance S3/in-progress still permitting dispatch; long-horizon S1/in-progress; benchmark-modernization S0/blocked **and** "Done/accepted"; systemwide-audit Done with open F-007 | Ledgers updated without status-block discipline; recent lifecycle docs never committed | The release's own narrative record does not exist in the release. "Reconciled ledgers" is unprovable, and the rule that newer records override older completion claims cannot be applied to files git has never seen | Resolve each initiative to exactly one of `included/excluded/superseded/completed/deferred(rationale)`; correct status blocks by **appending** a correcting entry, never rewriting; commit all lifecycle files in W1's explicit path list; populate `cf.tasks` | Reconciliation table in the dossier; every referenced lifecycle file tracked at the frozen SHA; no file claiming two stages | W1 (commit), W2 (truth) | blocking | b(untracked scope), a, c |
| **M-09** | S2 | CF task/spec debt | `task list --status open` → **181 open** (brief mentions only CF-SPEC-29's). CF-SPEC-29 has **13** open (CF-344…356). Non-terminal specs: CF-SPEC-19 `tasked`, 25 `tasked`, 28 `draft`, 29 `tasked`, 30 (this release). **CF-SPEC-30 SC-002 requires zero incomplete linked tasks at acceptance** — so CF-SPEC-29 is a hard dependency | Spec creation emits a fixed task template (`Validate US-001`, `Implement FR-00n`, `Prove SC-00n`); specs were accepted without closing generated children | "No open release-blocking CF tasks" is currently unprovable; and per the brief, staleness **must be proven, not assumed**, so 181 cannot be bulk-closed | Triage all 181 into `stale-administrative` (parent accepted, work evidenced elsewhere), `open-not-release-blocking` (deferred to a named future spec), `release-blocking` (close this release). **Every closure cites the evidence that satisfies it.** Explicit disposition for CF-SPEC-19/25/28/29 | Triage table, one row per task; zero in `release-blocking` at freeze; `next` no longer points at unresolved CF-SPEC-29 work | W2 | blocking for the release-blocking bucket | b, c |
| **M-10** | S2 | CF impact capability — **the brief is wrong** | Bare `impact` → `{"code":"not_yet_native"}`. **`intelligence impact --path <p>` works**: `confidence.level "high"`, `corpus {graph_version 2, kernel "rust", source "tree-sitter"}`. `index status`: `index_version 12`, `kernel "rust"`, `warnings []`. Fields `resolution`, `answer_completeness`, `freshness`, `graph_usable` **do not exist** in this build | The capability was **renamed**, not lost; `index_version 12` is what the current Rust kernel itself writes | A wave reading "refresh until `graph_usable=true`, then run `impact`" is **unexecutable**: no refresh changes `index_version` to 21 and bare `impact` never succeeds. **Drafts a and c both inherited this and would each have burned a wave**; a reviewer would report nonexistent fields as missing evidence | Waves call `intelligence impact --path <p>` (`--paths` is rejected) and read `confidence` + `corpus.source`; freshness is asserted via `index status` (`created_at` newer than the last source commit, `warnings: []`). Record the migration in the decision log so later agents do not re-derive it | `index status` fresh with no warnings on the frozen SHA; one recorded `intelligence impact --path` per changed architectural surface | W2 | blocking (the plan must be executable) | b, **syn** (re-verified) |
| **M-11** | S2 | Backend format + toolchain drift | `ruff format --check .` → **15 files** would be reformatted (repo venv ruff **0.16.4**); CI resolved **0.16.6** and saw **2** at `9961fa3d`. `backend/pyproject.toml:62` pins `ruff>=0.8.0` — a floating floor | No format-on-commit hook; formatter version free to drift between machines and CI | CI backend job fails and (via M-06) the functional suite never runs; format results are not reproducible across machines | `ruff format` once with the **pinned** version and commit; **pin ruff exactly** in dev deps to the version CI resolves; document the pin; add the pre-commit hook | `ruff format --check .` exit 0 on the Promotion SHA, locally **and** in CI, with `ruff --version` recorded alongside | W3 | blocking | c(pin), a,b(count) |
| **M-12** | S2 | Security evidence currency | `git diff -- security/` → +6 lines: `routes/audit.py` and `routes/metrics.py` added to **two** control scopes, plus `core/audit_middleware.py` and `VersionHistory.tsx`; `SECURITY_BENCHMARK.md` +1 | Audit/metrics surfaces brought under existing controls — a scope widening | The Istara contract makes the benchmark mandatory when a control's evidence path changes. The known-passing 28/28 **predates the frozen SHA and cannot be extrapolated to it** | Re-run `security_benchmark.py --fail-on-threshold` on the frozen SHA; confirm `tests/test_security_benchmark.py` covers the added paths; confirm the newly scoped routes **genuinely implement** the controls claimed rather than merely being listed | 28/28 (or higher denominator) on the Promotion SHA; scorecard attached | W3 (verify), W6 (re-run) | blocking | b |
| **M-13** | S2 | `governance` writes to `main` | `ci.yml:60` `contents: write`; `ci.yml:87` `git push origin HEAD:main`, guarded to `push` on `main` | README badge sync predates the protection design | A CI job writes to the release branch, weakening "merged code" as a distinct stage — and `governance` is today's **sole required check**, so it is the highest-value target in the repository. **Under M-07's `enforce_admins` + linear history this push will start failing**, so it must be fixed *before* the settings change | Move badge sync to a separate workflow with narrow permissions, or make it open a PR; the required check itself becomes `contents: read` | `governance` runs read-only; no direct-to-main push step remains; badge sync still works | W4 | **blocking before W5** | c(escalation), b(analysis) |
| **M-14** | S2 | Plan of record is unauditable | Task payload pins `wave_manifest_sha256 8601a1fc…`; `shasum -a 256` on the file gives `dd54b849…`. Canonicalisation probe: `json.dumps(obj, sort_keys=True, separators=(',',':'))` → **`8601a1fc…` match**. File mtime precedes task creation, so nothing mutated it. Separately, `.gitignore:142` ignores `.compass-forge/` | The hash is over canonical compact sorted JSON, documented nowhere; and the manifest lives in an ignored directory | Every reviewer who verifies the obvious way computes a mismatch and concludes tampering — **a false alarm in the one mechanism whose job is detecting tampering**. And the frozen SHA **does not contain the plan it was frozen against** | Document the canonicalisation beside the manifest; ship `scripts/verify_wave_manifest.py`; **export the approved manifest to a tracked `docs/build-stream/` path at freeze** and pin its canonical hash in the lifecycle status block | `verify_wave_manifest.py` exits 0; the tracked export exists at the frozen SHA | W1 | blocking (the tracked export) | b |
| **M-15** | S2 | Release hygiene | `git diff --check origin/main` → **295** trailing-whitespace / blank-line-at-EOF findings. Concentration: `2026-09-05-testing-branch-readiness…` (63), `2026-09-06-core-ux-research-spine…` (29), `long-horizon-agentic-engine-audit.md` (18). Code files: `test_stress_test_dataset.py`, `test_reports.py`, `test_code_applications.py`, `ChatView.tsx` | No whitespace hygiene gate; agent-authored Markdown carries trailing spaces | Explicit release-hygiene criterion fails; noise obscures real diffs | Strip trailing whitespace on affected files; add `git diff --check` to the pre-commit hook and a fast CI hygiene step. **Ledgers are append-only, so whitespace repair of historical ledger prose is a content edit** — restrict to non-ledger regions or record the touch in the decision log | `git diff --check origin/main` → empty on the frozen SHA | W3 | blocking | b,c,a |
| **M-16** | S2 | Lint measurement integrity — **resolves the K-2 draft conflict** | `npm run lint` → 315 problems / **233 errors**. **232 of them are inside `frontend/.stryker-tmp/sandbox-2OnHq3/`** (created 2026-09-09 11:12 by a failed local Stryker run). Real product errors: **1** — `ChatModelControls.tsx:20`, `interface ModelChoice extends ChatModelChoice {}`, `@typescript-eslint/no-empty-object-type`. `.stryker-tmp/` is gitignored (`.gitignore:64`) but **not** eslint-ignored; `eslint .` scans it. CI checks out clean, so CI's blocking lint passed | A generated sandbox is excluded from git but not from the linter, and a *failed* mutation run leaves it behind | **A principal architect (draft a) reported 233 release-blocking lint errors and "a defect materially wider than the empty-interface error."** The real fix is one line. Any developer or agent linting after a mutation run gets ~200 phantom errors and mis-scopes the release | (1) Fix the one real error: `type ModelChoice = ChatModelChoice;` (verify the two use sites at lines 246, 257). (2) **Add `.stryker-tmp/` to the eslint ignore list** so gitignored generated output cannot be linted. (3) Every local lint/mutation number in evidence records whether the sandbox was present | `npm run lint` → 0 errors with a clean tree **and** with a sandbox present; `npx tsc --noEmit` clean | W3 | blocking | **syn** (adjudicates a vs b,c) |
| **M-17** | S3 | Local mutation environment | `@stryker-mutator/core` 9.6.1 and `vitest-runner` 9.6.1 (peer vitest `>=2.0.0`), `vitest` 4.1.11 — **all peers satisfied**, so the plugin-init failure is *not* a version mismatch. Local `node -v` = **v26.0.0**; `ci.yml` pins **node 24** | Loader/ESM behaviour under an unpinned node major two releases ahead of CI | The local environment is **not authoritative** for mutation results — correctly distinguishing this from the genuine remote 73.08 failure, as the brief requires. The failed run also leaves the M-16 sandbox behind | Treat CI (node 24, `npm ci`) as the authoritative mutation lane; verify fixes there or in a node-24 container; add `.nvmrc`/`engines` pinning node 24. Bounded `npm ci` reinstall is permitted (generated dir) with an owner-visible ledger note | Mutation runs clean in the node-24 lane; `node -v` recorded beside every local frontend result | W3 | non-blocking for promotion; **blocking for trusting any local mutation number** | b, c |
| **M-18** | S3 | Desktop release status | `desktop` job is `continue-on-error: true` ("Dependencies may require system libs not available in CI"); it reported green in run 34039897688 **without proving compilation** | Ubuntu runner lacks Tauri system deps | The desktop surface has no defined release status — neither proven nor formally out of scope; a misleading green | Explicit owner decision recorded in the dossier: **(a)** in scope — add the system libs and make `cargo check` blocking; or **(b)** out of scope — excluded from required checks and stated in `TESTING.md` and the dossier. `continue-on-error` is not an acceptable release status | The dossier states the decision; the context name makes it obvious in the PR UI | W4 (prepare) / owner (decide) | deferred; **decision required before promotion** | b, c, a |
| **M-19** | S3 | Moving candidate surface | Brief: 4706 insertions / 118 untracked. Drafts b and c: **4712 / 119**. Base moved `85f64e4d` → `50c4d493` during the planning phase | The worktree is a live shared checkout that agents and the owner both write to | Any measurement not tied to a SHA is stale on arrival; two reviewers can legitimately disagree about the candidate — the exact ambiguity this release exists to end | W1 freezes first and measures afterwards; every evidence row records its SHA; the supervisor rejects SHA-less evidence. Between freeze and promotion the owner is asked to avoid writes, or accept re-freeze | Re-running the W1 measurements on the Base SHA reproduces identical numbers | W1 | blocking (procedural) | b, **syn** (confirmed in the act) |
| **M-20** | S3 | Required-check contract rot | Only `governance` is required while 13 jobs exist; nothing verifies that required contexts match job names | No contract between the workflow graph and the protection settings | Required-check rot and stale green; a renamed job silently stops being enforced | `scripts/check_required_checks.py` (or extend `check_ci_governance.py`): parse `ci.yml` job ids and compare against a committed required-checks manifest, which W5's owner settings change consumes verbatim | New check green; manifest committed and equal to the applied protection | W4 | **blocking before W5** | c |
| **M-21** | S3 | Spec/doc drift | `docs/architecture/research-validity-contract.md` header cites "CF-SPEC-124 / CF-1590"; no such objects exist (max task id 413) | Doc written against a planned/external numbering | Truth drift in a protected-contract document | Correct the header reference; content otherwise untouched | Grep shows only valid references | W2 | non-blocking | c |
| **M-22** | S3 | Research corpus scan surface | ~71 untracked `tests/document_corpus/rich/**` fixtures + generator. The audit's `RAW_SOURCE_FORBIDDEN` (rejecting `## Evidence unit candidate`, `Coding hints:`, `Implication candidate:`) and `scan_repeated_source_excerpts` run over **tracked files only** | A large document corpus is exactly the shape of change that can introduce pre-digested evidence — sources already containing conclusions | Synthesized prose could enter as if it were a raw source span; and the defence **says nothing about the corpus until W1 commits it** | Classify as test fixtures (`tests/` only, never product data); verify generator-authored/synthetic; **re-run the audit after the W1 commit**, when its scan surface grows | Audit green post-commit; corpus reproducible from its generator; fixtures confined to `tests/` | W1, W5 | blocking (inclusion) | b(scan surface), c(classification) |
| **M-23** | S3 | Promotion mechanics | `main` tip is 2026-05-27; the promotion is a 994-commit, ~1,400-file, ~+264.9k/−15.0k fast-forward. `main`'s workflow predates the current architecture | Long-lived divergent testing branch | Big-bang blast radius; **`main`'s historic green runs are not evidence about this candidate** | Full matrix on the exact Promotion SHA; the dossier carries a "main promotion mechanics" section. Owner chooses fast-forward vs `--no-ff` (recommendation: `--no-ff` for an auditable promotion point) + a post-merge `main` CI run | Dossier section present; owner decision recorded | W6 | owner-decision | c, a |
| **M-24** | S4 | Lint debt visibility | `ruff check . --statistics` advisory with **378** pre-existing style errors (E501/E402/UP042/E712/N806/F841) | Historical debt under an advisory posture | Style debt cannot hide correctness (M-03 fixes that class), but it remains invisible under a green required context | Keep the documented burn-down; flip global lint to blocking once the count reaches zero — **never by deleting rules** | `ruff check .` blocking green in a future release | post-release | deferred | b, c |

**Register summary:** 8 × S1 (M-01…M-08) · 8 × S2 (M-09…M-16) · 7 × S3 (M-17…M-23) · 1 × S4 (M-24).
Promotion is blocked until every S1 and S2 is closed or explicitly owner-accepted with rationale.

**Findings dropped or downgraded during synthesis (recorded so the reviewer can check the reasoning):**
draft a's "233 frontend lint errors / 82 warnings, materially wider than briefed" is **downgraded to
one error** and re-filed as M-16 (measurement-integrity defect) per K-2; draft a's and draft c's
"refresh the CF index to schema 21 / until `graph_usable=true`" is **removed as unexecutable** and
re-filed as M-10 per K-3; draft a's "scanner/input discrepancy requires diagnosis" is **replaced** by
M-02's root cause per K-4.

---

## C. Strict-wave manifest

Six strictly sequential waves, using **the conductor's existing manifest ids verbatim**
(`candidate-boundary`, `control-plane-lifecycle`, `correctness-quality`, `ci-enforcement`,
`browser-spine-acceptance`, `promotion-certification`) so the plan drops into the pipeline unchanged.
Draft c argued for splitting `correctness-quality` and `ci-enforcement` into four waves because
mutation work and owner-gated settings have different rollback shapes. That argument is **preserved
as internal phase boundaries** (W3a/W3b, W4a/W4b) rather than as new wave ids: each phase is a
separate reviewable commit set with its own rollback, but the manifest contract with the conductor
is not broken.

Each wave begins with a CF before-gate and work order, and ends with command evidence, an independent
review, an after-gate, a ledger entry, and a commit. Reviewer findings become **separate remediation
tasks with delta re-reviews**, never in-wave edits. The stream pauses for owner approval before W1,
and again before every outward operation in W4b and W6.

---

### W1 — `candidate-boundary`

**Objective.** Convert three ambiguous surfaces into one classified, committed, dependency-closed,
frozen boundary, losing nothing and accidentally including nothing.

**Scope.** Recovery snapshot; classification of 155 modified + 119 untracked paths; dependency-closure
proof; commit of `INCLUDE-*` paths; tracked export of the wave manifest; pre-commit hygiene hook.

**Inputs.** §A.3 algorithm; lifecycle ledgers; CF task list; M-01, M-08, M-14, M-19, M-22.

**Explicit exclusions.** No source repair (W3). No CI edits (W4). No CF task closure (W2). No push.
No branch creation beyond `backup/` and `quarantine/`. **No deletion of anything, ever.**

**Tasks.**
1. Step-0 recovery snapshot (bundle + tracked patch + untracked tarball + status + CF `state backup`),
   stored outside the repository; **restore-verify into a scratch clone before proceeding**.
2. Create `backup/pre-candidate-20260909` and `quarantine/ambient-20260909`.
3. Produce the classification TSV — one row per path with bucket, evidence citation, and sha256.
4. **Dependency-closure proof** (M-01): staged candidate resolves every import specifier.
5. Owner review of the `UNDECIDED` bucket — **owner-gated pause**; unruled paths default to quarantine.
6. Resolve the 17 untracked lifecycle files (M-08); commit those that are truth about included work.
7. Export the approved wave manifest to a tracked `docs/build-stream/` path; document the canonical
   hash recipe; add `scripts/verify_wave_manifest.py` (M-14).
8. Install the pre-commit hook: public-quality audit + `git diff --check` (M-02, M-15).
9. Commit via `git add --pathspec-from-file` only. Record start and end SHAs → **Candidate Base SHA**.
10. **Re-run the public-quality audit *after* the commit** — its scan surface just grew (M-02, M-22).

**Dependencies.** Owner approval of this master plan. Repository completion lock held for commits.

**Verification.** `git status --porcelain` residue is only `EXCLUDE-*`/`QUARANTINE`/`UNDECIDED`, each
accounted for in the TSV; `npx tsc --noEmit` resolves every specifier; `git stash list` unchanged;
`LLMs/` and `Model_Finetuning/` byte-identical and never enumerated; the recovery bundle restores in a
scratch clone; classification row count equals the measured path count; `git fsck --full` clean;
`verify_wave_manifest.py` exits 0; `pytest tests/test_public_repo_quality.py` re-run post-commit.

**CF gates/evidence.** `architecture_drift` and `test_ownership` before/after; `command` rows for
snapshot, classification, closure proof, commit; TSV attached; start/end SHAs recorded.

**Review questions.** Is every included path justified by cited evidence? Could any excluded path be
required by an included one — and was that tested rather than assumed? Does the recovery snapshot
demonstrably restore? Was `git add -A` used anywhere? Are protected directories untouched? Did the
audit re-run *after* the commit?

**Completion.** One commit whose contents are fully explained by the TSV; Base SHA recorded.

**Rollback.** Revert the commit; restore from bundle + tarball. The shared worktree is never cleaned.

**Residual risks.** Classification is judgement-based; the `UNDECIDED` bucket may be large and the
owner pause may block for a long time; provenance ambiguity is resolved by exclusion, never assumption.

---

### W2 — `control-plane-lifecycle`

**Objective.** Make Git, Build Stream, Compass Forge, and CI tell one true, provable story about the
candidate — without falsifying history.

**Scope.** Index freshness; the 181-task triage; CF-SPEC-19/25/28/29/30 dispositions; lifecycle status
reconciliation; `intelligence impact` per changed architectural surface; M-21 doc drift.

**Inputs.** W1 commit; M-08, M-09, M-10, M-21.

**Explicit exclusions.** No code repair. No CI edits. **No bulk task closure without cited evidence.**
**No chasing a schema-21 index target and no use of bare `impact`** (M-10). No CF history rewrite.

**Tasks.**
1. Refresh the index; assert `index status` → `warnings: []`, `created_at` newer than the W1 commit.
   Record `index_version`/`kernel` **as observed** — do not chase schema 21 (M-10).
2. Record the `impact` → `intelligence impact --path` migration in the decision log so later agents
   do not re-derive it.
3. Run `intelligence impact --path <p>` per changed architectural surface; record `confidence` and
   `corpus.source`; **then follow dependencies manually**, because the static graph misses dynamic
   dispatch and string-keyed routes. Do not believe the output beyond its stated confidence.
4. Triage all 181 open tasks into the three buckets; close `stale-administrative` **with citations**.
5. Explicit disposition for CF-SPEC-19/25/28/29; drive CF-SPEC-30 to `tasked` with real tasks.
   CF-SPEC-29's 13 open tasks are a hard dependency of SC-002 (M-09).
6. Reconcile every recent lifecycle file to exactly one status by **appending** corrections; populate
   `cf.tasks` in the convergence file.
7. Correct the `research-validity-contract.md` header reference (M-21).
8. Build the changed-path → obligation matrix (owning tests, docs, scenarios, security triggers,
   research paths) that W3 and W5 consume — draft a's contribution, folded in here rather than
   given its own wave.

**Dependencies.** W1.

**Verification.** `index status` fresh, no warnings; one recorded `intelligence impact --path` per
surface; `task list --status open` contains zero release-blocking tasks; triage table with one row per
task; no lifecycle file claiming two stages; `python scripts/check_integrity.py` green; the obligation
matrix has no unowned changed path.

**CF gates/evidence.** `command` rows per refresh/impact/triage; triage table and obligation matrix
attached.

**Review questions.** Is each closure evidenced or merely asserted? Does any closed task hide real
work? Do lifecycle statuses match the W1 classification? Was graph output believed beyond its
`confidence`? Were dynamic/string-keyed routes swept textually?

**Completion.** "No open release-blocking CF tasks" is provable from evidence rows alone.

**Rollback.** Task closure is reversible in CF; lifecycle corrections are append-only entries; restore
the native CF backup if state is damaged.

**Residual risks.** 181 tasks is a large manual triage; misclassifying a real blocker as
administrative is the principal danger — mitigated by requiring an evidence citation per closure. A
genuinely unfinished CF-SPEC-29 obligation becomes a **new blocking task**, never a cosmetic closure.

---

### W3 — `correctness-quality`

**Objective.** Repair every blocking correctness, format, lint, hygiene, mutation, and security
failure at **root cause**, with no threshold touched.

**Two phases, separately reviewable and revertible** (draft c's split, preserved internally):

**W3a — mechanical and correctness repairs.** M-02 (text), M-03, M-11, M-15, M-16, M-12 (verify).
**W3b — mutation quality and harness.** M-04 step 1, M-17.

**Inputs.** W1 commit; W2 obligation matrix and impact results.

**Explicit exclusions.** No CI restructuring (W4). No browser work (W5). **No threshold lowering, no
mutation-scope shrinking, no `continue-on-error` added, no test deletion, no skip, no blanket unsafe
autofix, and no editing of the public-quality audit** to obtain green.

**Tasks (W3a).**
1. Repo-relative path repair at `AGENTS.md:142` and the pi-capability lifecycle file — never edit the
   audit (M-02); sweep all tracked files for the substring before committing.
2. `TYPE_CHECKING` imports for `BudgetAllocation` and `ComputeNode`; **re-run the `get_type_hints`
   probe as the acceptance test**, not merely ruff falling silent (M-03).
3. Pin ruff exactly to the CI-resolved version, then `ruff format` the 15 files (M-11).
4. `ModelChoice` → `type ModelChoice = ChatModelChoice;`; verify use sites at lines 246, 257 (M-16).
5. Add `.stryker-tmp/` to the eslint ignore list (M-16).
6. Strip trailing whitespace, **excluding historical ledger prose** (M-15).
7. Re-run the security benchmark for the changed control matrix and confirm the newly scoped routes
   genuinely implement their claimed controls (M-12).
8. Run the **full** backend suite — the first run in this release able to see past the format gate.

**Tasks (W3b).**
9. Strengthen `runtimeConfig.test.ts` to kill the 21 survivors and cover the 14 no-coverage mutants,
   targeting ≥90 rather than the bare 75, so margin is restored (M-04).
10. Where a surviving mutant reveals a real bug, **fix the implementation** with its own test —
    `runtimeConfig.ts` covers origin/websocket URL derivation, which is auth-adjacent (c).
11. Pin node 24 via `.nvmrc`/`engines`; bounded `npm ci` reinstall with an owner-visible ledger note;
    re-verify mutation in the node-24 lane (M-17).

**Dependencies.** W1, W2.

**Verification.**
```
ruff format --check .                                        → clean   (pinned ruff, version recorded)
ruff check backend/ --select F821,F811,F822,E999             → 0
python -c "…get_type_hints probe on both functions…"         → returns dict, both
pytest ../tests/ -q -m "not live_llm"                        → 0 failed  (baseline 2329 passed/5 skipped)
pytest tests/test_public_repo_quality.py -q                  → passed
git diff --check origin/main                                 → empty
npm run lint && npx tsc --noEmit && npm run test:unit        → clean, 89/89   (node 24)
npm run test:mutation                                        → ≥75, target ≥90, triple recorded
python scripts/run_backend_mutation.py                       → pass
python scripts/security_benchmark.py --fail-on-threshold     → 28/28
```

**CF gates/evidence.** One `command` row per line above, each recording the SHA it ran against and,
for frontend rows, `node -v` and whether a Stryker sandbox was present (M-16, M-17).

**Review questions.** Was any fix a suppression? Did the mutation score rise from real behavioural
assertions or from tautological tests / narrowed scope? Was the score recomputed from the **raw
report** rather than the summary line? Does the backend suite pass now that formatting no longer masks
it? Were the F821 fixes verified **by execution**? Does the pinned ruff match CI's resolved version?

**Completion.** Every credential-free blocking check is green on one commit.

**Rollback.** Each task is an independent revertible commit; thresholds were never moved.

**Residual risks.** **W3 is the wave most likely to expand**: the full backend suite has never been
observed green on this candidate, because formatting aborts the job before it runs. Failures may be
hiding behind that gate.

---

### W4 — `ci-enforcement`

**Objective.** Make CI represent the architecture, and prepare — but never apply — the owner-gated
protection change.

**Two phases** (draft c's split, preserved internally):
**W4a — in-repo workflow redesign.** M-06, M-03 (policy), M-04 (steps 2–3), M-05 (define), M-13,
M-15/M-02 (hygiene job), M-18, M-20.
**W4b — the owner-gated settings package.** M-07: prepare an exact, reviewed request body; the owner
applies it. **No agent mutates repository settings.**

**Inputs.** W3's green candidate.

**Explicit exclusions.** **No repository-setting mutation.** No weakening of any existing check. No
new `continue-on-error` on a correctness gate. No threshold reduction. No live-credential lane.

**Tasks (W4a).**
1. Split `backend`/`frontend` into independent failure-domain jobs (§D.1, M-06).
2. Promote repo-wide `F821,F811,F822,E999` to blocking; keep the 378-error style backlog advisory with
   its burn-down note (M-03).
3. Add a fast `hygiene` job: public-quality audit + `git diff --check`.
4. Widen mutation scope advisory-first with its own threshold; set `related:false` (M-04).
5. Rename `qa-contract-stack` → `qa-contract-render`; define the `ui-journeys` job (executed in W5).
6. Remove the direct-to-`main` badge push; `governance` becomes `contents: read` (M-13).
7. Add `scripts/check_required_checks.py` + the committed required-checks manifest (M-20).
8. Record the desktop decision (M-18).
9. Update `TESTING.md` and `testing/TEST_HISTORY.md` — CI topology is changing.

**Tasks (W4b).**
10. Draft the exact `gh api` protection body listing every required context from §D.2.
11. Sequence the change with the owner (see the hazard below) and verify by API read-back afterwards.

**Dependencies.** W3. W4b additionally depends on M-13 being fixed, or the owner's own pushes break.

**Verification.** `check_ci_governance.py`, `check_workflow_contracts.py`, `check_required_checks.py`
pass; `actionlint` if repository-pinned; **a deliberately injected format error yields red
`backend-format` and green `backend-test` in one run** (the M-06 acceptance test); a docs-only test
failure does not mask backend results; the protection body is reviewed and attached, **unapplied**;
after the owner applies it, an API read-back plus a negative mergeability test.

**CF gates/evidence.** `command` rows; the protection request body attached as an artifact; the
API read-back JSON (tokens excluded) attached to the dossier.

**Review questions.** Can any correctness class still escape — the M-03 question, re-asked of the new
design? Does any job silently `needs:` a sibling quality gate? Could a required check pass while its
domain is broken? Does the required-context list exactly match the job names after renaming? Can a
cancelled or unexpectedly skipped job yield a misleading green?

**Completion.** A push produces a complete, independent failure picture, and the protection change is
queued for the owner.

**Rollback.** `ci.yml` is one file; revert restores prior behaviour. No external state was changed by
any agent.

**Residual risks.** **The single most dangerous step in the plan:** job renames invalidate existing
required contexts, so `main` can be left requiring a context that no longer exists (unmergeable) or
briefly unprotected. Old contexts must be retained until the replacements have been observed on
GitHub, and the protection update must be sequenced explicitly with the owner in one action. Runner
cost also grows with the browser lane (mitigated in §D.5).

---

### W5 — `browser-spine-acceptance`

**Objective.** Prove the changed system in a real browser, and prove the Research Spine is not
bypassable — with honest capability reporting.

**Scope.** Container-first Playwright journeys for changed surfaces; Research Spine probes; scenario
registry, coverage matrix, `TESTING.md`, `testing/TEST_HISTORY.md`.

**Inputs.** W2's obligation matrix; W4's `ui-journeys` job; W1's list of changed product behaviour.

**Explicit exclusions.** **No live model or provider execution. No server started outside the
container lane. No golden-data mutation** — synthetic data only. **No API-only step presented as a
browser journey.** No secrets, endpoints, or fingerprints exposed or persisted.

**Tasks.**
1. Stand up the QA stack via `docker-compose.qa.yml --profile ui` with **loopback-only publication**;
   wait for health; execute journeys for each changed behaviour — the chat model-control work, metrics
   and quality views, and the auth/token paths touched by the untracked `tokenStore` module.
2. Cover admin/researcher/viewer/stranger for auth-adjacent changes; light and dark; 375px reflow;
   Tab order and visible focus; loading, error, and empty states.
3. Research Spine probes for touched research paths (§F), including the M-22 corpus.
4. Donor/model-management probes for donated-compute paths; team/persona extensions where relevant.
5. Emit dated verdicts and deterministic screenshot/HAR/console/network paths keyed by SHA; emit
   explicit `not_runnable` **naming the missing capability** wherever a live dependency is absent.
6. Update the scenario registry, coverage matrix, `TESTING.md`, and `testing/TEST_HISTORY.md`.

**Dependencies.** W4a.

**Verification.** Each journey has a dated verdict and artifacts; every `not_runnable` names its
missing capability; no journey asserts on an API response in place of a rendered UI state; publication
is loopback-only (port inspection); teardown touches only the named synthetic QA project and volumes.

**CF gates/evidence.** `command` rows per journey batch; artifact paths recorded.

**Review questions.** Does each journey actually navigate, click, fill, upload, and send? Is any step
an API call in disguise — the M-05 failure mode, re-asked of the new suite? Is any `not_runnable`
concealing a real failure? Was golden data touched? Are provisional states and report gating visible
in the UI evidence?

**Completion.** Every changed behaviour has a real browser verdict, or an explicit, owner-visible
`not_runnable`.

**Rollback.** Test-only wave; revert the additions. Journey failures block promotion — they are fixed
(looping to W3) or owner-accepted as deferred with rationale.

**Residual risks.** **W5 is the largest unknown effort in the plan** and the wave most likely to
discover genuine product bugs, which loop back to W3. Flaky selectors are fixed as part of the
feature, per the repository's own contract.

---

### W6 — `promotion-certification`

**Objective.** Freeze one SHA, independently re-prove every release claim, and produce a binary,
owner-gated verdict.

**Scope.** Freeze; full re-verification on the frozen SHA; blind independent review; remediation and
delta re-review until dry; dossier; owner-gated push and PR.

**Inputs.** W1–W5, plus the owner's protection action.

**Explicit exclusions.** **No merge. No push to `main`. No PR unless separately authorized. No
repository-setting change. No source change without invalidating the freeze.**

**Tasks.**
1. Freeze the **Promotion SHA**; record it in the CF spec, lifecycle status block, and dossier (§A.4).
2. Re-run the **entire** §E matrix on the frozen SHA. Earlier results do not transfer.
3. **Owner-gated:** fast-forward push `testing`; confirm every required check green on that exact SHA
   via `gh run list --commit <SHA>` with `headSha` equality.
4. Blind independent architectural/code/security review scoped to `git diff origin/testing..<SHA>`
   plus the wave commits (the full `origin/main..<SHA>` delta is too large to review file-by-file);
   remediate; delta re-review until no S1/S2 remains.
5. Confirm the owner applied the protection change (M-07); re-read the endpoint as evidence.
6. Build release artifacts, SBOM, checksums, manifests bound to the SHA; **download and inspect them**
   rather than trusting that the build step succeeded.
7. Assemble the dossier (§H) — including the M-23 main-merge mechanics recommendation — and stop.

**Dependencies.** W1–W5; owner protection action; separate authorization for push and PR.

**Verification.** Every §E row marked `Re` has a result tied to the Promotion SHA;
`git rev-parse testing == PROMOTION_SHA` at dossier close; CF after-gates `architecture_drift` and
`test_ownership`; spec coverage/drift for CF-SPEC-30; `review_verdict` rows with no open findings.

**CF gates/evidence.** Full evidence set on the Promotion SHA; verdict rows; the dossier.

**Review questions.** Is every claim tied to the frozen SHA? Did anything move after the freeze? Is
any "green" inherited from an ancestor SHA or an earlier run? Can a reviewer reproduce the results
without relying on implementer claims? Does any unverified claim appear as confirmed?

**Completion.** A dossier stating **READY** or **NOT READY**, with owner approval outstanding.

**Rollback.** Abandon the SHA; record the invalidation reason; reopen the earliest affected wave and
issue a superseding dossier. `main` is untouched.

**Residual risks.** Any post-freeze commit forces a full re-freeze and re-verification. Late review
findings remediate inside W6 via delta re-review, or reopen a wave if scope changes.

---

## D. CI target architecture

### D.1 Job graph

```
                          ┌── hygiene              (public-quality audit + git diff --check)  blocking
                          ├── governance           (integrity, CI-gov, security; contents: READ) blocking
                          ├── feature-obligations                                              blocking
                          ├── backend-format ─┐
   push / PR ─────────────┼── backend-lint    ├── independent; none gating a sibling
                          ├── backend-test    │
                          ├── backend-mutation┘
                          ├── frontend-lint      ─┐
                          ├── frontend-typecheck  │
                          ├── frontend-unit       ├── independent
                          ├── frontend-mutation   │
                          ├── frontend-build     ─┘
                          ├── test-harness-js                                                  blocking
                          ├── qa-contract-render  (compose parse only — named honestly)
                          ├── ui-journeys         needs: qa-contract-render                    blocking
                          └── desktop-check       per M-18 owner decision
                                    │
                                    └── release-gate   if: always(); fails on any required
                                                       job failed / cancelled / unexpectedly skipped
```

**Independence rule.** No job may `needs:` a job whose failure is not a true precondition. The only
retained edge is `ui-journeys → qa-contract-render` (a stack that does not render cannot start).
**No quality gate gates another quality gate** — that is M-06's root cause.

**`release-gate`** (draft a's fail-closed aggregator) validates producer run ids and SHA, never trusts
a previous run or a branch-level status, and fails on cancellation or unexplained skip. Requiring the
aggregator **plus** the granular contexts gives both a single protectable gate and per-domain
diagnosis; the workflow file is CODEOWNERS-protected.

### D.2 Required checks

| Context | testing | main |
|---|---|---|
| `hygiene`, `governance`, `feature-obligations` | required | required |
| `backend-format`, `backend-lint`, `backend-test`, `backend-mutation` | required | required |
| `frontend-lint`, `frontend-typecheck`, `frontend-unit`, `frontend-build`, `frontend-mutation` | required | required |
| `test-harness-js`, `qa-contract-render` | required | required |
| `ui-journeys` | required on PR | required |
| `desktop-check` | per M-18 | per M-18 |
| `release-gate` | required | required |

Plus, on `main`: ≥1 approving review, code-owner review, dismiss-stale approvals, `enforce_admins` on,
force pushes off, linear history on, `strict` retained (it is already `true` — the one bright spot in
the current settings). **All of this is an owner action (§G).** The committed required-checks manifest
(M-20) is the single source consumed by that action.

### D.3 Event behaviour

- **PR** to `main`/`testing`/`staging`: full graph including `ui-journeys` and change-obligation checks.
- **Push to `testing`**: full graph — `testing` is the promotion source and must never carry an
  unproven SHA.
- **Push to `main`**: full graph. Badge sync no longer pushes from the required check (M-13).
- **Scheduled (weekly)**: full graph plus the wider mutation scope and the full journey matrix, so
  expensive coverage exists without lengthening PR latency and runner-image/dependency rot is caught.
  Required checks never depend on push-only or schedule-only paths.

### D.4 Change-scoped vs full-suite

Change-scoping is allowed for **cost**, never for a **correctness class**. Concretely:
`check_ruff_changed` keeps its blocking changed-file role **and** the correctness subset runs
repo-wide and blocking (M-03). Journey selection may be registry-tag-scoped on ordinary PRs to
`testing` only — never on PRs to `main`, never on pushes. **The frozen SHA always runs the full
matrix**; this promotion is a 994-commit event, where scoping would be false economy.

### D.5 Caches, artifacts, retention

Per-job `npm`/`pip`/`cargo` caches keyed by OS, runtime version, lockfile hash, and tool config; never
cache workspaces or results; no cache shared across a trust boundary. Artifact boundaries separate
test reports, mutation reports, security scorecard, browser evidence (screenshots/HAR/console), and
release binaries. **Every artifact embeds the SHA in its path** so it can never be mistaken for
another commit's. Release-evidence artifacts retain ≥90 days; the dossier additionally copies key
summaries into `docs/promotion/` so evidence survives artifact expiry.

### D.6 Mutation policy

`break: 75` is **never lowered**; `high: 90` / `low: 80` unchanged. Score improves via tests, or via
implementation fixes where a survivor reveals a real bug. Scope expands **advisory-first**, then
becomes blocking by explicit owner decision — so widening never silently blocks a release on a number
nobody has seen. No-coverage mutants count as failures and the in-scope target is zero. Every result
records the **killed/survived/no-coverage triple**: the composite score alone hid M-04's real shape.
The mutated scope never shrinks to pass.

### D.7 Formatting and lint policy

Formatting is blocking but **in its own job**, so it can never again hide the test suite. The
formatter version is **pinned exactly**, not floored, so results are reproducible across machines
(M-11). Lint is split **by severity class**: correctness classes (`F821,F811,F822,E999`) blocking
repo-wide; the 378-error style backlog advisory with its documented burn-down. **No correctness class
is ever advisory.** Generated directories that git ignores are also lint-ignored (M-16). The
`git diff --check` hygiene guard is blocking.

### D.8 Credential-free and live lanes

The credential-free lane is the default and is what gates the release. The live lane (live-LLM evals,
donor compute, private providers) is opt-in, owner-authorized, bounded to one configured target, never
runs on PR, and **fails closed as `not_runnable` naming the missing capability**. A `not_runnable` is
never counted as a pass and never silently omitted from the dossier; its absence can never turn a
required context green.

### D.9 Containers, desktop, stale-green prevention

`ui-journeys` runs container-first with loopback-only publication and synthetic data only. Desktop
status is **decided** per M-18 rather than left `continue-on-error` forever; whichever way the owner
decides, `TESTING.md`, the context name, and the dossier state it.

Stale or misleading green is prevented by six mechanisms: `strict: true` keeps branches current; the
`release-gate` aggregator is fail-closed on failure, cancellation, and unexplained skip; the
required-checks manifest is contract-checked in CI, so renaming a job fails until the manifest is
updated (M-20); every required context maps to a job that actually executes its domain — which is why
`qa-contract-render` is renamed (M-05); artifacts and attestations bind to the SHA; and no job writes
to a release branch (M-13). **A check that cannot fail for its stated reason is treated as a defect,
not as coverage.**

### D.10 External branch-protection changes

W4b, not `ci.yml`, changes required contexts, approvals, CODEOWNERS enforcement, admin enforcement,
and force-push policy. The plan keeps in-repository workflow changes and owner-gated GitHub
repository-setting changes strictly separated, and sequences them so `main` is never left requiring a
context that does not exist (§C W4 residual risk).

---

## E. Verification matrix

`Blk` = blocking · `CF` = credential-free · `Re` = **must be re-executed on the frozen Promotion SHA**.
Pre-freeze results are diagnostics, never certification. Evidence locations: CF `command` rows on the
owning wave task; SHA-keyed CI artifacts; `tests/simulation/artifacts/<SHA>/`;
`tests/real_user_benchmark/artifacts/<SHA>/`; the dossier at
`docs/promotion/2026-09-09-promotion-dossier.md`.

| # | Surface / claim | Command or journey | Env | Expected | Evidence | Blk | CF | Re |
|---|---|---|---|---|---|---|---|---|
| 1 | Candidate boundary | `git status --porcelain -uall` vs classification TSV | local | residue is only EXCLUDE/QUARANTINE | TSV + CF row | ✓ | ✓ | ✓ |
| 2 | **Dependency closure** | `npx tsc --noEmit` on the staged candidate | local n24 | every specifier resolves | CF row | ✓ | ✓ | ✓ |
| 3 | Recovery | restore bundle + tarball into a scratch clone | local | tree reconstructs, hashes match | CF row | ✓ | ✓ | – |
| 4 | Protected dirs | `git check-ignore`; path listing only | local | `LLMs/`, `Model_Finetuning/` untouched | CF row | ✓ | ✓ | ✓ |
| 5 | Wave-manifest integrity | `scripts/verify_wave_manifest.py`; tracked export present | local | exits 0; export at the SHA | CF row | ✓ | ✓ | ✓ |
| 6 | Backend format | `ruff format --check .` (pinned ruff) | CI | clean; version recorded | `backend-format` | ✓ | ✓ | ✓ |
| 7 | Backend correctness lint | `ruff check backend/ --select F821,F811,F822,E999` | CI | 0 | `backend-lint` | ✓ | ✓ | ✓ |
| 8 | F821 defects actually gone | `get_type_hints` probe on both functions | CI | returns a dict for both | CF row | ✓ | ✓ | ✓ |
| 9 | Backend suite | `pytest ../tests/ -q -m "not live_llm"` | CI | 0 failed; declared skips only | `backend-test` | ✓ | ✓ | ✓ |
| 10 | Public quality | `pytest tests/test_public_repo_quality.py -q` **post-commit** | CI | passed; `audit() == []` | `hygiene` | ✓ | ✓ | ✓ |
| 11 | Whitespace hygiene | `git diff --check origin/main` | CI | empty | `hygiene` | ✓ | ✓ | ✓ |
| 12 | Frontend lint | `npm run lint` (clean tree **and** with a sandbox present) | CI n24 | 0 errors | `frontend-lint` | ✓ | ✓ | ✓ |
| 13 | Typecheck | `npx tsc --noEmit` | CI n24 | clean | `frontend-typecheck` | ✓ | ✓ | ✓ |
| 14 | Frontend unit | `npm run test:unit` | CI n24 | ≥89/89 | `frontend-unit` | ✓ | ✓ | ✓ |
| 15 | Frontend mutation | `npm run test:mutation` | CI n24 | ≥75 (target ≥90); triple from the raw report; no-coverage 0 in scope | `frontend-mutation` | ✓ | ✓ | ✓ |
| 16 | Frontend build | `npm run build` | CI n24 | succeeds | `frontend-build` | ✓ | ✓ | ✓ |
| 17 | Backend mutation | `python scripts/run_backend_mutation.py` | CI | pass | `backend-mutation` | ✓ | ✓ | ✓ |
| 18 | Security benchmark | `security_benchmark.py --fail-on-threshold` | CI | 28/28 (or grown denominator) | scorecard | ✓ | ✓ | ✓ |
| 19 | Security matrix coverage | `pytest tests/test_security_benchmark.py -q` | CI | passed; new scopes covered | `governance` | ✓ | ✓ | ✓ |
| 20 | Governance battery | integrity, CI-gov, test-harness, workflow-contracts, QA-capabilities, change-obligations | CI | all exit 0 | `governance` | ✓ | ✓ | ✓ |
| 21 | Required-check contract | `scripts/check_required_checks.py` | CI | manifest == job ids == protection | `governance` | ✓ | ✓ | ✓ |
| 22 | Compose renders | `docker compose … config --quiet` ×4 profiles | CI | renders | `qa-contract-render` | ✓ | ✓ | ✓ |
| 23 | QA contract suite | QA contract/synthetic/audit pytest | Docker CI | pass | `qa-contract-render` | ✓ | ✓ | ✓ |
| 24 | **Real browser journeys** | container-first Playwright, changed surfaces | Docker, loopback | dated verdicts + artifacts | `ui-journeys` | ✓ | ✗ (needs Docker) | ✓ |
| 25 | Roles / themes / 375px / focus / states | journey matrix | Docker | pass or honest `not_runnable` | artifacts | ✓ | ✗ | ✓ |
| 26 | Research Spine non-bypass | spine contract tests + audit profile + research journeys (§F) | CI/Docker | no bypass | CF row | ✓ | ✓ | ✓ |
| 27 | Self-improvement governance | `pytest tests/test_improvement_governance.py tests/test_agent_learning_scope.py -q` | CI | pass | `backend-test` | ✓ | ✓ | ✓ |
| 28 | Simulation / RUB static | `npm run test:static`; `npm run check` | CI | 111 / 107 baselines held | `test-harness-js` | ✓ | ✓ | ✓ |
| 29 | Production rehearsal | `scripts/production_rehearsal.py --json` | CI | pass | `backend-test` | ✓ | ✓ | ✓ |
| 30 | Index freshness | `index status` (pinned native binary, from repo root) | local | fresh, `warnings: []` | CF row | ✓ | ✓ | ✓ |
| 31 | Impact per changed surface | `intelligence impact --path <p>` | local | `confidence` + `corpus.source` recorded | CF row | – | ✓ | – |
| 32 | No release-blocking CF task | `task list --status open` + triage table | local | zero blocking; `next` truthful | triage table | ✓ | ✓ | ✓ |
| 33 | Lifecycle truth | status-block parse vs last ledger; all Sep 6–9 files tracked | local | no contradictions | dossier | ✓ | ✓ | ✓ |
| 34 | Desktop | `cargo check` (+ build/package on supported OS) | CI matrix | pass, or explicit owner exclusion | `desktop-check` | per M-18 | ✓ | ✓ |
| 35 | Release artifacts | build, SBOM, checksums, manifest, **download and inspect** | CI | files match the SHA | artifacts | ✓ | ✓ | ✓ |
| 36 | CI green on the SHA | `gh run list --commit <SHA>` | GitHub | all required contexts green; `headSha` == dossier SHA | dossier | ✓ | n/a | ✓ |
| 37 | Branch protection | `gh api …/branches/main/protection` + negative mergeability test | GitHub | matches §D.2 | dossier JSON | ✓ | n/a | ✓ |
| 38 | Blind review dry | reviewer verdicts + delta re-reviews | — | pass; no open S1/S2 | `review_verdict` | ✓ | ✓ | ✓ |
| 39 | SHA still current | `git rev-parse testing` == `PROMOTION_SHA` | local | equal at dossier close | dossier | ✓ | ✓ | ✓ |

Rows 6–27 are the release-critical core. Explicitly **not** promotion gates, and recorded honestly as
`not_runnable` when absent: live-LLM evals, donor-compute probes, VPS deployment, performance soak.

---

## F. Research Spine assurance

The spine is:

```
Sources → Evidence Units → Independent Multi-Model Atomic Extraction + Open Coding
→ Reliability + Grounding → Reconciliation → Accepted Atoms/Nuggets → Facts → Insights
→ Recommendations → In Review → Human-Approved Done → Reports
```

**Changed research-data paths in this candidate.** `backend/app/services/research_validity_service.py`;
`backend/app/services/research_validity_evidence_units.py`; `backend/app/core/report_manager.py`
(graph neighbour, highest-scoring context hint); 48 modified `tests/simulation/scenarios`; modified
`tests/test_research_validity_contract.py`, `tests/test_research_integrity_validation.py`,
`tests/test_project_scope_contracts.py` (these **strengthen** the spine); and ~71 untracked files
under `tests/document_corpus/rich/**`.

**W2 builds a trace table** with one row per changed path and these columns: ingress source ·
evidence-unit constructor and exact raw-span handle · independent coder identities and **served-model**
receipts · reliability matrix/metrics · grounding validation · reconciliation decision · accepted
atom/nugget transition · facts/insights/recommendations derivation · In Review / human approval ·
Done transition · report query and gate · route evidence · project scope · owning tests and journeys.

**Invariants that must hold on every row.**

1. Documents, audio/interviews, surveys, channels, chat, integrations, skills, simulations, donated
   compute, and autoresearch outputs enter as sources/evidence units or remain explicitly
   non-research/provisional.
2. **No synthesized nugget prose substitutes for a raw evidence span** unless the exact original source
   span is retained and the artifact remains provisional.
3. At least three distinct healthy project-authorized **model identities** for governed multi-model
   coding; a *requested* or *configured* model is not served-model proof, and replicas are not
   independent raters.
4. Every coder covers every unit with an exact contiguous quote; incomplete, duplicate,
   mismatched-model, missing-route, or invalid-metric runs **fail closed** before promotion.
5. Reliability and grounding precede reconciliation; reconciliation decisions are durable and
   project-scoped.
6. Atoms/nuggets/facts/insights/recommendations stay **provisional** until accepted evidence and a
   human-approved Done state; reports query only accepted, reconciled evidence attached to Done tasks.
7. Donor selection and served-request route evidence survive the bridge, Pi frames, dispatcher, and
   persistence; donor visibility or readiness is **not** proof of use.
8. Telemetry and ReasoningBank are process signals, never report evidence. Memento learns strong
   positive signals only from verified, quality, reportable outcomes — **never from raw tool success**.
   Autoresearch stays sandbox/proposal-only. Meta-Hyperagent and Self-Evolution stay project-scoped
   and governed. RAG/GraphRAG/Prompt-RAG/LLMLingua preserve provenance and protected methodology
   blocks and cannot relax authorization or report gates.

**The corpus addition is this candidate's spine-relevant risk, and it needs stating plainly (M-22).**
A large new document corpus is exactly the shape of change that can introduce *pre-digested evidence* —
source files that already contain conclusions — letting synthesized prose enter as if it were a raw
source span. The audit already defends this: `RAW_SOURCE_FORBIDDEN` rejects `## Evidence unit
candidate`, `Coding hints:`, `Implication candidate:`, and `Report gate reminder:` in canonical
sources, and `scan_repeated_source_excerpts` catches duplicated excerpts. **That defence runs over
tracked files only, so it says nothing about the corpus until W1 commits it** — which is why the audit
must be re-run post-commit, and why the corpus is classified as test fixtures confined to `tests/`,
never product data.

**Executable gates.** `tests/test_research_validity_contract.py`,
`tests/test_research_integrity_validation.py`, `tests/test_project_scope_contracts.py`,
`tests/test_improvement_governance.py`, `tests/test_agent_learning_scope.py`, plus the QA audit
profile and at least one container journey showing a provisional state and a **denied** premature
report. The written contracts — `docs/architecture/research-validity-contract.md` and
`docs/architecture/self-improvement-governance-contract.md` — are re-read **against the actual diff**
rather than assumed current (and M-21 corrects the former's stale spec reference).

**Disposition.** Any discovered bypass is architecture debt. If it is reachable by a research-data
path in this candidate, **promotion is blocked**; if unreachable, it is recorded with a named
follow-up spec. Determined in W2, re-proven in W5 (matrix row 26). Nothing in this plan weakens,
bypasses, or parallel-tracks the spine, and no wave uses telemetry, ReasoningBank, Memento, or
autoresearch output as release evidence.

---

## G. Owner-gated operations

Automated waves must **never** perform these. Each requires explicit owner authorization at the time.

| # | Operation | Why gated |
|---|---|---|
| 1 | `git reset --hard`, `git clean`, `git checkout -- .`, `git stash drop`, amend, rebase, history rewrite | destroys unclassified local work irreversibly |
| 2 | Deleting, moving, pruning, cleaning, or enumerating the contents of `LLMs/` or `Model_Finetuning/` | protected, gitignored, irreplaceable |
| 3 | Deleting or pruning **any** untracked file or local artifact | 119 exist; classification is judgement-based |
| 4 | Force-push, tag/branch deletion, or any write to `main` | protection currently permits it — today's guard is policy, not mechanism |
| 5 | Starting servers, loading models, sending completion probes, exercising a private provider | live-safety contract; passive discovery stays passive |
| 6 | Reading, printing, or persisting secrets, private endpoints, fingerprints, tokens, connection strings | disclosure risk |
| 7 | Mutating GitHub repository settings, including branch protection, CODEOWNERS policy, or Actions secrets | out-of-repo state; W4b prepares, the owner applies |
| 8 | Pushing the candidate to `origin/testing` | W6 only, separately authorized |
| 9 | Creating the promotion PR | only via `promote-testing.yml` with environment approval |
| 10 | Merging to `main`, publishing a release, or deploying | the terminal decision; never automated |
| 11 | Lowering any mutation, security, quality, accessibility, or Research Spine threshold; accepting an S1/S2 risk | requires an explicit, justified owner decision changing acceptance |
| 12 | Rewriting an existing ledger entry | ledgers are append-only |
| 13 | Closing a CF task without cited evidence | staleness must be **proven**, not assumed |
| 14 | Editing or weakening the public-quality audit, or adding `continue-on-error` to a correctness gate | turning a red check advisory to obtain green is forbidden |

**Structural owner pauses:** approval of this master plan before W1; the W1 `UNDECIDED` review; the
W4b protection sequencing (see the ordering hazard); authorization before any live-capability lane;
authorization before the W6 push and PR; and the final human merge decision.

---

## H. Final release criteria

One binary verdict. **READY** requires **every** line below; any miss yields **NOT READY** with the
failing criterion named. There is no partial, conditional, or "ready except" state.

1. **Exact candidate SHA** — the full 40-character Promotion SHA, frozen, recorded in the CF spec, the
   lifecycle status block, and the dossier, and still equal to `testing` HEAD at dossier close;
   `git log --oneline <Base>..<Promotion>` fully explains everything added after the freeze.
2. **Clean intended worktree boundary** — every path classified; residue is only
   `EXCLUDE-*`/`QUARANTINE`/`UNDECIDED`, each accounted for; **dependency closure proven**; the
   recovery snapshot verified by restore; protected directories untouched (verified by path listing,
   not assumption); the quarantine branch exists.
3. **Every intended recent Build Stream plan reconciled** as included, excluded, superseded, completed,
   or explicitly deferred with rationale; **no file in `docs/build-stream/` is both "done" and
   "in-progress"**; every referenced lifecycle file is tracked at the frozen SHA.
4. **Compass Forge reconciled** — index fresh with `warnings: []`; one recorded
   `intelligence impact --path` per changed surface with its `confidence`; CF-SPEC-29 and CF-SPEC-30
   linked tasks resolved with cited evidence; zero release-blocking open tasks, **proven by the
   181-task triage rather than asserted**; `next` truthful.
5. **All required CI green on that exact SHA** — every §D.2 context, on the Promotion SHA itself, not
   an ancestor and not a re-run of an earlier commit; `headSha` equality verified; no advisory,
   cancelled, or unexplained-skip escape.
6. **Mutation thresholds met without lowering** — ≥75 from real test improvement or genuine
   implementation fixes, thresholds untouched since `9961fa3d`, with the killed/survived/no-coverage
   triple recorded from the raw report.
7. **Container-first UI verdicts** — dated and artifact-backed for every changed behaviour, across the
   role/theme/375px/keyboard/state matrix; every `not_runnable` explicit, owner-visible, and naming its
   missing capability. **A `not_runnable` is never a pass.**
8. **Research Spine and self-improvement governance proven non-bypassable** across every changed
   research-data path (§F).
9. **Security benchmark current** — `--fail-on-threshold` green on the frozen SHA, with the changed
   control matrix (M-12) covered by tests and the newly scoped routes verified to implement their
   claimed controls.
10. **Blind independent review pass** — comprehensive review plus delta re-reviews until dry, with no
    open S1 or S2 finding.
11. **Branch protection aligned** — owner-applied, re-read from the API, attached as evidence, and
    negatively tested (a PR with a failing required context must be un-mergeable).
12. **Promotion dossier complete** — §E matrix with results, findings register with dispositions,
    classification TSV, CF triage table, journey verdicts, security scorecard, mutation report,
    protection JSON, artifact checksums, and the M-23 main-merge mechanics recommendation.
13. **Owner approval still pending** — the dossier ends at the decision point. No PR, no merge, no
    deployment.

**Explicitly not evidence of readiness:** a green process, container, workflow, or artifact; a green
run on an ancestor SHA; `main`'s historic green runs (it has never contained this architecture); a
local result from an unpinned node-26 environment or a tree containing a Stryker sandbox; a compose
file that merely renders; or a `not_runnable` counted as a pass.

### H.1 Separation of code stages

| Stage | Where it exists after this plan | Proof object |
|---|---|---|
| transported | working tree before W1 | classification TSV |
| committed | Candidate Base SHA → Promotion SHA (local) | `git log` + tracked wave manifest |
| pushed | `origin/testing` @ Promotion SHA (owner-gated, W6) | `gh run list --commit` |
| CI-validated | the green required-check run on that SHA | run URL + `headSha` |
| artifact-built | build + QA containers from that SHA | artifacts + checksums + compose digests |
| PR-ready | dossier complete + protection aligned | dossier §H |
| merged | **not part of this plan** — the owner's act after READY | merge commit on `main` |
| deployed / live-verified | out of scope — a separate owner-gated operation | n/a |

---

## I. Coverage matrix — which draft insight each section incorporates

| Section | From draft a | From draft b | From draft c | Synthesis-only |
|---|---|---|---|---|
| §0 conflict adjudication | the 233-lint and schema-21 claims, tested | the CF command-migration and audit-rule-name root causes, confirmed | the dependency-closure claim, confirmed and extended | **all four adjudications (K-1…K-4), re-measured this session** |
| §A candidate definition | byte-level inventory bundle, hunk-granularity classification, isolated-worktree assembly, manifest reconciliation signoff | five-bucket classification, `--pathspec-from-file` rule, freeze/invalidation semantics, untracked-lifecycle problem, anti-replay compatibility | surface verdict (C selected), quarantine branch, backup branch, drift-prevention rules, `headSha` binding | **dependency-closure proof as an acceptance test** (M-01); moved-base correction |
| §B findings register | custody, CI observability, artifact-vs-journey distinction, deferred-work classification | M-02 root cause, M-03 (2 live F821 specimens), M-04 scope analysis, M-05 (`compose config` is a syntax check), M-12, M-14, M-17 | M-11 ruff pin, M-13 escalation, M-20, M-21, M-23, corpus classification | **M-16 (Stryker sandbox pollutes eslint)**; M-10 re-verified; M-19 confirmed |
| §C waves | wave-level rollback discipline, obligation-matrix wave (folded into W2), owner pauses | the six conductor wave ids, per-wave review questions, W3-may-expand risk, W4 ordering hazard | W3a/W3b and W4a/W4b phase split, manifest-id traceability | phase split preserved **without** breaking the conductor's 6-id contract |
| §D CI architecture | `release-gate` fail-closed aggregator, cache/artifact boundaries, desktop policy stance, stale-green mechanisms | independence rule, severity-class lint policy, mutation triple, honest job naming | required-checks manifest contract, weekly schedule, badge-push removal, loopback publication | lint-ignore rule for gitignored generated dirs (M-16) |
| §E matrix | rerun-on-frozen-SHA column, artifact download-and-inspect | 32-row structure, SHA-bound evidence, env column | `headSha` binding, baseline figures, honest non-gates | dependency-closure and sandbox-aware lint rows |
| §F Research Spine | 8 invariants, changed-path trace table columns | corpus pre-digested-evidence risk + tracked-only scan surface, executable gate list | changed-path enumeration, "strengthen the spine" test classification | corpus gate tied to the post-commit audit re-run |
| §G owner-gated | destructive-cleanup and settings-mutation prohibitions | 12-row table, structural pauses | quarantine-before-index-removal rule | audit-editing prohibition (row 14) |
| §H criteria | binary verdict with default NOT READY, state separation | 12 criteria, "explicitly not evidence" list | dossier contents, threshold-untouched-since-`9961fa3d` test | sandbox/node-26 added to the not-evidence list |

**Material gaps closed by synthesis:** draft a had no dependency-closure test and would have based the
candidate on an unbuildable surface; drafts a and c each contained an unexecutable Compass Forge wave;
draft a would have scoped ~200× too much frontend lint work; draft b under-rated the `governance`
main-push (S4 → S2 blocking-before-W4b, since protection will break it); no draft had a lint-ignore
rule for gitignored generated directories.

---

## J. Residual risks in this plan

1. **W3 may expand.** The full backend suite has never been observed green on this candidate, because
   formatting aborts the job before it runs. Real failures may be hiding behind that gate.
2. **W5 is the largest unknown effort** and the wave most likely to find genuine product bugs, looping
   back to W3. Sequence accordingly.
3. **The W4b ordering hazard** can leave `main` requiring contexts that no longer exist, or briefly
   unprotected. It needs deliberate sequencing with the owner in a single action.
4. **The 181-task triage is manual**; its principal danger is misfiling a real blocker as
   administrative — mitigated by requiring an evidence citation per closure.
5. **The worktree is shared and live** (M-19). Between freeze and promotion, any write forces re-freeze.
6. **The ruff pin must equal the version CI resolves**, or format results still drift (M-11).
7. **Mutation survivors may expose real bugs** in `runtimeConfig.ts` (origin/websocket URL derivation
   is auth-adjacent); implementation fixes are first-class outcomes, not scope creep.
8. **The 994-commit fast-forward is a large blast radius** for consumers of `main`; mitigated by the
   dossier's merge-mechanics section and a post-merge `main` CI run (M-23).
9. **Native `impact` may complete its Rust migration mid-pipeline.** Waves should adopt the bare
   command when it lands but must not block on it; `intelligence impact --path` is the current path.

### J.1 Explicitly not verified by this synthesis

- **GitHub Actions run 34039897688 contents** — read only through the brief and draft c's `gh` output,
  not independently by me. The mutation arithmetic reconciles exactly with the local Stryker config
  (95/130 = 73.08%), which corroborates it, but I did not read the CI log.
- **Live branch-protection API state** — draft b and draft c independently report identical values; I
  did not re-issue the API call in this session.
- **The full backend suite** (~2,335 tests) and **all browser journeys** — not run during planning, by
  design. They are mandatory §E rows on the Promotion SHA.
- **Whether the 378 advisory backend lint errors contain further correctness-class findings** beyond
  the two F821s. M-03's severity-class policy makes that class visible going forward regardless.
- **The local Stryker plugin-init failure was not reproduced.** Versions are mutually compatible and
  node 26-vs-24 is the likely cause (M-17); the leftover sandbox it created *was* observed (M-16).

---

*End of Master Plan B (synthesis). Proposal only — owner approval is required before W1 begins, and
promotion to `main` remains a separate, later, owner-gated decision.*
