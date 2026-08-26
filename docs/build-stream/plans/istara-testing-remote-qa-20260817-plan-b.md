# Plan B - Remote/API Docker QA readiness for Istara testing branch

- **Task:** `ISTARA-TESTING-REMOTE-QA-20260817-PLAN-B`
- **Role:** `istara-testing-remote-qa-20260817-architect-b`
- **Spec:** `CF-SPEC-53`
- **Pipeline:** `ISTARA-TESTING-REMOTE-QA-20260817`
- **Lifecycle:** `docs/build-stream/2026-08-17-istara-testing-docker-readiness.md`
- **Branch/worktree:** `testing` in `<repo-root>`
- **Scope:** Docker/Compose topology, provider-less local service dependencies, health/readiness, networking/ports/CORS/WebSocket, persistence/ephemerality, security controls, and safe multivac rollback/access.

> **Working constraint.** The existing unrelated modification to `docs/features/site/manifest.json` must remain isolated. This plan does not touch it.

## 1. Outcome and invariants

The testing branch must support a disposable full-feature QA environment without making Ollama or any local LM server a prerequisite. The canonical QA path must use one explicitly configured, authenticated remote/API provider contract for chat and embeddings, must preserve exact model identity and embedding-dimension checks, and must fail closed if the provider, network, or vector-space contract is incomplete.

The plan keeps these invariants intact:

- local model servers remain optional;
- no silent model download or auto-load is introduced;
- `assert_vector_space_invariant` remains load-bearing;
- remote secrets are injected, not committed;
- LAN access is explicit, bounded, and auditable;
- QA data is disposable and resettable;
- unrelated dirty work stays untouched.

## 2. Current evidence

The current branch state shows the readiness gap clearly:

- `docker-compose.yml` still hard-wires `backend.depends_on.ollama`, sets `LLM_PROVIDER=${LLM_PROVIDER:-ollama}`, and mixes `pids_limit` with `deploy.resources.limits` in a way that fails under the installed Compose v5.3.1 contract.
- `tests/real_user_benchmark/docker-compose.benchmark.yml` is localhost-oriented, still defaults to local-provider assumptions, and is not a complete full-feature QA contract.
- `backend/app/config.py` still defaults the general runtime to `lmstudio`, while the compose files point to local hosts and local embedding models.
- `backend/app/core/pi_runtime/{endpoints.py,model_manager.py,embeddings_gateway.py}` already model explicit remote/API endpoints, exact model identity, secret resolution, and the vector-space invariant. That is the contract to build on.
- `tests/test_harness_config.py` and `tests/pi_production/test_w8_embeddings_gateway.py` confirm the current harness and gateway assumptions still lean on local-provider defaults and embedding anchors.
- `scripts/reset_test_environment.py` already provides a guarded destructive reset for local test state and explicitly protects `LLMs/` and `Model_Finetuning/`.

## 3. Working hypothesis

The smallest governed fix is a dedicated QA orchestration layer that:

- validates under the installed Compose version;
- removes any local-LM prerequisite from startup;
- injects one explicit authenticated remote/API provider for chat and embeddings;
- makes LAN reachability, CORS, WebSocket, and auth behavior explicit;
- isolates persistent state behind named volumes with a deterministic reset/seed path.

If the current code cannot safely express distinct chat and embedding identities for the chosen remote provider, that gap should be surfaced and fixed with the smallest governed schema/env change rather than hidden behind a local fallback.

## 4. Coverage matrix

| Problem / blocker | Planned response | Primary verifier |
|---|---|---|
| Compose v5.3.1 validation conflict in the root stack | Normalize the shared compose resource syntax, then validate the testing overlay against the same contract | `docker compose config --quiet` |
| Ollama / local LM prerequisite in QA | Replace the QA startup dependency with an explicit remote/API provider contract | Backend startup + provider tests |
| Localhost-only browser/origin assumptions | Parameterize LAN origins, WebSocket URL, CORS, WebAuthn, and auth headers | HTTP/browser probes |
| Persistent state and unsafe cleanup | Add a disposable reset/seed lifecycle with isolated volumes | Reset script and volume checks |
| Secret leakage risk | Use env-file, keychain, or Docker secret injection with redaction checks | Config/log inspection |
| Vector-space drift | Preserve exact model identity and `assert_vector_space_invariant` | W8 gateway and vector-health tests |

## 5. Design

### 5.1 Compose topology

Create or adjust a testing compose entrypoint that is separate from benchmark-only semantics and is intended to be the canonical QA stack for this investigation.

The overlay should:

