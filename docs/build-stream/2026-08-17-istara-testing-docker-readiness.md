# Build Stream — Istara testing branch Docker readiness

<!-- STATUS BLOCK -->
```yaml
item: istara-testing-docker-readiness
branch: testing
cf: { spec: CF-SPEC-53, decisions: [20], tasks: [CF-651, CF-652, CF-653, CF-654, CF-655, CF-656, CF-657, CF-658, CF-659, CF-660, CF-661, CF-662, CF-663, CF-664] }
phase: "Phase 1 — readiness assessment and public CI/testing reframe"
stage: S1-plan
status: in-progress
blocked_on: "Owner approval, a new implementation spec, provider/runtime validation, and missing CI enforcement"
last: { agent: pi, at: 2026-08-18T00:03:55Z, ledger: L-3 }
next_action: "Create and approve the public provider-agnostic CI/testing implementation contract; do not launch Conductor implementation or mutate multivac yet."
```
<!-- /STATUS BLOCK -->

## Plan overview (roadmap)

**Problem/outcome.** The `testing` branch contains a large production-parity feature surface, but its current Docker/testing processes are not yet a reliable full-feature test environment. The goal is a disposable, resettable, LAN-reachable test deployment on `multivac` that can exercise Istara normally without contaminating production state, while identifying and fixing branch/process defects that block startup, health, UI access, or QA.

**Scope.** Compare `testing` with `origin/main`; inspect the test and Docker process contracts; establish an API-authenticated three-architect MECE investigation; make one explicitly configured, authenticated remote/API provider for chat and embeddings the canonical QA dependency; implement only the scoped testing Compose, health, seed/reset, test-harness, and documentation changes justified by evidence; validate locally and then on `multivac`; run broad deterministic QA and explicitly bounded live UI/feature checks.

**Non-goals.** No production deployment mutation, public internet exposure, real-user data, committed credentials, silent model downloads, or changes to `LLMs/` / `Model_Finetuning/`. The existing dirty `docs/features/site/manifest.json` change predates this initiative and must remain isolated.

**Appetite.** One focused delivery cycle with an investigation barrier before implementation; prefer a testing-only overlay and reversible scripts over changing the production compose contract.

**Known initial evidence.**

- The current branch is `testing` at `faaadee2`; it tracks `origin/testing`; the worktree already has an unrelated modification to `docs/features/site/manifest.json`.
- `docker-compose.yml` exists on both `testing` and `origin/main` with identical content. `tests/real_user_benchmark/docker-compose.benchmark.yml` exists only on `testing` and is the current testing-oriented overlay.
- With local Docker Compose v5.3.1, the base compose fails `docker compose config --quiet` because services combining `pids_limit` and `deploy.resources.limits.memory` are rejected with a `pids_limit`/`deploy.resources.limits.pids` conflict. The benchmark overlay validates because it supplies matching deploy PID limits for backend/frontend.
- The current benchmark overlay is not yet a full-feature deployment contract: relay, team/PostgreSQL, Caddy, observability, MCP, and autoresearch paths are not all enabled; defaults include hard-coded test credentials; browser URLs/CORS/WebAuthn are localhost-oriented; persistent named volumes are not ephemeral unless explicitly removed; and its Ollama/LM Studio defaults conflict with the corrected remote-provider requirement.

**Top risks.** Compose version drift; missing or misconfigured remote chat/embedding endpoint; accidental fallback to local-provider assumptions; vector-space/model identity mismatch; browser origin and port mismatch for LAN access; persistent volume/data leakage; branch-only test harness assumptions; full feature toggles silently off; API/OAuth auth mismatch in conductor workers; Docker published ports bypassing host firewall policy.

**Documentation impact.** Update `TESTING.md`, the appropriate `testing/` strategy/history material, and a testing deployment/how-to living document. If behavioral test/route/model contracts change, regenerate feature docs with `python scripts/feature_docs.py --seed-missing --generate-site --check` and run the feature-doc tests.

| Phase | Goal (one line) | Acceptance / verify | Status |
|-------|-----------------|---------------------|--------|
| 0 | Frame the request and capture the CF execution contract | `compass-forge spec plan CF-SPEC-53` | done |
| 1 | Find branch/process/Docker blockers and select a MECE remediation plan | Conductor architect drafts, synthesis, and cross-vote; owner approval required | in-progress |
| 2 | Implement the approved testing overlay, health/seed/reset process, and docs | `docker compose config --quiet`; focused tests; gates | planned |
| 3 | Build and run the disposable stack locally without loading unapproved heavy models | Rendered Compose, image build, health checks, reset/seed proof | planned |
| 4 | Deploy the testing branch on `multivac` with private-LAN/SSH-tunnel access | Server inventory, stack health, listener/firewall contract, browser/API QA | planned |
| 5 | Graduate durable facts and close the plan | CF evidence, independent review pass, security benchmark where triggered | planned |

## Decision log        <!-- append-only · spans ALL phases -->

