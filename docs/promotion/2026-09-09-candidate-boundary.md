# Candidate boundary — testing-to-main 2026-09-09 (W1, scoped freeze)

Wave: `candidate-boundary` · Spec: `CF-SPEC-30` · Task:
`testing-to-main-20260909-WAVE-candidate-boundary-IMPL`
Scope of this commit: `docs`, `scripts`, `tests` (`.compass-forge` is
gitignored and cannot be committed; its state is referenced, never moved).

All repository paths below are relative to the checkout root (`<REPO_ROOT>`).
The initial freeze accidentally committed seven artifacts containing the local
checkout path, increasing the tracked public-quality audit from 2 to 9 findings.
Remediation scrubbed those seven paths; the remaining tracked finding predates
this wave, while the ambient `AGENTS.md` finding remains uncommitted.

## 1. Frozen refs (measured 2026-09-09, this session)

| Ref | SHA | Evidence |
|---|---|---|
| Local `testing` HEAD at wave start | `63cf6dac` | `git rev-parse HEAD` |
| `origin/testing` | `9961fa3d` | `git rev-parse origin/testing` |
| `origin/main` | `fa6a1a39` | `git rev-parse origin/main` |
| Merge base with `main` | `fa6a1a39` (`main` is a strict ancestor) | `git merge-base HEAD origin/main` |
| Local vs `origin/testing` | 78 ahead, 0 behind | `git rev-list --left-right --count origin/testing...HEAD` |
| Tracked worktree delta at start | 155 files, +4712/−977 | `git diff --shortstat` |
| Untracked (excl. ignored) at start | 120 files | `git ls-files --others --exclude-standard \| wc -l` |
| Stash entries touched | 0 (list recorded, never dropped) | `git stash list` |

The **scoped candidate SHA** is the commit this wave creates (recorded in the
ledger entry for this task). It freezes the in-scope surface below. Product
code outside this scope stays dirty in the worktree, preserved untouched
(see §4), and is frozen by the wave that owns it (W3 for `backend`/`frontend`).

## 2. Surface verdicts

| Surface | Contents | Verdict | Reason |
|---|---|---|---|
| A — `origin/testing` `9961fa3d` | 994 commits over `main` | Rejected | Missing 78 local commits and every worktree change; CI red on it. |
| B — local committed `testing` alone | A + 78 commits | Rejected | Import closure fails: tracked-modified files import modules that exist only as untracked worktree files (e.g. `@/lib/tokenStore`); this surface cannot typecheck or build. |
| C (scoped) — local commits + classified in-scope worktree | B + `INCLUDE-*` paths under `docs`/`scripts`/`tests` | Selected as a boundary freeze; not independently promotable | The in-scope inventory is explicit, but five committed tests depend on excluded `backend/` changes. The scoped candidate therefore does **not** close its test graph and remains red pending W3; out-of-scope product files are preserved dirty, never swept in. |

Full surface C (including `backend`/`frontend`) is assembled by W3 on top of
this commit. W3 owns the missing implementation closure; this wave records the
known red rather than sweeping those files into the freeze or claiming closure.

## 3. Classification (in scope)

Machine-readable manifest:
`docs/promotion/2026-09-09-candidate-classification.tsv`
(one row per pre-existing classified path: `path · bucket · evidence citation · owning ref · sha256`).
Together with the four wave-produced files enumerated in §6, it accounts for
all 196 paths in candidate commit `3de70bfc`.

| Bucket | Rows | Meaning |
|---|---|---|
| `INCLUDE-LIFECYCLE` | 24 | `docs/build-stream` narrative, including this initiative's convergence lifecycle, plus the architecture study |
| `INCLUDE-PRODUCT` | 166 | `tests` modifications (69) and new fixtures/probes/corpus files (97), `tests/` only |
| `INCLUDE-HYGIENE` | 2 | `docs/features/site/manifest.json` docs-site rebuild artifact (`generated_at` refresh) and checkout-relative executable hygiene tooling (`docs/build-stream/run-blind-review.sh`) |
| `QUARANTINE` / `UNDECIDED` in scope | 0 | Every in-scope path is traced to evidence; nothing defaults to silent inclusion |
| Wave-produced files (§6) | 4 | This dossier, the TSV, the tracked manifest export, `verify_wave_manifest.py` — `INCLUDE-HYGIENE` by construction, committed via the same pathspec |
| **Total candidate paths** | **196** | **192 TSV rows + 4 wave-produced files; no silent inclusion** |

Commit rule used: `git add --pathspec-from-file` with the explicit
`INCLUDE-*` path list only. No `git add -A`, no pathless commit, no reset,
no clean, no stash drop, no amend, no rebase, no force-push.

## 4. Explicitly excluded and preserved (not in this commit)

| Path group | Count | Disposition |
|---|---|---|
| `backend/**` tracked modifications | 32 | Preserved dirty in worktree; owned by W3 `correctness-quality` |
| `frontend/**` tracked modifications + 4 untracked (`tokenStore.ts`, `tokenStore.test.ts`, `SeeMoreList.tsx`, `ToolAuditTrailTable.tsx`) | 43 + 4 | Preserved dirty/untracked; untracked four are REQUIRED import-closure inputs for W3 (22 tracked files import them); never deleted |
| `AGENTS.md`, `qa/Dockerfile`, `recipes/istara-main/recipe.toml`, `security/SECURITY_BENCHMARK.md`, `security/control_matrix.json` | 5 | Preserved dirty; `AGENTS.md:142` leak stays until W3a text repair (M-02); audit re-run recorded as still-red in §7 |
| Protected: `Model_Finetuning/` | ignored, untouched, never enumerated | Verified via `git check-ignore`; byte-identical |
| Protected: `LLMs/` | absent in this checkout; nothing to preserve | No action |
| Generated/ignored: `.stryker-tmp/`, `node_modules`, `.results`, `.compass-forge/` | excluded, never deleted | `.stryker-tmp` sandbox is the M-16 lint trap; left for W3 eslint-ignore fix |
| Recovery branches | `backup/pre-candidate-20260909`, `quarantine/ambient-20260909` at wave-start SHA | Local only; no push |

