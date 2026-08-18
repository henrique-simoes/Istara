# ISTARA Public CI Testing Automation — Architect B Draft

## 1) Executive summary and outcomes
This plan defines a public, host-independent, provider-agnostic CI workflow for Istara where every code change is routed to declared obligations, deterministically tested, and optionally exercised with bounded authorized live provider checks before human promotion. The public CI path is usable by any developer with no dependency on private infrastructure, while private adapters (including `multivac`) are explicitly optional and quarantined to staging/experimental paths.

Outcome targets:
- Every feature/subfeature change must declare required tests and evidence prior to merge.
- CI artifacts (logs, manifests, image names, coverage, and obligations report) are reproducible and disposable.
- PR promotion to `main` is blocked until automated checks pass **and** owner-visible human approval is recorded.
- `multivac` never becomes a required dependency for public branch CI or official docs/workflows.

## 2) Goals, non-goals, assumptions, constraints

### Goals
- Define branch lifecycle and branch-protection rules for feature branches, a public testing branch, and `main`.
- Define an automatic coverage classifier and fail-closed policy for any changed behavior.
- Specify deterministic test automation order and evidence requirements, including provider-contract and safety gates.
- Define portable, reproducible, disposable Docker QA artifact workflow.
- Define strict boundaries for optional private adapters and non-public staging.
- Preserve the Research Spine and security invariants in every automated lane.

### Non-goals
- This stage does not implement code/workflow changes.
- This stage does not start runtime services, run real model providers, or provision multivac.
- This stage does not alter source behavior in `backend`, `frontend`, `relay`, `pi-runtime`, or production runtime state.

### Assumptions
- Workflow orchestration and registry scripts already in place can be extended (`scripts/check_change_obligations.py`, `scripts/check_public_tree_clean.py`, `scripts/check_ci_governance.py`, `scripts/public_repo_quality_audit.py`).
- Build Stream lifecycle documents in `docs/build-stream/` are authoritative entry points for implementation evidence.
- `CHANGE_CHECKLIST.md`/`README.md`/`TESTING.md` are contract docs that must be updated with same PR-facing process semantics.

### Constraints
- No PR creation, promotion, merge, Docker-run, model calls, or `multivac` mutation in this stage.
- Private artifact folders (`LLMs/`, `Model_Finetuning/`) are off-limits.
- Public CI must be provider-agnostic by default.

## 3) Current-state evidence and gaps
- `scripts/check_ci_governance.py` exists and can be run from repo root; baseline check passes in current state.
  - Command output observed: "CI/CD governance check passed."
- `scripts/check_public_tree_clean.py` exists and supports staged/base/head validation for public tree hygiene.
- `scripts/check_change_obligations.py` exists, requiring `--base` and `--head`, so it is directly usable as a change-classification gate.
- `scripts/public_repo_quality_audit.py --check` currently reports historical repository findings (`machine_checkout_path`, `ai_disclaimer`) across many docs/plan files and is therefore currently non-greedy for immediate green status.
- Lifecycle tracking is already defined in `docs/build-stream/2026-08-18-istara-public-ci-testing-automation.md` and is in `S1-plan` with active findings register.
- Prior planning artifacts for this initiative already exist under:
  - `docs/build-stream/plans/istara-testing-remote-qa-20260817-plan-b.md` (reference candidate, currently unavailable in this worktree view)
  - `docs/build-stream/plans/istara-public-ci-testing-20260818-plan-a.md`
  - `docs/build-stream/plans/istara-public-ci-testing-20260818-plan-c.md`
- Current `CHANGE_CHECKLIST.md`, `README.md`, and `TESTING.md` must be updated in implementation per project gate rule (`CHANGE_CHECKLIST`, `README`, `README.pt-BR`, `TESTING.md`).

Unverified items from available evidence (must be confirmed in implementation):
- Exact branch protection state and status checks in GitHub.
- Exact container profile behavior for all target runners.
- Baseline of existing CI lanes across all workflow files.

## 4) Target architecture and branch/CI state machine

### Branch topology
- `main`: protected merge target, requires owner human gate + full acceptance evidence.
- `testing` (public integration branch): required landing point for all feature PRs.
- `feature/*` or task branches: all changes start here.

