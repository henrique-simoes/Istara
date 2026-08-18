# Build Stream — Public Istara testing branch and CI automation

<!-- STATUS BLOCK -->
```yaml
item: istara-public-ci-testing-automation
branch: conductor/istara-public-ci-testing-20260818
cf: { spec: CF-SPEC-56, tasks: [CF-717, CF-718, CF-719, CF-720, CF-721, CF-722, CF-723, CF-724, CF-725, CF-726, CF-727, CF-728, CF-729, CF-730] }
phase: "Phase 1 — MECE master planning"
stage: S1-plan
status: in-progress
blocked_on: "Owner approval of the winning MECE plan before implementation or PR creation"
last: { agent: openai/gpt-5.6-luna, at: 2026-08-18T00:24:01Z, ledger: L-3 }
next_action: "Synthesize this draft with Architect B and Architect C, cross-vote the master candidates, then stop at the owner-approval barrier."
```
<!-- /STATUS BLOCK -->

## Plan overview (roadmap)

**Outcome.** Create a professional, public, provider-agnostic testing branch and CI system for Istara. Every feature change must be mapped to the appropriate deterministic and authorized runtime checks, produce a reusable disposable Docker QA artifact, and stop at a human approval gate before any PR is created or promoted to `main`.

**Official-path principle.** The public workflow must be usable by every Istara developer without requiring a particular host, private endpoint, cloud vendor, local model server, or owner credential. `multivac` is an optional private adapter for the owner's environment only; it is never the official CI or staging dependency.

**Safety spine.** The plan must preserve the Research Spine, source-span evidence, provisional-only synthetic data, exact model/provider identity, embedding dimensions, `assert_vector_space_invariant`, fail-closed provider behavior, credential isolation, and no silent model loading. Inference-free lanes must not be described as full-feature readiness, and synthetic vectors must never bypass production gates.

**CI/staging distinction.** CI is automated pre-merge validation and artifact production. Staging is a running integrated environment used for acceptance. The plan must define both without conflating them, and must place the human gate after automated evidence but before PR creation to `main`.

| Phase | Goal | Acceptance / verification | Status |
|---|---|---|---|
| 0 | Frame the owner-approved initiative and Compass Forge contract | `compass-forge spec clarify/plan/tasks CF-SPEC-56` | done |
| 1 | Produce and converge a thorough MECE master plan | Conductor architect drafts, synthesis, cross-vote, no implementation | in-progress |
| 2 | Owner approves the frozen plan and releases implementation | `conductor.py approve`; explicit owner approval evidence | planned |
| 3 | Implement public branch/CI, feature mapping, Docker artifact, and developer workflow | deterministic gates, CI workflows, contract tests, docs | planned |
| 4 | Validate disposable runtime and provider-neutral adapter contracts | local authorized runtime checks; Research Spine and fail-closed evidence | planned |
| 5 | Validate optional staging adapters, including private `multivac` | read-only-first, explicit authorization, isolated project, rollback evidence | planned |
| 6 | Human gate, PR creation, promotion, and learning | automated evidence green, owner approval, PR-ready artifact; no auto-merge | planned |

## Decision log <!-- append-only -->

DEC-1 | 2026-08-18 | S0 | owner
Context: The existing `testing` branch/process is documented but not current-by-construction, lacks Docker/feature CI enforcement, and cannot make the private `multivac` server the public testing dependency.
Decision: Create a public, provider-agnostic testing branch and CI system for every Istara developer, with an optional private `multivac` adapter and a human gate before PR creation to `main`.
Why: This separates reusable project infrastructure from one owner's host while preserving a practical private validation path.

DEC-2 | 2026-08-18 | S1 | owner
Context: The requested MECE roster changes the planning perspectives while keeping the implementation, fixer, and reviewer assignments.
Decision: Architect A uses the current Pi model `openai/gpt-5.6-luna` at xhigh; Architect B uses Codex `gpt-5.3-codex-spark` through standalone OAuth Codex CLI at xhigh; Architect C uses Pi `deepseek/deepseek-v4-flash` at high. Implementer, fixer, and reviewer remain on their existing routes. All architect routes have no fallback.
Why: The three primary architect identities are distinct across harness/model, planning remains independently comparative, and stale Kimi quota/fallback paths are removed from this run.

## Ledger <!-- append-only -->

### L-1 | 2026-08-18T00:12:00Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1
Did: Created the new public CI/testing initiative from the owner request, clarified CI versus staging, defined the public/provider-agnostic boundary, kept `multivac` optional, created CF-SPEC-56 with clarification answers, generated its plan and tasks, and prepared the three-architect Conductor roster.
Result: Planning is ready to dispatch. No source implementation, Docker startup, provider request, model provisioning, PR creation, merge, or `multivac` mutation has occurred.
Verified: `compass-forge spec clarify CF-SPEC-56`; `compass-forge constitution check`; `compass-forge spec plan CF-SPEC-56`; `compass-forge spec tasks CF-SPEC-56`; read-only inspection of current branch/worktrees and Conductor routing; lifecycle and architect brief created in this worktree.
Next: Run the Conductor's three-architect MECE planning stages and stop at the owner-approval barrier.