## 5. Build Stream dispositions

| Lifecycle record | Status | Disposition |
|---|---|---|
| `2026-09-09-testing-to-main-convergence.md` (this initiative) | S1-plan, in-progress | Included; ledger appended by this wave |
| Winning master plan slot b (`plans/testing-to-main-20260909-master-b.md`) | Owner-approved | Included (already tracked) |
| `plans/testing-to-main-20260909-plan-b/c.md`, `master-c.md` | Synthesized, not winners | Included (already tracked); superseded as plan of record, preserved as audit trail |
| `plans/testing-to-main-20260909-plan-a.md`, `master-a.md` | Superseded drafts | Included by this wave; disposition superseded |
| `pi-compat-20260908-{plan,master}-a.md` | Prior run records | Included by this wave; disposition superseded |
| `2026-09-06-systemwide-remaining-surfaces-and-design-hardening.md` and other dated 09-06…09-08 records | Various done/in-progress | Included by this wave as narrative truth-input; contradictions flagged for W2 (M-08), never rewritten here |
| `2026-09-08-systemwide-audit-coverage.md` (Done with open F-007), `benchmark-modernization-full-ui-suite.md` (S0/blocked and Done), `pi-capability-inheritance.md` + `long-horizon-engine-comparison` (in-progress claims) | Contradictory stage claims | Deferred to W2 `control-plane-lifecycle` for append-only correction; no status rewritten in this wave |
| CF-SPEC-29 and the 181 open CF tasks | Triage pending | Deferred to W2; no bulk closure here (M-09) |

## 6. Wave-produced files (this commit)

- `docs/promotion/2026-09-09-candidate-boundary.md` (this dossier)
- `docs/promotion/2026-09-09-candidate-classification.tsv` (192 rows)
- `docs/build-stream/2026-09-09-testing-to-main-waves-manifest.json` (tracked export of the conductor manifest)
- `scripts/verify_wave_manifest.py` (M-14 canonical-hash verifier, stdlib only)

Manifest hash recipe (M-14): the task payload pins the SHA-256 of the
canonical compact sorted JSON (`json.dumps(obj, sort_keys=True,
separators=(',',':'))`), NOT of the file bytes. Pinned `8601a1fc…` reproduces
exactly; `verify_wave_manifest.py --expected-hash` exits 0 (see §7).

## 7. Verification on the frozen surface

| Check | Result |
|---|---|
| `verify_wave_manifest.py --expected-hash 8601a1fc…` | Exit 0, `canonical_sha256=8601a1fc…` matches the task payload (M-14 closed for this wave; not tampering) |
| `git fsck --full` | Clean (recorded as command evidence) |
| `git status` residue after commit | Only §4 excluded/preserved paths remain; each accounted for above |
| `git stash list` | Unchanged (0 entries before and after) |
| Protected dirs | `Model_Finetuning/` still ignored/untouched; `LLMs/` absent |
| `pytest tests/test_public_repo_quality.py -q` / direct `audit()` count | The freeze expanded the tracked scan surface and regressed direct findings **2 → 9** by adding seven `machine_checkout_path` violations (not merely one failed pytest function). This remediation scrubs all seven; the focused audit must return to the two-finding baseline before re-review. |
| `git diff --check` on wave-produced files | Clean (no new whitespace findings from this wave) |
| CF `index status` / `intelligence impact --path` | Deferred to W2 per M-10 (no schema-21 chase, no bare `impact`) |
| Committed tests on candidate `3de70bfc`: `python -m pytest tests/test_files.py tests/test_websocket.py tests/test_auth_security.py -q` in a clean detached worktree | **5 failed, 61 passed**. Failures: quarantined-file serving; WebSocket rejection of a pre-MFA session after enrollment; MFA factor-change step-up; HTTP rejection of a pre-MFA session after enrollment; idle-session revocation. The same tests pass only with the preserved dirty `backend/` implementation, so this is a known deferred W3 condition, not closed candidate evidence. |
| `npx tsc --noEmit` dependency closure | Deferred to W3: the full closure spans the out-of-scope `frontend/` untracked modules, which this scoped wave preserves but does not commit |

## 8. Residual risks and handoff

- Classification of test/probe intent is judgement-based; every row cites evidence so the reviewer audits rather than re-derives.
- The candidate SHA of this wave covers only `docs`/`scripts`/`tests`; promotion binds to the later W6 Promotion SHA, never to this SHA alone.
- Owner writes to the shared worktree between freeze and W3 invalidate file hashes; any such drift forces re-measurement (M-19 rule: evidence without a SHA is rejected).
- Next: W2 `control-plane-lifecycle` consumes the TSV + tracked manifest + this dossier; W3 consumes the preserved `backend`/`frontend` dirty surface plus the 4 untracked `frontend/src` closure files.
