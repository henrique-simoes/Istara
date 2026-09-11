# Architect B Plan — Pi vs Legacy B1–B4 Benchmark

## Scope and planning basis

This plan implements and executes the benchmark program in
`docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md` §10. It does not
change the product's engine default, delete the legacy engine, or treat benchmark output
as research evidence. The current tree has no `tests/pi_benchmark/`,
`comparison-Istara-pi/`, or `scripts/pi_benchmark_report.py`; both existing JavaScript
runners also lack the proposed `--engine pi|legacy|both` orchestration. Therefore B1–B4
cannot be run honestly until the benchmark apparatus is implemented and contract-tested.

The experiment remains opt-in and reversible. Istara owns authorization, project scope,
tool execution, persistence, telemetry, the Research Spine gates, and endpoint isolation.
The benchmark may observe those paths but may not bypass them or promote provisional
research artifacts. No live server, model load, or completion probe starts without the
owner's explicit permission. T3 additionally requires an approved dollar envelope recorded
as Compass Forge evidence.

## Technical design

### One immutable experiment manifest

Add `tests/pi_benchmark/` as the authoritative paired-run harness. Its CLI creates a
manifest before execution containing: schema version, git SHA and dirty-state digest,
benchmark phase, determinism tier, scenario/rubric/compiler versions and SHA-256 hashes,
engine order, DUT and judge model identities, seeds, N, temperature and token limits,
fixture/corpus hashes, redacted endpoint fingerprints, exact-versus-estimated usage policy,
per-run ceilings, and the owner's approval-evidence reference where required. Refuse to
resume or combine runs whose immutable fields differ.

Every pair uses one fixture snapshot and seed, then runs `legacy→pi` for half the seeds and
`pi→legacy` for the other half to reduce order bias. Each engine gets a fresh project/run
namespace while sharing byte-identical inputs. A missing or failed arm is emitted as
`not_runnable` with a typed reason; it is never dropped or converted to zero. T0/T1, T2,
and T3 records remain separate through reporting.

### Route-level runner and provenance

Implement `tests/pi_benchmark/runner.py`, scenario packs, feature-criteria compiler,
JudgeLayer, and probes described by §10.3. Re-host the 15 canonical Pi scenarios through
real ASGI/HTTP route/service boundaries rather than importing their test doubles. Add
`--engine pi|legacy|both` to both existing JavaScript runners and thread it to the already
supported `x-istara-agent-engine` client header. The paired runner must assert the returned
engine attribution and usage-ledger engine match the requested arm.

Write redacted, schema-validated run records beneath
`tests/pi_benchmark/.results/runs/<run-id>/`. Preserve raw source spans and Research Spine
state/evidence handles where a scenario touches research data. Candidate/provisional
artifacts never count as accepted facts, insights, recommendations, Done tasks, or reports.
Run directories are local, gitignored, append-only inputs to report generation; reruns get
new IDs rather than overwriting prior evidence.

### Metrics and judging

Create a versioned `metrics-schema.json` covering the ten owner axes, capability
differences, run status, tier, provenance, usage exactness, and paired-statistic fields.
Capture Pi's exact usage and legacy provider usage when available; otherwise set
`estimate=true` and name the estimator. Never aggregate exact and estimated values in an
unlabelled series.

Deterministic checks remain primary. Judge calls use a model different from every DUT,
strip engine labels, evaluate both A/B and B/A positions, cache by input/rubric/model hash,
and expose disagreement rather than forcing a winner. The report computes paired deltas,
effect sizes, and 10,000-resample bootstrap 95% confidence intervals. A CI crossing zero is
rendered as `no detected difference`. Capability asymmetries (Pi abort/cache/streaming and
legacy donor reachability) are descriptive, not scored.

### Report generation

Add `scripts/pi_benchmark_report.py` as the only producer of numeric report claims. It
validates all input records, rejects incompatible manifests or mixed tiers, and writes a
timestamped bundle to `comparison-Istara-pi/reports/<timestamp>/`: `report.md`, a
self-contained `report.html`, and `scorecard.json`. It also updates
`comparison-Istara-pi/README.md` with a dated link only after a secret scan and report
reproducibility check. The final verdict may say win, loss, or no detected difference per
axis; it must list `not_runnable`, manual feature criteria, missing usage, judge disagreement,
and threats to validity.

