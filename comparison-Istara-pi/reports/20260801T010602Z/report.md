# Pi vs Legacy Benchmark Report (retake, B1–B4)

- **Generated:** `2026-08-01T01:07:38Z`
- **Verdict:** `no_significant_difference` — no winner is declared before the blind judging session scores the quality axes.
- **Total Records:** `283` (Pi: `142`, Legacy: `141`)

Judged axes: Tool Calling & Vocabulary: pi 0.8077 vs legacy 0.8312 (delta -0.026, CI [-0.1429, 0.0909]); Output Quality & Deterministic Checks: pi 6.75 vs legacy 6.6364 (delta 0.1136, CI [-0.1591, 0.3636]); Research Validity Spine (10 Phases): pi 1.0 vs legacy 0.8095 (delta None, CI None); Skill Contract & Marker Compliance: pi 1.0 vs legacy 1.0 (delta 0.0, CI None); A2A Collaboration & Dominance: pi 1.0 vs legacy 1.0 (delta 0.0, CI None). Execution evidence (cost, status, MoA, routes) is provider-reported; deterministic industry scores (BFCL/τ-bench) feed axis 1.

---

## 1. Execution Evidence (real, provider-reported)

### Status by lane and engine

| Lane | Engine | ok | not_runnable | Failure reasons |
|---|---|---|---|---|
| `none` | `legacy` | `112` | `0` | — |
| `none` | `pi` | `110` | `4` | other×4 |
| `self_moa` | `legacy` | `27` | `2` | other×2 |
| `self_moa` | `pi` | `27` | `1` | other×1 |

### Token & cost (exact vs estimated, never summed — A15)

| Engine | ok records (exact) | Exact cost | Estimated cost | Exact tokens | Mean cost / ok | Mean tokens / ok |
|---|---|---|---|---|---|---|
| **Pi** | `137` | `$0.180548` | `$0.000000` | `105367` | `0.001318` | `769.1` |
| **Legacy** | `138` | `$0.184309` | `$0.000307` | `112400` | `0.001336` | `814.5` |

Same provider/model/endpoint for both arms; per-record means are the comparable unit, not lane totals (lanes have equal unit counts).

### MoA reconciliation (AC-8: every downgrade is not_runnable, never a success)

| Mode | Units | Reconciled | Degraded | Not run | Mean consensus |
|---|---|---|---|---|---|
| `self_moa` | `57` | `5` | `50` | `1` | `0.1245` |

---

## 2. Quality Axes — blind judging results

Axes marked `judged` carry real scores: deterministic BFCL/τ-bench ground-truth scoring
(axis 1) and the Kimi blind A/B session (axis 3; position-swapped, rubric v1.0.0).
Remaining axes are null until their judged/probe evidence exists — never placeholders.

| Metric Axis | Pi Engine | Legacy Engine | Delta [95% CI] | Status |
|---|---|---|---|---|
| 1. Tool Calling & Vocabulary (BFCL strict + τ action) | `0.8077` | `0.8312` | `-0.026` `[-0.1429, 0.0909]` | `judged`
| 2. Feature Matrix Integration (86 features: 16 auto / 70 manual) | — | — | — | `measured` |
| 3. Output Quality & Deterministic Checks (blind A/B) | `6.75` | `6.6364` | `0.1136` `[-0.1591, 0.3636]` | `judged`
| 4. Research Validity Spine (10 phases) | — | — | — | `judged` |
| 5. Memory Cross-Session Recall | — | — | — | `pending_judging` |
| 7. Tool Call Efficiency Frontier | — | — | — | `measured` |
| 8. Skill Contract & Marker Compliance | — | — | — | `judged` |
| 9. System-Prompt Adherence & Probes | — | — | — | `measured` |
| 10. A2A Collaboration & Dominance | — | — | — | `judged` |

**Verdict:** `no_significant_difference` — Judged axes: Tool Calling & Vocabulary: pi 0.8077 vs legacy 0.8312 (delta -0.026, CI [-0.1429, 0.0909]); Output Quality & Deterministic Checks: pi 6.75 vs legacy 6.6364 (delta 0.1136, CI [-0.1591, 0.3636]); Research Validity Spine (10 Phases): pi 1.0 vs legacy 0.8095 (delta None, CI None); Skill Contract & Marker Compliance: pi 1.0 vs legacy 1.0 (delta 0.0, CI None); A2A Collaboration & Dominance: pi 1.0 vs legacy 1.0 (delta 0.0, CI None). Execution evidence (cost, status, MoA, routes) is provider-reported; deterministic industry scores (BFCL/τ-bench) feed axis 1.

---

## 3. Threats to Validity & Reproducibility

1. **Single provider/model:** both arms ran on the same approved DeepSeek route, so engine differences are isolated from model differences; judge (Kimi k3) is not the DUT model provider but shares the vendor family — residual judge-family bias is a known limitation; blind A/B with deterministic position swap mitigates position bias.
2. **Legacy arm DUT identity (F-11, FIXED in CF-320):** legacy units in this bundle dispatch through `AgenticDispatcher.ensemble` onto the benchmark-seeded registry node — the production legacy loop (registry selection → openai-compat transport), verified by route evidence `benchmark-deepseek-registry` and exact provider usage on every record.
3. **Internal-pack prompts are route-validation smoke prompts**, not deep scenario workloads: axis-3 quality differences are small by construction (23/44 pairs tied). BFCL/τ-bench (axis 1) is the stronger differentiator in this bundle.
4. **full_ensemble lane:** with one approved endpoint, multi-endpoint ensembles are structurally degraded and counted `not_runnable` by design (AC-8) — multi-model ensembles are untested here (petals bridge P3 targets this).
5. **τ-bench fidelity:** adapted single-turn (no env/user simulator); small n (16-17). Treat τ scores as directional only.
6. **Order bias:** paired runs record arm order (`legacy_first` vs `pi_first`).
7. **Reproducibility:** two invocations over identical run sets produce byte-identical `scorecard.json` (modulo `generated_ts`).