### L-2 | 2026-08-18T00:21:04Z | S1-plan | deepseek/deepseek-v4-flash | executor | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-C -->
Did: Wrote the independent Architect C draft plan at docs/build-stream/plans/istara-public-ci-testing-20260818-plan-c.md (774 lines, 20 sections) covering: Docker/QA artifact portability with per-run isolation, seed/reset/audit/retention contracts; provider-neutral chat/embedding adapter contracts with exact identity, no-fallback, dimension/readiness evidence and one-target live authorization; Research Spine-valid provisional-only synthetic QA (is_qa_provisional blocks accepted/reportable states); security/privacy controls incl. redaction scan and provenance; staging contract + read-only-first multivac adapter with rollback; human-gate evidence bundle; implementation phases C1-C5 with entry/exit gates; Given/When/Then acceptance criteria; exact verification commands; alternatives/risks/debt/rollback; files-surfaces list; owner-gated open decisions; task breakdown. Planning-only: no product source, CI workflow, Compose, test, or generated-doc changes; no Docker started, no provider/model calls, no multivac access, no PR/merge.
Result: Draft plan artifact complete for MECE synthesis; lane boundaries stated for A (state machine/gate mechanics) and B (workflow graph). Unverified items explicitly labeled: multivac surface, current .gitignore contents, live-lane pass state, existing SBOM tooling.
Verified: wc -l docs/build-stream/plans/istara-public-ci-testing-20260818-plan-c.md -> 774 lines; grep -c '^## ' -> 20; evidence rows E1-E15 cited from docker-compose.yml, .github/workflows/ci.yml, backend/app/core/pi_runtime/embeddings_gateway.py (assert_vector_space_invariant), backend/app/services/research_validity_service.py, backend/app/api/routes/llm_servers.py, backend/app/core/embedding_validation.py, scripts/check_public_tree_clean.py, scripts/check_change_obligations.py, TESTING.md, pytest.ini, security/SECURITY_BENCHMARK.md; command evidence + self_report recorded via compass-forge.
Next: Conductor synthesizes A+B+C drafts into MECE master candidates, cross-votes, then pauses at the owner-approval gate (Phase 2); no implementation before approval.


### L-3 | 2026-08-18T00:24:01Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-A -->
Did: Wrote the independent holistic Architect A draft at `docs/build-stream/plans/istara-public-ci-testing-20260818-plan-a.md` (1,204 lines; 72,853 bytes). It covers public branch and promotion state machine, fail-closed feature/subfeature obligations, deterministic and authorized test lanes, immutable disposable Docker QA artifacts, provider/vector-space safety, Research Spine and self-improvement governance, security, optional `multivac` staging adapter, implementation phases, executable acceptance, evidence, risks, rollback, and owner-gated decisions.
Result: Plan A is ready for MECE synthesis. It recommends a public `testing` integration branch, a registry-driven obligation classifier, distinct contract-only/synthetic-provisional/authorized-live lanes, and a human approval boundary before promotion-PR creation. No product source, CI workflow, Compose file, test, provider, model, server, Docker runtime, or `multivac` state was changed.
Verified: plan structure assertion (passed; 1,204 lines / 72,853 bytes); `python -m py_compile scripts/check_ci_governance.py scripts/check_test_harness.py scripts/check_public_tree_clean.py scripts/check_change_obligations.py` (passed); `python scripts/check_ci_governance.py` (passed); `python scripts/check_test_harness.py` (passed); `docker compose -f docker-compose.yml config --quiet` (failed with the inherited `pids_limit`/`deploy.resources.limits.pids` conflict; no services started).
Next: Conductor synthesizes this draft with Architect B and Architect C, cross-votes the master candidates, and pauses for owner approval before implementation.

## Phase 1 — MECE master planning

**Architect coverage contract:**

- Architect A: whole-system architecture, branch/PR lifecycle, developer experience, feature-to-test obligations, human approval gate, public contract, and synthesis-quality challenge.
- Architect B: CI/test automation, GitHub workflow design, changed-path classification, unit/integration/E2E/simulation/security orchestration, Docker artifact publication, caching, evidence, and PR promotion mechanics.
- Architect C: Compose/runtime portability, provider-neutral model and embedding contracts, Research Spine validity, synthetic data/reset/retention, security/isolation, optional staging adapters, and `multivac` rollback.

**Execution:** Planning-only Conductor dispatch. Architects may write only their assigned plan artifacts and lifecycle planning evidence. They must not modify product source, start Docker, call live providers, provision models, access or mutate `multivac`, create a PR, merge, or deploy.

**Review:** The Conductor will synthesize MECE master candidates, cross-vote them, preserve disagreement and trade-offs, and pause for explicit owner approval. No implementation task may run before approval.

### Review (Phase 1)

**Findings register**

| ID | Sev | Dim | Where | Finding | CF task | Status |
|---|---|---|---|---|---|---|
| P1-F-1 | open | Plan | pending architect plans | Planning coverage and unresolved trade-offs are not yet known. | pending | open |

**Phase summary:** Pending the three-architect MECE run.

## Summary (S5 — whole plan)

Pending. This section is completed only after implementation, validation, human approval, PR creation, and final evidence review.
