# FINAL certification — main-readiness-final-20260911 on 25e2063d (2026-09-11)

Wave: `certification-final` · Spec: `CF-SPEC-30` · Task: `main-readiness-final-20260911-WAVE-certification-final-IMPL`
Pipeline run: `main-readiness-final-20260911` · Lifecycle: `docs/build-stream/2026-09-09-testing-to-main-convergence.md` (L-78)

## 0. VERDICT: READY — OWNER-GATED PROMOTION (full local matrix green on the exact final SHA; push + CI observation + protection + promotion dispatch remain owner-owned)

Final SHA: `25e2063d33bc948cb6e80c93015a09e82e207b50` (short `25e2063d`), tree `e609049f32c1256d88d5905389827c4627fc2463`, branch `conductor/readiness5-20260910`, baseline `origin/main` `fa6a1a39` (strict ancestor; fast-forward mechanically possible).
Delta since the last pushed CI SHA `15ef4835` (7 commits): `95c1fa57` pi-preflight test-harness fix (L-72) → `01def0c8` blind review PASS (L-73) → `becfca4d` retry-evidence note → `d55ba289` promotion-range lint clear 274→0 (L-74) → `fe55d464` blind review FAIL prompt-fidelity (L-75, F-LPR-1 Major + F-LPR-2/F-LPR-3 minors) → `b3011c01` prompt-byte restoration + dispatch regressions (L-76) → `25e2063d` delta re-review PASS (L-77). Diff `15ef4835..25e2063d`: 79 files, +795/−340.
Freeze provenance: worktree at certification is byte-identical to `25e2063d` — 0 modified, 0 untracked, 0 stash; `git diff --check` clean; `git branch -r --contains HEAD` empty (never pushed — no agent push). This dossier + lifecycle + TESTING/TEST_HISTORY edits are committed AFTER the matrix run, so the certified product SHA is `25e2063d` and the push ref (G1) will be the post-certification branch tip; re-verify `git diff --stat 25e2063d..<pushed-tip>` is docs-only at push time (procedure in §5).
This header supersedes the W5 header below (which certified `3b4b881d`); the W5 header and the 2026-09-09 dossier are preserved verbatim underneath as the historical appendix.

## 1. Release matrix on 25e2063d (every row re-ran for this certification, keyless lane)

