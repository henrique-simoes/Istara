# Local review handoff: Review_pi_test

## Scope

This branch completes the opt-in Pi adaptation in the isolated replacement worktree. It is local-only: no push, remote pull request, external channel traffic, or persistent global conductor-routing mutation occurred.

## Final evidence

- Build Stream Conductor: converged after five review rounds; final independent Sol delta review passed with no findings.
- Compass Forge: CF-120 through CF-133 done; CF-SPEC-7 accepted without force with 56 evidence records.
- Production Pi adapter: 21 tests pass and map all 15 canonical scenarios to production services and the real Pi Agent Core worker.
- Bounded DeepSeek production core: exactly one owner-approved request, no retry, `done`/`stop`, supervisor stopped; prompt, output, credentials, and endpoint URL remain redacted.
- Feature docs: `python scripts/feature_docs.py --seed-missing --generate-site --check` passed (86 features, 224 artifacts).
- Security benchmark: `python scripts/security_benchmark.py --fail-on-threshold` passed (28/28, 100%).
- Compass Forge after-gate: no new failures, warnings, route/type/contract drift, or security findings. The gate's non-zero status is inherited `unexpected_large_files` debt already present in its baseline.

## Review focus

1. Pi is default-off and fails closed before transport or outbound effects on registration, terminal error, or abort failures.
2. Chat, admitted A2A inbox work, `pi_local`, governed Autoresearch, memory/research state, and steering reach the production Pi worker through Istara-owned authorization and governance.
3. The coupled same-model transport spy proves API-endpoint and donated-compute isolation in both directions; Petals-style donation scheduling itself is unchanged.
4. The 15-scenario matrix uses real production routes/services with a loopback provider stub, not the lab facade.
5. The bounded DeepSeek probe proves one production-core provider request only; it is not a load, multi-turn, tool-use, or external-channel claim.

## Rollback

Do not select Pi, or revert the local commits on `Review_pi_test`. Default Istara routing and origin remain unchanged.
