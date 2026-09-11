# Build Stream — Auth Hardening Milestone (no merge)

<!-- STATUS BLOCK -->
```yaml
item: auth-hardening-milestone
branch: testing
phase: "Phase 4 — Validation, port, QA proof (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: opencode, at: 2026-09-07T22:45:24Z, ledger: L-004 }
next_action: "Owner merge decision; residual list in L-003/L-004. No merge performed."
```
<!-- /STATUS BLOCK -->

## S0 Frame (DEC-1)
- Owner ordered the full hardening list done on `testing`, no merge yet.
- Safety rule (DEC-1): implement + full-test in isolated clone
  `/Users/user/Documents/Istara-auth-hardening` (testing HEAD + worktree
  synced); port to `Istara-main` only after green; QA/live proof after port.
- Scope: fail-closed field encryption; DATA_ENCRYPTION_KEY rotation +
  re-encryption; file rotation covers old backups; env rotation durable;
  RAG at-rest scope; MFA step-up + mfa-claim enforcement; bearer→cookie
  (pending CSRF review); JWT idle; hygiene batch (purge, caps, enumeration,
  TOTP atomicity, bootstrap race, invite strength, IP/UA minimization).
- Out: merge to main (explicitly deferred), unrelated behavior changes.

## Append-Only Ledger
- **L-001** (2026-09-07): Clone created from testing HEAD, worktree synced
  (83 dirty files mirror). Opening CF-SPEC-18, running baseline.
- **L-002** (2026-09-07): BASELINE recorded in clone (CF-SPEC-18 clarified/
  planned, CF-181 work-order + gate-before). First full run: 61 failed
  (missing pi-runtime node_modules — env gap, fixed with npm ci). Clean
  baseline bar: **7 failed / 2224 passed** — all 7 pre-existing
  (4 scope-contract source-text assertions, 2 pi_replacement display-order,
  1 public-repo-quality AGENTS.md checkout_path), unrelated to auth.
- **L-003** (2026-09-07T22:30:53Z): MILESTONE COMPLETE in clone, ported to
  testing, live on QA. CF-181 gate-after 0 new, evidence 961, finished.
  Encryption: fail-closed `encrypt_field` (raises, versioned ENC:kid: rows,
  legacy decrypt, previous-keys rotation endpoint + test, backup re-encrypt
  on file rotation + test, env-key durability fix, honest RAG-scope UI copy).
  Auth: MFA step-up on all factor changes + atomic counter claim + global
  claim enforcement (middleware + route helper + /me) with 2 new tests;
  cookie-primary transport (tokenStore memory-only, credentials:include
  everywhere, 4 tokenStore tests); 8h idle revocation. Hygiene: challenge
  purge, 10-key cap, enumeration unification + test, invite breach parity +
  test, bootstrap race guard, masked IP previews in UI. Verified: clone full
  suite **2233 passed, same 7 baseline failures, 0 regressions**; testing
  worktree 116 targeted + 84 frontend green; benchmark 28/28; QA rebuilt
  (backend+ui), memory 9292/9292 intact; Playwright UI proof **11/11**
  (UI-form login, no persisted token, session cookie, chat send, encryption
  card + scope copy, sessions + masked IP, dark parity, keyboard focus,
  0 console/5xx errors) with light/dark screenshots reviewed. No volumes
  touched, no merges. Residuals: WS exemption handlers unaudited;
  per-project crypto keys (documented design); PBKDF2 static salt fallback;
  Keychain-via-CLI argv; /tmp staging on crash; unsalted email hash —
  all Minor/Nit, catalogued for follow-up.
- **L-004** (2026-09-07T22:45:24Z): WHOLE-STACK LIVE VERIFICATION on rebuilt QA
  (CF-181 gate-after 0 new, evidence 963). Owner's split-brain concern
  investigated directly: found WS handlers enforced revocation/idle but NOT
  the MFA claim → fixed both `/ws` (4001 close) and `/ws/relay` (JWT path
  invalidated) with a live-handshake WS test (stale→4001, fresh→connected).
  Verified: 24/24 views render, 0 netFails, keyboard+reflow+dark hold (1 known
  benign /v1/models 404; laws-dark marker flake re-proven benign); revoked
  and garbage sessions return uniform 401 on all 14 API surfaces (me, sessions,
  projects, tasks, memory, chat-catalog, metrics, audit×2, files, backups,
  webauthn, notifications); UI proof 11/11 (form login, no persisted token,
  session cookie, chat send, encryption card + scope copy, sessions + masked
  IP, keyboard focus, 0 errors); memory 9292/9292 + files/backups/webauthn
  reads live; idle-timeout unit test green. New tests this lane: WS MFA,
  idle-timeout. Fixed along the way: `select`/`_select` alias slips in both
  WS files (caught by the new tests, not by existing suite).