- start only the services needed for the QA path;
- keep optional services behind explicit profiles;
- avoid any dependency on a local LM daemon to pass readiness;
- preserve a single known ingress path for frontend and backend;
- keep resource declarations Compose-valid under the installed version;
- make backend, frontend, and any supporting data services health-gated in a deterministic order.

Preferred service posture:

- backend and frontend are always present;
- postgres is present when team/shared state is required;
- relay, telemetry, MCP, and autoresearch are explicit opt-ins rather than hidden defaults;
- Caddy is only used if it is the chosen ingress boundary for the run, otherwise direct host ports are used with a tight firewall contract;
- no service should depend on `ollama` as a prerequisite for the QA environment.

### 5.2 Provider and secrets contract

Bind the QA stack to one explicit remote/API provider contract for chat and embeddings.

The implementation must:

- inject provider credentials from a gitignored env file, Docker secret, or keychain-backed environment;
- keep credentials out of compose files, logs, generated manifests, and docs;
- preserve exact model identity in the provider selection path;
- reject missing or mismatched endpoint identity rather than falling back silently;
- keep the remote provider OpenAI-compatible or another already-supported provider only if both chat and embedding contracts are explicit and proven.

If separate chat and embedding identities are not already expressible safely, the smallest governed change should add that expressiveness directly instead of reusing a local default.

### 5.3 Networking and access boundaries

Make LAN access explicit instead of accidental.

The QA contract should define:

- exact frontend and backend public origins;
- exact WebSocket URL;
- exact CORS origins;
- exact WebAuthn origins when the browser path is exercised;
- exact proxy trust boundaries when a reverse proxy is used;
- explicit bind host and published ports;
- an access-token or equivalent auth boundary for non-localhost access.

Verification must prove that the listener set matches the intended ingress contract and that the published ports are the only externally reachable sockets needed for the QA run.

### 5.4 Persistence and reset lifecycle

QA state must be disposable.

The plan is to:

- use isolated named volumes for backend data, uploads, project data, database state, and benchmark artifacts;
- keep the reset path deterministic and idempotent;
- seed a known demo/test identity set and synthetic project corpus without contaminating production state;
- preserve the protected local artifact folders;
- make the reset entrypoint explicit enough that a fresh run can be recreated from the same command set.

The existing `scripts/reset_test_environment.py` should be reused as the destructive local reset primitive where it already fits; any Docker-specific cleanup should be a thin wrapper around that contract, not a second bespoke deletion system.

### 5.5 Health and readiness

The QA stack should not report ready until the relevant health checks are satisfied.

At minimum:

- backend health must reflect application readiness, not just process uptime;
- vector health must still prove the embedding dimension contract;
- settings/status surfaces must reflect the remote/API provider state without probing unsafe local endpoints;
- frontend readiness must wait on backend readiness;
- optional services should fail independently without collapsing the whole stack unless they are part of the chosen canonical QA profile.

### 5.6 Multivac rollout and rollback

The multivac path must be treated as a separate operational surface.

Before any mutable action:

- take a read-only inventory of the current host and stack;
- confirm the exact compose file, env set, and published ports;
- confirm the firewall/listener contract on the host;
- confirm the rollback target and stop path.

Rollback should be a single operator action that restores the previous known-good compose state and removes only the ephemeral QA volumes created by this run.

## 6. Likely file targets

| File | Why it is in scope |
|---|---|
| `docker-compose.yml` | Root compose resource validation and shared service contract. |
| `docker-compose.testing.yml` or equivalent QA overlay | Canonical disposable QA entrypoint for this task. |
| `tests/real_user_benchmark/docker-compose.benchmark.yml` | Reference/orchestration parity; update only where needed, not to overload benchmark semantics. |
| `backend/app/config.py` | Remote/API provider, origin, secret, and runtime defaults. |
| `backend/app/core/pi_runtime/endpoints.py` | Secret resolution and identity-pinned endpoint binding. |
| `backend/app/core/pi_runtime/model_manager.py` | Exact chat/embed endpoint resolution and any minimal identity-gap fix. |
| `backend/app/core/pi_runtime/embeddings_gateway.py` | Embedding dispatch, model identity, and vector-space checks. |
| `backend/app/api/routes/settings.py` | Settings/admin surface for provider inventory, status, and redaction-safe endpoint management. |
| `scripts/reset_test_environment.py` or a thin wrapper | Disposable reset/seed behavior for QA state. |
| `README.md` | Updated run instructions if the canonical QA entrypoint changes. |
| `README.pt-BR.md` | Mirror the user-facing run instructions if the English README changes. |
| `TESTING.md` | Developer-facing verification matrix and live/QA command guidance. |
| `testing/TESTING_STRATEGY.md` | If the orchestration contract changes, keep the testing strategy aligned. |
| `testing/TEST_HISTORY.md` | Curated evidence only, if the change becomes release-relevant. |
| `tests/test_harness_config.py` | Harness contract coverage for the new QA entrypoint. |
| `tests/test_test_environment_reset.py` | Reset/seed contract coverage. |
| `tests/test_model_provider_contract.py` | Provider/auth contract coverage. |
| `tests/pi_production/test_w8_embeddings_gateway.py` | Exact embedding and vector-space behavior. |
| `tests/pi_production/test_engine_http_provider.py` | Remote HTTP provider stack behavior. |

