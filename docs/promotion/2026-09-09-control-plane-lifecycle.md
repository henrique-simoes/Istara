# W2 Control-Plane Lifecycle Dossier — 2026-09-09

Wave: `control-plane-lifecycle` · task `testing-to-main-20260909-WAVE-control-plane-lifecycle-IMPL`
Spec: CF-SPEC-30 · Base: W1 candidate freeze (boundary dossier + 192-row TSV, r2 re-review PASS)
Scope: docs, `.compass-forge`, scripts. No code repair (W3), no CI edits (W4),
no bulk task closure without cited evidence, no `impact`/schema-21 chase (M-10),
no history rewrite. Paths below are repo-relative; `<REPO_ROOT>` stands for the
checkout root per the M-02 path-hygiene rule.

## 1. Index freshness (deliberate refresh, M-10)

- `index refresh` run deliberately from the project root with the pinned native
  binary after HEAD `5845d2de` (2026-09-09T17:07:23Z), because `index status`
  showed `created_at 2026-09-09T16:15:42Z` — older than HEAD.
- Post-refresh `index status`: id 38, `created_at 2026-09-09T17:19:20Z` (newer
  than HEAD), `index_version 12`, `kernel rust`, `graph_version 2`,
  `indexed_file_count 943`, `warnings []`. Recorded **as observed**: there is no
  schema-21 target and no `graph_usable` field in this build; K-3/M-10 stand.

## 2. Impact capability migration (decision, M-10)

DEC-2 (recorded in the convergence ledger): bare `impact` is `not_yet_native`
in the R2 runtime; the working command is `intelligence impact --path <p>`
(singular `--path`; `--paths` is rejected). Waves read `confidence` +
`corpus.source`; freshness is asserted via `index status`, never via a
schema chase. Later agents must not re-derive this.

Per-surface results (all `corpus {graph_version 2, kernel rust, source tree-sitter}`):

| Surface | Confidence | must/should/tests | Gate hints |
|---|---|---|---|
| `backend/app/services/research_validity_service.py` | high | 30/30/30 | architecture_drift |
| `backend/app/api/routes/audit.py` | high | 18/30/21 | architecture_drift, contract_drift |
| `backend/app/api/routes/metrics.py` | high | 21/30/19 | architecture_drift, contract_drift |
| `backend/app/core/agentic/dispatcher.py` | high | 30/30/30 | architecture_drift |
| `frontend/src/components/chat/ChatModelControls.tsx` | high | 2/30/15 | architecture_drift, contract_drift |
| `docs/architecture/research-validity-contract.md` | low (no graph seed — expected for docs) | 0/0/0 | architecture_drift |

Manual dependency follow (static graph misses dynamic dispatch and
string-keyed routes): the audit surface is consumed via `audit_middleware`
plus `agent_lifecycle`, `report_manager`, `task_router`, `skill_factory` —
middleware/string-keyed paths, not static imports; no `importlib` dynamic
dispatch in the dispatcher or audit/metrics route sources; the compute relay
websocket (`compute.py:188-189`) is route-declared. Obligation matrix rows for
these paths name the middleware consumers explicitly.

## 3. Lifecycle reconciliation (M-08 — one status per initiative)

Re-measured 2026-09-09; two of M-08's four claims were already stale, which the
table records rather than conceals.

| Initiative file | M-08 claim | Re-measured | Disposition |
|---|---|---|---|
| `2026-09-08-pi-capability-inheritance.md` | S3/in-progress, permittable dispatch | S3-review/in-progress; r3 PASS (L-41), zero open review findings; `next_action` was contaminated with convergence-run text; `cf.tasks []` while CF-SPEC-29 has 13 open | **in-progress** — corrected by appended L-42 (tasks populated, next_action fixed); live-lane badge debt carried |
| `2026-09-04-long-horizon-...md` | S1/in-progress | S5-ship/completed; next points at the consolidating file | **completed** — M-08 stale on this file; no correction needed |
| `2026-09-08-benchmark-modernization-full-ui-suite.md` | S0/blocked AND Done/accepted | Block says S0-frame/in_progress/owner-approval; next_action overclaimed Done (scoped to CF-SPEC-24 batch); ledger mixes S5 (L-010) and S2 (L-011, corpus pending) | **in-progress (S2-execute)** — corrected by appended L-012; Batch 3 done, CF-SPEC-25 corpus/run pending |
| `2026-09-08-systemwide-audit-coverage.md` | Done with open F-007 | S5-ship/done; F-007 is documented **accepted-risk** (managed CF block, export-pipeline concern) | **completed with accepted residual** — no correction needed |
| `2026-09-09-testing-to-main-convergence.md` (this release) | — | Phase 0/S3-review block predates W1/W2 execution | **in-progress (Phase 2)** — block refreshed at L-19; `cf.tasks` populated with the wave task set |
| `2026-09-08-agentic-long-horizon-improvement.md` | — | S1-plan/in_progress; CF-SPEC-19 tasked, 9 open children | **deferred to CF-SPEC-19** (active, not release-blocking) |
| Older completed files (07-19 core-replacement tail, 07-20 runtime-completion, 07-22 benchmark, 08-22 migration, 08-23 integrity tail, 08-28 debt, 08-29 routing, 09-05 readiness, 09-06 core-ux, 09-06 systemwide-remaining, 09-07 gates, 09-08 engine-study/auth-milestone/auth-audit/chat-errno2/memory-reindex/settings-collapse) | — | S5-ship/done|completed, accepted parents | **completed** — no touch |
| Older still-open files citing external numbering (07-19 readiness CF-SPEC-5, 07-20 full-replacement CF-SPEC-8, 08-17 docker CF-SPEC-53, 08-18 automation CF-SPEC-56, 08-18 governance CF-SPEC-57, 08-23 agentic-core CF-SPEC-2) | — | reference spec/task ids with no object in this CF state; work superseded by the completed files above | **superseded (historical)** — ledgers append-only, left untouched; open CF children (CF-SPEC-2 ×3, CF-SPEC-8 ×8) triaged as deferred to their named specs, not closed |

