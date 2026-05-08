# Security Policy

## Supported Versions

Istara security fixes target `main`, `staging`, and the latest published installer release. Older local source installs should update before reporting bugs unless the issue prevents updating.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately through GitHub private vulnerability reporting when it is available for the repository. If that channel is unavailable, open a minimal public issue that asks for a private security contact without including exploit details, secrets, access tokens, private URLs, screenshots of credentials, or user data.

Include the affected version, deployment mode, operating system, reproduction steps, and the minimum evidence needed to understand impact. Do not attach database dumps, logs with tokens, connection strings, passkeys, recovery codes, API keys, or private LLM server URLs.

## Handling Timeline

Istara treats authentication, authorization, WebAuthn/passkeys, recovery codes, connection strings, pooled compute, MCP/tool execution, webhooks, LLM-provider routing, autoresearch, self-evolution, agentic memory, and release packaging as high-risk surfaces.

The release owner should acknowledge a report within three business days, triage severity, create a private fix branch or local Compass Forge work order, run the tracked security benchmark, and publish a patched release when the fix is verified. Critical issues should receive a mitigation notice as soon as a safe workaround exists.

## Security Documentation

- `security/SECURITY_BENCHMARK.md` defines the release security control matrix, benchmark threshold, evidence rules, and standards mapping.
- `security/RELEASE_SECURITY_READINESS.md` is the release checklist for auth configuration, transport headers, endpoint validation, uploads, backups, MCP, LLM providers, webhooks, and log redaction.
- `security/ISTARA_SECURITY_ASSESSMENT_2026-05-08.md` is the current release-hardening assessment and follow-up backlog.
- `TESTING.md` and `testing/TEST_HISTORY.md` describe how security evidence is logged without committing raw scorecards, private URLs, secrets, or runtime data.

## Incident Response

For suspected exploitation:

1. Preserve logs and affected runtime data without exposing them in public issues.
2. Rotate exposed JWT, encryption, LLM-provider, webhook, connection-string, and relay secrets.
3. Revoke affected sessions, passkeys, recovery codes, and compute donation strings.
4. Run `python scripts/security_benchmark.py --fail-on-threshold` and `python scripts/security_release_readiness.py`.
5. Document scope, affected versions, remediation, and follow-up tests in the release notes or a private incident record.

Logs are treated as sensitive data. Istara should redact tokens, credentials, connection strings, and sensitive URL parameters before writing application or access logs.