| # | Criterion | Command | Result |
|---|---|---|---|
| 1 | Governance battery (8) | `check_integrity.py`, `check_ci_governance.py`, `check_test_harness.py`, `check_required_checks.py`, `check_workflow_contracts.py`, `check_qa_capabilities.py`, `security_release_readiness.py`, `public_repo_quality_audit.py --check` | 8/8 PASS (required-checks: 17 contexts incl `desktop-check`, release-gate lockstep) |
| 2 | Feature obligations (base `origin/main`) | `check_feature_obligations.py --base origin/main --head HEAD` | PASS (`pass: true`, 0 unknown) |
| 3 | Change obligations (base `origin/main`) | `check_change_obligations.py --base origin/main --head HEAD` | PASS |
| 4 | Production rehearsal | `production_rehearsal.py --json` (py3.12 venv) | `passed: true` |
| 5 | Security benchmark plain | `security_benchmark.py --fail-on-threshold` | PASS — 28/28 controls, score 100.0, 0 triggered |
| 6 | Security benchmark changed-paths | same, `--changed-paths-file` with all 1577 `origin/main..HEAD` paths | PASS — 28/28, 100.0, 372 paths triggered |
| 7 | Full backend suite (exact CI command) | `cd backend && pytest ../tests/ -q --tb=short -m "not live_llm"`, keyless (`env -u DATA_ENCRYPTION_KEY`), py3.12.13, both pi surfaces `npm ci`'d | **2377 passed / 6 skipped / 1 deselected / 0 failed** (262.53s; collect 2384, 1 deselected → 2383 run = 2377+6) |
| 8 | Backend mutation gate | `scripts/run_backend_mutation.py` | exit 0 — 252 killed / 97 survived / 0 no-cov over 349 mutants (`compute_capacity.py`; gate is exit-0, posture unchanged; `mutants/` cleaned by the gate itself) |
| 9 | Frontend types | `cd frontend && npx tsc --noEmit` (node 24.20.0) | clean (exit 0) |
| 10 | Frontend lint | `npm run lint` (node 24.20.0) | 0 errors / 41 advisory warnings (M-24 posture) |
| 11 | Frontend unit | `npm run test:unit` (node 24.20.0) | 23 files / 121 tests passed |
| 12 | Frontend build | `npm run build` (node 24.20.0) | green — compiled successfully, static pages generated, 0 errors (build side-effect `frontend/next-env.d.ts` reverted; tree clean) |
| 13 | Frontend mutation | `npm run test:mutation` (node 24.20.0) | **90.77** (118 killed / 12 survived / 0 no-cov / 0 errors) ≥ break 75 |
| 14 | Backend-dir ruff (pin 0.16.6) | `ruff check . --select F821,F811,F822` + `ruff format --check .` (working-directory backend) | All checks passed; 371 files formatted |
| 15 | Promotion-range lint gate (base `origin/main`) | `scripts/check_ruff_changed.py --base origin/main --head HEAD` (ruff 0.16.6) | exit 0 — All checks passed (274-error debt cleared by `d55ba289`; F-CI-R1-3 advisory closed by this result) |
| 16 | QA compose renders | `docker compose -f docker-compose.qa.yml --profile <p> config --quiet` for contract/synthetic/audit/ui | 4× exit 0 (parse-only, M-05 honest) |
| 17 | Lifecycle verifiers | `verify_build_stream_status.py` + `verify_wave_manifest.py` + `check_integrity.py` | OK (status/roadmap agree; wave manifest canonical; local conductor-mirror warning is worktree-expected — manifest lives under ROOT) |
| 18 | Scenario/registry checks | `tests/simulation` `npm run test:static`; `node --check` 82/83/84 | 41/41 pass (registry bijection + fail-closed selection incl.); 82/83/84 syntax OK |
| 19 | Real-user static + relay | `tests/real_user_benchmark` `npm run check`; `cd relay && npm test` | 107 pass / 0 fail; relay 18 pass / 0 fail |
| 20 | Pi diff-proof gate | `scripts/pi_bump_diff_proof.py verify` | PASSED (pins 0.85.1 both surfaces) |
| 21 | Branch-protection package | `testing/required-checks.json` vs `docs/promotion/branch-protection/gh-api-body.json` | 17 == 17 verbatim incl `desktop-check`; `check_required_checks.py` lockstep PASS |
| 22 | CF gate after --new-only | pinned binary from ROOT (registered project; worktree is not) | status `pass`, `failures: []`, `issues: []` (scope residual R-2 below) |
| 23 | Last pushed CI run (RECORDED, not claimed) | GH run `34618262996` on `15ef4835` (2026-09-11T15:48Z, push) | CONCLUSION: **failure** — 16/17 green (incl `ui-journeys`, `desktop-check`, all frontend, mutation, governance); `backend-test` 3 failed / 2371 passed — exactly the pi-worker trio whose fix (`95c1fa57`, L-72) postdates the pushed SHA and is verified fixed at L-73 on py3.12. **No CI run exists for `25e2063d`; exact-SHA CI is owner-push-owned (G1).** |

Ruff scope note (unchanged posture): rows 14–15 are the CI-authoritative scopes. No ROOT-scope lint debt is claimed or fixed here.

## 2. Browser lane W2 (carried from the 3b4b881d certification below — NOT re-executed on 25e2063d)