### State machine
1. Feature branch changes and pull request created.
2. PR required target = `testing` (not `main`).
3. PR CI runs deterministic gates:
   - governance/public-tree gate
   - changed-path + obligations gate
   - unit/test/type/lint/build and contract/security gates
   - container build + smoke gates
4. If any mandatory obligation is missing, gate fails (fail-closed) and PR is blocked.
5. If green, CI artifacts are published as signed/disposable QA outputs.
6. Reviewer and owner inspect artifacts, then owner records explicit approval for branch promotion.
7. PR from `testing` to `main` remains disabled by default.
8. After explicit owner gate record, PR creation to `main` is re-enabled under controlled release recipe.
9. Merge to `main` creates production release workflow; post-merge canary optional.

### Failure/retry behavior
- Any non-deterministic lane (e.g., provider-auth live lane) records retries with capped budgets and reruns only on request.
- Artifact publication is per run; no cross-run mutable state is promoted.
- On recurring infra flake, fail artifact as infrastructure risk only after two independent verification attempts.

### Artifact retention
- CI artifacts are retained with branch/ref/build UUID and immutable retention policy (for example, 14 days for logs, 30 days for SBOM/report bundles, 90 days for release-ready digest indexes).
- Docker QA artifacts are ephemeral by default and cleaned by retention workflow.

## 5) Declarative feature/subfeature coverage registry and obligation algorithm

### Registry model
Create/maintain a registry (YAML) keyed by source path globs:
- `feature_id`, `subfeature_id`, `owners`, `required_obligation_sets`, `exceptions`, `requires_human_review`, `docs_features_update`.

### Path -> obligation mapping
For each changed file in PR diff:
1. Normalize path and match most specific registry rule.
2. For every matching feature, append mandatory obligation profiles:
   - `contracts`
   - `unit`
   - `frontend`
   - `backend`
   - `security`
   - `research_spine`
   - `runtime`
3. For `ui/`, `menu/`, `route/`, `store/`, `agent/`, `skill/`, `model/`, `test/` paths, require docs/features update evidence and explicit test obligations.
4. Resolve union of all obligations and execute each test lane exactly once.

### Fail-closed policy
- If a changed file cannot be classified to one or more registry entries and is not whitelisted, PR fails with explicit diagnostic listing uncovered paths.
- Owner must either classify coverage before merge or add a temporary override in a separate PR with explicit review note and a time-limited temporary risk id.

### CI enforcement points
- Pre-merge gate step reads: `scripts/check_change_obligations.py --base <BASE> --head <HEAD>`.
- Any miss increments and fails the run immediately before expensive runtime jobs.

### Living feature documentation coupling
For UI/menu/route/store/agent/skill/model/test changes:
- Run feature-doc parity command and fail PR if docs/features are stale.
- `docs/features` and generated site artifacts must stay aligned per existing AGENTS contract.

## 6) Full automated test pyramid and execution matrix

Execution order is strict to keep signal and cost bounded:

1. **Static and policy gate**
   - `python scripts/check_public_tree_clean.py --base <BASE> --head <HEAD>`
   - `python scripts/check_ci_governance.py`
   - `python scripts/public_repo_quality_audit.py --check` (policy-fail, with historical findings triaged first)

2. **Contract and obligation gate**
   - `python scripts/check_change_obligations.py --base <BASE> --head <HEAD>`
   - docs/features parity command (including `docs/features/site/manifest.json` updates)
   - verify open API/protocol contracts touched

3. **Repository and API contract checks**
   - backend migration/type/lint/test subsets
   - service contract and route tests tied to changed symbols

4. **Frontend quality gates**
   - frontend unit/type/lint/build
   - targeted route/render tests for changed surfaces

5. **Backend + relay + runtime checks**
   - selected backend and relay tests + deterministic worker tests
   - simulation harness preflight, synthetic corpus slice tests

6. **Safety and benchmark gates**
   - security benchmark lane
   - rate-limit and auth behavior checks
   - governance/telemetry checks required by Research Spine-related lanes

7. **Container and artifact gates**
   - Docker/Compose config compile
   - disposable build artifact build + health checks (no live model providers)
   - publish artifact descriptor (digest, tag, commit, git-tree, run id)

8. **Authorized-live provider lane** (bounded, opt-in)
   - single provider target only, explicitly configured per pipeline invocation
   - exact provider id + capability declaration + timeout budget + no-fallback policy
   - must remain separately marked as non-default and non-merge-critical unless declared required by registry profile

