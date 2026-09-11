# W5 certification header — readiness5-20260910 on 3b4b881d (2026-09-11)

Wave: `certification` · Spec: `CF-SPEC-30` · Task: `testing-to-main-20260910-WAVE-certification-IMPL`
Plan: `docs/build-stream/plans/readiness5-20260910-plan-a.md` §Wave W5

## 0. VERDICT: READY — OWNER-GATED PROMOTION (local matrix green on 3b4b881d; push + protection + CI observation remain)

Candidate SHA: `3b4b881de23f60e8b58d8a84a907b33c0e105f21` (short `3b4b881d`), branch `conductor/readiness5-20260910`, baseline `abc9da92`.
Range `abc9da92..3b4b881d`: W1 `c5e2dfca` + W2 `97a73a8a` + fix `97dbb2ce` + W3 `ed2aa7b8` + fix `66c0ff87` + W4 `9aa3034a` + review `3b4b881d`.
`origin/testing` `9961fa3d` (ahead, never pushed); `origin/main` `fa6a1a39` strict ancestor.
Worktree: 0 modified, 0 stash; 2 untracked docs (plan-a.md, evaluation-log.md) — non-product, disclosed.
`git diff --check` clean. CF: 9 command rows on the IMPL task (pinned binary, ROOT, --target ROOT). No push/PR/merge/settings by this stage.

B1/B4/B5 now closed by real lane execution (W2 82 15/15, 83 17/17, 84 13/13, 248 checks); W3 live 3-model run with k/a + reconciliation + adversarial/debate + 5 probes; W4 150-turn both engines with telemetry + docs + UI. M-18 decided (desktop-check required). B2 (exact-SHA CI) + B3 (protection PUT + negative proof) remain owner-gated, listed in §5, never claimed.

## 1. Release matrix on 3b4b881d

- governance battery 8/8 PASS (integrity, ci-governance, test-harness, required-checks, workflow-contracts, qa-capabilities, security_release_readiness, public-repo audit)
- feature-obligations PASS (0 unknown; was 486 at W1 start); production_rehearsal PASS via ROOT venv
- security_benchmark plain PASS 28/28 100.0 triggered []; changed-paths (abc9da92..HEAD) PASS 28/28 triggered [PiModelManagement, authStore, ci.yml, check_ci_governance]
- backend full suite: 2330 passed / 5 skipped / 1 deselected, 0 failed (uncontended; better than W1 2315/7-flaky)
- backend mutation exit 0 (252 killed / 97 survived / 0 no-cov, 349 mutants compute_capacity.py)
- frontend: tsc clean; eslint 0 errors / 41 warnings; unit 23 files / 121 tests; build green; mutation 90.77 (118/12/0) node v24.20.0, break 75 untouched
- backend-dir ruff 0.16.6 format clean (371 files) + F821/F811/F822 clean; `git diff --check` + `origin/main` clean
- compose renders contract/ui/synthetic/audit all exit 0 (parse-only, M-05 honest)
- lifecycle verifiers OK (status + triage + wave_manifest canonical 8601a1fc)
- simulation test:static 41/41 + node --check 82/83/84 + real_user check + relay test green
- CF gate after --new-only 0 new issues (full 420 pre-existing python_import_cycles baseline, untouched); index v21 rust graph v3 warnings [] 1473 files
- GH Actions on SHA: no run (local-only, never pushed) — CI proof CI-owned post-push; review pending by design

Ruff scope note: ROOT `ruff format --check` reports 42 md fences + ROOT `ruff check F821/F811/F822` reports 6xF811 in tests/test_research_integrity_* — both outside every CI job scope (working-directory backend) and pre-readiness5 (changed main..abc9da92, untouched W1-W4). Rows above are CI-authoritative greens; ROOT notes disclosed, not fixed here (no scope expansion).

## 2. Browser lane W2 (executed)

