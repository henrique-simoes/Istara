# Build Stream — Auth Surface Audit (Encryption/Passkeys/2FA) + Release Readiness

<!-- STATUS BLOCK -->
```yaml
item: auth-surface-audit-and-release-readiness
branch: testing
phase: "Phase 3 — Verdict (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: opencode, at: 2026-09-07T18:55:54Z, ledger: L-002 }
next_action: "Owner merge decision; pre-merge gates listed in L-002."
```
<!-- /STATUS BLOCK -->

## S0 Frame (DEC-1)
- Audit File & Backup Encryption, Passkeys/WebAuthn, TOTP + recovery codes
  against better-auth and platform conventions (WebAuthn/FIDO2 RP semantics,
  TOTP RFC 6238, recovery-code one-timeness), with multi-tenancy/teams,
  active sessions, and permission surfaces in scope.
- Objective is check-and-improve, NOT redesign: minimal fixes only for clear
  blockers; everything else reported with severity.
- Then assess testing→main release readiness across all recent plans.
- DEC-1 (owner): audit + readiness verdict, no behavior redesign.

## Append-Only Ledger
- **L-001** (2026-09-07): Opened. Fanning out 3 audit lenses + CF orient.
- **L-002** (2026-09-07T18:55:54Z): AUDIT CLOSED + READINESS VERDICT (CF-SPEC-17,
  CF-165 evidenced 958 + finished; gate after 0 new).
  3 independent lenses, skeptic-passed: 0 Blockers. Passkeys/WebAuthn clean
  (RP/origin exact, 120s single-use purpose-scoped challenges, sign-counter
  replay, ownership, UV, user-global credentials correct). TOTP/recovery/sessions
  solid at rest (160b secrets, Argon2id one-time codes, server-side revocation,
  invite HMAC, 404-conceal isolation). 11 Majors, all design-level, reported
  not changed per objective: fail-open field encryption, memory-only auto-key
  + false log, no rotation paths, rotation strands backups, env rotation not
  durable, unencrypted RAG derivatives, DB URL in backups, MFA rotation/step-up
  gaps, unenforced mfa claim, localStorage bearer.
  4 minimal fixes applied + tested: stale passkey_enabled cleared on last
  revoke; generic WebAuthn failure details (log keeps specifics); honest
  key-custody log via persist_env_value bool return; DATABASE_URL userinfo
  redaction. Verified: webauthn+backup 20, auth×5 files 51, benchmark 28/28
  100%, diff-check clean. Full 2227-suite end-to-end NOT run this session.
  READINESS: ~85% — merge gates: (1) commit hygiene for 82 dirty files in
  scoped commits + green CI, (2) full backend suite green, (3) owner manual QA
  pass, (4) majors accepted/scheduled. Residuals catalogued in report.
