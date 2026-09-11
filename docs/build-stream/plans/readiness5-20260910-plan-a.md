# S1 Plan — readiness5-20260910 (sole architect: manager/deepseek-flash)

Status: **owner-approved in session (2026-09-10)**. Run id `testing-to-main-20260910`.
Baseline: `conductor/main-readiness-20260909` @ `abc9da92` (contains testing + B1–B6 remediation).
Worktree: `/Users/user/Documents/Istara-wt-readiness5-20260910` branch `conductor/readiness5-20260910`.
Lifecycle: `docs/build-stream/2026-09-09-testing-to-main-convergence.md` (append L-46+).

Cast (fixed): implementer = `pi meta/muse-spark-1.3-contributor xhigh`; code-reviewer =
`pi meta/muse-spark-1.3-contributor xhigh` (owner choice, same-model review disclosed);
fixer = `pi deepseek/deepseek-flash xhigh`. All review gates run blind two-phase
(change-kind `security_or_architecture`).

## Non-negotiable run constraints
- All containers build/run **only on Mac Studio** (`ssh macstudio`, `/usr/local/bin/docker`).
  Never start Docker locally.
- **Preserve everything** under `~/istara-qa-testing-20260829/` (checkout, `.env`, `data/`,
  `.qa-shared/`, DB backups, evidence). Never modify those files; copy from them if needed.
  Never touch `proj-st150-pi-dd6bf277` / `session-st150-pi-b7a9bf45` data in a destructive way.
- New deployment dir only: `~/istara-qa-readiness5-20260910/` on the Mac Studio.
- Loopback-only ports + SSH tunnels for access. Never expose services publicly.
- **No Petals model inference anywhere**; exclude `tests/petals_bridge/` and any Petals donor
  path from every lane. Other Petals-adjacent unit tests may run only if model-free.
- Live model endpoints from the Mac Studio `.env` (already configured):
  `pi-zai-glm`, `pi-codex-luna`, `pi-codex-terra`. Do not print or commit keys.
- Synthetic creds/data for QA; real research data (CareNav) stays in the preserved DBs and
  its own project. **Never mingle CareNav with other projects/corpora.**
- Surgical edits only; no new product features. Any new fixture/corpus must be justified and
  isolated per project.
- No secrets, tokens, private URLs, or endpoint fingerprints in any commit/artifact.
- Every wave: compass-forge task evidence (command rows), gate after `--new-only`, ledger entry
  in the lifecycle, and a truthful result (failures recorded, never suppressed).

## Wave W1 — readiness-core (no environment dependency)
Goal: make the candidate's deterministic gates green and honest on the baseline.
1. `check_feature_obligations --base origin/main --head HEAD` must exit 0: classify the 486
   unknown paths into `testing/feature_coverage.yml` ownership (or the audited mechanical
   allowlist with justification). Keep patterns narrow; never a blanket `backend/**`.
2. Harness fail-closed gaps: scenario duplicate-id detection must exist AND be invoked;
   `tests/simulation/run.mjs` `loadScenarios` must fail closed on an import error and on a
   requested id that matches nothing (keep substring selection working for real ids).
3. Pi model management: fix the OAuth device-flow poll hot loop
   (`frontend/src/components/settings/PiModelManagement.tsx` ~280-303: dedupe status before
   `setActiveOAuth`, key the effect on flow id/provider, keep one interval) + add fake-timer
   regression. Surface `fetchAll` errors distinctly from empty (same pattern as the catalog
   error seam already on the baseline).
4. Docs truth: TESTING.md suite topology counts; mark any stale numbers from the tree.
5. M-18 (owner: desktop-check REQUIRED): add `desktop-check` to `testing/required-checks.json`
   `required_contexts`, keep the fail-closed release-gate contract green, update
   `docs/promotion/branch-protection/gh-api-body.json`, and the contract tests.
6. Fix any defect found by the reviewer; keep the diff surgical.

Acceptance: governance battery (integrity, ci-governance, test-harness, required-checks,
workflow-contracts, qa-capabilities, release-readiness, public-repo audit, production
rehearsal) exit 0; `security_benchmark --fail-on-threshold` pass; backend full suite green;
frontend tsc/lint/unit/build/mutation green; feature-obligations exit 0; `git diff --check`
clean; `compass-forge gate after --new-only` 0 new issues.

## Wave W2 — browser lane + UI/UX/WCAG on Mac Studio
Goal: real container-first browser evidence for the changed product surfaces.
1. Sync the candidate tree to `~/istara-qa-readiness5-20260910/` on the Mac Studio (rsync,
   excluding node_modules/.venv/.next/.results/data); build `docker-compose.qa.yml`
   (`--profile ui`, plus `qa-live-gate` only if needed later). Loopback-only publication.
2. SSH tunnels to the local machine; run the simulation harness against the QA stack:
   changed-feature journeys 82/83/84 + the proven set + representative product surfaces.
3. Matrix: admin/researcher/viewer/stranger where relevant, light/dark, 375px reflow,
   keyboard Tab + visible focus, loading/error/empty/disabled/permission-denied/stale-backend.
   Real browser acts only; API-behind-browser steps labelled.
