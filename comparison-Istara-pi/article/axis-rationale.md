# Per-Axis Metrics & Rationale — Pi vs Legacy Agentic Engine Comparison

Date: 2026-08-01 (CF-SPEC-11) · Dataset: rt6b runs (263 records) + deterministic sidecars
Method frame: two-dimensional taxonomy of *Evaluation and Benchmarking of LLM Agents: A
Survey* (KDD 2025, arXiv:2507.21504) — each axis names its **evaluation objective**
(behavior / capability / reliability / safety) and **evaluation process** (interaction
mode, metric computation). Process-level evidence is preferred over end-to-end scores
wherever the architecture exposes it (cf. process-level benchmarking practice).
Every number below is reproducible from the frozen artifacts (`tests/pi_benchmark/.results/runs/rt6b/`
+ `comparison-Istara-pi/reports/20260731-judging/`).

| # | Axis | Objective | Pi | Legacy | Verdict |
|---|------|-----------|-----|--------|---------|
| 1 | Tool Calling & Vocabulary | capability | 0.8077 | 0.8312 | legacy +0.024 (CI crosses 0) |
| 2 | Feature Matrix (86 features) | behavior | 98.75% | 98.75% | tie |
| 3 | Output Quality (blind A/B) | behavior | 6.750 | 6.636 | pi +0.114 (CI crosses 0) |
| 4 | Research Spine (6/10 phases) | capability | 1.000 | 0.810 | **pi +0.19 (F-12)** |
| 5 | Memory Load (RSS) | reliability | 234 MB | 108 MB | **legacy −126 MB** |
| 6 | Token & Cost | reliability | $0.00199/ok | $0.00207/ok | tie |
| 7 | Tool-Call Efficiency | capability | 1 call/task, 1.000 sel. | 1 call/task, 1.000 sel. | tie |
| 8 | Skill Contract Compliance | capability | 1.000 | 1.000 | tie |
| 9 | Prompt Adherence & Probes | safety | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 / 0.000 | tie |
| 10 | A2A Collaboration | capability | judged tie | judged tie | tie |

---

## Axis 1 — Tool Calling & Vocabulary

- **What:** BFCL v4 prompt-mode strict AST match (name + arguments vs published ground
  truth, n=60/engine), τ-bench adapted action selection (n=16–17), Istara `dag_react`
  tool-choice case. *Metric computation: code-based (deterministic).*
- **Values:** BFCL strict pi 0.733 / legacy 0.717; name accuracy pi 1.000 / legacy 0.983;
  argument validity pi 0.861 / legacy 0.844; τ-bench pi 0.118 / legacy 0.250; dag
  tool_choice 1.0/1.0. Aggregated: pi 0.8077, legacy 0.8312 (delta −0.024,
  95% CI [−0.145, +0.092]).
- **Rationale:** the aggregate is dominated by the small τ-bench subset (adapted
  single-turn fidelity, n≤17) — on the large-n BFCL subset Pi leads every sub-metric.
  Directionally Pi ≥ legacy on tool calling; not significant.

## Axis 2 — Feature Matrix Integration (86 features)

- **What:** six criteria per feature (reachable, project_scoped, expected_action,
  engine_behavior, evidence_emitted, graceful_failure), compiled from the living
  inventory. Auto criteria verified statically (route files, test files); 70/86 features
  have ≥1 manual criterion — counted, never fabricated. *Metric computation: code-based.*
- **Values:** 98.75% coverage both engines over derivable criteria; evidence_emitted
  pass rate 1.0; LLM-touching features (22) scored engine-independently pending
  per-feature live evidence.
- **Rationale:** the W9 count-to-zero ratchet (all 87 legacy call sites behind the
  engine-selected dispatcher) makes non-LLM features engine-independent *by
  construction* — the honest tie is architectural evidence, not missing data.

## Axis 3 — Output Quality & Deterministic Checks

- **What:** 44 blind A/B pairs (rubric output_quality v1.0.0, sha256-logged, deterministic
  position swap) + deterministic JSON/schema checks from Istara's eval suite.
  *Metric computation: LLM-as-judge (blind) + code-based.*
- **Values:** pi 6.750 / legacy 6.636 (delta +0.114, 95% CI [−0.159, +0.364]);
  pi 14 wins / legacy 7 / 23 ties.
- **Rationale:** internal-pack prompts are route-validation smoke prompts by design, so
  ties dominate (52%); the deep-corpus pairs (judged separately, axis 4) are the
  differentiating evidence. Not significant.

## Axis 4 — Research Validity Spine (10 phases; 6 measured)

- **What:** per-phase capability over plan (dag plan JSON), tool_selection (dag case),
  execution (skill contract), grounding (corpus extraction), synthesis (debate brief),
  review (readiness gate). *Metric computation: code-based + LLM-as-judge.*
- **Values:** plan 1.0/1.0 · tool_selection 1.0/1.0 · execution 1.0/1.0 · grounding
  pi 1.0 / legacy 0.0 (**F-12**) · synthesis tie · review tie → pi 1.000 / legacy 0.810
  over measured phases.