## Task graph

### E0 — Freeze the protocol and build the apparatus

Definition of Ready: W0–W9 focused validation is green; the working SHA is recorded; the
owner has selected T2 DUT models and a distinct judge model; no live process is needed for
this task.

1. Add the versioned manifest and metrics schemas, CLI, redaction/secret-scan helpers, and
   deterministic paired-order/seed logic under `tests/pi_benchmark/`.
2. Implement the canonical, Research Spine, A2A, memory-load, skills, tool, feature-matrix,
   and system-prompt probe packs. Manual feature criteria remain explicit and counted.
3. Add legacy usage capture at the dispatcher/registry seam and correct the long-horizon
   chunk-count token proxy to consume the usage ledger. Do not change donor routing.
4. Plumb `--engine` through the simulation and real-user runners and assert request,
   response, and ledger attribution.
5. Implement blind/position-swapped judging, deterministic metric computation, bootstrap
   statistics, and report generation. Add fixtures that prove regeneration is byte-stable
   after normalizing timestamps.
6. Add `.results/` to `tests/pi_benchmark/.gitignore`; ensure no endpoint URL, token,
   connection string, raw secret, or private fingerprint can reach run/report artifacts.
7. Update affected living feature docs, testing docs, the security control matrix if a
   control/evidence path changes, and regenerate feature documentation.

Dependencies: E0 blocks B1–B4. Split implementation into schema/runner, scenarios/probes,
usage/engine plumbing, judge/statistics, and reporting subtasks so each can receive an
independent review and focused verification.

### B1 — Contract tier (T0/T1)

Definition of Ready: E0 is reviewed; all schema, redaction, pairing, and `not_runnable`
negative tests pass; no model or server is loaded.

1. Generate one frozen manifest for the 15 canonical scenarios plus W2 surfaces.
2. Run both engines at T0 and T1 with identical fixtures/seeds and alternating order.
3. Validate every expected pair, deterministic contract, engine-attribution field, usage
   exactness label, and fail-closed behavior.
4. Produce a B1 report draft and baseline digest. Any contract failure blocks B2; fix the
   apparatus or product under a separate CF remediation task, then rerun under a new ID.

### B2 — Breadth tier (T2, N≥5)

Definition of Ready: B1 passes; explicit owner permission for bounded local server/model
loading is recorded; model inventory and capacity preflight pass; T2 DUT and judge are
distinct; fixtures and rubric versions are frozen.

1. Run a one-pair T2 smoke test with strict wall-clock, turn, token, and memory ceilings.
   Tear it down and inspect redaction, routing isolation, and ledger attribution.
2. Run N≥5 paired repetitions for the full canonical, feature-criteria, skills, tool,
   system-prompt, and graceful-failure packs. Randomize only the declared seed/order; hold
   model, temperature, prompt, corpus, and limits fixed.
3. Run blind, position-swapped judging after DUT captures are frozen. Count judge workload
   separately from DUT usage.
4. Generate the first complete report bundle. Record manual criteria and unavailable
   features in denominators; do not impute scores.

### B3 — Depth tiers (T2 high-N, then gated T3)

Definition of Ready: B2 report validates; spine/A2A/memory scenarios have no unresolved
contract failures; local capacity supports the chosen high-N; T3 remains disabled.

1. Run a preregistered T2 high-N set for end-to-end Research Spine, A2A, memory-load, and
   tool-optional ablation scenarios. Choose N before seeing comparative results and record
   it in the manifest.
2. Generate a T3 dry-run cost estimate from observed T2 input/output/cache tokens and the
   versioned pricing table, including both DUT arms, retries, judge calls, and contingency.
   Emit scenario counts, proposed N, per-run ceiling, worst-case total, and teardown plan.
3. Stop. Present the estimate to the owner and obtain an explicit in-chat dollar envelope;
   attach the approval as CF evidence. If approval is absent or below the estimate, mark T3
   `not_run: owner_budget_not_approved` and continue only with a clearly labelled T2 report.
