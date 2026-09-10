# Owner-gated `main` branch protection — prepared request package (M-07/D.10)

**Status: PREPARED, NOT APPLIED.** No agent may mutate GitHub repository
settings. This package is the single deliverable the repository owner applies
by hand, in one sequenced action, after the redesigned CI has been observed
green on GitHub.

## Source of truth

- Required contexts: `testing/required-checks.json` → `required_contexts`
  (contract-checked in CI by `scripts/check_required_checks.py` — the manifest
  and the workflow cannot drift).
- Settings: `testing/required-checks.json` → `branch_protection_settings`.

## The exact apply command

Run from a checkout with `gh` authenticated as the repository owner:

```bash
gh api --method PUT "repos/<OWNER>/<REPO>/branches/main/protection" \
  --input docs/promotion/branch-protection/gh-api-body.json
```

`gh-api-body.json` (committed beside this README) is rendered verbatim from
the manifest. If the manifest has changed since this package was prepared,
re-render the body from the manifest instead of trusting this file.

## Sequencing (load-bearing — read before applying)

1. **Observe the new graph first.** Push this change to `testing` and confirm
   on GitHub that every context in the manifest ran at least once, including
   `ui-journeys` (container-first browser lane) and `release-gate`.
2. **One action.** Old and new context names are disjoint (`backend` →
   `backend-format`/`backend-lint`/`backend-test`/`backend-mutation`; `frontend`
   → five contexts; `qa-contract-stack` → `qa-contract-render`). Applying the
   new context set and removing old ones in the same PUT avoids a window
   where `main` requires a context that no longer exists (unmergeable) or
   nothing at all (unprotected).
3. **M-18 decided (2026-09-10): `desktop-check` is REQUIRED.** The owner chose
   in-scope-and-blocking, so the manifest, the `release-gate` needs list,
   and this body all list `desktop-check`. Do not apply an older copy of this
   package that omits it.
4. **`strict: true` is retained** (already true today — the one bright spot
   in the current settings).

## Required verification after applying (attach to the promotion dossier)

1. **API read-back** (tokens redacted):

   ```bash
   gh api "repos/<OWNER>/<REPO>/branches/main/protection" \
     | jq '{required_status_checks, enforce_admins, required_pull_request_reviews, restrictions, required_linear_history, allow_force_pushes}'
   ```

   Expect: the exact manifest context list, `enforce_admins.enabled: true`,
   `required_pull_request_reviews` ≥ 1 with code-owner review and
   dismiss-stale, `required_linear_history.enabled: true`,
   `allow_force_pushes.enabled: false`.

2. **Negative mergeability test**: open a PR to `main` that fails one required
   context; the PR must be un-mergeable while that check is red.

3. **Badge-sync coexistence check**: after a release-affecting merge to
   `main`, `.github/workflows/badge-sync.yml` may push a `[skip ci]` badge
   commit. It is a normal push (no force), so linear history and admin
   enforcement tolerate it; confirm it still succeeds and only touches
   `README.md`/`README.pt-BR.md`.

## What this package deliberately does NOT do

- It does not weaken or remove any existing check (the old `governance`
  context remains required — it is in the new manifest too).
- It does not grant any workflow new write scopes (CI is read-only; badge
  sync is the only generated write path, narrowed to `main`).
- It does not auto-merge, auto-promote, or bypass the human gate in
  `promote-testing.yml`.
