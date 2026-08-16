> > ```
> > Pi vs Legacy Benchmark Report (retake, B1–B4)
> > ```

* **Generated:** `2026-07-31T19:17:43Z`

* **Verdict:** `pending_judging` — no winner is declared before the blind judging session scores the quality axes.

* **Total Records:** `157` (Pi: `78`, Legacy: `79`)

Execution evidence is complete: status, cost/token usage, route truth, and MoA reconciliation below are real provider-reported data. Quality axes (1-5, 7-10) are pending the post-run blind judging session; no winner is declared until judged scores exist.

***

## 1. Execution Evidence (real, provider-reported)

### Status by lane and engine

| Lane            | Engine   | ok   | not\_runnable | Failure reasons     |
| --------------- | -------- | ---- | ------------- | ------------------- |
| `full_ensemble` | `legacy` | `0`  | `22`          | other×22            |
| `full_ensemble` | `pi`     | `0`  | `22`          | other×22            |
| `none`          | `legacy` | `22` | `11`          | startup\_failure×11 |
| `none`          | `pi`     | `22` | `10`          | startup\_failure×10 |
| `self_moa`      | `legacy` | `22` | `2`           | other×2             |
| `self_moa`      | `pi`     | `22` | `2`           | other×2             |

### Token & cost (exact vs estimated, never summed — A15)

| Engine     | ok records (exact) | Exact cost  | Estimated cost | Exact tokens | Mean cost / ok | Mean tokens / ok |
| ---------- | ------------------ | ----------- | -------------- | ------------ | -------------- | ---------------- |
| **Pi**     | `44`               | `$0.087706` | `$0.000000`    | `44718`      | `0.001993`     | `1016.3`         |
| **Legacy** | `44`               | `$0.091133` | `$0.000000`    | `44717`      | `0.002071`     | `1016.3`         |

Same provider/model/endpoint for both arms; per-record means are the comparable unit, not lane totals (lanes have equal unit counts).

### MoA reconciliation (AC-8: every downgrade is not\_runnable, never a success)

| Mode            | Units | Reconciled | Degraded | Not run | Mean consensus |
| --------------- | ----- | ---------- | -------- | ------- | -------------- |
| `full_ensemble` | `44`  | `0`        | `40`     | `4`     | `0.0279`       |
| `self_moa`      | `48`  | `4`        | `40`     | `4`     | `0.1102`       |

***

## 2. Quality Axes — pending blind judging

Run records intentionally carry `metrics=None`: quality scores come only from the
post-run judging session (blind A/B, position swap, rubric bank). Until then every
quality axis is null — this report never emits placeholder scores.

| Metric Axis                                                      | Pi Engine | Legacy Engine | Status            |
| ---------------------------------------------------------------- | --------- | ------------- | ----------------- |
| 1. Tool Calling & Vocabulary                                     | —         | —             | `pending_judging` |
| 2. Feature Matrix Integration (86 features: 16 auto / 70 manual) | —         | —             | `pending_judging` |
| 3. Output Quality & Deterministic Checks                         | —         | —             | `pending_judging` |
| 4. Research Validity Spine (10 phases)                           | —         | —             | `pending_judging` |
| 5. Memory Cross-Session Recall                                   | —         | —             | `pending_judging` |
| 7. Tool Call Efficiency Frontier                                 | —         | —             | `pending_judging` |
| 8. Skill Contract & Marker Compliance                            | —         | —             | `pending_judging` |
| 9. System-Prompt Adherence & Probes                              | —         | —             | `pending_judging` |
| 10. A2A Collaboration & Dominance                                | —         | —             | `pending_judging` |

***

## 3. Threats to Validity & Reproducibility

1. **Single provider/model:** both arms ran on the same approved DeepSeek route, so engine differences are isolated from model differences; judge = DUT model (role-separated, blind, position-swapped) — residual self-judge bias is a known limitation.
2. **Legacy arm DUT identity (F-11, OPEN Blocker):** benchmark legacy units dispatch through the benchmark-isolated approved provider adapter (F-10) — a single raw completion, NOT the production legacy ReAct loop through `AgenticDispatcher.ensemble`. The F-11 delta re-review (2026-07-23, L-66) ruled this breaks the legacy DUT identity required by Plan C. **All `legacy ok` records in this bundle are therefore a raw single-completion cost/latency baseline, not measurements of Istara's legacy agentic loop.** A valid paired verdict requires the F-11 fix (legacy arm routed through the dispatcher onto a benchmark-seeded registry endpoint) and re-dispatch of the legacy units.
3. **full\_ensemble lane:** with one approved endpoint, multi-endpoint ensembles are structurally degraded and counted `not_runnable` by design (AC-8) — multi-model ensembles are untested in this run.
4. **Order bias:** paired runs record arm order (`legacy_first` vs `pi_first`).
5. **Reproducibility:** two invocations over identical run sets produce byte-identical `scorecard.json`.