4. With approval, run one bounded T3 canary pair. Verify model identities, no donor traffic
   on Pi, cost accounting, redaction, and ceiling enforcement before the remaining pairs.
5. Execute the approved low-N T3 matrix without exceeding the envelope. Fail closed on
   unpriced usage, ceiling breach, identity drift, secret-scan failure, or attribution
   mismatch; teardown all owned processes/endpoints after the run.
6. Freeze B3 inputs and compute final paired statistics separately for T2 and T3.

### B4 — Reproducible report and rollout handoff

Definition of Ready: B3 inputs are frozen; all run directories pass schema and secret
validation; any omitted T3 work has an explicit reason.

1. Regenerate all numeric tables/charts exclusively from frozen JSON and judge caches.
2. Independently reproduce the bundle from the artifact index and compare normalized
   hashes. Sample-trace at least one value per axis back to run records and usage rows.
3. Publish only to the local `comparison-Istara-pi/reports/<timestamp>/` tree, link the
   dated Markdown from its README, and record the raw-artifact index and threats to validity.
4. Run full benchmark, Research Spine, documentation, and security gates; obtain an
   independent review of methodology, code, statistics, security, and report claims.
5. Hand the report to the owner for the separate rollout decision. Do not flip
   `agentic_engine_default`, remove legacy code, push, deploy, or open a PR in B4.

## Acceptance criteria

1. **Given** a fixed scenario, model, parameters, fixture hash, and seed, **when** `both`
   engines run, **then** exactly two attributable records are emitted with the same pair ID
   and neither arm can silently disappear.
2. **Given** an engine failure or unavailable feature, **when** the run closes, **then** the
   arm is `not_runnable` with a typed reason and remains in every denominator/report table.
3. **Given** exact Pi usage and exact-or-estimated legacy usage, **when** metrics aggregate,
   **then** exactness labels survive to every JSON/table/chart and unlike categories are not
   silently pooled.
4. **Given** a research-data scenario, **when** it traverses the application, **then** raw
   source spans, reliability/reconciliation state, human-review state, and route evidence
   remain traceable; provisional outputs never count as reportable research.
5. **Given** judge evaluation, **when** a pair is scored, **then** the judge differs from all
   DUTs, engine identity is blind, both positions are evaluated, rubric/input hashes are
   logged, and deterministic checks remain visible.
6. **Given** N≥5 T2 pairs, **when** comparison statistics are generated, **then** each axis
   reports paired delta, effect size, 10k-bootstrap 95% CI, and `no detected difference`
   whenever the CI crosses zero.
7. **Given** any proposed T3 run, **when** approval evidence or sufficient envelope is
   missing, **then** no API request occurs. With approval, aggregate and per-run ceilings
   fail closed and include judge spend.
8. **Given** frozen run records, **when** B4 is generated twice, **then** normalized outputs
   are identical, all numbers trace to JSON, all required files exist, and the secret scan
   is clean.
9. **Given** completion of B4, **when** the branch is inspected, **then** the engine default
   and legacy implementation are unchanged and the report requests—but does not enact—the
   owner's rollout decision.

## Exact verification plan

The implementer may refine selectors as tests are added, but these command contracts and
their semantics must remain stable:

