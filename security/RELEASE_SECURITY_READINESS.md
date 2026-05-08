# Release Security Readiness

Last reviewed: 2026-05-08

This document records the release-hardening checks that sit around Istara's code-level security benchmark. It maps the current implementation to official guidance and keeps the public-release process repeatable.

Use this with `SECURITY.md`, `security/SECURITY_BENCHMARK.md`,
`security/ISTARA_SECURITY_ASSESSMENT_2026-05-08.md`, and
`testing/TEST_HISTORY.md`. Raw scorecards and local runtime findings stay
gitignored; release-relevant summaries belong in the tracked history.

## Official References Checked

| Area | Reference | Istara release expectation |
|---|---|---|
| Auth framework baseline | Better Auth options and security docs | Explicit base URL/trusted origins, secure cookie policy, session revocation, rate limits, secret rotation readiness, and trusted proxy care remain mirrored in Istara's Python auth controls. |
| Application security | OWASP ASVS 5.0.0 | Auth, session, access control, logging, file upload, API, and configuration controls stay mapped in `security/control_matrix.json`. |
| Identity assurance | NIST SP 800-63-4 and SP 800-63B-4 | Team deployments target AAL2-style controls, with passkey/WebAuthn support as the phishing-resistant path where available. |
| Passkeys | W3C WebAuthn Level 3 | RP ID and origin validation, challenge replay prevention, credential ownership, and revocation stay covered by tests. |
| Logging | OWASP Logging Cheat Sheet | Logs must exclude or mask session identifiers, access tokens, passwords, connection strings, API keys, and database connection strings. |
| Supply chain | GitHub Artifact Attestations and OpenSSF Scorecard | Installer builds generate provenance attestations and the repository posture is checked by Scorecard. |

## Required Release Gates

Every release candidate must pass:

1. `python scripts/check_integrity.py`
2. `python scripts/check_ci_governance.py`
3. `python scripts/check_test_harness.py`
4. `python scripts/security_release_readiness.py`
5. `python scripts/security_benchmark.py --fail-on-threshold`
6. `python scripts/production_rehearsal.py --json`

The production security benchmark threshold is 98 percent. Partial controls are not allowed for release readiness unless a future matrix version explicitly marks them as waived with evidence and owner approval.

## Auth And Session Review Checklist

- Trusted origins and cookie settings are centralized and tested.
- Public/release profiles must pass the production auth audit: team mode on, strong JWT secret, exact HTTPS browser origins, production WebAuthn RP ID, and no CORS regex.
- Production responses must pass the backend security-header contract for CSP, HSTS, frame denial, nosniff, referrer policy, and restrictive browser permissions.
- Local mode rejects remote password login unless a valid connection string is redeemed.
- WebAuthn/passkey registration and assertion verification validate origin/RP expectations.
- TOTP and recovery-code lifecycle changes are audited.
- Session revocation and active-session views remain available to users.
- Startup secrets, generated admin credentials, API keys, tokens, credentials, connection strings, and private URLs are not printed to logs.

Better Auth is not the runtime library for Istara, but its official guidance is used as a comparison point for base URL, trusted origin, secure cookie, session, rate-limit, IP-header, and secret-rotation practices.

## LLM Serving And Compute Review Checklist

- Startup registers only the configured local provider and optional configured fallback; it must not autoload multiple heavy models.
- Live test profiles use a gitignored endpoint and a single fixed model id.
- User-added LLM provider URLs must not contain embedded credentials, sensitive query strings, metadata-service targets, or public plaintext HTTP endpoints.
- Compute donation connection strings are one-time, signed, and do not embed reusable login tokens.
- Resource reporting is tested through backend and frontend contracts.
- Provider and model-selection changes run compute registry, LLM server, and test harness governance checks.

## Agentic And Integration Ingress Checklist

- A2A JSON-RPC mutation requires auth, actor traceability, body/metadata caps, per-client rate limits, replay rejection, and audit events.
- Team-mode agent-card discovery requires authenticated researcher access unless explicitly disabled for a deployment.
- Webhook ingress must verify platform signatures or shared tokens and reject exact replay within the configured replay window.
- MCP client URLs must pass the same endpoint-safety policy as LLM servers, and cached MCP tool descriptors must be bounded and prompt-sanitized.
- RAG and ReasoningBank context must remain wrapped as untrusted data before model prompts or agent planners consume it.

## Data Integrity And Packaging Checklist

- Runtime data, vector indexes, local databases, uploaded files, logs, eval results, `LLMs/`, and `Model_Finetuning/` must stay out of public commits and installer source bundles.
- Invalid documents and orphaned vector/index directories are reported or quarantined through admin-visible flows, not silently deleted.
- Uploaded files are streamed, signature-checked, optionally scanner-checked, and quarantined before RAG ingestion when prompt-injection or scanner signals are present.
- Backups redact `.env` values and exclude secret-like files, private keys, `LLMs/`, and `Model_Finetuning/` when copying user-controlled directories.
- Clean installs create runtime folders only at runtime.
- Release packaging excludes backend `.env`, local data, virtual environments, build caches, node modules, and simulation/eval outputs.

## Operational Security

Istara has a tracked vulnerability-disclosure and incident-response policy in `SECURITY.md`. External penetration testing, FIDO certification, and third-party compliance review are still recommended before enterprise-scale deployment, but the internal release gate now has concrete evidence for supply-chain posture, security-test rehearsal, and operational readiness.