W2 evidence (16 scenarios + 3 evaluators: 15 PASS + 1 SKIP, 248 checks; 82 15/15, 83 17/17, 84 13/13) was executed against the `3b4b881d`-era tree. Since then the product changed only by: `95c1fa57` (test-harness only), `d55ba289` (lint-only; two prompt-byte regressions caught at L-75 and restored byte-identical at L-76 with AST proof + dispatch regressions), `cb533538`/`bf5178a8`/`d3dae350` (Slack name restore, CI dual-install, mcp bound — all pre-`15ef4835`, covered by pushed CI's green `ui-journeys`). No behavioral product change is unaccounted: prompt bytes are AST-verified identical to pre-lint, the Slack name is SDK-parity, and the full suite + frontend unit/build are green on `25e2063d`. Re-running the live lane on the final SHA is owner-optional; the lane is recorded as carried, not fresh. No Petals/push.

## 3. Live ensemble W3 + long-horizon W4 (carried, same basis as §2)

W3 (3-model admission/reconciliation/adversarial/debate + 5 probes) and W4 (151 turns/engine, telemetry, DAGs, docs + UI slice) ran against the `3b4b881d`-era tree with blind PASS verdicts (L-58, L-60) and minors as follow-ups. Same carry basis as §2: no unaccounted behavioral change since; live re-runs owner-optional. No Petals/push.

## 4. Closure map at 25e2063d

M-01 through M-17 closed (carried); M-18 decided (desktop-check required, green in pushed CI and in the 17-package); M-19 through M-22 closed (carried); M-23 owner (G5 below); M-24 posture kept (41 eslint warnings advisory). F-CI-R1-1/R1-2/R2-1 closed with delta-PASS verdicts (L-67/68/69/71); F-CI-R1-3 advisory closed by row 15. F-LPR-1/F-LPR-2 closed with delta-PASS (L-77); F-LPR-3 advisory (suite-count environment note) rides. F-PTG-1/F-PTG-2 advisory ride. Riding minors from earlier waves (F-R5-W2-R1-2, F-R5-W3-R1-2/R1-3/R1-4, F-R5-W4-R1-1/R1-2, registerPasskey residual) remain follow-ups, non-blocking. B1 (browser lane carried, §2), B2 owner (row 23), B3 owner (G3 below), B4/B5 closed (carried), B6 this dossier.

## 5. Owner checklist (owner-only; no agent — ordered, with exact commands)

- [ ] G1 push + CI: from a clean checkout of branch `conductor/readiness5-20260910`, verify `git rev-parse 25e2063d` resolves, `git status --short` is empty, and `git diff --stat 25e2063d..<tip>` is docs-only (this dossier, lifecycle, TESTING.md, TEST_HISTORY.md). Push the branch to `origin/testing`. Record `gh run list --commit <pushed-tip SHA>` id + per-job result — expect 17/17 green (row 23's 3 backend-test failures must NOT recur: the fix `95c1fa57` ships in the pushed ref).
- [ ] G2 info: W2–W4 QA evidence (§2–§3 + appendix) suffices; QA-host state disposable.
- [ ] G3 protection: `testing-promotion` environment does NOT exist yet (API 2026-09-11 lists only `github-pages`) — create it first with required reviewers. Then PUT `docs/promotion/branch-protection/gh-api-body.json` (verified 17/17 == manifest, row 21) per `docs/promotion/branch-protection/README.md`, attach the API read-back + a negative mergeability test.
- [ ] G4 dispatch: `gh workflow run promote-testing.yml --ref testing -f source_sha=<pushed-tip SHA after G1 green> -f base_branch=main` (anti-replay requires the SHA to equal current `testing` HEAD; the workflow itself requires a green CI run on that exact SHA, so G1-green precedes dispatch). Verify the created promotion PR, then human review + merge per M-23 (`--no-ff` recommended so the certification record ships with the code).
- [ ] G5 merge + post-merge main CI observation; record results in `testing/TEST_HISTORY.md`.

## 6. Residuals (non-blocking, honest)

R-1 exact-SHA GitHub CI unobserved (row 23; push owner-gated). R-2 CF `gate after --new-only` ran on the registered ROOT tree (`fd1c3934`), not the worktree SHA — pass/0-new is ROOT-scoped; worktree architecture risk is bounded by rows 1–3 + 21 (no manifest/recipe/contract change in the certified delta). R-3 live lanes carried, not fresh (§2–§3). R-4 full-tree python import-cycle baseline is pre-existing (gate new-only 0 new). R-5 backend mutation 97 survived / frontend 12 survived (both within gate posture: exit-0 / break-75). R-6 local lane ran keyless on py3.12.13 macOS; CI (Ubuntu py3.12) is authoritative. R-7 `verify_wave_manifest.py` local-mirror warning is worktree-expected (manifest canonical under ROOT).

Certified by main-readiness-final-20260911-implementer (meta/muse-spark-1.3-contributor, xhigh). Do NOT push — the manager pushes after verifying SHA (G1).

---
Historical appendix: W5 header on 3b4b881d + 2026-09-09 dossier preserved verbatim below (superseded verdicts remain as audit trail).

---
# W5 certification header — readiness5-20260910 on 3b4b881d (2026-09-11)

Wave: `certification` · Spec: `CF-SPEC-30` · Task: `testing-to-main-20260910-WAVE-certification-IMPL`
Plan: `docs/build-stream/plans/readiness5-20260910-plan-a.md` §Wave W5

## 0. VERDICT: READY — OWNER-GATED PROMOTION (local matrix green on 3b4b881d; push + protection + CI observation remain)

Candidate SHA: `3b4b881de23f60e8b58d8a84a907b33c0e105f21` (short `3b4b881d`), branch `conductor/readiness5-20260910`, baseline `abc9da92`.
Range `abc9da92..3b4b881d` (13 commits, oldest→newest): W1 `c5e2dfca`; W1 review bookkeeping — harness fallback-ledger commits `512f662e` `28327268` `534d4479` and owner-authorized replacement verdict `996d8223` (PASS, L-50); W2 `97a73a8a`; W2 review `ab8698f4` (FAIL → fix task); W2 fix `97dbb2ce`; W3 `ed2aa7b8`; W3 review `835d1a23` (FAIL → fix task); W3 fix `66c0ff87`; W4 `9aa3034a`; W4 review `3b4b881d` (PASS).
Certification commit `23554f74` (direct child of the candidate; docs-only diff — TESTING.md, lifecycle, this dossier, TEST_HISTORY.md — so product-identical); `git rev-list --count abc9da92..23554f74` == 14. The W5 review `8f77fb73` and the remediation commits after it extend the branch tip past both, so the pushed ref (G1) is the branch tip, not the candidate `3b4b881d`.
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
- [ ] G1 push + CI: manager verifies the candidate exists (`git rev-parse 3b4b881d` resolves), that the certification commit `23554f74` is its direct child and product-identical (`git rev-parse 23554f74^` == `3b4b881d`; `git diff --stat 3b4b881d..23554f74` docs-only), the worktree state (0 modified / 2 untracked docs: plan-a.md, evaluation-log.md), and `git rev-list --count abc9da92..23554f74` == 14 (13 commits to the candidate + the certification commit; the review/remediation commits after it grow this count, so verify 14 against `23554f74`, not against the pushed tip). Manager pushes branch `conductor/readiness5-20260910` to `origin/testing` — the pushed ref is the branch tip (descendant of `23554f74`), **not** the candidate SHA `3b4b881d` — and reports `gh run list --commit <pushed-tip SHA>` id + result (expect 17/17 incl ui-journeys + desktop-check first observation).
- [ ] G2 info: W2-W4 QA evidence above suffices; preserved dirs untouched; QA-host state disposable.
- [ ] G3 protection: PUT gh-api-body.json (verified == manifest 17/17 incl desktop-check), attach API read-back + negative mergeability test, sequencing per README.
- [ ] G4 merge: record M-23 (--no-ff recommended; certification commit `23554f74` parent == `3b4b881d`, and `git diff --stat 3b4b881d..<pushed-tip>` docs-only at merge time → product-identical), merge, post-merge main CI. Protection + PR owner-gated.

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
