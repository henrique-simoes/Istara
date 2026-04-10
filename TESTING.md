# Testing Queue

Changes that are on `staging` and awaiting review before merging to `main`.

## Awaiting Review (on staging)

| PR | Change | Added | Notes |
|---|---|---|---|
| - | - | - | - |

## Verified & Ready for `main`

| PR | Change | Reviewed | Notes |
|---|---|---|---|
| - | - | - | - |

---

### How to Use This File

1. **Push to staging** → Add an entry under "Awaiting Review"
2. **Test locally** → Check out `staging`, run `./istara.sh start`, verify the change works
3. **Mark verified** → Move the entry to "Verified & Ready for `main`"
4. **Merge to main** → PR from staging → main, clear the verified entries

### How to Test Staging Locally

```bash
git checkout staging && git pull origin staging
./istara.sh start   # or docker compose up for containerized testing
```

### What to Test

- **API changes**: `curl` the endpoints, check responses
- **UI changes**: Open http://localhost:3000, navigate the affected views
- **Auth changes**: Login, logout, token refresh, 2FA flow
- **E2E tests**: `ISTARA_ADMIN_USER=<user> ISTARA_ADMIN_PASSWORD=<pass> python tests/e2e_test.py`
- **Unit tests**: `pytest tests/`
- **Simulation scenarios**: `ADMIN_USERNAME=<user> ADMIN_PASSWORD=<pass> node tests/simulation/run.mjs --skip-skills`
