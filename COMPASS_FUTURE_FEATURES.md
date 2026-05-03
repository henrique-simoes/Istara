# Compass Future Features Ledger

Status: living Compass ledger for deferred product, architecture, observability, and security work.

Purpose: this file tracks future plans and feature ideas that are important enough to preserve, but not yet ready for `current_plans.md` execution. Use it when a session discovers a real product gap, deferred hardening task, observability need, or design direction that future work must take into account.

## Rules

- Keep entries concrete and actionable.
- Do not use this file as a substitute for `current_plans.md` when implementation is already underway.
- Promote an item into `current_plans.md` when the user asks to plan or implement it.
- When implementing an item, update or remove its ledger entry and note the shipped behavior in `CHANGELOG.md`.
- Include security, privacy, data model, frontend, testing, and Compass documentation implications when known.
- Prefer honest unknowns over fake certainty.

## Entry Template

```markdown
### Feature: Short Name
Status: candidate | planned | in-progress | shipped | superseded
Priority: P0 | P1 | P2 | P3
Owner surface: backend | frontend | desktop | docs | cross-system
Source: user request, review finding, production issue, research insight

Problem:
- What gap exists?

Expected behavior:
- What should be true when complete?

Architecture notes:
- Models/routes/frontend/stores/services likely affected.

Security/privacy notes:
- Roles, data exposure, audit, retention, or threat-model impact.

Testing/docs:
- Tests and Compass docs that must change.

Open questions:
- Decisions needed before execution.
```

---

## Future Feature Candidates

### Feature: Durable Token, Model, And Compute Donation Accounting
Status: candidate
Priority: P1
Owner surface: cross-system
Source: admin/researcher/viewer RBAC completion, 2026-05-02

Problem:
- The Admin Dashboard currently labels token/model accounting as `not_collected_yet` and compute donation metrics as `partial_runtime_only`.
- Existing `AuditLogMiddleware` and telemetry spans provide general durable audit and operational telemetry, but they do not yet provide complete per-user/per-project/per-agent token cost attribution or durable compute donation session accounting.

Expected behavior:
- Admins can see durable usage metrics by user, project, agent, skill, model, provider, and time range.
- Admins can see compute donation sessions with donor identity, node id, models advertised/used, session start/end, uptime, request counts, token counts when available, failures, and health history.
- Missing provider data is represented as unknown/not collected, not zero.
- Metrics can be exported for billing, governance, capacity planning, and research operations review.

Architecture notes:
- Likely needs new models such as `UsageEvent`, `ModelUsageAggregate`, `ComputeDonationSession`, or equivalent.
- LLM router, relay, compute registry, skill execution, chat/design chat, task execution, and autoresearch should emit structured usage events.
- Admin Dashboard should gain filters for user/project/agent/model/time range.
- Existing telemetry spans should be reused where possible instead of duplicated.

Security/privacy notes:
- Usage data can reveal sensitive research activity patterns. Admin-only access by default.
- Avoid storing prompt/content unless explicitly needed; prefer counts, ids, timing, model, and route metadata.
- Project-scoped summaries may be visible to project admins only if product policy allows it.
- Retention policy and export behavior should be explicit.

Testing/docs:
- Backend tests for event creation, aggregation, admin-only access, and absent-data semantics.
- Frontend tests or simulation for Admin Dashboard usage filters and empty states.
- Update `docs/TEAM_RBAC_PERMISSION_MATRIX.md`, `docs/features/system-overview.md`, `Tech.md`, and this ledger.

Open questions:
- Should token cost use configurable provider pricing tables, local-only estimated cost, or token counts only?
- Should compute donors see their own contribution history, or only admins?
- What retention period should apply to detailed usage events?

### Feature: Provider Webhook Verification Audit
Status: candidate
Priority: P2
Owner surface: backend
Source: final RBAC route inventory, 2026-05-02

Problem:
- Webhook endpoints are intentionally public for external providers, but each provider path should be reviewed against its provider-specific verification model.

Expected behavior:
- WhatsApp and Google Chat webhook receivers verify provider signatures/tokens where supported.
- Verification failures are auditable and rate-limited.
- Public webhook exemptions are documented as intentional, not accidental.

Architecture notes:
- Inspect `backend/app/api/routes/webhooks.py`, channel adapters, secret storage, and integration setup UI.

Security/privacy notes:
- Webhooks can ingest external messages into project/channel flows. Verification and replay protection matter.

Testing/docs:
- Add route tests for valid/invalid verification.
- Update integration docs and security guidance.

Open questions:
- Which provider verification secrets are configured today, and where should rotation live?