### Why ordered this way
- Cheap deterministic failures happen first, preventing resource and time waste.
- Runtime/provider-sensitive checks are last and isolated so they do not mask deterministic failures.

## 7) Disposable Docker QA artifact: reproducibility, host agnosticism, and cleanup

### Artifact contract
- Image tag format: `<registry>/<repo>:qa-${GITHUB_SHA}-${RUN_ID}` and optional branch slug suffix.
- Provenance metadata included (git tree hash, commit, registry, base image hashes, profile, provider profile ID, run id).

### Compose/runtime model
- Introduce QA compose profile set with isolated project name: `istara-qa-${RUN_ID}`.
- Volumes include run id suffix, e.g. `istara-qa-${RUN_ID}-postgres`.
- Credential injection only through ephemeral secrets and environment files, never committed.
- Network: loopback-first plus explicit ingress allowlist.

### Reset, seed, reseed, and audit
- Deterministic seed fixture pack per lane.
- `POST /_qa/reset` and `POST /_qa/reseed` test endpoints behind an explicit QA token.
- Retain only run-specific artifacts in `${RUN_ID}` scope.
- Post-run cleanup: remove volumes and containers by label selectors.

### Public artifact outputs
- artifact digest file
- QA run manifest
- log bundle path
- command/result matrix with durations and non-deterministic retry flags

## 8) Provider neutrality without weakening safety

- Provider adapters are selected by explicit manifest entry, not host detection.
- Chat and embedding contracts must each publish:
  - provider key (e.g., `provider_id`, `model_id`, `embedding_model_id`)
  - vector dimension / capability signatures
  - max context and timeout policy
  - explicit fail action on incompatibility
- One authorized live target per run only.
- No hidden fallback chain.
- Vector-space contract check remains active:
  - enforce dimension and provider invariants before any cross-system runtime test.
  - deny lane transitions when identity/drift changes are detected.
- Any provider contract mismatch fails hard and routes to manual risk triage.

## 9) Research Spine and self-improvement governance validation

- Keep lane distinction explicit:
  - contract-only lane (synthetic and deterministic inputs)
  - provisional runtime lane (explicitly marked non-reportable)
  - authorized live lane (credentialed, bounded, and reviewer-visible)
- Preserve evidence-unit provenance by keeping raw-source spans in artifacts.
- Reconciliation checkpoints enforce:
  - coding completion
  - reliability score + grounding pass
  - no-silent migration from provisional to accepted states
- Human approvals remain required before accepted artifacts, docs, or done signals can be produced.

## 10) Security and privacy controls

- Secrets via repository/runner secret stores and local environment references only.
- Never log provider responses with secrets or full payloads.
- Redaction policy in logs and artifacts.
- Docker runs without privileged mode; no host mount of daemon socket unless explicitly justified per job.
- CORS/WebSocket/CSRF baseline hardening unchanged and validated by security gate.
- Supply-chain controls: dependency hash pinning and optional SBOM/signature checks.
- Rate-limit and abuse controls preserved in gateway lanes.

## 11) Human gate and PR promotion flow

1. All automated gates produce a machine-readable evidence bundle.
2. Bundle is linked to the PR and requires reviewer handoff.
3. Owner records explicit human-approval decision (`approved_for_main` / `rejected`) in a signed artifact and Conductor-visible record.
4. PR target can switch from `testing` to `main` only after approval is present and current.
5. Promotion to `main` and PR creation cannot proceed from private-only or simulated-only paths.

## 12) Optional `multivac` adapter: contract and rollback

- `multivac` is categorized as **optional private adapter**, not required for public CI.
- Any `multivac` path:
  - inventory only, no schema mutations unless owner-authorized ticket.
  - unique project naming, no reuse of existing run state.
  - TLS/loopback/tunnel mode as declared in adapter profile.
- Rollback:
  - disable adapter profile
  - remove credentials and DNS mappings
  - leave public CI untouched and green.

## 13) Verification commands and evidence artifacts