NEW dir ~/istara-qa-readiness5-20260910 Mac Studio, --profile ui loopback-only, SSH tunnel QA_TEAM_MODE=true synthetic creds. Final battery 16 scenarios + 3 evaluators: 15 PASS + 1 SKIP (05 stub no chat model), 248/0 checks — 82 15/15, 83 17/17, 84 13/13, smoke 7/7, reps 10 27/27 + 12 8/8 + 26 17/17 + 70 18/18 + 79 10/10. Axe 0 violations, Nielsen 4.3/5 (H3 3/5 advisory), perf 12/12. 50 screenshots. proven-extra 8 journeys (resolve 15 selected / 67 not_runnable / 0 pending); coverage-matrix dated 2026-09-11. Fixes: HomeClient cookie boot, session/passkey cookie-tolerant + regressions, ConfirmDialog dialog semantics, resolveCatalogListState alert. Artifacts tests/simulation/.results/runs/2026-09-11T01-35-10-892Z. Review FAIL->fix F-R5-W2-R1-1->delta PASS (L-52/53/54). Minor R1-2 + registerPasskey residual follow-ups. No Petals/push.

## 3. Live ensemble W3

Sibling w3-live-backend, host-only 0600 env, scratch DB (originals untouched, CareNav read-only). A: 3/3 admission distinct receipts (glm-5.3-flash, gpt-5.6-luna, gpt-5.6-terra). B: 6-unit run 3 raters distinct, requested==served, k=-0.102/a=0.493 needs_reconciliation (operational small-n). C: gate refused 6 unreconciled -> allowed 6 accepted. D: adversarial (luna) + 3-pass debate + self_moa honest degradation. E: 5 probes typed. Fix: debate route model+served_model + test; D re-run re-merge F-R5-W3-R1-1 fixed (3/3 receipts, models_used 3). Artifacts qa/runs/w3-live-ensemble-2026-09-11T02-32-09Z-97dbb2ce (secret-scan 0). Review FAIL->fix->delta PASS (L-56/57/58). Minors R1-2/R1-3/R1-4 follow-ups. No Petals/push.

## 4. Long-horizon W4

Image w4candidate, scratch DBs verified, endpoints host-only 0600. Harness-only --thinking-mode (5 lines). 151 turns/engine same model pi-zai-glm served glm-5.3-flash 302/302 success 0 errors 0 fallbacks 32/32 steerings; pi 18.7s $0.31 (30/9), legacy 21.3s unmetered (43/13); stops 150+1 length vs 151 stop; typed retrieval_fallback only. DAGs 500 seeded provisionals/engine, no self-elevation. Telemetry 151 usage rows + 1364/1399 spans; aggregator content-free; audit 5 gaps (G1/G2/G3/G5 + turn-1 dup). Docs + UI dated slice + 79 extended + screenshots. Artifacts qa/runs/w4-long-horizon-20260911-zai-glm (run-both 618e4c8e). Review blind PASS 2 minors (L-60 R1-1/R1-2). No Petals/push.

## 5. Owner checklist (owner-only; no agent)

- [ ] G0 desktop DONE (M-18 in-scope blocking; desktop-check required everywhere).
- [ ] G1 push + CI: manager verifies SHA (`rev-parse` == 3b4b881d, status clean except 2 untracked docs, log abc9da92..HEAD == 8 commits), pushes conductor/readiness5-20260910 to origin/testing, reports `gh run list --commit <SHA>` id + result (expect 17/17 incl ui-journeys + desktop-check first observation).
- [ ] G2 info: W2-W4 QA evidence above suffices; preserved dirs untouched; QA-host state disposable.
- [ ] G3 protection: PUT gh-api-body.json (verified == manifest 17/17 incl desktop-check), attach API read-back + negative mergeability test, sequencing per README.
- [ ] G4 merge: record M-23 (--no-ff recommended; dossier-tip parent == 3b4b881d product-identical), merge, post-merge main CI. Protection + PR owner-gated.