## 7. Task breakdown

| ID | Task | Output |
|---|---|---|
| B1 | Capture the compose, provider, network, and reset baseline from the current branch and compare it to `origin/main`. | File-level impact map and selected fix surface. |
| B2 | Implement the QA compose overlay and normalize any shared compose syntax required for `docker compose config --quiet` to pass. | Validated compose entrypoint and health order. |
| B3 | Implement the remote/API provider injection path, secret redaction, and explicit LAN origin/auth boundaries. | Fail-closed provider bootstrap and redaction-safe config. |
| B4 | Implement or wire the disposable reset/seed lifecycle and volume isolation. | Repeatable QA reset and clean rollback path. |
| B5 | Add or update readiness checks and the minimal tests that prove the new contract. | Targeted unit/contract coverage. |
| B6 | Refresh docs and history artifacts only where the user-facing QA contract changed. | Updated README/TESTING docs and evidence notes. |
| B7 | Run verification, record command evidence, and attach the gate outputs. | Evidence-backed handoff package. |

## 8. Acceptance criteria

- The canonical QA compose entrypoint validates under the installed Compose version.
- The QA environment does not require Ollama or any other local LM server to start.
- One explicitly configured authenticated remote/API provider is used for chat and embeddings.
- Exact model identity and embedding dimension checks remain intact and fail closed.
- LAN access is explicit: origins, WebSocket, CORS, auth, and published ports match the intended contract.
- Secrets are injected, not committed, and are absent from generated config and logs.
- The environment can be reset to a known seeded state without contaminating non-QA data.
- Rollback returns the host to the previous known-good state and removes only ephemeral QA volumes.
- Any behavioral route/model/test contract change is reflected in the relevant docs and tests.

## 9. Verification plan

Run the narrowest commands that prove the changed surface, then widen only if the fix crosses a boundary.

```bash
# Compass Forge gate / evidence scaffolding
compass-forge gate before
compass-forge gate after

# Compose and orchestration
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.testing.yml config --quiet
docker compose -f docker-compose.testing.yml ps

# Contract tests
pytest tests/test_harness_config.py -q
pytest tests/test_test_environment_reset.py -q
pytest tests/test_model_provider_contract.py -q
pytest tests/pi_production/test_w8_embeddings_gateway.py -q
pytest tests/pi_production/test_engine_http_provider.py -q

# Security-sensitive surfaces, if auth/secret/network contracts change
python scripts/security_benchmark.py --fail-on-threshold
pytest tests/test_security_benchmark.py -q

# Docs, if route/model/test behavior changes
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q

# Live host proof on multivac, only after approval and with the chosen QA stack
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/settings/status
curl -fsS http://127.0.0.1:8000/settings/vector-health
ss -ltnp
```

If the testing overlay uses a different public host or port set, the verification commands must be updated to match the exact deployed contract.

## 10. Rollback

Rollback should be explicit and low-risk:

1. Stop the QA compose project.
2. Remove only the ephemeral QA volumes created by the run.
3. Restore the previous env file or secret source.
4. Revert the compose/docs/test changes in the worktree if the plan is not approved.
5. Leave unrelated user edits untouched, especially `docs/features/site/manifest.json`.

## 11. Risks

- Compose version drift could keep the root file and the QA overlay from validating the same way.
- A remote provider contract that cannot represent distinct chat and embedding identities would force a small schema/env change.
- LAN exposure can be accidentally widened if CORS, WebSocket, or firewall settings are not treated as a single contract.
- Secret redaction can fail in logs or generated config if the provider contract is not centralized.
- The current harness and benchmark helpers still assume local-provider defaults; those assumptions need to be removed only where the QA contract requires it.

## 12. Notes for the implementer

- Preserve the untouched dirty worktree file and do not use it as a proxy for this task.
- Keep the QA overlay disposable and reversible.
- Treat local LM services as optional support, not readiness prerequisites.
- If a minimal code change is needed to express separate chat and embedding identities safely, prefer that governed change over a local fallback or a synthetic-vector shortcut.