### Mandatory command suite for implementation CI job
- `python scripts/check_public_tree_clean.py --base <BASE> --head <HEAD>`
- `python scripts/check_ci_governance.py`
- `python scripts/check_change_obligations.py --base <BASE> --head <HEAD>`
- `python scripts/public_repo_quality_audit.py --check`
- selected contract + API + frontend + backend test command groups
- `python scripts/feature_docs.py --seed-missing --generate-site --check`
- security benchmark command (project-owned)
- docker compose config/compose artifact smoke commands

### Required evidence artifacts
- change-obligation report JSON
- test lane matrix with pass/fail by rule
- artifact manifest (`manifest.json`/digest files)
- vector-space and provider-identity evidence outputs
- failure rationale for blocked lanes
- owner gate outcome record

## 14) Alternatives and failure modes

### Alternatives considered
- Continue current `main`-centric PR model: fails because it leaks owner-specific dependencies.
- Keep benchmark overlay only: fails because it does not enforce feature obligations at path-level and misses deterministic PR gate control.
- Shared self-hosted runners only: increases operational coupling and reintroduces private assumptions.
- Single fixed-provider lane only: violates provider neutrality and fallback constraints.

### Failure modes
- Registry divergence or stale globs
- Public tree quality command regressions unrelated to current PR
- provider capability mismatch in live lane
- synthetic data false-positive on vector assertions
- stale docs/features sync causing false gates

Mitigations:
- auto-generated coverage report and required triage ticket
- historical audit artifact cleanup policy
- explicit adapter capability contract and fail-closed policy

## 15) Architecture debt

- Missing end-to-end branch-protection evidence and enforcement in repository documentation.
- Public artifact phrase enforcement currently flags historical docs and may block immediate green checks.
- Current implementation is not yet guaranteed provider-neutral at all workflow call-sites.
- Optional staging/private adapters are insufficiently separated in onboarding docs.

## 16) Implementation phases (target execution)

| Phase | Scope | Exit gate | Owner action |
|---|---|---|---|
| A. Foundations | Add obligation registry, gating scripts, and docs index updates | obligation gate passes with synthetic fixture | Owner approves registry shape |
| B. Branch + governance | Implement `testing` branch + PR targeting + branch checks | branch state machine validated | Owner confirms promotion boundary |
| C. CI graph + artifact | Implement deterministic job graph + QA artifact publishing + cleanup | all mandatory jobs green | Owner confirms publish retention policy |
| D. Provider/runtime lane | Add provider identity manifest, assertion gates, and bounded live lane | vector-space and identity checks green | Owner approves one-target policy |
| E. Security + finalization | Wire secret policy, redaction checks, PR approval step | full evidence package and policy gate | Owner signs approval record |

## 17) Acceptance criteria (Given/When/Then)

1. Given a feature PR touching `backend`, when obligations are not declared in registry, then CI fails with an unclassified-path finding and no merge is allowed.
2. Given a PR with declared feature coverage, when all deterministic lanes pass, then the run publishes QA manifest artifacts and enters optional live-authorized lane only if explicitly configured.
3. Given a failed public-tree quality check, then CI blocks and emits a remediation report before any container artifact publish.
4. Given `multivac` is unavailable, then public branch CI remains fully runnable using public providers and local adapters configured by profile defaults.
5. Given all required gates pass and owner gate recorded, then PR from `testing` to `main` is unlocked; otherwise it remains blocked.

## 18) Files/surfaces likely to change in implementation

- `README.md`
- `README.pt-BR.md`
- `CHANGE_CHECKLIST.md`
- `TESTING.md`
- `.github/workflows/` (workflow graph and protections)
- `docs/features/**` and `docs/features/site/manifest.json`
- scripts under `scripts/` (change-obligation, artifact, feature-doc gating, optional provider assertion helpers)
- contract/test scaffolding referenced by touched feature subareas
- Docker/compose profile definitions and QA artifact tooling

## 19) Open decisions (owner-gated)

- Approve the exact list of deterministic jobs that remain non-optional before a PR can reach `testing` and those required before owner gate to `main`.
- Decide whether the live provider lane is required for every PR category or only explicitly labeled high-risk features.
- Decide the retention and storage of QA artifacts (GitHub artifacts vs object storage).
- Confirm final branch protection syntax and whether `main` receive can be enabled as repository rule or repository-level manual override.
- Confirm whether existing historical findings from `public_repo_quality_audit` should be grandfathered or remediated before full fail-on-error is enforced.
