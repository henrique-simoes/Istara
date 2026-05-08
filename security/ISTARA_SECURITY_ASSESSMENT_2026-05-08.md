# Istara Security Assessment - 2026-05-08

## Scope

This was an authorized defensive assessment of Istara's current codebase, focused on public-release readiness for:

- Authentication, account lifecycle, sessions, cookies, WebAuthn, and local/team-mode boundaries.
- Authorization, project roles, admin surfaces, and researcher access.
- Public and semi-public ingress: connection strings, A2A JSON-RPC, webhooks, MCP, uploads, and UI login paths.
- Agentic/LLM risk surfaces: prompt injection, tool delegation, A2A messages, memories, RAG, model/provider routing, and audit evidence.
- Data and release integrity: secrets, logs, installer dependencies, security benchmark coverage, and Compass Forge gates.

The test method stayed local and non-destructive: source review, safe ASGI requests against the in-process app, targeted regression tests, and security benchmark execution. No third-party targets were touched.

## External References Checked

- [OWASP Web Security Testing Guide - latest](https://owasp.org/www-project-web-security-testing-guide/latest/)
- [OWASP ASVS releases](https://github.com/OWASP/ASVS/releases)
- [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [Better Auth security reference](https://better-auth.com/docs/reference/security)
- [Better Auth options reference](https://better-auth.com/docs/reference/options)
- [Better Auth cookies reference](https://better-auth.com/docs/concepts/cookies)
- [W3C WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)

## Confirmed Findings And Fixes

### 1. Public Registration Stayed Open After Bootstrap

Risk: `/api/auth/register` was public in team mode and allowed anyone who could reach the server to create a researcher account after the first admin existed. That did not match Istara's intended model: first-admin bootstrap, then admin-created users or invite/connection-string onboarding.

Fix:

- `backend/app/api/routes/auth.py` now permits public registration only when there are no users.
- The first public registration creates the initial admin account.
- `team-status.registration_enabled` now returns true only while first-admin bootstrap is still available.
- `frontend/src/components/auth/LoginScreen.tsx` and `frontend/src/app/login/page.tsx` hide/guard public registration once users exist.
- Regression tests prove first bootstrap succeeds and post-bootstrap public registration returns 403.

### 2. A2A JSON-RPC Bypassed API Middleware

Risk: `/a2a` intentionally lives outside `/api`, and global middleware exempted non-API paths. That left `tasks/send` able to persist A2A messages and broadcast events without team authentication.

Fix:

- `backend/app/main.py` now performs route-level A2A authorization.
- Team mode requires a valid bearer token or trusted cookie session with at least researcher role.
- Local mode preserves local-first semantics while respecting the existing remote-local-admin and network-token guards.
- JSON-RPC body size, message text, metadata, and agent id lengths are bounded.
- Persisted A2A task metadata now records the submitting user id and username.
- Regression tests prove unauthenticated writes fail, authenticated researcher writes succeed, and oversized bodies are rejected before persistence.

### 3. Uploads Read Full Files Into Memory

Risk: `/api/files/upload/{project_id}` read the whole upload body before writing it, which made large uploads a memory pressure path and left no direct hard cap at the API boundary.

Fix:

- `backend/app/config.py` now defines `upload_max_bytes` with a default 100 MB cap.
- `backend/app/api/routes/files.py` streams uploads in chunks and returns HTTP 413 once the cap is exceeded.
- Partial files are deleted on rejection.
- Existing extension allowlist, project authorization, and path-containment behavior remain in place.
- Regression tests prove oversized uploads fail closed without leaving partial artifacts.

## Controls Confirmed During Review

- Global API authentication middleware protects non-public `/api` routes in team mode and attaches local admin only in local desktop mode.
- Browser origin checks reject untrusted login/register and cookie-authenticated mutation attempts.
- Session cookies are HttpOnly and governed centrally.
- JWTs are validated, bound sessions are revocable, and deleted/role-changed users are resolved through database authority for bound sessions.
- WebAuthn uses persisted, single-use, expiring challenge state and validates RP/origin/user ownership.
- Recovery codes are table-backed, one-time, auditable records.
- Connection strings remain scoped and audited.
- Markdown rendering does not enable raw HTML rendering for user content.
- Sensitive log redaction is installed during app startup.
- Security benchmark and release-readiness gates are tracked under `security/`.

## Benchmark And Test Evidence

Commands run successfully:

- `python -m py_compile backend/app/api/routes/auth.py backend/app/api/routes/files.py backend/app/main.py backend/app/core/security_middleware.py`
- `pytest tests/test_auth_security.py::test_public_registration_bootstraps_first_admin_and_closes tests/test_auth_security.py::test_public_registration_rejects_post_bootstrap_accounts tests/test_a2a_security.py tests/test_files.py::test_upload_rejects_oversized_file_without_partial_artifact -q`
- `pytest tests/test_auth_security.py tests/test_a2a_security.py tests/test_files.py tests/test_network_security.py tests/test_connections.py tests/test_mcp.py tests/test_content_guard.py tests/test_security_benchmark.py -q`
- `pytest tests/test_webauthn.py tests/test_webhooks_security.py tests/test_channel_file_security.py tests/test_proxy_security.py tests/test_updates_security.py tests/test_log_redaction.py tests/test_security_release_readiness.py tests/test_transport_headers.py tests/test_project_rbac.py -q`
- `npm run lint` in `frontend/`
- `npx tsc --noEmit` in `frontend/`
- `python scripts/security_benchmark.py --fail-on-threshold`
- `python scripts/security_benchmark.py --fail-on-threshold` with changed security paths supplied
- `python scripts/security_release_readiness.py --json`

Results:

- Focused new regression slice: 6 passed.
- Broader auth/security slice: 94 passed.
- Secondary security breadth slice: 54 passed.
- Frontend lint: pass.
- Frontend typecheck: pass.
- Security benchmark: 27 applicable controls, 27 pass, 100.0 percent, no blocked controls.
- Release readiness: pass, no issues.

## Security Benchmark Updates

`security/control_matrix.json` now includes controls for:

- `AUTH-008`: public registration limited to first-admin bootstrap.
- `API-002`: streamed file uploads with hard size and path controls.
- `AI-004`: authenticated and bounded A2A JSON-RPC mutation.

The security-sensitive changed-path list now includes `backend/app/main.py`, file upload routes, A2A tests, frontend login surfaces, and file upload tests so future benchmark runs detect this class of change.

## Residual Risks And Recommended Next Hardening

1. Add per-client rate limiting for `/a2a` JSON-RPC, especially `tasks/send`.
2. Consider requiring auth for `/.well-known/agent.json` in team deployments if agent capability disclosure becomes sensitive.
3. Add optional content scanning or CDR for uploaded PDF/DOCX/media files before they enter extraction, preview, RAG, or vector pipelines.
4. Add prompt-injection regression cases that prove uploaded documents cannot override tool, memory, MCP, or A2A authorization policy.
5. Add production CSP/HSTS validation for the deployed frontend host, not only API transport headers.
6. Run an independent external penetration test before broad public launch.
7. Keep running the agentic/RAG/memory eval baseline whenever prompt-RAG, LLMLingua, ReasoningBank, Memento skills, A2A, or meta-hyperagent routing changes.

## Follow-Up Release Hardening Implemented

The next release-hardening pass converted the internal residual items into tracked controls:

- `/a2a` now has per-client and `tasks/send`-specific rate limits, replay rejection, audit events, and authenticated team-mode agent-card disclosure by default.
- Uploaded artifacts now pass deterministic file-signature checks, optional scanner hooks, and prompt-injection quarantine before text enters vector or keyword RAG indexes.
- Webhook ingress now rejects exact replay of already accepted WhatsApp and Google Chat payloads inside the configured replay window.
- Production security headers are centralized and validated as a contract, and public/team deployments have an explicit auth-origin/RP/JWT audit helper.
- User-configured LLM and MCP endpoints reject embedded credentials, sensitive query strings, metadata/link-local targets, and public plaintext HTTP URLs.
- MCP tool descriptors discovered from external servers are bounded and prompt-sanitized before caching.
- ReasoningBank memories mark prompt-injection-like content and wrap retrieved memory context as untrusted data.
- Backups exclude secret-like files, private keys, `LLMs/`, and `Model_Finetuning/` from copied directories while retaining checksum validation and safe extraction.

## Verdict

The reviewed surfaces are materially stronger after this pass. The highest-risk confirmed issues were patched with targeted regression tests and benchmark coverage. Based on the local evidence above, the security benchmark is at the release target with 100 percent internal control pass rate. Remaining items are release-hardening recommendations rather than known active blockers from this assessment.
