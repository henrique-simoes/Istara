# Pi benchmark role-correction planning brief

This is a planning correction for the Pi benchmark lifecycle only. Do not edit the
master plan and do not change Istara production routing.

## Authoritative role separation

1. DUT/evaluation: the benchmark runs Istara's original agentic loop and the Pi
   adaptation against the same scenario inputs and compares their captured behavior.
2. Evaluation backend: live model calls made by either Istara arm use the configured
   DeepSeek API route under the existing cumulative `$1.00` cap. The benchmark runner
   must exercise Istara's API/dispatcher; it must not call DeepSeek directly as a
   substitute for Istara.
3. MoA: self-MoA and full-ensemble behavior are properties of Istara's existing
   dispatcher/validation path. The benchmark records requested versus served route
   identity and marks downgrades as degraded/blocked, without changing production
   defaults.
4. Judging: after B0 and B1…B_N are terminal, launch a separate Build Stream
   Conductor session over durable benchmark artifacts. Kimi is the intended judge
   harness/model for that session. The judge scores captured results and creates
   `report.md`, `report.html`, `scorecard.json`, and per-judgment outputs; it must not
   rerun the DUT or make new benchmark-provider calls.
5. BSC implementation/review workers are orchestration infrastructure, not DUT or
   judge evidence unless explicitly assigned to the post-run judging session.

## Required correction

Reconcile `docs/build-stream/2026-07-22-pi-benchmark.md` and the Pi benchmark work-order
so they use these exact roles consistently. Preserve the `$1.00` evaluation ledger,
`max_processes=N`, immutable manifest, resumable B1…B_N waves, and existing production
Istara model-selection behavior. Remove ambiguous language that calls Kimi the DUT
provider or DeepSeek the judge. Append a decision/ledger entry explaining the correction.

## Acceptance

- The lifecycle clearly says what is evaluated, what provider serves the DUT calls, and
  what the post-run judge does.
- The work-order gives the same role separation to every future Conductor worker.
- The plan lists evaluation packs: canonical 15-scenario contract coverage, feature
  breadth, Research Spine lifecycle, A2A collaboration, prompt/injection probes,
  usage/cost accounting, and MoA route/downgrade evidence.
- No backend/frontend production file is changed.
- Verify with `git diff --check` and a scoped diff/path audit.