DEC-1 | 2026-08-17 | S0 | owner
Context: The testing branch has failing processes and needs a production-like but disposable Docker environment for broad UI and QA work.
Decision: Investigate the branch against main, use a three-architect MECE conductor plan, implement the approved testing path, and deploy only after the stack is verified.
Why: This preserves independent architectural coverage before changing a security- and deployment-sensitive surface; a testing overlay is safer than mutating production behavior.

DEC-2 | 2026-08-17 | S1 | pi
Context: The repository's base compose and the existing benchmark overlay have different validation behavior, and the remote test stack already exposes a failed startup.
Decision: Treat current runtime findings as blockers to diagnose and preserve as evidence; do not restart, remove, or repair the existing remote stack until the approved implementation plan defines the exact reversible change.
Why: Server operations are outward-facing and the existing stack may be owner-managed. Read-only inventory preserves rollback and prevents accidental data/model mutation.

DEC-3 | 2026-08-17 | owner-corrected | pi
Context: The earlier investigation treated an empty Ollama deployment as the model bootstrap blocker, but the corrected requirement is that Ollama and every local LM server are optional.
Decision: Make one explicitly configured, authenticated remote/API provider path for both chat and embeddings the canonical testing contract. Preserve exact model identity, dimension checks, `assert_vector_space_invariant`, and fail-closed behavior; do not probe, load, or mutate a provider without explicit approval.
Why: The testing environment should not require local model storage or a local inference daemon, while Research Spine validity still requires a real, source-grounded embedding path rather than a disabled or synthetic substitute.

## Ledger              <!-- append-only · spans ALL phases -->

### L-1 | 2026-08-17T16:48:41Z | S1-plan | pi | planner | Phase 1
Did: Oriented Compass Forge, refreshed the repository/index, created and clarified CF-SPEC-53, generated its task graph, inspected branch/Compose/Docker/test contracts, and inventoried `multivac` without mutating it.
Result: Confirmed a testing branch with a branch-only benchmark Compose overlay, a base Compose validation conflict, and an existing remote stack blocked by empty Ollama models and the backend vector-space invariant. No implementation or remote mutation performed.
Verified: `compass-forge status`; `compass-forge next`; `compass-forge agent-brief --compact`; `compass-forge refresh`; `compass-forge index refresh`; `compass-forge spec clarify CF-SPEC-53`; `compass-forge spec plan CF-SPEC-53`; `compass-forge spec tasks CF-SPEC-53`; `docker compose -f docker-compose.yml config --quiet` (fails with PID/deploy conflict); overlay config validation (passes); read-only `ssh multivac` inventory (reachable; no config changes).
Next: Generate the API-only three-architect conductor pipeline and run the investigation plan; stop at the conductor's owner-approval barrier before implementation.

### L-2 | 2026-08-17T18:02:05Z | S1-plan | pi | planner | Corrected requirement and planning reset
Did: Reconciled the investigation with the owner-corrected requirement that Ollama and all local LM servers are optional. Recorded Compass Forge decision 19, preserved the old remote zero-model startup as read-only diagnostic evidence, and stopped the stale synthesis workers before any implementation or provider mutation.
Result: The next MECE plan must treat one explicitly configured, authenticated remote/API provider for both chat and embeddings as canonical; local endpoints must not be a readiness prerequisite. Exact model identity, embedding dimensions, and `assert_vector_space_invariant` remain mandatory, and no provider calls or model loading are authorized by this correction alone.
Verified: `compass-forge decision record --title "Testing QA uses remote/API model and embedding providers" ...`; `compass-forge intelligence impact --path docs/build-stream/2026-08-17-istara-testing-docker-readiness.md ...`; `compass-forge intelligence why docs/build-stream/2026-08-17-istara-testing-docker-readiness.md`; read-only inspection of `backend/app/config.py`, `backend/app/main.py`, `backend/app/core/pi_runtime/model_manager.py`, `backend/app/core/pi_runtime/embeddings_gateway.py`, `docker-compose.yml`, and `tests/real_user_benchmark/docker-compose.benchmark.yml`; no code or remote changes.
Next: Generate a fresh API-only three-architect conductor pipeline with the corrected provider contract, then stop at its owner-approval barrier.

## Phase 1 — broad investigation and MECE plan

**Frame/Plan:** Three independent architect lanes will cover: (A) branch delta, test process, and feature/subfeature coverage; (B) Docker/Compose lifecycle, health, networking, persistence, and `multivac` operations without making a local model daemon a prerequisite; (C) ephemeral data, Research Spine validity, seeded UX/QA workflows, auth/origin boundaries, remote/API chat-and-embedding provider contract, and conductor API-auth feasibility. Synthesis must produce one MECE master plan with exact verification commands, rollback, and a feature-to-process coverage matrix. Implementation remains gated until the owner approves the winning plan.

**Execution:** Pending conductor planning dispatch.

### Review (Phase 1)