4. Run the accessibility/heuristics/performance evaluators; capture screenshots + verdicts +
   HAR/console/network artifacts keyed to the SHA; inspect screenshots for interaction,
   WCAG, heuristic and user-flow problems; record findings.
5. Fix real defects found (surgical); add/extend regression scenarios; promote newly executed
   journeys into `testing/ui-journeys.smoke.json` / `proven-extra.json` so CI executes them.
6. Static audit: no unconditional/contradictory `passed: true` remains anywhere in
   `tests/simulation/scenarios/`; registry bijection holds; no duplicate ids.

Acceptance: dated browser verdicts for every executed journey, screenshots present, zero
unexplained `not_runnable` for changed features, fixes reviewed, CI lane lists updated.

## Wave W3 — live ensemble + Research Spine (through Pi model management)
Goal: first live, evidenced exercise of the multi-model/ensemble paths.
1. On the live QA stack (Mac Studio, `.env` endpoints), run a governed independent coding run
   over CareNav evidence units with **three distinct models** (`pi-zai-glm`, `pi-codex-luna`,
   `pi-codex-terra`): exact-span grounding, reliability (Fleiss/Krippendorff), served-model
   receipts, reconciliation decisions, report gating (accepted/reconciled only).
2. Exercise **adversarial review and debate/ensemble validation live** (never-tested paths):
   capture route evidence, model identity per pass, inputs/outputs evidence, and the
   operational-vs-formal-reliability labels. Low-confidence/absent-model paths must end in an
   honest typed result, never a silent fallback.
3. Verify the fail-closed gates with at least one adversarial probe each: missing coder,
   paraphrased quote, missing served identity, duplicate rating, unreconciled report attempt.
4. Record and archive run ids + metrics + receipts as SHA-keyed artifacts; fix real defects
   surgically; update tests where they were stale/wrong (no weakening).

Acceptance: ≥1 live 3-model coding run with κ/α recorded and accepted evidence promoted
through reconciliation; adversarial/debate runs recorded with receipts; fail-closed probes
proven; **no Petals inference**.

## Wave W4 — 150-turn long-horizon benchmark + telemetry + engine-choice UI
Goal: complete the long-horizon evaluation on BOTH engines with full telemetry/trajectories.
1. Restore a copy of the preserved research DB (`~/istara-qa-testing-20260829/.qa-shared/`
   newest `istara-qa-live.db` and/or `data/istara-qa-150turn-*.db`) into the new deployment.
   CareNav only; no other corpus in that project. Never mutate the originals.
2. Run `tests/run_150_turn_stress_test.py` for **both** engines (`legacy` and `pi`) with
   resume/checkpoints (extended worker timeout), live endpoints; complete the 150-turn
   trajectory or resume to completion; record per-turn results.
3. Telemetry/trajectories (owner requirement): per-turn/per-tool/per-model OTel spans and
   agentic usage rows; aggregate by engine and by model (latency p50/p90/p99, tokens, cost,
   error taxonomy, steering counts, tool-call depth, stop reasons); save SHA-keyed artifacts.
   Audit Istara's telemetry settings and capture correctness (enabled, content-free,
   attribution present) and report gaps with evidence.
4. Update the documented engine comparison (`docs/build-stream/2026-09-04-long-horizon-engine-
   comparison-and-main-promotion.md`, `docs/scientific_audit/long-horizon-agentic-engine-audit.md`)
   and `docs/architecture/agentic-engine-deep-dive.html` with the new measured numbers.
5. Update the engine-choice UI (`frontend/src/components/settings/AgenticCoreSection.tsx`
   and any metrics surface it links) so users can compare engines with real, dated metrics;
   screenshots light/dark/375px in the same wave (no new feature surface).

Acceptance: 150-turn completion (or documented resumable run) for both engines; telemetry
aggregates generated from real runs and stored; telemetry audit conclusion recorded; docs +
UI updated and reviewed; CareNav context isolated; no Petals.

## Wave W5 — certification + push (manager-owned push)
1. Re-run the full release matrix on the frozen SHA: all governance scripts, production
   rehearsal, security benchmark (plain + changed-paths), backend full suite, frontend
   suite, ruff, compose renders, CF gate new-only, lifecycle verifiers, scenario checks.
2. Correct `docs/promotion/2026-09-09-promotion-certification.md` to a truthful verdict bound
   to the new SHA with the evidence references; update `TESTING.md` / `testing/TEST_HISTORY.md`.
3. Verify the branch-protection package matches the required-check manifest (desktop-check
   now required) and produce the owner checklist.
4. Manager (not a worker) pushes `conductor/readiness5-20260910` to `origin/testing` after
   certifying the SHA, then reports the CI run id/result. Branch protection + promotion PR
   remain owner-gated.

Acceptance: matrix green locally on the recorded SHA; dossier truthful; push completed with
the SHA recorded; CI result reported.

## Rollback
Each wave is a normal commit range; a bad wave is reverted by SHA. The preserved Mac Studio
content is never mutated, so research data cannot be lost by this run.
