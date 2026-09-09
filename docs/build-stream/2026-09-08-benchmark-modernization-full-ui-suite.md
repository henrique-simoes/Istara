# Build Stream — Real-User Benchmark Modernization + Full UI Suite (planning)

<!-- STATUS BLOCK -->
```yaml
item: benchmark-modernization-full-ui-suite
branch: testing
cf: { spec: CF-SPEC-21, tasks: [CF-221, CF-222, CF-223, CF-224, CF-225, CF-226, CF-227, CF-228, CF-229, CF-230, CF-231, CF-232, CF-233, CF-234] }
phase: "Phase 0 — Frame + drift map (this file)"
stage: S0-frame
status: in_progress
blocked_on: owner-approval
last: { agent: pi, at: 2026-09-08T03:40:00Z, ledger: L-010 }
next_action: "Done. CF-SPEC-24 accepted 18/18. Suite complete per matrix; 30 static-by-design, 48 live-skips honest."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### S0 Frame — PRFAQ / one-pager (DRAFT, needs owner approval)
**Press release.** Istara's heaviest test layers once again prove what the
product actually does: Petals donation via the current Pi Model Management
pipelines, simulated team members with distinct roles, and a UI-driven matrix
covering every feature and sub-feature through a container — all green on
current code.

**Problem.** `tests/real_user_benchmark/` predates Pi Model Management:
donor sandboxes know only `llamacpp`/`ollama` + Q4/file checks; zero calls to
model-catalog/resolve/provisioning/endpoint-policy surfaces; petals flow aims
at the old relay shape (consent/status/node-scoped completions unexercised);
`/api/v1/models/load` has no backend route (dead call); May-era UI scenarios
and `scenario-76` predate current UI copy and engine plumbing.

**Outcome.** (1) Benchmark modernized to current code: Pi-managed donor
topology, model-mgmt + petals-bridge coverage, kinds-aware connection strings,
dead calls removed; `npm run check` + `plan` green. (2) Comprehensive
container-first UI suite: per-sub-feature scenario matrix with dated verdicts.

**Goal.** Modernize + complete; no product behavior change. Live runs (probe/
full, donors, Colima, models) stay owner-gated per repo policy.

**Non-goals.** No product code changes except test-only blockers (scoped,
flagged). No live model runs without explicit owner go-ahead. No merges.

**Appetite.** Modernization + suite completion with evidence; live-run
campaign is a separate authorized follow-up.

### Acceptance criteria
- `Given` `npm run check` in `tests/real_user_benchmark` `When` run `Then`
  green (verify: `npm --prefix tests/real_user_benchmark run check`).
- `Given` plan-only mode `When` run `Then` it plans the modernized workload
  without credentials (verify: `npm --prefix tests/real_user_benchmark run plan`).
- `Given` any benchmark API call `When` cross-checked `Then` a live backend
  route exists (verify: static route audit, zero dead calls).
- `Given` a UI scenario `When` run against current frontend `Then` selectors
  resolve and verdicts record (verify: scenario runs on QA `ui` profile).

### Drift evidence (measured, not claimed)
- D1: donor sandboxes accept only `llamacpp|ollama` (`donor-sandboxes.mjs:203`);
  current `PiModelManager` has catalog/resolve/resolve_distinct/provisioning/
  petals-projection — zero benchmark references (grep: none).
- D2 (corrected during S1): `/api/v1/models/load` targets the DONOR's own
  LMStudio server, not the Istara backend — valid call, not dead. Replaced by
  a systematic route audit (every benchmark backend call vs live routes).
- D3: petals-bridge now has consent/status/node-scoped completions
  (`petals_bridge.py:54,82,124,131`); benchmark petals path predates them.
- D4: `scenario-76` + foundation scenarios untouched since Mar–May; runner
  fresh (Sep 6). Selectors will have drifted.
- D5: connection-string kinds (`user_invite`/`compute_donation`,
  `connection_string.py:66,98`) postdate benchmark redeem flow — verify
  kind-awareness.

### Phased task graph (for S1)
| Phase | Goal | Verification |
|---|---|---|
| 1 | Benchmark modernization (donors→Pi topology, model-mgmt coverage, petals-bridge, kinds, dead-call removal) | `npm run check` + `run plan` green; route audit 0 dead |
| 2 | Stale scenario re-baseline (selectors/copy, engine headers) | drifted scenarios green on QA `ui` |
| 3 | Coverage matrix completion (per-sub-feature scenarios, roles, dark/375px) | matrix with dated verdicts |
| 4 | Blind review + docs graduation | independent measurement, TESTING.md updates |

### Rollback
Test-only files; revert = file-scoped revert. No product behavior touched.

## Decision log
- **DEC-1 | 2026-09-08 | S0 | owner** — Context: owner confirmed benchmark
  donor flow predates Pi Model Management and ordered modernization +
  comprehensive suite. Decision: proceed test-only, phased (benchmark first,
  UI matrix second); live runs stay owner-gated. Why: donor/petals coverage
  must prove current pipelines before any campaign claims.

## Append-Only Ledger
- **L-003 | 2026-09-08 | S2-execute | pi | CF-224**
  Did: post-change gate Phase 1 (gate-after 0/0; connections+compute 70/70).
  CF-224 done.
- **L-004 | 2026-09-08 | S2-execute | pi | CF-228 (Phase 2 pilot)**
  Did: triaged all 78 scenarios (marker+API+acts audit): 0 text-stale by
  markers (weak signal), but 45/78 have ZERO browser acts (structural
  staleness confirmed incl. scenario-76) and project-settings has no scenario
  at all. Re-baselined 76 with a real browser entry (verified selectors,
  helpers extracted); created `tests/simulation/coverage-matrix.json`
  (24 views × sub-features → scenarios/drive/verdict slots). Gate-after: 0 new
  failures; 1 inherited complexity note (76 run() 24, +0 branches — documented,
  no suppression). CF-228 done with evidence.
  Verified: triage script, `node --check`, static selector proofs, diff-check.
  Next: matrix fill per AGENTS.md contract (needs QA lane for live verdicts).
- **L-005 | 2026-09-08 | S2-execute | pi | QA lane (macstudio)**
  Did: Docker Desktop empty locally (killed my own just-started build, nothing
  deleted); found live fleet on macstudio SSH (nifty_dirac + QA stack, all Up).
  Synced 17 test files via docker-cp tarball (md5-verified). Live verdicts in
  container: sweep 24/24 render 0 netFails (1 benign /v1/models 404, now
  printed); auth UI proof 11/11; uniformity PASS; benchmark check 107/107.
  Scenarios 49/34/69 PASS (38/38 incl. new browser checks); 32/51/61 failed
  honestly (see L-006). Launched 76 live in background.
  Verified: container logs + md5s. Next: fix failures (L-006).
- **L-002 | 2026-09-08 | S1-plan/S2-execute | pi | CF-221…223**
  Did: CF-SPEC-21 clarified/planned/tasked (CF-221…CF-234); baseline
  (check 101/101, plan-only clean); implemented Phase 1: pi-managed donor
  kind (config/validate/no-container/summary + bypass + 3 tests), new
  model-management-probes module + 3 tests, run.mjs wiring (import,
  featureResults keys, kind asserts, probe call), fixed 3 dead probes
  (`/api/autoresearch/status|config` → `/api/status|/api/config` — routes
  flattened since Aug, probes silently 404ing); corrected D2 (v1/models/load
  is donor-directed, valid). check 107/107, plan green, 0 dead calls.
  Gate after CF-223: 0 new failures; 16 complexity notes on harness files
  recorded as inherited debt (0 new functions added). CF-221/222/223 done.
  Verified: `npm run check`, `run plan`, route audit greps, Aug action-logs.
  Next: Phase 2 (UI matrix) under new claim.
- **L-001 | 2026-09-08 | S0-frame | pi | —**
  Did: drift analysis (D1–D5) via route/call cross-checks; wrote this file.
  Result: scope framed; 0 files touched except this plan.
  Verified: greps above re-runnable.
  Next: owner approval (DEC-1), then CF spec + S1.
- **L-006 | 2026-09-08 | S2-execute+S4 | pi | live failures → fixes**
  CORRECTION (same day, deeper investigation): the `/api/autoresearch/*`
  rewrite was MY error, not a product finding. Root cause of my error:
  route audit read decorator suffixes (`@router.get("/status")`) + mount
  prefix (`/api`) but missed the router-level `APIRouter(prefix=
  "/autoresearch")` (autoresearch.py:36) — true shape was prefixed all
  along. Proof: frontend api.ts (9 prefixed calls, 0 flat), backend's own
  error string (`via /api/autoresearch/toggle`), local authed probe
  (prefixed 200, flat 404), deployed openapi (7/7 prefixed, 0 flat),
  test_autoresearch 200s. **F-A1 CLOSED as audit false-positive** — no
  divergence exists; prefixed wins unanimously. All rewrites reverted and
  verified live (61 15/15). Lesson: route audits must resolve
  decorator + router-prefix + mount-prefix, and live-probe before rewriting.
  Did: live run exposed (a) my prefix rewrite was WRONG: deployed backend
  serves `/api/autoresearch/*` (openapi-verified), repo HEAD says flat —
  reverted all rewrites (benchmark 3, scenarios 61/64/67), filed **F-A1**
  (code/deployment route-shape divergence — owner must decide which shape
  wins; suite tracks deployment truth meanwhile); (b) real product crash:
  config POST poisoned `settings.backup_retention_count` to str via
  `persist_env_value` setattr (no pydantic validation on plain setattr) →
  every later create_backup 500'd — fixed with `_coerce_for_settings`
  (int/float/bool, safe passthrough) + regression test, healed QA via
  container restart (no data deleted); (c) 51 numeric-compare + 32
  auth-context brittleness fixed in-scenario. Re-ran live: 61 15/15, 32 5/5,
  51 18/18. Local: backup 12/12, ruff clean, benchmark 28/28.
  Product change flagged: `backend/app/core/env_persistence.py` (+coercion),
  `tests/test_backup.py` (+regression) — crash fix, no behavior redesign.
  Verified: backend traceback, openapi dump, live re-runs, local suites.
  Next: close-out (CF-225…234, accept).
- **L-007 | 2026-09-08 | S5-ship | pi | done**
  Did: finished CF-225/226/227/229–234 with evidence; `spec accept CF-SPEC-21`
  (no force, 14/14). Live scoreboard: sweep 24/24, auth 11/11, uniformity,
  benchmark-check 107, scenarios 49/34/69/61/32/51 all PASS live (101 checks);
  76 running live with browser entry already green. Matrix live verdicts set.
  Status Block done. Residuals: F-A1 (route-shape decision for owner),
  F-007, 76 full verdict pending, remaining 38 api-only scenarios per contract.
  Verified: accept payload; container logs.
  Next: none scheduled.
- **L-008 | 2026-09-08 | S5-ship | pi | Batch 1 done (CF-SPEC-22)**
  Did: converted scenarios 10/14/20/21/27 (+shared helper hardening:
  tour dismissal, marker polling, case-insensitive match after live failures
  root-caused via DOM probes + failure screenshot). Live in nifty_dirac:
  Batch 1 136/136 ALL CLEAR; 76 full trajectory 9/9 ALL CLEAR. Matrix live
  verdicts set (agents/skills/chat). CF-SPEC-22 accepted 14/14, no force.
  Verified: container logs, screenshot diagnosis, node--check, diff-check.
  Next: Batch 2 whenever ordered.
- **L-009 | 2026-09-08 | S5-ship | pi | Batch 2 done (CF-SPEC-23)**
  Did: converted scenarios 45/46/59/55/50 (interfaces×2, integrations×2
  incl. surveys tab, notifications) via shared helper — no helper changes
  needed. Live in nifty_dirac: 107/107 ALL CLEAR on first run (35+25+18+
  15+14). Matrix live verdicts set (interfaces/integrations/notifications).
  CF-SPEC-23 accepted 18/18, no force. Scenario 30 kept static-by-design
  (code-audit scenario, labeled in matrix).
  Verified: container log, node--check, gate 0/0, diff-check.
  Next: Batch 3 (leftovers + new project-settings scenario).
- **L-010 | 2026-09-08 | S5-ship | pi | Batch 3 done (CF-SPEC-24)**
  Did: converted remaining 31 API-only scenarios via scripted pattern +
  new 81-project-settings (browser + members/metrics API) + registry entry;
  added selector-visibility checks to helper after 42 exposed placeholder-
  vs-innerText gap. Live in nifty_dirac: group A 260/261 (42 fixed same
  turn), group B 214/214 ALL CLEAR; 48 browser PASS + live steps honestly
  skipped (no keys). Matrix: all 24 views carry live verdicts (30 static-
  by-design labeled). CF-SPEC-24 accepted 18/18, no force.
  Verified: container logs, report.json, node--check all, gate 0/0.
  Next: none — suite complete per matrix; AGENTS.md contract governs additions.
- **L-011 | 2026-09-08 | S2-execute | pi | Rich corpus (CF-SPEC-25/CF-287)**
  Did: built Harbor Ledger rich corpus (generator + 75 files/11,056 lines +
  manifest ground truth + selector + README). Web-survey verdict: no open
  corpus offers deep coherent transcripts with answer keys, so synthetic-
  with-provenance was chosen over scraping (consent/licensing/PII). Fixed
  language leakage (EN/ES split banks), expanded to ~12 EN + ~6 ES quotes
  per theme, bulked context packs to 250–488 lines. Deterministic verified.
  Gate-after CF-287 0/0. Full 79-scenario run in progress in nifty_dirac.
  Verified: generation ×3, selector smoke, node--check, diff-check.
  Next: judge full-run verdicts; wire rich corpus into scenarios/runners.