```bash
# Static apparatus and focused unit contracts (no live model loading)
python -m pytest tests/pi_benchmark -q -m "not live"
npm --prefix tests/real_user_benchmark run check
npm --prefix tests/simulation run test:static

# B1 T0/T1 paired contract runs
python -m tests.pi_benchmark.runner --phase B1 --tier T0 --engine both --repetitions 1 --manifest-out tests/pi_benchmark/.results/manifests/b1-t0.json
python -m tests.pi_benchmark.runner --phase B1 --tier T1 --engine both --repetitions 1 --manifest-out tests/pi_benchmark/.results/manifests/b1-t1.json
python -m tests.pi_benchmark.validate --phase B1 --require-complete-pairs --require-redacted

# B2 and the pre-approved local portion of B3; run only after explicit model-load permission
python -m tests.pi_benchmark.runner --phase B2 --tier T2 --engine both --repetitions 5 --manifest-out tests/pi_benchmark/.results/manifests/b2-t2.json
python -m tests.pi_benchmark.runner --phase B3 --tier T2 --engine both --repetitions <preregistered-N> --packs spine,a2a,memory,tool-ablation --manifest-out tests/pi_benchmark/.results/manifests/b3-t2.json
python -m tests.pi_benchmark.validate --phase B2,B3 --tier T2 --require-complete-pairs --require-redacted

# T3 estimate is read-only; execution is a separate, owner-gated command
python -m tests.pi_benchmark.cost_estimate --manifest tests/pi_benchmark/.results/manifests/b3-t2.json --pricing labs/pi-replacement/src/raw-llm-capture.mjs --include-judge --output tests/pi_benchmark/.results/b3-t3-cost-estimate.json
python -m tests.pi_benchmark.runner --phase B3 --tier T3 --engine both --repetitions <owner-approved-N> --approval-evidence <CF-evidence-id> --max-total-cost-usd <owner-approved-envelope> --manifest-out tests/pi_benchmark/.results/manifests/b3-t3.json

# B4 reproducibility and repository gates
python scripts/pi_benchmark_report.py --runs tests/pi_benchmark/.results/runs --output comparison-Istara-pi/reports/<timestamp>
python -m tests.pi_benchmark.validate_report comparison-Istara-pi/reports/<timestamp> --require-reproducible --require-redacted
python -m pytest tests/pi_production tests/pi_migration tests/test_research_integrity_reports.py -q
npm --prefix pi-runtime test
python scripts/feature_docs.py --seed-missing --generate-site --check
python scripts/security_benchmark.py --fail-on-threshold
compass-forge gate after --task <benchmark-task> --summary
```

In addition, record `git status --short`, the exact commit SHA, process ownership/teardown
evidence for live runs, manifests, validation summaries, cost estimate, owner approval ID,
and every command result as CF evidence. A green mocked suite is B1 evidence only; it must
not be presented as live T2/T3 proof or deployment readiness.

## Risks and mitigations

- **Harness bias or engine leakage:** shared fixtures, alternating order, returned-engine and
  ledger assertions, blind labels, and independent methodology review.
- **Non-independent judge:** fail closed when judge identity overlaps a DUT; position swap
  and expose judge disagreement alongside deterministic checks.
- **Research Spine bypass:** route-level scenarios, preserved source spans/state handles,
  explicit provisional status, and Research Spine regression suite.
- **Cost or secret exposure:** dry-run estimate, explicit owner envelope, per-run/aggregate
  ceilings, unpriced-usage refusal, redaction-before-write, secret scan, and owned teardown.
- **Local resource interference:** explicit permission, one bounded model target at a time,
  capacity preflight, canary pair, sequential scheduling where needed, and RSS sampling.
- **False precision:** preserve exact/estimate flags, tier separation, paired CIs/effect
  sizes, no-difference wording, manual/not-runnable counts, and threats-to-validity section.
- **Baseline contamination:** immutable manifests, fresh namespaces, clean fixture restore,
  dirty-state digest, and append-only run IDs.
- **Scope creep into rollout:** engine-default flip and legacy deletion are explicit
  non-goals and require a new owner-approved spec after B4.

## Rollback and recovery

All product-path changes are telemetry-additive or benchmark-only and must land in small
commits. If engine plumbing or legacy usage capture regresses production behavior, revert
that subtask and restore the prior default-off dispatch path; retain failed benchmark
artifacts as quarantined evidence marked invalid. If a live run fails, stop only processes
started by the benchmark, restore its isolated project fixtures, and resume with a new run
ID from the last validated phase—never overwrite or splice the failed pair. If report logic
is wrong, fix the generator and regenerate from frozen JSON; do not hand-edit numbers. If
T3 approval is withdrawn or the cost ceiling is reached, abort before the next request,
record the bounded partial matrix, and publish a T2-only or explicitly incomplete report.

The global rollback is to leave `agentic_engine_default` unchanged on legacy, preserve both
engines, remove no user data, and omit the report link until validation passes.