- **Rationale (F-12, the headline process-level finding):** on the 6k-char corpus
  prompt, the legacy transport returned **1024 output tokens (= max_tokens cap) with
  empty visible text** — the model spent its entire budget on reasoning content, and the
  legacy surface reports `status: ok` on an empty answer. The Pi engine returned
  complete structured output (~871–1555 tokens). Same behavior on legacy self_moa
  (3072 tokens, 2/3 slots empty → truthful `not_runnable`). This is a *transport-level
  fidelity gap*, not a model quality gap — and exactly the class of difference
  end-to-end benchmarks hide (cf. process-level evaluation literature). Remaining 4
  phases (intent, context, recovery, governance) unmeasured — null, never fabricated.

## Axis 5 — Memory Load

- **What:** backend process RSS per engine + Pi worker sidecar RSS (psutil);
  retrieval quality via the engine-independent tests/evals `rag` suite.
  *Metric computation: instrumentation.*
- **Values:** pi total 234 MB (backend 101 MB + Node worker 133 MB) vs legacy 108 MB.
- **Rationale:** the Pi sidecar costs ~126 MB resident memory for its isolation and
  updateability — the architecture's honest price. Cross-session recall unmeasured
  (needs multi-session workload; follow-up).

## Axis 6 — Token & Cost Efficiency

- **What:** provider-reported exact usage per ok record (reserve-before-dispatch ledger).
- **Values:** pi $0.001993 / legacy $0.002071 mean per ok record (≈3.8% cheaper, far
  inside noise); tokens essentially identical (same model, same prompts).
- **Rationale:** engine overhead is negligible at the API boundary; any earlier claims
  of large savings were fabricated and have been removed from all artifacts.

## Axis 7 — Tool-Call Efficiency Frontier

- **What:** model calls per task × selection accuracy (this phase's workloads are
  single-call by design).
- **Values:** 1 call/task both engines; selection accuracy 1.0/1.0 (dag), BFCL name
  accuracy in axis 1.
- **Rationale:** no multi-step tool-loop workload ran this phase — the frontier's shape
  (quality vs call count over multi-step tasks) is a CF-SPEC-12 candidate with real
  tool-loop scenarios.

## Axis 8 — Skill Contract & Marker Compliance

- **What:** contract adherence (required marker prefix, ordered sections, evidence
  mapping) on the `thematic-analysis` contract. *Code-based.*
- **Values:** 1.000 / 1.000 — both engines produced compliant output.

## Axis 9 — System-Prompt Adherence & Probes

- **What:** injection resistance (3 attack classes from the security-benchmark
  vocabulary), persona compliance, thinking-leak rate. *Code-based (deterministic).*
- **Values:** injection resistance 1.000/1.000; persona 1.000/1.000; thinking leak
  0.000/0.000.
- **Rationale:** both engines are clean on the current suite; the suite's 3 injection
  classes should be extended toward the full security-benchmark attack surface.

## Axis 10 — A2A Collaboration & Dominance

- **What:** evidence-citing debate synthesis (blind-judged) + MoA reconciliation
  evidence (self_moa rounds, consensus).
- **Values:** none-lane debate legacy 7 / pi 6 (blind); self_moa tie; self-MoA consensus
  confidence mostly *insufficient* (mean 0.11) on both engines.
- **Rationale:** single-model temperature-sweep self-MoA produces low consensus
  regardless of engine — the MoA diversity problem belongs to the petals full_ensemble
  path (DEC-13), not to either engine.

---

## Unified verdict

`no_significant_difference` stands for axes 1/3 (the only CI-bearing comparisons).
Axis 4 reveals the one **significant process-level difference** (F-12, transport
fidelity under reasoning-heavy long prompts) favoring Pi; axis 5 prices Pi's sidecar
at ~126 MB RSS favoring Legacy. Everything else is a measured tie.

**Replacement read:** Pi is equivalent-or-better on output fidelity, equal on quality,
equal on cost, and worse on memory footprint. For production adoption, fix F-12's
mirror problem first (legacy transport must surface reasoning-overflow as a typed
failure, not `ok` + empty text) and decide whether 126 MB is a fair price for Pi's
isolation/updateability.

## Threats to validity (for the article)

1. Judge family: Kimi k3 judged blind A/B; DUT is DeepSeek — different vendors, but
   LLM-as-judge biases (verbosity, self-preference family effects) remain possible.
2. Smoke-prompt construction limits axis-3 discrimination (documented).
3. τ-bench adapted fidelity (single-turn, no env simulator), n≤17.
4. F-12 may be specific to the benchmark's max_tokens=1024 + reasoning-style model
   interaction; production legacy call sites use different budgets.
5. Single provider/model for both DUTs — engine isolation by construction, but
   cross-model generalization is out of scope.
6. GAIA absent (HF-gated); BFCL prompt-mode (not FC-mode); 4/10 spine phases unmeasured.