## 6. Closure map at 3b4b881d

M-01 closed; M-02 closed; M-03 closed (backend-dir); M-04 closed (90.77+exit-0); M-05 closed-executed; M-06 closed; M-07 closed-prepared; M-08 closed; M-09 closed (REVIEW is the one open task by design); M-10 closed (v21 observed); M-11 closed (0.16.6 pin); M-12 closed (plain+changed); M-13 closed; M-14 closed; M-15 closed; M-16 closed; M-17 closed (node-24 lane); M-18 decided; M-19 closed; M-20 closed; M-21 closed; M-22 closed; M-23 owner (§5); M-24 deferred. B1 closed (0 pending); B2 owner; B3 owner; B4 closed (17/17); B5 closed (13/13 + TEAM_MODE); B6 closed (this dossier). Minors F-R5-W2-R1-2, F-R5-W3-R1-2/R1-3/R1-4, F-R5-W4-R1-1/R1-2, registerPasskey residual — follow-ups, non-blocking.

## 7. Residuals (non-blocking)

Local machine evidence (node 26 default / 24.20.0 mutation; ruff 0.16.6 ROOT venv; ROOT venv backend suite — worktree has no .venv). CI is authoritative (G1 proof). Full-tree 420 cycles + 41 warnings pre-existing (gate 0 new). ROOT ruff notes disclosed (§1). 2 untracked docs excluded from SHA (re-freeze if tracked). Telemetry gaps + small-n labels operational only.

Certified by testing-to-main-20260910-implementer (meta/muse-spark-1.3-contributor, xhigh). Do NOT push — manager pushes after verifying SHA.

---
Historical appendix: 2026-09-09 dossier + 2026-09-10 addendum preserved verbatim below (superseded verdicts remain as audit trail for 4a7f4e0c / B1-B6).

---
# Promotion certification dossier — testing-to-main 2026-09-09 (W6)

Wave: `promotion-certification` · Spec: `CF-SPEC-30` · Task:
`testing-to-main-remediation-20260909-IMPL`

## 0. VERDICT: **BLOCKED — EVIDENCE-PENDING (readiness claim withdrawn 2026-09-10)**

The 2026-09-09 final readiness review reopened this certification. The `READY —
owner-gated promotion` verdict previously recorded here **overstated readiness** and is
withdrawn: the remaining blockers are not a rerun of already-green suites. Open items
(plan `docs/build-stream/plans/testing-to-main-remediation-20260909-plan-a.md`, B1–B6):

- **B1** — the full browser lane selects 7 of 82 registered scenarios and records 75
  generic `not_runnable` entries; scenarios 82/83/84 have never executed anywhere (row 22
  below is syntax/registry verification only, not execution evidence).
- **B2** — no GitHub Actions run exists for any candidate SHA (row 23); the certified SHA
  differs from the branch tip.
- **B3** — live `main` protection still requires only `governance` and lacks the
  review/admin/linear/no-force controls of the committed package.
- **B4** — scenario 83 contained unconditional and contradictory pass logic (fixed in
  remediation IMPL; deterministic oracles now assert real filter/empty/error states).
- **B5** — scenario 84 omitted researcher/viewer/stranger cells, bookkeeping was
  scenario-level, and the coverage matrix lacked 82/83/84 (fixed in remediation IMPL;
  obligation-ledger cells + matrix rows now exist).
- **B6** — this dossier and the lifecycle claimed more readiness than the evidence
  supports; the desktop scope decision remains unmade.

Sections 1–6 remain an accurate record of what WAS certified locally on `4a7f4e0c`
(deterministic gates, not live behavior). They confer **no** readiness claim by
themselves. Promotion stays blocked until exact-SHA CI, a full container browser lane,
applied-and-proven branch protection, the owner's desktop/promotion-mechanics decisions,
and a fresh certification all exist (§7).