**Findings register**

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| P1-F-1 | Blocker | Integration | `docker-compose.yml` services with `pids_limit` plus deploy memory limits | Base Compose does not validate under the installed Compose v5.3.1 contract; the testing overlay currently masks this with deploy PID limits. | pending | open |
| P1-F-2 | Blocker | Bugs | `multivac` `istara-testing` backend startup | Backend fails vector-space invariant startup because the deployment has no configured remote/API embedding path; the old Ollama path has zero models and is not a valid prerequisite under the corrected requirement; frontend remains Created behind the backend health dependency. | pending | open |
| P1-F-3 | Major | Security | benchmark overlay environment/origins/ports | Defaults are localhost-oriented and contain test credentials; remote/LAN browser access and secret/data lifecycle are not yet a governed contract. | pending | open |
| P1-F-4 | Major | Coverage | `tests/real_user_benchmark/docker-compose.benchmark.yml` | Existing overlay does not provide a complete full-feature testing profile or an explicit ephemeral reset/seed lifecycle for all required services. | pending | open |

**Remediation:** Findings remain open until the conductor plan and implementation create scoped CF tasks and independently verified fixes.

**Phase summary:** Initial investigation has converted the vague failing-test/process concern into concrete Compose, model-process, access-boundary, and feature-coverage questions. The remote stack is intentionally left untouched pending the approved plan.

## Summary (S5 — whole plan)

Pending. The current branch/process is not ready to claim a reusable full-feature Docker QA primitive.

## Current readiness assessment and public CI/testing objective

Recorded 2026-08-18 after the initial readiness investigation.

### Not-ready status

- The `testing` branch at `faaadee2` does not track the candidate testing overlay, testing environment template, Docker reset/seed scripts, or their contract tests. Those remain in the unmerged Conductor worktree.
- The candidate process is documented and has useful static contracts, but no current CI obligation detects when a new feature requires a Compose, provider, seed, or live QA update.
- CI currently targets `main` and `staging`; it has no dedicated testing-overlay render/build/runtime job, no disposable-stack reset/reseed job, and no executable feature-to-Docker coverage matrix.
- The existing feature matrix is planning/documentation evidence, not an enforced registry. Snapshot counts and manual checklists can drift as features evolve.
- Provider readiness and runtime QA remain unproven. Existing read-only `multivac` evidence shows zero local models and a backend startup failure at the fail-closed vector-space invariant. No invariant bypass, synthetic vector, silent model load, or provider mutation is permitted.
- The candidate overlay retains follow-up risks: a liveness-only Ollama healthcheck can pass with zero usable models, and the external-provider path may still depend on the Ollama service. These require approved contract work, not safety-gate weakening.

### Reframed objective

Create a professional, public, provider-agnostic testing branch and CI system that every Istara developer can use. A changed feature must automatically trigger the appropriate deterministic contracts, feature-coverage obligations, Docker render/build checks, and—when explicitly authorized—runtime QA against a disposable synthetic environment. The shared contract must preserve the Research Spine, exact source-span evidence, model/embedding identity and dimension validation, `assert_vector_space_invariant`, fail-closed provider behavior, credential isolation, and resettable provisional-only data.

The official path must be host- and provider-agnostic. `multivac` is only an optional private deployment adapter for the owner's environment, using the same public artifact and contract; it is not the project's official testing or staging dependency. CI is pre-merge automation and evidence. Staging is a running integrated environment for acceptance. They must remain separate, and neither may require the owner's server.

### Preconditions before implementation

1. Owner approves the reframed objective and Conductor routing.
2. A new durable implementation spec defines the public branch, CI checks, Docker artifact contract, provider-neutral adapter boundary, feature-coverage registry, optional staging adapters, and acceptance evidence.
3. The implementation/review cycle converges through Conductor.
4. Local deterministic and authorized runtime validation passes before any `multivac` preparation.
5. `multivac` deployment remains opt-in, read-only-first, separately evidenced, and reversible.

### L-3 | 2026-08-18T00:03:55Z | S1-plan | pi | planner | Public CI/testing reframe

Did: Recorded the not-ready assessment and separated the official public testing path from the owner's private `multivac` deployment target. Distinguished CI (automated pre-merge checks and artifacts) from staging (a running integrated environment), and recorded Compass Forge decision 20.

Result: The future initiative is explicitly provider-agnostic and developer-usable. The current branch/process is not ready because the candidate overlay is unmerged, feature-to-Docker obligations are not enforced, CI lacks dedicated testing-stack automation, the feature matrix is not executable, and runtime/provider validation is incomplete.

Verified: `compass-forge status`; `compass-forge next`; `compass-forge agent-brief --compact`; `compass-forge refresh`; `compass-forge index refresh`; `compass-forge intelligence impact --path docs/build-stream/2026-08-17-istara-testing-docker-readiness.md`; `compass-forge intelligence why docs/build-stream/2026-08-17-istara-testing-docker-readiness.md`; read-only inspection of the branch, candidate worktree, CI workflows, change-obligation checks, testing docs, Compose overlay, and provider/runtime contracts; no implementation, Docker startup, provider request, or `multivac` mutation.

Next: Obtain owner approval, create the new implementation spec, then use Conductor for the public CI/testing delivery only.
