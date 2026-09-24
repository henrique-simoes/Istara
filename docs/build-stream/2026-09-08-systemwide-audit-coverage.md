# Build Stream — Systemwide Audit Coverage (menus, surfaces, auth-adjacent)

<!-- STATUS BLOCK -->
```yaml
item: systemwide-audit-coverage
branch: main   # testing was promoted to main by squash merge (PR #34, 2f106b57), so its commits are not ancestors of main
cf: { spec: CF-SPEC-20, tasks: [CF-207, CF-208, CF-209, CF-210, CF-211, CF-212, CF-213, CF-214, CF-215, CF-216, CF-217, CF-218] }
phase: "Whole plan — shipped"
stage: S5-ship
status: done
blocked_on: null
last: { agent: claude-opus-5-5, at: 2026-09-24T03:39:14Z, ledger: L-1 }
next_action: "Done. CF-SPEC-20 accepted; residual: F-007 accepted-risk stands, Docker/QA + Playwright matrices deferred."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### S0 Frame (owner-approved, DEC-1)
**Problem.** Istara has 24 menus plus auth-adjacent systems (files, backups,
invites, websockets, integrations, loops, autoresearch, compute relay). The
owner wants proof — not belief — that every one works for real users, tracked
so multiple agents can divide the work without collisions.

**Outcome.** A coverage matrix where every surface carries a dated verdict
(verified + evidence, or open findings with severity), all on the QA stack
(`istara-qa-live-20260902`, project `proj-st150-pi-dd6bf277`).

**Method per surface (non-negotiable).** Render + console-error + network-failure
triple; exercise mutations (create/edit/delete where safe — never golden data);
loading/error/empty states; keyboard Tab + visible focus; role scoping
(admin/researcher/viewer); light/dark + 375px reflow for UI surfaces.
Findings get IDs and severity; fixes happen in **separate scoped work orders**,
never inside the audit (separation of duties).

**Non-goals.** No redesigns, no new features, no merges, no destructive ops
(`down -v`, resets, volume deletion, model cleanup, golden-data mutation).

### Standing verification commands
- 24-view sweep: `docker exec nifty_dirac node /work/tests/simulation/test_phase9_broad_24view_sweep.mjs`
  (expects 24/24 render, 0 netFails; known benign: one `/v1/models` 404)
- Auth UI proof: `docker exec nifty_dirac node /work/tests/simulation/probe_auth_hardening_ui.mjs`
  (expects 11/11, 0 errors)
- Auth uniformity: `docker exec nifty_dirac node /work/tests/simulation/probe_auth_uniformity.mjs`
  (expects uniform 401s, exit 0)
- Backend slices: `pytest -q tests/test_auth_security.py tests/test_webauthn.py tests/test_backup.py tests/test_settings.py tests/test_connections.py tests/test_websocket.py`
- Benchmark: `python scripts/security_benchmark.py --fail-on-threshold` (expects 28/28 pass)

## Phase 1 — DONE ledger (verified with evidence)
| Surface | Verdict | Evidence |
|---|---|---|
| 24 menus render/keyboard/reflow/dark | ✅ 24/24, 0 netFails | phase9 sweep 2026-09-07 + re-run this session |
| Auth transport (cookie-first, memory token) | ✅ 11/11 UI proof, 0 errors | probe_auth_hardening_ui (form login, no persisted token, cookie, chat send) |
| Auth uniformity (revoked/garbage × 14 surfaces) | ✅ uniform 401s | probe_auth_uniformity |
| WS MFA parity (`/ws` 4001, relay JWT path) | ✅ unit-tested (stale→4001, fresh→connected) | `test_websocket_rejects_pre_mfa_session_after_enrollment` |
| Idle timeout (8h default) | ✅ unit-tested (backdated → 401 everywhere) | `test_idle_session_revoked_after_inactivity_window` |
| MFA step-up + claim + atomic counters | ✅ 34/34 auth file | `test_auth_security.py` full file |
| Passkeys (cap, purge, enumeration, flag hygiene) | ✅ webauthn file green | `test_webauthn.py` |
| Encryption at rest (fail-closed, rotation, backups) | ✅ field/file/backup/settings green | `test_field/file_encryption.py`, `test_backup.py`, `test_settings.py` |
| Invites breach parity | ✅ explicit rejection test | `test_invite_redeem_rejects_breached_password` |
| Memory persistence (9292/9292 across recreate) | ✅ API + UI screenshot | memory-reindex plan L-003 |
| Chat sends (Pi + legacy paths) | ✅ API + UI echo proofs | errno2 plan L-002; UI proof this session |
| Security benchmark | ✅ 28/28, 100% | scorecard runs this session |

## Phase 2 — OPEN surface queue (for contributors; claim one row at a time)
| # | Surface | Focus | How to verify |
|---|---|---|---|
| 1 | WS exemption handlers | each WS endpoint authenticates independently — prove it | targeted handshake tests (accept/deny matrix) |
| 2 | File serve/download authz | who can fetch what; quarantine files servable? | API matrix as viewer/researcher/admin + stranger |
| 3 | Backup restore/verify round-trip | post-rotation re-encryption restores correctly | rotate → backup → restore on scratch project |
| 4 | Invite lifecycle | expiry, double-redeem, type-confusion, weak passwords | API matrix (extends existing tests) |
| 5 | Interfaces (Figma/Stitch) | config, import, extract, error states | UI sweep + API checks |
| 6 | Loops scheduler execution | schedules fire, pause/play/delete/trigger honest | UI + API + history tab |
| 7 | Channel inbound flows | telegram/whatsapp inbound → findings, zero external traffic | scenario tests + UI |
| 8 | Autoresearch runners | start/stop, budgets, fail-closed on no compute | UI (no live models) + unit |
| 9 | Compute relay + donation | node register, scopes, token rotation blast radius | API matrix + UI |
| 10 | 7 baseline failures | 4 scope-contract texts, 2 pi display-order, 1 repo-quality path | fix-or-justify each with evidence |
| 11 | Residual minors | PBKDF2 salt, /tmp staging, email hash, Keychain argv | one scoped work order each |
| 12 | Mobile nav + per-role menus | researcher/viewer see exactly their menus, nothing more | Playwright role matrix |

**Contributor protocol.** `claim-next-task` (or append your name to a row) →
`work-order` + `gate before` → verify with the standing commands → findings with
IDs → `gate after` + `task evidence` → `finish-task` → append ledger entry
below. Never fix inside the audit; open a scoped work order per Blocker/Major.

## Phase 2 — Execution log (rows claimed)

### Row 1 — WS exemption handlers (claimed 2026-09-08, pi-audit, CF-207)
**Scope.** Middleware `SecurityAuthMiddleware` skips `upgrade: websocket`
(`backend/app/core/security_middleware.py:160-170`); each WS endpoint must
authenticate independently. Grep proves exactly 2 WS routes:
`@router.websocket("/ws")` (`backend/app/api/websocket.py:397`) and
`@router.websocket("/ws/relay")` (`backend/app/api/routes/compute.py:188`,
re-exposed as `/ws/relay` in `backend/app/main.py:797`).

**Method.** Static handshake audit of both handlers + existing unit suites
(no live servers started per repo policy; Docker daemon unavailable so QA
`docker exec` probes recorded as not-runnable this run).

**Verdict: PARTIAL — code enforces auth on both paths, handshake matrix
under-tested (2 findings below, fixes live in separate work orders).**

| Check | /ws | /ws/relay | Evidence |
|---|---|---|---|
| no token → 4001 | ✅ code (`websocket.py:465`) | ✅ code (`compute.py:~262`) | static + suite |
| invalid token → 4001 | ✅ code (`:438`) | ✅ code (`:262`) | static |
| revoked session → 4001 | ✅ code (`:441-446`) | ✅ code (payload nulled) | static |
| pre-MFA stale → 4001, fresh → connected | ✅ tested | ✅ code (`:237-250`) | `test_websocket_rejects_pre_mfa_session_after_enrollment` |
| project denied → 4003 | ✅ code (`:462`) | N/A (scope-via-connection-string) | static |
| explicit no-token/invalid/revoked handshake test | ❌ gap (F-001) | ❌ gap (F-002) | no `websocket_connect` test |

**Verification run (2026-09-08, branch `testing`):**
- `pytest tests/test_websocket.py -q` → **16 passed**
- `pytest tests/test_websocket.py tests/test_auth_security.py -q` → **51 passed**
- `pytest tests/test_connections.py -q` → **13 passed**
  (connection-string/relay scope logic; no WS handshake test)
- `python scripts/security_benchmark.py --fail-on-threshold` → **28/28 pass, 100%**
- `gate after --task CF-207` → **new_issue_count 0, new_failures 0** (status fail =
  24 inherited `python_import_cycles`, 0 new)
- QA `docker exec` sweeps → **not runnable** (docker daemon down,
  `dial unix .../docker.sock: no such file`); no servers started per policy.

**Findings register (audit; fixes in separate scoped work orders, never here):**
| ID | Sev | Where | Finding | CF task | Status |
|----|-----|-------|---------|---------|--------|
| F-001 | Major | `tests/test_websocket.py` vs `backend/app/api/websocket.py:421-465` | Only one handshake test (`/ws` pre-MFA stale/fresh). No explicit `websocket_connect` test for no-token→4001, invalid-token→4001, revoked-session→4001, project-denied→4003. | CF-214 | fixed |
| F-002 | Major | `tests/test_connections.py` vs `backend/app/api/routes/compute.py:188-262` | Zero handshake tests for `/ws/relay` accept/deny matrix (network-token vs JWT vs none; stale-MFA vs fresh). Relay auth proven by code read + connection-string unit tests only. | CF-214 | fixed |
| F-003 | Major | `backend/app/api/routes/files.py:858-881` (`serve_file`), `:775-831` (`get_file_content`) vs `:103-134` quarantine | Quarantined uploads (`DocumentStatus.QUARANTINED`) remain servable: neither serve path checks doc status. Upload quarantine proven (`test_upload_quarantines_*`); serve-denial unproven and code permits it. Fix lives in separate work order. | CF-214 | fixed |
| F-004 | Minor | `backend/app/api/routes/files.py` role matrix | No dedicated stranger/cross-project `serve`/`content` deny test at file-route level; authz relies on shared `get_visible_project_or_404` (viewer-read / researcher-mutate correct by code read). Recommend explicit matrix test. | CF-214 | fixed |
| F-005 | Minor | `tests/test_project_scope_contracts.py` (4 tests) | Brittle source-text assertions (exact code literals, e.g. `source_ids: Optional[list[str]] = None`) drifted from implementation; properties themselves hold (loops/scheduler scope enforced + tested in `test_loops.py`). Repair literals after verifying each property. | CF-214 | fixed |
| F-006 | Major | `tests/test_pi_replacement_candidate.py` (2 display-order tests) vs `chat.py:_generate_native_tools` | Tool-result display (`**name**: RESULT`) missing from persisted transcript (`parts` = pre-tool text + final only). Suspect the de-dup fix removed the direct append while the queued content-event drain never fires on this path — i.e. duplication fixed into deletion. Investigate `_tool_exec`/drain, fix-or-justify with evidence. | CF-214 | fixed |
| F-007 | Minor | `AGENTS.md:127` vs `scripts/public_repo_quality_audit.py:74` | Absolute checkout path (`<REPO_ROOT>`) inside the compass-forge managed block trips `machine_checkout_path`. Managed block required for CF target resolution — justify as accepted-risk (export pipeline should strip), do NOT hand-edit managed block. | accepted-risk | accepted-risk |
| F-008 | Minor | `frontend/src/lib/navigation.ts` role matrix | Central `filterNavItemsForRole` + `mobilePrimaryItemsForRole` unit-tested (`navigation.test.ts` 2/2) and backend enforces per-route; Playwright researcher/viewer menu-matrix not runnable here (no browser/QA). Recommend extending unit matrix for mobile per-role sets. | CF-214 | fixed |

### Row 2 — File serve/download authz (claimed 2026-09-08, pi-audit, CF-208)
**Scope.** `backend/app/api/routes/files.py`: `GET /files/{pid}/serve/{fn}`
+ `GET /files/{pid}/content/{fn}` (viewer+), `GET /files/{pid}` (viewer+),
mutations (`upload` researcher, `reprocess`/`scan` researcher).

**Verdict: PARTIAL — authz + traversal + scoping enforced; quarantined
files servable (F-003), route-level deny matrix unproven (F-004).**

| Check | Result | Evidence |
|---|---|---|
| viewer/researcher/admin read own-project | ✅ code (`_get_project min_role=viewer` on list/content/serve) | static |
| mutations require researcher | ✅ code (upload `:226`, reprocess `:696`, scan `:840`) | static |
| stranger / cross-project denied | ✅ by construction (project-scoped doc query + `get_visible_project_or_404`; no route-level deny test — F-004) | static |
| path traversal blocked | ✅ (`_safe_filename` rejects dirs; `_path_within_roots` containment) | static |
| quarantine files NOT servable | ❌ (F-003 — both serve paths ignore `DocumentStatus.QUARANTINED`) | static + test gap |

**Verification run:** `pytest tests/test_files.py` → **10 passed**;
`pytest tests/test_documents.py + test_file_encryption + test_channel_file_security`
→ **27 passed**; `security_benchmark` → **28/28 pass**;
`gate after CF-208` → **new_issues 0, new_failures 0**.
Docker QA probes not runnable (daemon down; no servers started per policy).

- **DEC-2 | 2026-09-08 | S2-execute | owner** — Context: owner ordered full
  completion: audit all remaining rows, then fix everything in one pass, then
  blind review. Decision: Rows 3–12 audited under CF-209; all open findings
  (F-001…F-n) fixed in a single scoped pass under CF-214/215 (code+tests only,
  no redesigns); blind reviewer measures independently before ship. Why: one
  fixing pass minimizes gate churn; blind review preserves independence.
  Alternatives rejected: per-finding work orders (12x gate overhead for
  test-only gaps sharing one pattern).

### Rows 3–12 — batch audit (2026-09-08, pi-audit, CF-209)
Method per row: route-handler auth read + existing unit suites (no live
servers started; Docker/QA probes and live-external flows recorded as
not-runnable with reason). Index `graph_usable: true` throughout.

| Row | Surface | Verdict | Evidence |
|---|---|---|---|
| 3 | Backup restore/verify | ✅ | admin-only on all 10 routes (`backup.py`); tar-slip-safe extract (`_safe_extract_tar`: traversal/link/device reject + `filter=data`); `pytest test_backup.py` **11/11**; benchmark 28/28. Restore-on-scratch not runnable here (no spare stack) — round-trip covered by existing backup tests. |
| 4 | Invite lifecycle | ✅ | expiry (`_connection_expired`: inactive/redeemed/expired), single-use (`is_redeemed` set both modes), type-confusion (`user_invite` vs donation reject), breach parity (`is_password_breached`), redeem rate-limit; double-redeem tested (`first/second_redeemer`); `test_connections.py` **13/13**. |
| 5 | Interfaces (Figma/Stitch) | ✅ | project-scoped + researcher-gated (`require_project_access min researcher` on import/configure); `test_interfaces.py` in 51-batch green. Live Figma import not runnable (no creds/external) — unit + code-read only. |
| 6 | Loops scheduler | ✅ | `project_id` required + `require_project_access` (viewer reads, researcher mutations); pause/resume/config scoped; `test_loops.py` in 51-batch green. |
| 7 | Channel inbound | ✅ | WA HMAC verify + replay reject, TG secret-token, simulate-inbound requires `project_admin`; `test_channel_inbound` **5/5**, channels+resilience+compute **82/82**. Live inbound excluded by zero-external-traffic policy. |
| 8 | Autoresearch runners | ✅* | project scope enforced, fail-closed 503s on runtime failure, start/stop/config tested (`test_autoresearch.py` in 51-batch). *Budget knob: no `budget`/`max_cost` string in route/runners — verify in fix pass whether budgets live elsewhere; Minor gap if absent. |
| 9 | Compute relay + donation | ✅ | relay WS auth (Row 1) + connection-string scopes + rotation-invalidates (`test_network_token_rotation…`); `test_connections` **13/13**, compute batch green. |
| 10 | 7 baseline failures | PARTIAL | all 7 reproduced identical to auth-milestone baseline: 4 scope-text (F-005), 2 pi display-order (F-006), 1 repo-quality (F-007). |
| 11 | Residual minors | MIXED | PBKDF2: **already remediated** (random 16B salt, 260K iter, constant-time compare, Argon2id auto-upgrade — no static salt in code) → close. Keychain: secret is subprocess **stdout**, only service name in argv → downgrade to Nit/close. /tmp: `TemporaryDirectory` auto-cleanup → accepted-risk Minor, no change. Unsalted email hash: deterministic by design for lookup → accepted-risk Minor, no change. |
| 12 | Mobile nav + per-role | ✅* | central `filterNavItemsForRole`/`mobile*ForRole` + backend per-route gates; `navigation.test.ts` **2/2**. *Playwright role matrix not runnable → F-008. |

**Batch verification totals:** backup 11/11 · channel_inbound 5/5 ·
autoresearch+loops+interfaces 51/51 · channels+resilience+compute 82/82 ·
scope-contracts 32/36 (4 known) · pi_replacement 20/22 (2 known) ·
repo-quality 0/1 (1 known) · navigation 2/2 · benchmark 28/28 ·
`gate after CF-209` new 0/0 (see L-008).

### Fix pass (single pass per DEC-2; CF-214)
| Finding | Fix | Files | Verification |
|---|---|---|---|
| F-003 | deny `QUARANTINED` with 403 on both serve paths | `backend/app/api/routes/files.py` (+2 checks) | new `test_quarantined_files_are_not_servable`; `test_files.py` 12/12 |
| F-001 | `/ws` handshake tests (missing/invalid→4001, nonmember project→4003) | `tests/test_websocket.py` (+3) | `test_websocket.py` 19/19 |
| F-002 | `/ws/relay` handshake tests (none→4001, network-token→accept) | `tests/test_websocket.py` (+1) | 19/19 |
| F-004 | stranger→404 / anonymous→401 serve matrix | `tests/test_files.py` (+1) | 12/12 |
| F-006 | **real bug:** restore queued `content` display event in both `_tool_exec` copies (`_generate_native_tools`, `_generate_text_fallback`) — W2 merge dropped the `queue.put(content)` the bridge drain design requires | `backend/app/api/routes/chat.py` (+8) | `test_pi_replacement_candidate.py` 22/22 (was 20) |
| F-005 | repaired 6 drifted literals after verifying each property holds (single-line calls, `X \| None` syntax, refined Done-gate advisory — gate behavior intact) | `tests/test_project_scope_contracts.py` | scope contracts 36/36 (was 32) |
| F-008 | mobile per-role matrix unit tests (partition, admin-only, researcher sets) | `frontend/src/lib/navigation.test.ts` (+3) | vitest 5/5 (was 2) |
| F-007 | accepted-risk, no change (managed block; export-pipeline concern) | — | documented |
| Row 11 | PBKDF2 verified remediated (random salt/260K/constant-time/Argon2id upgrade); keychain downgraded (secret=stdout, not argv); /tmp + email-hash accepted-risk | — | code-read, no change |
| Row 8 | budgets confirmed present (`ConfigUpdate`: max_experiments/run/day, min_delta, repeats) | — | code-read, no change |
Regressions: chat+auth+backup+connections+documents 94/94 · integration-chat+channelfile+fileenc+documents 29/29 · benchmark **28/28** · ruff: 0 new (15 pre-existing identical on HEAD) · `gate after CF-214` new 0 new-failures (3 inherited complexity flags, L-011).

### Blind reconciliation (S3; sheet frozen 2026-09-08T00:28:12Z)
| # | Claim | Sheet | Result |
|---|---|---|---|
| M-1…M-5 | 12 / 19 / 36 / 22 / 17 | 12 / 19 / 36 / 22 / 17 | agree |
| M-6 | benchmark 28/28 | 28/28 100% | agree |
| M-7 | guards both serve paths | lines 785 + 870 | agree |
| M-8 | display puts ×2 copies, no direct append | 664/665 + 805/806, none | agree |
| M-9 | 5 new tests pass isolated | 5 x 1 passed | agree |
| M-10 | ruff 0 new | same 15 as HEAD class | agree |
| M-11 | diff-check clean | CLEAN | agree |
| M-12 | literals resolve | agree* | agree* |
| M-13 | refutations hold (403s, 4001) | both pass | agree |
*M-12 tooling note: reviewer's `grep` without `-F` treated `[]`/`|` as regex
so one pattern matched nothing; re-verified directly (service 136/211,
deployments 143, channels 111, TaskEditor 432). No finding.
**Reviewer verdict: zero material divergences → no second fixing round.**
F-007 accepted-risk + deferred live matrices (Docker/QA, Playwright,
restore-on-scratch) stand as documented residuals.

## Summary (whole plan)
Outcome vs S0: every surface carries a dated verdict — Rows 1–2 PARTIAL→fixed,
Rows 3–9 PASS, Row 10 PARTIAL→fixed except F-007 accepted-risk, Row 11 mixed
(2 closed, 2 accepted-risk), Row 12 PASS. 8 findings: 7 fixed+tested, 1 accepted-risk.
Headline: F-006 was a real transcript bug (tool displays deleted, not duped) — fixed.
Residual risk: inherited chat.py complexity debt (no suppression); live-stack
matrices still unproven here. Retro: recipe-step task titles misdescribe audit rows
— future audits should mint row-named tasks. CF-SPEC-20 accepted (14/14 tasks,
17 command + 37 total evidence).

## Decision log
- **DEC-1 | 2026-09-08 | S0 | owner** — Context: owner ordered full Istara
  coverage with contributor-friendly tracking. Decision: this audit file is the
  single map; fixes live elsewhere. Why: keeps the audit honest (an auditor
  grading their own fixes is the classic failure mode) and lets agents divide
  rows safely via the append-only ledger.

## Append-Only Ledger
- **L-001 | 2026-09-08 | S0-frame/S1-plan | opencode | —**
  Did: CF-SPEC-20 created, clarified, planned, tasked (CF-207…CF-218); wrote
  this file with Phase 1 done-ledger and Phase 2 open queue.
  Result: coverage map exists; 0 app-code files touched.
  Verified: `spec tasks CF-SPEC-20` lists CF-207…CF-218 open; `git diff --check` clean.
  Next: close both plans with evidence rows and final report.
- **L-002 | 2026-09-08 | S1-plan | opencode | —**
  Did: re-ran the standing verification battery on the rebuilt QA stack after
  the WS-MFA + idle work: phase9 sweep 24/24, uniformity matrix uniform,
  auth UI proof 11/11, websocket file 16/16 — all green, results above.
  Result: Phase 1 verdicts re-confirmed post-change; no regressions observed.
  Verified: exact commands in Standing verification; outputs match expectations.
- **L-003 | 2026-09-08 | S2-execute | pi-audit | Phase 2-Row 1**
  Did: claimed CF-207, ran work-order + gate before; refreshed index
  (graph_usable true); ran impact/why/test-impact on websocket.py
  (resolved/partial/medium, repo_index, 30 must-inspect); audited both WS
  handlers + middleware exemption; ran pytest websocket 16/16, websocket+auth
  51/51, connections 13/13, security_benchmark 28/28; gate after 0 new drift.
  Result: Row 1 PARTIAL — auth enforced on both WS paths; F-001/F-002 opened
  (handshake matrix under-tested); 0 app-code files touched.
  Verified: exact commands above; `gate after --task CF-207` new_failures 0.
  Next: record CF evidence + finish CF-207; contributor claims Row 2.
- **L-004 | 2026-09-08 | S2-execute | pi-audit | Phase 2-Row 1**
  Did: wrote Row 1 execution log + findings F-001/F-002 into this file;
  updated Status Block.
  Result: plan file carries dated Row 1 verdict with evidence; CF-207 ready
  to finish.
  Verified: `git diff --check` clean (this file only + CF state).
  Next: contributor claims Phase 2 Row 2 (file serve/download authz).
- **L-005 | 2026-09-08 | S2-execute | pi-audit | Phase 2-Row 2**
  Did: claimed CF-208, work-order + gate before; refreshed index (usable);
  impact on files.py (complete/high/repo_index); audited serve/content/list/
  upload/reprocess/scan role gates, traversal + scoping, quarantine status
  handling; ran test_files 10/10, documents+file_encryption+channel_file
  27/27, benchmark 28/28; gate after 0 new drift.
  Result: Row 2 PARTIAL — F-003 (quarantine servable, Major), F-004
  (route-level deny matrix gap, Minor); 0 app-code files touched.
  Verified: commands above; `gate after --task CF-208` new_failures 0.
  Next: record CF evidence + finish CF-208.
- **L-006 | 2026-09-08 | S2-execute | pi-audit | Phase 2-Row 2**
  Did: wrote Row 2 execution log + F-003/F-004 into this file; updated
  Status Block (Row 3 next).
  Result: plan carries dated Row 2 verdict with evidence.
  Verified: `git diff --check` clean (this file only + CF state).
  Next: contributor claims Phase 2 Row 3 (backup restore/verify).
- **L-007 | 2026-09-08 | S2-execute | pi-audit | fix-auth**
  Did: owner authorized single fixing pass (DEC-2); claimed CF-209
  (implement), work-order + gate before recorded; index refreshed
  (graph_usable true). Starting Rows 3–12 audit batch.
  Result: fixing pass governed; audit batch open.
  Verified: `gate before --task CF-209` ok; `index status` usable.
  Next: audit Rows 3–12, record findings F-005+.
- **L-008 | 2026-09-08 | S2-execute | pi-audit | Phase 2-Rows 3-12**
  Did: audited Rows 3–12 (route auth reads + suites: backup 11/11, inbound
  5/5, auto+loops+iface 51/51, channels 82/82, scope 32/36, pi-repl 20/22,
  repoq 0/1, nav 2/2, bench 28/28); wrote Rows 3–12 log + F-005…F-008.
  Result: 4 ✅, 4 ✅-with-note, 1 PARTIAL (Row 10), Row 11 mixed (2 closed,
  2 accepted-risk); 0 app-code touched. Gate after CF-209 new 0/0.
  Verified: commands in Rows 3–12 log; CF-209 evidence + finished.
  Next: single fixing pass under CF-214 (DEC-2).
- **L-009 | 2026-09-08 | S2-execute | pi-audit | fix-pass**
  Did: fixed F-001/F-002 (4 WS handshake tests), F-003 (quarantine 403 ×2
  paths + test), F-004 (stranger/anon matrix + test), F-005 (6 literals
  repaired post-verify), F-006 (real bug: queued content display in both
  _tool_exec copies), F-008 (3 nav matrix tests); F-007 accepted-risk;
  Row 11/Row 8 closed by verification. Ran regressions 94/94 + 29/29 +
  bench 28/28; ruff 0 new; gate after CF-214 new 0/0.
  Result: all fixable findings fixed in one pass; 6 files touched (2 code,
  4 test).
  Verified: exact suites in Fix-pass table; `git diff --check` clean.
  Next: blind review, then spec accept.
- **L-010 | 2026-09-08 | S3-review | pi-audit | blind-pack**
  Did: wrote blind review pack (open questions, no claimed results) beside
  this file; spawned reviewer process; froze measurement sheet before
  opening implementation evidence.
  Result: independent measurement recorded; see reconciliation below.
  Verified: sheet file + reviewer log.
  Next: reconcile divergences; remediate if needed; spec accept.
- **L-011 | 2026-09-08 | S2-execute | pi-audit | gate-debt**
  Did: inspected CF-214 gate-after (new_issues 3, new_failures 0): all 3 are
  chat.py complexity flags (file 1760>1200 lines; `chat` 49, `generate` 33).
  Verified inherited: file was 1752 lines at HEAD (already over); my 8 added
  lines are branch-free (2 comments + f-string assign + queue.put ×2 sites,
  diff-verified); flagged functions untouched by my hunks; ruff 15 identical
  on HEAD. No suppression written (would weaken gate for future chat.py work).
  Attached debt note as CF-214 evidence. Also disclosed: worktree carries
  others' uncommitted changes (e.g. `_chat_log.exception` hunks in chat.py,
  101 files) — not mine, not touched.
  Result: process slip owned (finished CF-214 before reading gate detail);
  debt recorded, gate honestly red on inherited grounds.
  Verified: `git diff` hunk audit above; ruff HEAD comparison.
  Next: blind review.
- **L-012 | 2026-09-08 | S5-ship | pi-audit | done**
  Did: reconciled blind sheet (13/13 agree, 1 tooling note re-verified,
  zero divergences → no second round); finished CF-210/211/212/213/215/216/
  217/218/219/220 with command evidence; `spec accept CF-SPEC-20` (no force).
  Result: spec accepted; plan Status Block done with summary + retro.
  Verified: accept payload (14 tasks, 17 command evidence); sheet FROZEN.
  Next: none — residuals documented (F-007, live matrices).

### L-1 | 2026-09-24T03:39:14Z | S5-ship | claude-opus-5-5 | executor | —
Did: record correction found by Ainulindalë's truth reconciler. Its work reached main through the squash merge of testing (PR #34, 2f106b57); the block named `testing`, whose commits a squash leaves off main's history.
Result: the Status Block says what is true today.
Verified: `git merge-base --is-ancestor 2f106b57 origin/main` (the squash of testing); `git diff --stat 2f106b57 9620e5d8` empty; `compass-forge spec show` for each named spec.
Next: as the block says.