## 1. Candidate SHA and freeze provenance

| Item | Value |
|---|---|
| **Candidate SHA** | `4a7f4e0c5598296b1011ef5e4a5855c6a62517ff` (short `4a7f4e0c`) |
| Candidate tree hash | `92289053a055652fc576a23d607535d47a042e46` |
| Worktree state at certification | clean (0 modified, 0 untracked non-ignored, 0 stash) |
| Parent | `ee40f9be` (W5 remediation commit) |
| `origin/testing` | `9961fa3d` — candidate is **126 ahead / 0 behind** |
| `origin/main` | `fa6a1a39` — strict ancestor of the candidate (`git merge-base` = main tip), so a fast-forward is mechanically possible (M-23) |
| Wave-1 freeze | `docs/promotion/2026-09-09-candidate-boundary.md` (scoped freeze `3de70bfc`) |

**Freeze provenance.** Waves W1–W5 verified the release inside this shared worktree, but
their backend/frontend fixes remained uncommitted at `ee40f9be` (131 tracked-modified
files, +3851/−1291, plus the 4 required import-closure files). W6 completed the freeze:
commit `4a7f4e0c` stages exactly that classified remainder via explicit pathspec (never
`git add -A`) — W3 correctness fixes (ruff pin, eslint ignore, runtimeConfig hardening),
W5 security fixes (MFA boundary matcher, `get_current_user` + A2A defense-in-depth,
global middleware enforcement, provisional baseline), M-02 path scrub, security-benchmark
scope widening, single `EXPOSE 8000`, all lifecycle narratives, and `tokenStore.ts`/
`tokenStore.test.ts`/`SeeMoreList.tsx`/`ToolAuditTrailTable.tsx` closing the 22-file
import chain (M-01/K-1). Pre-freeze gates: `git diff --check` clean;
`public_repo_quality_audit.py --check` passed.

**SHA attribution rule.** Every matrix row in §2 executed with the worktree byte-identical
to `4a7f4e0c`. The only commit after the freeze is this dossier plus the lifecycle ledger
entry (docs-only; zero product code). Promotion options (owner decides, M-23): (a) promote
`4a7f4e0c` exactly; (b) promote the dossier tip (contains `4a7f4e0c` as parent; product
surfaces content-identical). Recommendation: (b) with `--no-ff`, so the certification
record ships with the code it certifies.

## 2. Release matrix — all rows on `4a7f4e0c`

