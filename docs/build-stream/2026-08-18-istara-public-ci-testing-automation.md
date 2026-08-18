# Build Stream — Public Istara testing branch and CI automation

<!-- STATUS BLOCK -->
```yaml
item: istara-public-ci-testing-automation
branch: conductor/istara-public-ci-testing-20260818
cf: { spec: CF-SPEC-56, tasks: [CF-717, CF-718, CF-719, CF-720, CF-721, CF-722, CF-723, CF-724, CF-725, CF-726, CF-727, CF-728, CF-729, CF-730] }
phase: "Phase 1 — MECE master planning"
stage: S1-plan
status: in-review
blocked_on: "Waiting for owner approval of the selected Phase 1 master plan"
last: { agent: deepseek/deepseek-v4-flash, at: 2026-08-18T00:39:44Z, ledger: L-10 }
next_action: "All three architect votes recorded (A/B/C); await conductor consensus_result and explicit owner approval in Phase 2; no implementation before approval."
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

### L-4 | 2026-08-18T00:25:39Z | S1-plan | gpt-5.3-codex-spark | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-PLAN-B -->
Did: Wrote independent Architect B planning draft at docs/build-stream/plans/istara-public-ci-testing-20260818-plan-b.md, covering public branch/CI state machine, fail-closed feature-obligation mapping, deterministic test automation order, provider-agnostic disposable Docker QA artifact design, Research Spine-compliant provisional lane boundaries, security posture, optional `multivac` adapter boundaries, and acceptance criteria in executable form.
Result: Planning artifact is ready for MECE synthesis; no code/workflow/compose/tests/runtime or provider calls were changed.
Verified: `python scripts/check_public_tree_clean.py --help`; `python scripts/check_change_obligations.py --help`; `python scripts/check_ci_governance.py` (passed); `python scripts/public_repo_quality_audit.py --check` (failed on historical findings unrelated to this draft, treated as pre-existing).
Next: Await synthesis/cross-vote and owner approval checkpoint before any implementation work.

### L-5 | 2026-08-18T00:30:01Z | S1-plan | gpt-5.3-codex-spark | planner | synthesize <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-B -->
Did: Synthesized the consolidated plan artifact at `docs/build-stream/plans/istara-public-ci-testing-20260818-master-b.md` from Architect A/B/C drafts and wrote a unified MECE master plan covering branch/CI state machine, feature-obligation mapping, ordered automation matrix, disposable public Docker QA artifact contract, provider-neutrality checks, Research Spine controls, security controls, human gate, and alternatives.
Result: Planning completion for stage ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-B; no code/workflow/runtime implementation executed.
Verified: `compass-forge --workspace /Users/user/Documents/compass-forge status`; `compass-forge --workspace /Users/user/Documents/compass-forge next`; `compass-forge --workspace /Users/user/Documents/compass-forge work-order --role istara-public-ci-testing-20260818-architect-b --task ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-B`; `compass-forge --workspace /Users/user/Documents/compass-forge spec show CF-SPEC-56`; `ls -la .github/workflows` (discovery evidence); `git branch -a` (branch topology); `cat docs/build-stream/plans/istara-public-ci-testing-20260818-master-b.md`.
Next: Provide this plan to conductor consensus and wait for owner approval before any implementation tasks.


### L-7 | 2026-08-18T00:34:52Z | S1-plan | deepseek/deepseek-v4-flash | executor | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-C -->
Did: Synthesized the three immutable architect drafts (A: holistic/branch+PR, B: CI automation, C: runtime/provider/spine/security) into one complete MECE master-plan candidate at docs/build-stream/plans/istara-public-ci-testing-20260818-master-c.md (1289 lines, 20 sections, 27 consolidated Given/When/Then acceptance criteria). Recorded 7 explicit reconciliation decisions (R1-R7: script-scoped reset over HTTP QA endpoints; merged Compose profile naming; staging as environment mirror; two-layer registry with one authority + consulted qa/runtime_capabilities.json; live lane owner-dispatched only; consolidated Phase 0-6 plan; single themed acceptance set) and a coverage matrix mapping each master section to its source draft. Grounded all claims in repo evidence (E1-E16) verified at worktree HEAD; carried UNVERIFIED items forward (multivac surface, .gitignore contents, live-lane pass state, SBOM tooling, branch-protection state). Planning-only: no product source, CI workflow, Compose, test, or generated-doc changes; no Docker started, no provider/model calls, no multivac access, no PR/merge.
Result: MECE master-plan candidate C complete for the conductor's cross-vote; conflicts resolved; no voting performed in this synthesize phase.
Verified: wc -l -> 1289 lines; grep -c '^## ' -> 20 sections; 27 AC-* criteria; repo facts re-verified: assert_vector_space_invariant at backend/app/core/pi_runtime/embeddings_gateway.py, ci.yml jobs (governance/backend/frontend/test-harness-js/desktop), scripts/check_change_obligations.py --base/--head, TESTING.md live LLM profile (ISTARA_RUN_REAL_LLM_BENCHMARK=1); command evidence + self_report recorded via compass-forge (workspace /Users/user/Documents/compass-forge).
Next: Conductor cross-votes the three master candidates (A/B/C), preserves disagreement/trade-offs, and pauses at the owner-approval barrier (Phase 2); no implementation before approval.

### L-8 | 2026-08-18T00:38:13Z | S1-plan | gpt-5.3-codex-spark | executor | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B -->
Did: Reviewed and compared master-plan candidates A and C against the user request, then issued a MECE cross-vote.
Result: Voted `C` (`75a1fc68de62745e5a9aaabe8580d02d071e3a98260a765b37c17f7b0cd91d37`) to carry the synthesis that explicitly resolves draft conflicts, keeps one canonical feature obligation authority, and preserves explicit owner-gated uncertainty and rollback paths.
Verified: `compass-forge --workspace /Users/user/Documents/compass-forge task evidence ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B --type plan_vote ...`; `compass-forge --workspace /Users/user/Documents/compass-forge task evidence ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B --type command --summary "Read work-order payload for vote"`; `compass-forge --workspace /Users/user/Documents/compass-forge task evidence ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-B --type self_report --summary ...`.
Next: Await owner approval for the selected Phase 1 master plan before any implementation work.

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

### L-6 | 2026-08-18T00:34:06Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-MASTER-A -->
Did: Synthesized the three immutable Architect A/B/C snapshots into `docs/build-stream/plans/istara-public-ci-testing-20260818-master-a.md`. Reconciled the whole-system branch/promotion lifecycle, one canonical feature-obligation and capability registry, deterministic CI graph, disposable Docker QA, provider/vector safety, Research Spine and self-improvement governance, security, optional owner-local staging, human approval, implementation phases, executable acceptance, evidence, rollback, open decisions, and a draft coverage matrix. No product source, workflow, Compose, test, generated-doc, runtime, provider, Docker, staging, PR, or production surface was changed.
Result: Candidate A is complete and ready for consensus review. The synthesis deliberately avoids three competing registries by keeping runtime capabilities in the canonical coverage registry; it distinguishes contract-only, synthetic-provisional, authorized-live, and staging claims; and it preserves unverified blockers, owner decisions, inherited gate debt, and rollback boundaries. The lifecycle status now reflects concurrent master-plan review; no existing ledger entry or unrelated worker artifact was edited.
Verified: the plan validator command passed: `python - <<'PY' ... required sections present; no trailing whitespace/TODO/clarification markers ... PY` (1,222 lines / 81,351 bytes); `git status --short --untracked-files=all` showed the candidate plus pre-existing architect instruction/master-plan files. No architecture gate was run because this stage is planning-only and changes no architecture boundary.
Next: Conductor cross-votes master candidates A, B, and C, records the selected candidate ID in `plan_vote` evidence, and pauses for explicit owner approval before implementation.


### L-9 | 2026-08-18T00:39:33Z | S1-plan | openai/gpt-5.6-luna | planner | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-A -->
Did: Reviewed exactly the two supplied master-plan snapshots (candidate B and candidate C) and recorded a vote for candidate C; no code or plan artifact was edited.
Result: Candidate C selected for explicit R1-R7 reconciliation, coverage matrix, labeled uncertainties, single registry authority, phase gates, acceptance criteria, and rollback/evidence boundaries; ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-A is ready for conductor tally.
Verified: packet validation Python command -> passed; Compass Forge command, plan_vote, and self_report evidence rows -> recorded.
Next: Conductor tallies the cross-votes, freezes the winning master plan, and waits at the owner-approval barrier before implementation.

### L-10 | 2026-08-18T00:39:44Z | S1-plan | deepseek/deepseek-v4-flash | reviewer | Phase 1 <!-- bsc-ledger:ISTARA-PUBLIC-CI-TESTING-20260818-VOTE-C -->
Did: Read both MECE master-plan candidates supplied for the cross-vote (candidate A at docs/build-stream/plans/istara-public-ci-testing-20260818-master-a.md, 1223 lines/24 G/W/T criteria; candidate B at docs/build-stream/plans/istara-public-ci-testing-20260818-master-b.md, 433 lines/6 criteria), verified both are byte-identical to their conductor consensus snapshots (diff -q passed for both), ran a required-term/section/GWT structural validator, and recorded a MECE cross-vote as Architect C (slot c).
Result: Voted candidate A (1bc3c6cd42ef3e87a77be964f71fe7055cdcc860b437d9af04d96168c829bed6): it resolves the known conflicts explicitly (single canonical registry, staging as post-main mirror, fork-PR permission boundary, inherited Compose pids_limit conflict must be reproduced before parity), carries 24 executable Given/When/Then criteria with per-phase (0-6) verification/entry-exit gates/rollback, and specifies the load-bearing safety detail (promotion-manifest.json SHA/base/digest/approval binding, 10-point provider readiness with assert_vector_space_invariant and no-fallback one-target live lane, per-gate Research Spine QA proof table, self-improvement isolation, redaction/public-tree contracts) that candidate B only sketches. Candidate B is coherent but thinner and cites a known-failing verification command (public_repo_quality_audit.py --check) and a ghcr.io registry-write tag that is fork-unsafe. No plan file, spec, or code was edited; planning-only.
Verified: shasum -a 256 on both .compass-forge/conductor/consensus-snapshots/*.md; diff -q master-a.md snapshot-a (identical); diff -q master-b.md snapshot-b (identical); python3 plan validator -> candidate a: 1223 lines / 19 sections / 24 GWT / no missing terms; candidate b: 433 lines / 19 sections / 6 GWT / no missing terms; plan_vote + self_report + command evidence recorded via compass-forge (workspace /Users/user/Documents/compass-forge).
Next: Conductor collects VOTE-A/VOTE-B/VOTE-C, records consensus_result, then pauses at the owner-approval barrier (Phase 2); no implementation before approval.