Rule applied throughout: ledgers are append-only; corrections are new entries
(L-42, L-012, L-19), never rewrites. No file claims two stages after this wave.

## 4. Task triage (M-09 — 182 open, zero release-blocking)

Artifact: `docs/promotion/2026-09-09-control-plane-triage.tsv` (182 data rows,
one per open task, each with bucket + evidence citation).

| Bucket | Rows | Rule |
|---|---|---|
| release-blocking | **0** | nothing open blocks this promotion (justifications below) |
| open-not-release-blocking | 182 | deferred to a named spec/run with cited parent status |
| stale-administrative | 0 | **zero closures executed**: no open task sits under an accepted spec, so no row meets the bar (parent accepted + work evidenced elsewhere). Proving the empty set is the honest result of "staleness must be proven, not assumed". |

Group justifications (each row cites its own):
- CF-SPEC-30 template children CF-402..CF-410 (9): this release proceeds via
  wave tasks (boundary IMPL/REVIEW done; this IMPL claimed; REVIEW next);
  template scaffolding closes at spec acceptance per SC-002 — closing now
  would falsify acceptance later.
- CF-SPEC-29 children CF-344..CF-356 (13): parent tasked; wave review PASS
  (L-41); single carried live-lane badge-execution debt is owner-gated and
  pending-not-passing — flagged for W6/owner, not silently closed.
- CF-SPEC-19/25/28-family and all other tasked/planned-spec children (130):
  deferred to their named specs (lifecycle dispositions in §3); closing other
  initiatives' live work from this wave would be the cosmetic closure M-09
  names as the principal danger.
- `recipe_step` tasks without a parent spec, CF-138..CF-343 (30): process-level
  workflow steps with no acceptance record to cite; closure requires the
  run-owner decision — explicitly not closed by W2.
- CF-SPEC-7 (planned) carrying 8 open children: ordering oddity noted for the
  spec owner; not release-blocking for this promotion.

Owner-gated follow-ups (not executed here): run-owner close/pass on the 30
`recipe_step` rows; CF-SPEC-7 planned-vs-children ordering; CF-SPEC-30 template
children at acceptance.

## 5. Explicit spec dispositions

- CF-SPEC-19 tasked: active (agentic-long-horizon S1) — deferred, not blocking.
- CF-SPEC-25 tasked: active (Batch 3 + rich corpus, 13 open) — deferred, not blocking.
- CF-SPEC-28 draft: no open children in triage — nothing to dispose.
- CF-SPEC-29 tasked: wave review passed, live-lane debt carried (§4) — hard
  dependency of SC-002 tracked, not hidden.
- CF-SPEC-30 tasked (this release): wave tasks are the execution path; template
  children held for acceptance.

## 6. Obligation matrix (W3/W5 input)

Artifact: `docs/promotion/2026-09-09-obligation-matrix.tsv` (284 rows — every
W1-classified path plus every preserved-dirty path; columns: wave owner,
owning tests, owning docs, scenarios, security trigger, spine touch).
Coverage: zero unowned paths except `1{print`, an untracked ambient
shell-redirect junk file preserved in place as QUARANTINE (never staged;
owner may remove — W2 deletes nothing). Notable routings: corpus fixtures →
public-quality audit scan surface (M-22, tests-only); audit.py/metrics.py/
audit_middleware → `security_benchmark --fail-on-threshold` (M-12);
research_validity_* → spine gates non-bypassable; backend/frontend dirty
surface → W3a/W3b ownership (excluded from the W1 freeze, preserved dirty).

## 7. Doc drift (M-21)

`docs/architecture/research-validity-contract.md` header cited an external
spec/task numbering with no object in CF state. Corrected to a repo-rooted
governance pointer (content otherwise untouched); grep confirms the stale
tokens are gone from the file. Known sibling drift left for owners (out of
W2 scope, recorded not hidden): `self-improvement-governance-contract.md`
header numbering and the historical `CF-SPEC-124` citations in
`docs/features/...` architecture files.

## 8. Verification

- `index status`: id 38, `created_at` newer than HEAD `5845d2de`, `warnings []`,
  `index_version`/`kernel` recorded as observed (§1).
- Six `intelligence impact --path` runs with confidence + corpus recorded (§2).
- `python3 scripts/verify_wave_manifest.py` exit 0 (M-14 still holds post-W2).
- `python3 scripts/check_integrity.py` green.
- `pytest tests/test_public_repo_quality.py`: expected outcome is the standing
  baseline (tracked `AGENTS.md` leak preserved for W3a per M-02 ordering; W2
  adds no new finding — verified by re-running the audit after the commit).
- `git diff --check` clean on all W2-touched files; no `git add -A` (explicit
  pathspec list in the commit); `LLMs/`/`Model_Finetuning/` untouched
  (former absent, latter ignored — never enumerated).
- Research Spine / self-improvement contracts preserved: noFinding/fact/insight
  created; no gate weakened; no threshold touched; corpus stays tests-only.

## 9. Residuals for W3+

M-02 text repair (W3a), M-03 F821 (W3a), M-11 ruff pin (W3a), M-15 whitespace
(W3a), M-16 eslint (W3a), M-12 benchmark re-run on Promotion SHA (W3 verify /
W6 re-run), M-04 mutation (W3b), CF-SPEC-29 live-lane badge execution
(owner-gated), §4 owner follow-ups, §7 sibling drift.