| # | Criterion | Command | Result |
|---|---|---|---|
| 1 | Required-check lockstep (16 contexts) | `python3 scripts/check_required_checks.py` | PASS |
| 2 | Workflow contracts (incl. badge-sync) | `python3 scripts/check_workflow_contracts.py` | PASS |
| 3 | CI governance topology | `python3 scripts/check_ci_governance.py` | PASS |
| 4 | Test-harness contract | `python3 scripts/check_test_harness.py` | PASS |
| 5 | Repo integrity | `python3 scripts/check_integrity.py` | PASS |
| 6 | QA capabilities | `python3 scripts/check_qa_capabilities.py` | PASS |
| 7 | Security benchmark | `python3 scripts/security_benchmark.py --fail-on-threshold` | PASS — exit 0, 28/28 controls, score 100.0 |
| 8 | Public-repo quality audit (post-freeze scan surface) | `python3 scripts/public_repo_quality_audit.py --check` | PASS |
| 9 | Backend full suite | `cd backend && .venv/bin/python -m pytest ../tests/ -q -m "not live_llm" --ignore=../tests/simulation` | **2363 passed / 5 skipped / 1 failed** → the single failure was `test_checked_in_convergence_lifecycle_passes_status_verifier` (stale lifecycle Status Block, W6's own file) → **fixed in the stage commit; targeted re-run green** (§3) |
| 10 | Backend mutation gate | `backend/.venv/bin/python scripts/run_backend_mutation.py` | PASS — exit 0 (252 killed / 97 survived / 0 no-coverage over 349 mutants of `compute_capacity.py`; gate is exit-0, posture unchanged) |
| 11 | Frontend types | `cd frontend && npx tsc --noEmit` | clean (exit 0) |
| 12 | Frontend lint | `npm run lint` | 0 errors / 41 advisory warnings (M-16/M-24 posture) |
| 13 | Frontend unit | `npm run test:unit` | 108/108 (node v26.0.0 recorded; unit lane is version-stable) |
| 14 | Frontend mutation threshold | `npm run test:mutation` under node **v24.20.0** (authoritative lane, M-17) | **90.77** (118 killed / 12 survived / 0 no-coverage) ≥ break 75, meets the ≥90 target; `thresholds.break: 75` untouched |
| 15 | Backend format + correctness lint | `ruff format --check .` (ruff 0.16.6 pinned); `ruff check . --select F821,F811,F822` | both clean |
| 16 | Release hygiene | `git diff --check origin/main` | 0 findings |
| 17 | Lifecycle status verifier | `python3 scripts/verify_build_stream_status.py docs/build-stream/2026-09-09-testing-to-main-convergence.md` | pre-fix **FAIL** (stale Phase-4 Status Block) → fixed in stage commit → post-fix **OK** |
| 18 | Control-plane triage verifier | `python3 scripts/verify_control_plane_triage.py` | OK — stage-aware prerequisites pass |
| 19 | Wave-manifest integrity | `python3 scripts/verify_wave_manifest.py` | OK — `canonical_sha256=8601a1fc…` matches the lifecycle pin (M-14) |
| 20 | Architecture gate (CF) | `gate before --target <REPO_ROOT>` (pinned binary) | 0 architecture-rule issues, 0 cycles, `new_issues []`, `new_python_import_cycles []`, `new_forbidden_dependencies []`; 218 advisory `warn` complexity findings (pre-existing posture, never blocking) |
| 21 | CF index freshness | `index status` | fresh: `index_version 12`, kernel `rust`, graph_version 2, `warnings []` (M-10) |
| 22 | Container UI journeys (local) | `docker info`; `docker compose --profile contract config --quiet`; `--profile ui config --quiet`; scenario registry refs | **`not_runnable: docker-unavailable`** — daemon unreachable (exit 1; no permission to start one per the Live-LLM/server safety rule). Both compose renders exit 0; scenarios 82/83/84 exist, parse (`node --check`), and resolve in `lib/scenario-registry.mjs`. Nothing fabricated; live execution is CI `ui-journeys`-owned (W4/W5 precedent) |
| 23 | GitHub Actions on the candidate SHA | `gh run list` | **no run exists** — the SHA is local-only (126 ahead, never pushed). Last `testing` runs are 2026-09-06 (pre-candidate). Same-run CI proof is CI-owned after the owner pushes (§5, action 1) |
| 24 | CF task-graph state | `task list --status open` | 182 open, **0 in the `release-blocking` triage bucket**, 0 `promotion-prerequisite` outstanding; the single open pipeline task is this wave's REVIEW (by design) |
| 25 | Blind independent review | conductor pipeline | **pending by design** — `testing-to-main-20260909-WAVE-promotion-certification-REVIEW` runs after this stage; its verdict joins the dossier as a CF evidence row |

## 3. In-stage defect found and fixed

The full-suite run (row 9) and the lifecycle verifier (row 17) both failed on one root
cause: the convergence lifecycle Status Block still claimed `phase: Phase 4 /
S4-remediate` while the ledger showed waves 4–5 closed and W6 active — the same
stale-status contract `scripts/verify_build_stream_status.py` exists to catch. Fixed in
this stage's commit: Status Block advanced to `Phase 6 — Certify promotion readiness` /
`S2-execute`, roadmap phases 2–5 marked `done` and 6 `in-progress`, `cf.tasks` and
`next_action` refreshed (ledger `L-42`). Post-fix: verifier **OK**, targeted pytest
**passed**. No product code was touched by the fix.

## 4. Findings register closure map (M-01…M-24 at `4a7f4e0c`)

| ID | Sev | Disposition at the candidate SHA |
|---|---|---|
| M-01 candidate custody | S1 | **Closed** — freeze complete, clean tree, 0 stash; W1 manifest + W6 freeze commit |
| M-02 public-artifact audit | S1 | **Closed** — audit passed post-freeze (scan surface includes all committed corpus/docs) |
| M-03 escaped correctness | S1 | **Closed** — `F821,F811,F822` clean; 0 cycles at gate |
| M-04 mutation hollowness | S1 | **Closed** — frontend 90.77 ≥ 90 target (node-24 lane, triple recorded); backend mutmut exit 0; thresholds untouched |
| M-05 UI acceptance | S1 | **Closed as defined** — container-first `ui-journeys` lane shipped; local execution honest `not_runnable`; live proof CI-owned (disclosed residual) |
| M-06 CI failure domains | S1 | **Closed** — 17 independent jobs + fail-closed aggregator; contract checks green; same-run Actions proof CI-owned |
| M-07 branch protection | S1 | **Closed-prepared** — exact `gh api` package at `docs/promotion/branch-protection/`; application is owner-gated (§5) |
| M-08 lifecycle truth | S1 | **Closed** (W6 repair) — Status Block refreshed, verifier OK; all referenced lifecycle files tracked at the SHA |
| M-09 CF task debt | S2 | **Closed** — triage: 0 release-blocking, 0 promotion-prerequisite outstanding |
| M-10 CF capability | S2 | **Closed** — `intelligence impact --path` used by waves; index fresh, no warnings |
| M-11 format/toolchain drift | S2 | **Closed** — `ruff==0.16.6` exact pin; format clean |
| M-12 security evidence currency | S2 | **Closed** — 28/28 at the SHA; widened scope committed |
| M-13 governance writes | S2 | **Closed** — CI write-free; badge-sync main-only `[skip ci]` |
| M-14 manifest hash | S2 | **Closed** — verifier OK, canonical hash matches |
| M-15 whitespace hygiene | S2 | **Closed** — `git diff --check origin/main` empty; hook + CI hygiene step |
| M-16 lint integrity | S2 | **Closed** — 0 errors; `.stryker-tmp` eslint-ignored |
| M-17 mutation env | S3 | **Closed** — node-24 pin (`.nvmrc`/`engines`); mutation run under v24.20.0 recorded |
| M-18 desktop release status | S3 | **Owner decision required before promotion** (§5) — `desktop-check` is an honest conditional, no false green |
| M-19 moving surface | S3 | **Closed** — one frozen SHA, clean tree at certification |
| M-20 required-check rot | S3 | **Closed** — manifest↔job-graph lockstep green |
| M-21 spec/doc drift | S3 | **Closed** (W2) |
| M-22 corpus scan surface | S3 | **Closed** — audit green post-commit; corpus tracked and confined to `tests/` |
| M-23 promotion mechanics | S3 | **Owner decision** (§5) — main is a strict ancestor; `--no-ff` recommended; post-merge `main` CI run required |
| M-24 lint debt | S4 | Deferred — 41 advisory warnings visible under a green required context |

Wave findings: F-W3-R1-1/R2-1/R2-2 (fixed/pass, L-35), W4 residuals (disclosed, L-37),
F-W5-R1-1…R1-4 (fixed/pass, L-41). No open Blocker/Major anywhere in the register.

## 5. Owner actions required for promotion (explicitly owner-blocked, not agent-performable)

1. **Push the candidate** (`git push origin testing`) so GitHub Actions executes the full
   matrix — including the container-first `ui-journeys` lane with a real Docker daemon and
   the failure-domain independence property (M-06) — **on the exact candidate SHA**. The
   in-repo contract gates (rows 1–21) are green; the Actions run is the live CI proof this
   dossier deliberately does not fabricate.
2. **Apply the branch-protection package** (`docs/promotion/branch-protection/`): the 16
   required contexts from `testing/required-checks.json`, ≥1 approving review, code-owner
   review, `enforce_admins`, force-push off, linear history on (M-07). Attach the API
   read-back to the dossier.
3. **Record the M-18 desktop decision** (in-scope with system libs and blocking
   `cargo check`, or formally out of scope in `TESTING.md`) **and the M-23 mechanics**
   (fast-forward vs `--no-ff`, recommended `--no-ff`, plus a post-merge `main` CI run),
   then execute the promotion merge. No PR is opened and no settings are changed by this
   pipeline.

## 6. Residual risks (disclosed, non-blocking)

- Local mutation/type/unit evidence was produced on this machine; CI (node 24, pinned
  ruff) is the authoritative long-term lane — the local node-24 lane was used for the
  frontend mutation row precisely to honor M-17.
- `ui-journeys` live execution: `not_runnable` locally (no Docker daemon); scenarios
  82/83/84 are syntax- and registry-verified only.
- The CF graph index (17:43Z) predates the freeze commit by a few hours; it is advisory
  context only — the architecture gate's cycle/issue analysis is current-tree based.
- Complexity advisories (218 `warn`) and 41 lint warnings are pre-existing posture under
  the documented burn-down (M-24); nothing new was introduced by the freeze.

---
*Certified by `testing-to-main-20260909-implementer` (zai/glm-5.3-flash, effort=max) —
matrix rows recorded as CF command evidence on
`testing-to-main-20260909-WAVE-promotion-certification-IMPL`; reviewer verdict to be
appended by `testing-to-main-20260909-WAVE-promotion-certification-REVIEW`.*

---

## 7. Remediation addendum (2026-09-10) — readiness re-baselined

The 2026-09-09 final readiness review raised blockers B1–B6 (map in §0). Owner-approved
remediation plan: `docs/build-stream/plans/testing-to-main-remediation-20260909-plan-a.md`
(pipeline `testing-to-main-remediation-20260909`, task
`testing-to-main-remediation-20260909-IMPL`). Remediation IMPL delivered, in the shared
worktree, the local-scope closures:

| Blocker | Local-scope closure delivered | Still owed before any readiness claim |
|---|---|---|
| B1 | fail-closed journey resolver (`tests/simulation/lib/journey-selection.mjs` + registry bijection + importability gate in CI); 82/83/84 named individually as pending credential-free release obligations | first real container-lane execution of 82/83/84 (CI `ui-journeys` / exact-SHA Mac lane) |
| B4 | scenario 83 rewritten: zero-match, restore, disabled-only, empty, and load-failure branches all assert real state; zero unconditional passes remain; product seam `resolveCatalogListState` + `role="alert"` error state with unit tests | same execution evidence as B1 |
| B5 | scenarios 82/83/84 declare admin/researcher/viewer/stranger cells via the obligation ledger (`variant-obligations.mjs`); isolated-context role driver (`role-variants.mjs`, labeled provisioning setup); coverage matrix rows for 82/83/84 and corrected project-settings mapping; CI lane sets `QA_TEAM_MODE=true` so role cells are honestly drivable | same execution evidence as B1 |
| B6 | this §0 verdict corrected to BLOCKED — EVIDENCE-PENDING; lifecycle appended (L-44) with truthful status | owner desktop decision (G0), exact-SHA CI (G1/W4), Mac Studio QA (G2/W5), protection package applied and negatively proven (G3/W6) |

B2/B3 have no agent-performable local closure: they require the owner push and the
protection PUT respectively (plan G1/G3). Until every row above reaches dated evidence on
one exact SHA, this dossier's operative verdict is §0, not the historical §2 matrix.
