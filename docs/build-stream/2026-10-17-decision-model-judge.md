# Decision-model judge layer (JEV primary, universal decider interface)

## Status Block

<!-- STATUS BLOCK -->
```yaml
item: decision-model-judge
branch: feat/decision-model-judge
cf: { spec: CF-SPEC-1, tasks: [CF-2, CF-3, CF-4] }
phase: "Phase 2 — trajectory store + calibration gate"
stage: S5-ship
status: blocked
blocked_on: "owner — push of feat/decision-model-judge for Phase 2 (3821e1c8 and the lifecycle commit); CI must run test_decision_trajectory_store.py and the alembic 035 test, which cannot run locally"
last: { agent: claude-code, at: 2026-10-18T03:04:42Z, ledger: L-11 }
next_action: "After the owner approves: push, dispatch ci.yml, read backend-format/backend-lint/backend-test (strict lint covers only the last commit's files on dispatch, CI-2); if green, finish CF-4, mark Phase 2 done, start Phase 3 (assurance modes)."
```
<!-- /STATUS BLOCK -->

## Plan overview

### Problem

The owner's specialization thesis (Simões & Ramires, 2026, *Avaliando orquestração multiagente e
multimodelo local e de fronteira*) formalizes a four-layer evaluation stack for Istara (Tabela 4):

| Layer | Mechanism | Criterion | Role |
|---|---|---|---|
| 1 Deterministic | code rules, schemas, invariants | JSON Schema, types, exact spans | free first filter |
| 2 **Typed decider** | closed-space classification, one pass | **ECE, Brier, threshold τ** | high-volume triage of transitions and evidence |
| 3 Generative judge | LLM semantic review | coherence/depth rubrics | exploratory opinion, **no isolated veto** |
| 4 Human | senior researcher adjudication | abstentions and audit | final approval of findings |

Layers 1, 3 and 4 exist (`finding_grounding.py` and the coder quote check; `validation_executor.py`;
`ReconciliationDecision` + Done-task gating). **Layer 2 does not exist anywhere in the code**: no
typed decider, no selective abstention, no ECE/Brier calibration gate. The thesis lists this as its
sixth limitation ("formalizado, mas sua medição empírica no Istara ainda está em implementação").

### Outcome

Istara gains a provider-neutral typed-decider layer. A decider maps (task context, item state,
rubric) to a probability vector over a closed decision set Y (thesis Eq. 5–6). Istara recomputes
and calibrates confidence itself, takes the minimum-Bayes-risk decision under an asymmetric loss
(Eq. 7), abstains to human review below a pre-registered τ (Chow, Eq. 8), and trusts a decider
version only after it passes a calibration gate (ECE Eq. 9, Brier + Murphy decomposition Eq. 10).
**JEV (TypeSafe, hosted API) is the primary decider.** Open-weight decision models plug into the
same interface.

### Thesis invariants (non-negotiable, cited)

1. **Triage, never authority.** A decider never accepts, promotes, or reports evidence. Its only
   powers are *route to human review*, *set review priority*, and *raise a blocking flag*. Promotion
   stays with reliability (κ ≥ 0.60), reconciliation, and Human-Approved Done
   (`research-validity-contract.md`).
2. **Not an independent coder.** Rao & Callison-Burch (2026) found typed-decider errors correlate
   with generative judges' errors on the same ambiguous items, so the Condorcet assumption fails.
   Decider verdicts are never entered into the Fleiss/Krippendorff matrix and never count as a rater.
3. **Calibration is an acceptance criterion** (thesis, "Calibração de probabilidades"). An
   uncalibrated or unmeasured decider version is untrusted. An untrusted decider runs in **shadow
   mode**: verdicts are recorded and labelled `untrusted`, with no routing effect, so behaviour is
   exactly today's (DEC-2). A decider can only add review routing, never relax a gate, so shadow
   mode is the fail-closed state.
4. **Asymmetric costs.** C_FP (hallucination promoted as evidence) ≫ C_FN (valid inference sent to
   an analyst). τ* = C_FP / (C_FP + C_FN); multiclass reject when 1 − ĉ(x) > C_R / C_E.
5. **Calibration is per language and domain** (Laya's Khmer result: accuracy 0 at mean confidence
   0.952). Trust is scoped to (provider, *versioned* model, task family, language).
6. **Blind and order-inverted** (thesis LLM-as-judge protocol). Choice options are evaluated in two
   orders, and disagreement is an abstention.
7. **Separate execution status from delivered result** (axis-4 finding). An empty or failed decider
   call is `not_runnable`, never a verdict.

### JEV contract (from docs.typesafe.ai, read 2026-10-17)

- `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer`. Body: `{state, model,
  questions: {id: {type: choice|score|noul, instructions, criteria}}}`. Choice ≤ 255 options; score
  2–10 ordered levels; noul returns P(yes) only.
- Response: `model` (the versioned id that answered), `answers[id]` with `probabilities` (sum 1) and
  `confidence` for choice/score, `usage.input_tokens/output_tokens`. Errors: 400
  `max_tokens_exceeded`, 401, 413, 415, 422, 429/529 (backoff, honor `retry-after`).
- Models: `jev-1.13.0` (`jev-latest`), `jev-1.14.0` (`jev-preview`), 64k per request / 32k per
  question, billed on input tokens only. **Aliases move, so thresholds tuned on one version must pin
  the versioned id** (Models page).
- Confidence is a statistic of the distribution, not a calibration guarantee. Choice:
  (p_max − 1/n)/(1 − 1/n); score: 1 − Σp_i|i−m| / MAD_unif; noul: none (|2p−1| suggested). There are
  no temperature or abstain parameters, so calibration and abstention are the client's job, which is
  where the thesis puts them.
- Documented jaggedness (jev-1.13): literal reading, no arithmetic/counting/dates, context rot on
  large state, steerable by adversarial state, **first-option bias in Choice**, English-primary.
  Design consequences: atomic questions; arithmetic in code; filtered state; untrusted-content
  wrapper; option-order permutation (invariant 6); language-scoped trust (invariant 5).
- Privacy: no training on customer data; zero data retention only on enterprise contracts. **Sending
  source spans to JEV is cloud egress of research data** (owner decision D1).
- The citation-check cookbook (string match, then one Choice supports / contradicts / says_nothing,
  then a confidence gate to a human) is the same shape as Istara's layer 1 → layer 2 → layer 4.

### Universal interface (decided shape, subject to S1 design)

The System One wire contract is the canonical internal representation. It has become the de facto
standard: Kev-4B, Laya and OpenJev serve it, and llama.cpp merged a `/v1/systemone` server
endpoint (ggml-org/llama.cpp#29818, 2026-10-02; GGUFs: Laya, Julia-1, Lev, OpenJev, Kev-4B).

```
DecisionRequest(state, questions: {id: Choice|Score|Noul}, subject_handle, task_family, language)
      │
      ▼
DeciderAdapter  ── systemone_http   → TypeSafe JEV (primary) · llama.cpp server · Kev · Laya · OpenJev · Standard One
                ── openai_decisions → POST /v1/decisions (public beta)
                ── openrouter / cloudflare_workers_ai → hosted JEV and Clef
                ── (later) local encoders: GLiNER2.5-Decide, Von, Laya via transformers
      │   returns the FULL probability vector + served versioned model id + usage
      ▼
Istara core (provider-independent)
   confidence recompute → temperature scaling (fit per trust scope) → Bayes risk (loss matrix)
   → Chow reject (τ) → order-permutation consistency → DecisionRecord (content-free telemetry)
```

**Admissibility rule.** An adapter that cannot return the full probability vector, or cannot report
the served model identity, is not a typed decider and is refused at registration. Without the vector
there is nothing to calibrate (thesis Eq. 6–10). Without the served identity, the receipt rule in
the spine contract (served model ≠ requested model is a provenance failure) cannot hold.

### Decision space Y (first slice)

`grounded_evidence` · `speculative_inference` · `factual_hallucination` ·
`methodological_violation` (thesis, "Modelos de decisão tipados"). This is asked as atomic questions,
not one compound one: a Choice over relation-to-span (supports / contradicts / says_nothing), a Choice
over epistemic status (fact / inference / hypothesis / recommendation, from Tabela 3 "Qualidade de
síntese"), and Nouls for codebook inclusion/exclusion criteria. Code maps the answers to Y.

### Goal / non-goals

- **Goal:** layer 2 implemented end to end for one spine seam, with JEV as the primary decider, at
  least one open-weight decider proven through the same interface, a calibration trust gate, human
  routing of abstentions visible in the UI, and **onboarding**: general Istara onboarding plus a
  first-activation flow that teaches what a decision model is and where to configure the JEV API or
  a local decision model (DEC-1).
- **Goal (expansion, DEC-3):** every decision is stored as a content-free *decision trajectory*
  joined to its later human label, and that history feeds recalibration, ReasoningBank lessons,
  governed self-evolution proposals and autoresearch, without self-confirmation (research doc §6).
  Users choose an *assurance mode* (LLM judges only, decision models only, both, or none). Deciders
  and judges share one ensemble-health error model (calibration, error correlation, J_eff).
  Autoresearch defects AR-1…AR-8 and AV-1 are fixed, and a `decision_policy` runner is added. The
  mathematics and references are documented for publication
  (`docs/scientific_audit/decision-model-judge-research.md`, `decision-model-references.md`,
  `autoresearch-hill-climbing-audit.md`).
- **Non-goals:** deciders accepting or promoting anything; deciders as κ raters or as replacements
  for the formal coding-run coders (pending Q1); confidence raised by past agreement outside the three
  channels in research doc §6.3; vote-merging deciders and judges into an automatic verdict;
  fine-tuning a decider; desktop UI coverage (CI has none, per AGENTS.md §6).

### Appetite

Five phases, each independently shippable behind `ISTARA_DECIDER_ENABLED` (default off). The first
three phases make no product-path change.

### Phases

| # | Phase | Goal | Acceptance (Given/When/Then) | Verification | Status |
|---|---|---|---|---|---|
| 0 | Math core | pure, network-free math: confidence recompute, temperature scaling, Bayes risk + Chow, order-flip merge, ECE (plain and Horvitz–Thompson weighted), Brier + Murphy, n_eff, cross-fitted T fit, Beta reliability posterior (lower bound), Learn-then-Test τ, Dawid–Skene EM, pairwise error correlation + Yule's Q + J_eff | **Given** the JEV docs' worked examples (choice 0.9/0.06/0.04 → 0.85; score 0/0.57/0.43 → ≈0.35) and hand-computed fixtures for every estimator, **when** the core runs, **then** it reproduces them to 1e-9; τ* = C_FP/(C_FP+C_FN); temperature scaling preserves argmax and lowers held-out ECE on a miscalibrated fixture; LTT never returns τ below τ*; Dawid–Skene recovers planted confusion matrices on synthetic data | `pytest tests/test_decision_math.py -q` | done |
| 1 | Adapter + JEV | `systemone_http` adapter (TypeSafe JEV primary; llama.cpp / Kev / Laya / Standard One compatible), registry, admissibility rule (full probability vector + served versioned id), secrets in Keychain/env, per-project egress authorization | **Given** a stub `/v1/systemone` server, **when** Istara decides, **then** the request matches the JEV schema, the served versioned id is recorded, aliases are refused for trusted scopes, 429/529 back off honoring `retry-after`, 400 `max_tokens_exceeded` / empty / partial answers are `not_runnable`, a missing probability vector refuses registration, and a project without opt-in never reaches the hosted endpoint | `pytest tests/test_decider_adapter.py tests/test_decider_registry.py -q`; `python3 scripts/security_benchmark.py --fail-on-threshold` | done |
| 2 | Trajectory store + calibration gate | `DecisionTrajectory` (alembic, content-free handles, §5 of the research doc), versioned human-label mapping from `ReconciliationDecision` / review outcomes / `classify_review_feedback`, blind random audit sampling (rate ρ, propensity π), `app.evals.decision_eval` trust gate per scope with cross-fitting, shadow mode (DEC-2) | **Given** labelled trajectories with a known audit design, **when** a scope is evaluated, **then** weighted ECE/Brier/κ/order-flip/risk–coverage are reported on held-out folds, `trusted` requires n_eff ≥ 50 and the DEC-1 ceilings, audit items hide the decider verdict from the reviewer, and an untrusted scope has no routing effect | `pytest tests/test_decision_trajectory.py tests/test_decision_eval.py -q` | in-progress |
| 3 | Assurance modes | project-level assurance policy (`auto`, `llm_judges`, `decision_models`, `both`, `none`) honoured by `validation.py` and `validation_executor.py`; Self-MoA stays the single-endpoint fallback; AV-1 fix (reward = human outcome, Thompson sampling constrained to the mode); research-validity contract + governance contract + ensemble-method matrix updated | **Given** each mode, **when** a task is validated, **then** only the evaluators the mode allows are called (dispatcher call log proves no LLM-judge call in `decision_models` mode), `none` marks the task `unvalidated` and still requires human review, outputs from `both` are shown side by side and never vote-merged, and the coding-run reliability gate is unchanged in every mode | `pytest tests/test_assurance_modes.py tests/test_adaptive_validation.py tests/pi_production/test_w7_validation.py tests/test_research_validity_contract.py -q` | planned |
| 4 | Spine seam (code applications) | decider triage after the deterministic quote check; routing and priority into `CodeReviewQueue`; trajectory written per application | **Given** a governed coding run, **when** applications are admitted, **then** each gets a trajectory; with a trusted scope, abstentions and `factual_hallucination` / `methodological_violation` route to review with priority; no acceptance state changes because of the decider; κ inputs are byte-identical with the decider on vs off; telemetry is content-free | `pytest tests/test_research_validity_contract.py tests/test_code_applications.py tests/test_decision_spine_seam.py -q`; credential-free simulation scenario with a stub decider; UI walk | planned |
| 5 | Learning loop + ensemble health | ReasoningBank `decision_review` lessons (aggregate, content-free, after human label only); scheduled recalibration with cross-fitting; CUSUM drift → shadow; self-evolution proposals for question sets and τ overrides via improvement governance (protected values excluded); ensemble health shows per-evaluator calibration, error correlation, Yule's Q, J_eff, Dawid–Skene reliabilities | **Given** a history of labelled trajectories, **when** the loop runs, **then** lessons cite only handles, a recalibration changes T only if held-out ECE improves, drift returns a scope to shadow with a recorded reason, governance refuses proposals that touch κ ≥ 0.60 / the ECE ceiling / n_min / the never-promote rule, and Ensemble Health renders the new metrics in all roles, light/dark, 375px, keyboard | `pytest tests/test_decision_learning_loop.py tests/test_spine_learning_loops.py tests/test_meta_hyperagent.py -q`; ensemble-health scenario; UI walk | planned |
| 6 | Autoresearch | fix AR-1…AR-8 (each with a failing regression test first); new `decision_policy` runner (objective: held-out weighted Brier, coverage at fixed risk); decider `score` as an optional measurement instrument per assurance mode; judges pinned away from the endpoint under test | **Given** a deterministic fake runner with known noise, **when** the loop runs, **then** a candidate whose true effect is zero is kept at most at the nominal error rate, the incumbent is re-measured paired, failed measurements are `not_runnable` (never 0.5), `mutation_diff` persists, and a `decision_policy` experiment stays a governed proposal | `pytest tests/test_autoresearch_engine.py tests/test_autoresearch_statistics.py tests/test_decision_policy_runner.py tests/pi_production/test_w6_engine_selection.py -q` | planned |
| 7 | Onboarding + configuration UX | general Istara onboarding and first-activation flow for decision models (DEC-1): what a decision model is (closed answers in, label + probabilities out; triage, never authority), when it helps, cloud-egress consequences, where to configure the JEV API key and endpoint or a local `/v1/systemone` server, per-project opt-in, assurance-mode selection, trust status (shadow / calibrating / trusted) and how calibration works | **Given** a new install, **when** the user goes through onboarding, **then** decision models and assurance modes are introduced with skippable guidance and no decider is enabled; **given** a project with none configured, **when** the user first opens decision-model settings, **then** a first-activation flow explains the concept, the egress choice and the two configuration paths, stores the key only in Keychain/env, never enables egress without explicit project opt-in, and shows trust status; walked by role (admin/researcher/viewer), light/dark, 375px, keyboard; empty/loading/error states | new + updated simulation scenarios (onboarding, settings, `09`/`90` sweeps); `python3 scripts/feature_docs.py --seed-missing --generate-site --check`; `python3 scripts/check_a11y_contrast.py`; UI walk with screenshots | planned |
| 8 | More adapters, trajectory audit, further integrations | OpenAI Decisions / OpenRouter / Cloudflare adapters; per-transition (s,a,o) tool-call audit (Wang & Gao; benchmark axes 1, 4, 9); integrations I4–I14 (all four groups, DEC-4); decider-coder research arm on the canonical corpus with human gold codes, never counted in the gate (DEC-6, research doc §13); live runs only with owner permission | **Given** each adapter's stub, **then** it passes the shared adapter conformance suite; trajectory audit flags schema-invalid calls and observations that do not support the next state | `pytest tests/test_decider_conformance.py tests/test_trajectory_audit.py -q`; live calibration run **only with owner permission** (AGENTS.md §9) | planned |
### Doc impact

Research write-ups (new, this frame): `docs/scientific_audit/decision-model-judge-research.md`,
`docs/scientific_audit/decision-model-references.md`,
`docs/scientific_audit/autoresearch-hill-climbing-audit.md`. Living docs updated per phase:
`docs/scientific_audit/ensemble-method-matrix.md` and `bibliography-audit.md` (Phase 3/5), the
governance contract (Phase 5), and the autoresearch feature docs (Phase 6).

`docs/architecture/research-validity-contract.md` (new "Typed decision layer" section + telemetry
taxonomy `decider.*`), `docs/architecture/self-improvement-governance-contract.md` (deciders cannot
learn from raw success), `Tech.md`, `security/control_matrix.json` + `SECURITY_BENCHMARK.md`
(new provider credential and egress), `TESTING.md`, `docs/features/` (`feature_docs.py`), personas if
agent tools change, glossary entries (ECE, Brier, selective classification).

### Rollback

Feature flag off restores today's behaviour exactly. `DecisionRecord` is an additive table (one
alembic migration, reversible). No existing state machine changes meaning.

### Top risks

| Risk | Mitigation |
|---|---|
| Research data egress to a third party | per-project authorization, default deny; local open-weight decider as the egress-free path (D1) |
| Decider silently gaining veto or promotion power | invariant 1 enforced by a guard test: acceptance state unchanged with the decider on vs off |
| Calibration drift on a JEV alias move | pin versioned ids; a new version starts untrusted |
| Portuguese and other non-English research | trust scope includes language; thesis future work names PT calibration explicitly |
| Prompt injection through source spans | untrusted-content wrapper in `state`; adversarial fixtures in the calibration set |
| Correlated errors with the generative judge | decider never counted as an independent rater; disagreement between layers is a review signal |

## Open questions (expansion)

- **Q1 Coding-run coders.** Decided (DEC-6): research arm only. Does "decision models only" also apply to the formal coding-run
  reliability gate (three or more distinct LLM coders, Fleiss/Krippendorff)? Recommended: no.
  Assurance modes govern operational validation and reconciliation assistance; coders stay LLMs,
  because a decider is not an independent rater (Invariant 2, [R6]).
- **Q2 Integration breadth.** Which integration points beyond I1–I3 (research doc §11) belong in this
  plan's Phase 8, and which become their own plans?
- **Q3 Audit rate ρ.** The share of non-routed items sent to blind human review to keep calibration
  unbiased. Recommended: 10% (adds reviewer load in proportion).
- **Q4 Where publication docs live.** Recommended: `docs/scientific_audit/` (public with the repo),
  as drafted.
- **Q5 Model id in the ledger.** Build-stream asks for a model id per ledger entry; the owner's global
  rule forbids writing it without permission. Entries use `claude-code` until the owner decides.

## Owner decisions (closed by DEC-1)

- **D1 Egress.** Decided (DEC-1): per-project opt-in, default deny. When off, the configured local
  decider is used; if none is configured the layer is inactive. Never a silent fallback.
- **D2 First seam.** Decided (DEC-1): code applications (Phase 3) first, trajectory audit in Phase 4.
- **D3 Thresholds.** Decided (DEC-1), pre-registered defaults, overridable by governed project policy:
  C_FP:C_FN = 9:1 → τ* = 0.90; ECE ceiling 0.05; Cohen κ vs labels ≥ 0.60 (matches the existing
  judge-validation rule); minimum 50 labelled items per trust scope; order-flip disagreement ≤ 5%.
- **D4 Open-weight reference.** Decided (DEC-1): **no default local decider.** Users who want one are
  guided through onboarding (Phase 4). Kev-4B via llama.cpp `/v1/systemone` is the documented
  example; OpenJev is flagged for its reported CC BY-NC licence.

## Decision log

DEC-1 | 2026-10-17 | S0-frame | owner
Context: S0 frame for CF-SPEC-1, four open decisions (D1–D4).
Decision: Frame approved. D1 per-project opt-in for JEV egress, and **onboarding (general Istara onboarding and first activation) must cover decision models**. D2 code applications first. D3 proposed defaults (τ* = 0.90 from 9:1, ECE ≤ 0.05, κ ≥ 0.60, ≥ 50 items per scope, order-flip ≤ 5%). D4 no default local decider; onboarding teaches what a decision model is and where to configure the API or a local model, for optimal UX.
Why: owner's answers, 2026-10-17. The onboarding requirement became roadmap Phase 4; trajectory audit moved to Phase 5.

DEC-2 | 2026-10-17 | S0-frame | claude-code
Context: With no default decider (D4), "untrusted → every item abstains to human" would flood the review queue as soon as an uncalibrated decider is configured, and would change today's behaviour.
Decision: An untrusted or unconfigured decider runs in shadow mode: verdicts recorded and labelled, no routing effect. Only a trusted decider in an opted-in project may add review routing or priority.
Why: A decider can only add review routing and never relax a gate, so shadow mode is the fail-closed state, and the feature-flag-off rollback stays exact. Rejected: all-abstain (floods human review, defeats the thesis's aim of concentrating the review budget on real uncertainty).

DEC-3 | 2026-10-17 | S0-frame | owner
Context: After DEC-1 the owner extended the request: store decisions and their human outcomes as trajectories for ReasoningBank and self-evolution; document the mathematics and every reference for articles and the thesis revision; reduce hallucinations from deciders and LLM judges inside ensemble health; add user-selectable assurance modes (LLM judges only, decision models only, both); put deciders into autoresearch hill climbing and audit that loop; survey the architecture for further integrations; prefer the compass-forge skill over AGENTS.md for CF usage.
Decision: Frame expanded to nine phases (0 math core … 8 further integrations). Build-stream hard stop 3 (S0 goal change) returns the plan to S0 until the owner approves and answers Q1–Q5.
Why: owner request, 2026-10-17. Research basis in `docs/scientific_audit/decision-model-judge-research.md`.

DEC-4 | 2026-10-17 | S0-frame | owner
Context: Answers to Q2, Q3 and Q5 (Q1 is still open; the owner asked for research first, now in research doc §13).
Decision: Q2: Phase 8 includes all four integration groups: claim checks + spine.verify/self_check (I4–I6), trajectory audit (I8), interviews + reports (I7, I9), routing + guardrails (I11–I14; I14 runs the security benchmark). Q3: blind audit rate ρ = 10%. Q5: the model id may appear in this plan's ledger and decision log only, never in code, commits or PRs.
Why: owner's answers, 2026-10-17.

DEC-5 | 2026-10-17 | S0-frame | claude-opus-5-5
Context: Q4 (where the publication docs live) was proposed with a default and not objected to.
Decision: Keep them in `docs/scientific_audit/` (public with the repo), indexed in its README.
Why: That folder already holds the bibliography audit and ensemble-method matrix, which these documents extend.

DEC-6 | 2026-10-17 | S0-frame | owner
Context: Q1, after the research in research doc §13 (deductive coding is mechanically feasible; no peer-reviewed evaluation of typed decision models for qualitative coding was found; independence concerns [R6, R17]).
Decision: Decider coding enters as a research arm only: deciders code alongside the LLM coders on the canonical corpus with human gold codes, reporting per-code calibration, risk–coverage, error correlation, and κ/α with and without the decider. Decider codes are never counted in the reliability gate. Any spine change is decided later from that evidence.
Why: owner's answer, 2026-10-17. Keeps Invariant 2 intact while producing the evidence a spine change would need.

DEC-7 | 2026-10-17 | S1-plan | claude-opus-5-5
Context: Phase 0 design and execution choices.
Decision: (1) Stdlib-only package `backend/app/core/decision/` in the style of `app/evals/stats.py`. (2) Temperature scaling on log-probabilities with a 1e-12 floor, because hosted deciders return no logits. (3) Exact binned Brier decomposition with Stephenson et al.'s within-bin terms. (4) J_eff caps negative correlation at zero. (5) Learn-then-Test takes iid labelled pairs; stratum assembly belongs to Phase 2. (6) `DawidSkeneResult` exposes its log-likelihood trace and documents that three binary evaluators are barely identifiable. (7) Local verification on Python 3.9 with a stdlib runner, because the owner forbids installs here and on the Mac Studio (2026-10-17) and neither host has Python ≥ 3.11, pytest, ruff or Docker; the code avoids 3.10+ runtime syntax so the same tests run in CI on 3.12.
Why: (1)–(5) per the Phase 0 design section; (6) the planted three-evaluator test showed EM converging to biased estimates (prior 0.59 vs 0.65), while five evaluators recovered within 0.04 with a monotone likelihood, so the implementation is right and the limitation is statistical; (7) the owner's instruction.

DEC-8 | 2026-10-17 | S2-execute | claude-opus-5-5
Context: `gate after --task CF-3` reported two new Python import cycles caused by the decider package `__init__` re-exporting from `client`, while `client` and `registry` import their siblings through the package.
Decision: The package `__init__` holds only a docstring; `open_decider` and `authorized_hosted_endpoint_ids` move to `app/core/decider/access.py`; callers import submodules directly.
Why: It removes the cycles rather than suppressing them, and makes `access.open_decider` visibly the single entry point. Rejected: suppressing the cycle, or lazy imports inside `__init__`, which would hide the coupling.

DEC-9 | 2026-10-18 | S1-plan | claude-opus-5-5
Context: The roadmap named the trust gate `app.evals.decision_eval`.
Decision: The gate lives in `app/core/decision/trust.py`, with persistence in `app/services/decision_trajectories.py`.
Why: Phase 4 routing reads trust at request time, while `app/evals/` holds offline measurement harnesses. Same contract and tests, different module.

DEC-10 | 2026-10-18 | S2-execute | claude-opus-5-5
Context: Testing the gate on planted data showed a perfectly calibrated decider with weak discrimination (latent spread 2: accuracy 0.77, κ 0.55) is refused on κ, while spread 4 (accuracy 0.87, κ 0.74) is trusted.
Decision: Keep κ ≥ 0.60 as a separate requirement from ECE (DEC-1 unchanged). The trust tests use spread 4 for an informative decider and keep spread 2 as an explicit "calibrated but not good enough" case.
Why: The thesis asks for calibrated *and* useful triage; a calibrated coin flip should not route research items. This is documented in research doc §4 for the article.

## Ledger

### L-1 | 2026-10-18T00:10:18Z | S0-frame | claude-code | framer | —
Did: Read the thesis PDF (30 pp., text via PDFKit), `research-validity-contract.md`, `answer_eval.py`,
`validation_executor.py`, `finding_grounding.py`; JEV docs (API, models, confidence, state,
jaggedness, citation-check cookbook, AI primer, legal); open decision-model landscape. Registered the
local Compass Forge project (`init`), refreshed the index (`graph_usable: true`), ran impact on the
five seams, created CF-SPEC-1. Wrote this frame.
Result: Layer 2 is absent from the codebase. The System One contract is the universal IR. Four owner
decisions are open (D1–D4).
Verified: `compass-forge index status` → `graph_usable: true`; `intelligence impact` on
`validation_executor.py` and `answer_eval.py` → resolved/complete/high; on
`research_validity_service.py`, `research_validity.py`, `agentic/__init__.py` → resolved/partial/medium.
`classify --recipe istara-main` → standard_change (basis scored); framer raises this to **Full**
(new external LLM-provider credential and egress on the spine's trust boundary, AGENTS.md §9).
Next: owner approval → DEC-1 → `spec clarify` → S1.

### L-2 | 2026-10-18T00:16:13Z | S0-frame | claude-code | framer | —
Did: Recorded the owner's answers as DEC-1, logged DEC-2 (shadow mode), added roadmap Phase 4 (onboarding + configuration UX) and moved trajectory audit to Phase 5. Wrote clarify answers and ran `spec clarify CF-SPEC-1`.
Result: S0 exit criteria met; stage moves to S1-plan.
Verified: `python3 scripts/verify_build_stream_status.py <this file>` and `verify_lifecycle.py` (results in the session's closing check).
Next: stage exit: S0 approved (DEC-1) → S1 Phase 0 design.

### L-3 | 2026-10-18T00:38:02Z | S0-frame | claude-code | framer | —
Did: Mapped ReasoningBank, self-evolution, meta-hyperagent, autoresearch engine and runners, validation/adaptive selection and consensus with `compass-forge intelligence impact` (index refreshed: `graph_usable: true`; all inputs `resolved`, completeness `partial`, cut at the 2-hop bound) and source reading. Surveyed dispatcher purposes for closed-set decisions. Read abstracts of R6, R7, R24; confirmed R16, R17, R26 through search. Wrote the research doc, references log and autoresearch audit. Expanded the roadmap to nine phases; logged DEC-3.
Result: Findings AR-1…AR-8, AV-1, SV-1 (autoresearch audit). Integration candidates I1–I14. Open questions Q1–Q5.
Verified: `python3 scripts/verify_build_stream_status.py` and `verify_lifecycle.py` on this file (run after this entry).
Next: owner answers Q1–Q5 → DEC-4 → `spec clarify` → S1.

### L-4 | 2026-10-18T00:51:44Z | S0-frame | claude-opus-5-5 | framer | —
Did: Recorded DEC-4 (Q2, Q3, Q5) and the Q4 default. Researched decider-based qualitative coding (R30–R36) and wrote research doc §13. Earlier entries L-1…L-3 were written by the same model under the label `claude-code`, before the owner allowed the model id (DEC-4).
Result: Mechanics are feasible for deductive coding only; no peer-reviewed evaluation of typed decision models for qualitative coding was found; recommended a decider-coder research arm with no change to the spine gate.
Verified: lifecycle verifiers run after this entry.
Next: owner decides Q1 → DEC-6 → S1.

### L-5 | 2026-10-18T00:53:40Z | S0-frame | claude-opus-5-5 | framer | —
Did: Recorded DEC-6 (Q1) and added the decider-coder research arm to Phase 8. Re-ran `spec clarify CF-SPEC-1` with the expanded verification bar. All S0 questions are closed.
Result: S0 exit criteria met for the expanded frame (DEC-3…DEC-6). Stage moves to S1-plan.
Verified: lifecycle verifiers run after this entry.
Next: stage exit: S0 approved → S1 Phase 0 design.

### L-6 | 2026-10-18T01:05:01Z | S2-execute | claude-opus-5-5 | executor | Phase 0
Did: S1: wrote the Phase 0 design section, generated the CF constitution, ran `spec plan` and `spec tasks` (CF-1…CF-11; scoped CF-2 to Phase 0 by comment, since CF has no `task create`), work order, `gate before` (baseline record 1, 447 inherited issues). S2: created `backend/app/core/decision/` (`__init__`, `confidence`, `decision_rule`, `calibration`, `reliability`, `ensemble`) and `tests/test_decision_math.py`; appended a Tech.md entry (change-obligation rule `backend/app/core/*.py`); added the Dawid–Skene identifiability finding and R37 to the research docs.
Result: 23/23 tests pass. The first run failed 1/22 (Dawid–Skene three-evaluator recovery); diagnosis showed weak identifiability rather than a bug (DEC-7), so the test now uses five evaluators and a separate test asserts a monotone likelihood. 6/6 deliberate mutants were killed. Two docstring lines over 100 characters and two constructs the formatter would rewrite were fixed by hand.
Verified: `/usr/bin/python3 -I <scratchpad>/run_plain_tests.py tests/test_decision_math.py` → "23 passed, 0 failed, 23 total"; mutation script → 6/6 KILLED; `py_compile` + a line-length/whitespace scan → 0 issues; `compass-forge index status` → graph_usable true, no blocking or unindexed paths; `intelligence impact` on `calibration.py` → resolved/complete/high, dependents only the package `__init__` and the test; `gate after --task CF-2` → comparable, new_issue_count 0, new_failures 0, new_warnings 0 (recipe `generic`: `init` did not activate `istara-main`, so the gates ran without the Istara recipe; same recipe both sides). `task evidence CF-2` recorded (provenance asserted); `finish-task CF-2` ok. Not run: ruff check / ruff format --check (unavailable; CI backend-format and backend-lint cover them), pytest itself.
Next: Phase 0 S3 self-review.

### L-7 | 2026-10-18T01:07:11Z | S4-remediate | claude-opus-5-5 | remediator | Phase 0
Did: Self-only S3 review by edge-case probes (findings F-1…F-6 in the Phase 0 register), S4 fixes for F-1…F-5 in `calibration.py`, `ensemble.py`, `decision_rule.py`, plus two regression tests. Recorded a second evidence row on CF-2.
Result: F-1…F-5 fixed; F-6 (ruff/pytest not run) stays open until CI runs, which needs a push, an outward-facing step that is the owner's call.
Verified: stdlib runner → "25 passed, 0 failed, 25 total"; mutation script → 6/6 killed; formatter-collapse heuristic → none; `gate after --task CF-2` → comparable, new issues 0, new failures 0, new warnings 0.
Next: owner approves commit + push → CI → close F-6 → Phase 0 done → Phase 1.

### L-8 | 2026-10-18T01:44:18Z | S5-ship | claude-opus-5-5 | executor | Phase 0
Did: Committed `e72875df` (owner-approved, no attribution lines per the owner's global rule) and pushed `feat/decision-model-judge`. A feature-branch push does not trigger `ci.yml` (push/PR only on main/staging/testing), so I dispatched it (`gh workflow run ci.yml --ref feat/decision-model-judge`, runs 39085727702 and 39086661581). The first run showed `feature-obligations` red; running the classifier locally against `origin/testing` revealed the real obligation F-7, fixed in `4e0c534e` by registering `research.decision-models` in `testing/feature_coverage.yml`.
Result: F-6 and F-7 fixed; Phase 0 done; CI-1 (dispatch-only crash in `feature-obligations`) logged as an out-of-scope defect.
Verified: run 39086661581 at `4e0c534e` → backend-format success, backend-lint success, backend-test "2699 passed, 7 skipped, 1 deselected" (59 PASSED lines across `test_decision_math.py` and `test_research_validity_contract.py`); every other job green except `feature-obligations` (`CalledProcessError: git rev-parse ''`) and the `release-gate` aggregator that follows it. `python3 scripts/check_feature_obligations.py --base origin/testing --head HEAD` → "Feature-obligation classification passed"; `check_change_obligations.py` → "Change-governance check passed". CF-2 evidence row 3 recorded.
Next: Phase 1 S1.

### L-9 | 2026-10-18T02:13:21Z | S4-remediate | claude-opus-5-5 | executor | Phase 1
Did: S1 design written; CF-3 scoped by comment; `gate before --task CF-3` (baseline record 4). Implemented `backend/app/core/decider/` (`contract`, `registry`, `credentials`, `client`, `access`), `DecisionModelProjectPolicy` + migration 034 + `register_models` entry, the `decider_endpoints_json` setting, tests (`test_decider_contract.py`, `test_decider_registry.py`, `test_decider_client.py`), an alembic-test head bump, control AI-005 plus benchmark triggers and a detection test, a SECURITY_BENCHMARK.md entry, a feature-coverage paths and security obligation, and a Tech.md entry. Self-review via the gate found F-8 (fixed, DEC-8) and F-9 (suppressed to 2026-12-31). Committed `bd743f96` locally; not pushed.
Result: Phase 1 code complete; CI verification pending (F-10).
Verified: stdlib runner → contract "8 passed", registry "6 passed", math "25 passed"; mutation script → 5/5 killed (egress, served identity, alias detection, probability sum, retry-after); `security_benchmark.py --fail-on-threshold --changed-paths-file` → status pass, score 100.0, change detected (12 paths), no blocked controls; `check_feature_obligations.py --base origin/testing --head HEAD` → passed; `check_change_obligations.py` → passed; `public_repo_quality_audit.py --check` → passed; `gate after --task CF-3` → comparable, new issues 0, new failures 0, new warnings 0 (after F-8 and F-9); CF-3 evidence recorded (asserted). Not run locally: `test_decider_client.py`, `test_alembic_fresh_database.py`, `test_security_benchmark.py` under pytest, ruff.
Next: owner approves push → CI → close F-10 → Phase 1 done.

### L-10 | 2026-10-18T02:56:58Z | S5-ship | claude-opus-5-5 | executor | Phase 1
Did: Pushed the Phase 1 commits (owner-approved) and dispatched CI three times. Run 39089349304 failed backend-format on one missing trailing comma (F-11, fixed in `1e25278b`). Run 39090202504 then strict-linted `contract.py` and failed N818 (F-12, fixed in `2e28e7d6` by renaming both exception classes). That run also revealed that dispatch-run strict lint covers only the last commit's files (CI-2). Before the rename commit I ran an AST review of every branch backend file (unused imports, N802/N803/N806/N818, E711/E712, E741), which found nothing beyond the N818 pair. Finished CF-3.
Result: Phase 1 done. CI-2 recorded alongside CI-1.
Verified: run 39091047564 at `2e28e7d6` → backend-format success; backend-lint success (strict on `decider/access.py`, `client.py`, `contract.py`, `registry.py`); backend-test "2729 passed, 7 skipped, 1 deselected", 87 PASSED across `test_decider_*`, `test_decision_math`, `test_alembic_fresh_database` and `test_security_benchmark`; `feature-obligations` failed only with `CalledProcessError: git rev-parse ''` (CI-1); local `check_feature_obligations.py --base origin/testing --head HEAD` → passed; stdlib runner on Python 3.9 → 8 + 6 + 25 passed after the rename; `finish-task CF-3` → finished.
Next: Phase 2 S1.

### L-11 | 2026-10-18T03:04:42Z | S4-remediate | claude-opus-5-5 | executor | Phase 2
Did: S1 design; CF-4 scoped; `gate before --task CF-4` (baseline 8); spine impact read for `research_validity_reconciliation.py` and `models/research_validity.py` (30 dependents each; read-only by design). Implemented `core/decision/labels.py`, `sampling.py`, `trust.py`, `CrossFitResult.held_out_rows`, `models/decision_trajectory.py`, migration 035, `services/decision_trajectories.py`, tests, the Tech.md entry and research doc §4 additions. Committed `3821e1c8` locally.
Result: Phase 2 code complete; F-13 fixed; F-14 accepted-risk; F-15 waits on CI.
Verified: stdlib runner → trust "15 passed", math "25 passed", contract "8 passed", registry "6 passed"; formatter/lint heuristics → 0 candidates; `gate after --task CF-4` → comparable, 0 new issues, failures and warnings; `check_feature_obligations` and `check_change_obligations` against `origin/testing` → passed; `security_benchmark.py` → pass, 100.0, nothing blocked; `public_repo_quality_audit.py --check` → passed. Not run locally: `test_decision_trajectory_store.py`, `test_alembic_fresh_database.py`, ruff.
Next: owner approves push → CI → close F-15 → Phase 2 done.

## Phase 0 — math core

### Design (S1)

**Package** `backend/app/core/decision/`: pure standard-library Python, no I/O, no network, no
model calls, following the house style of `backend/app/evals/stats.py`. Every function takes plain
sequences or mappings and optional per-item weights $w_i$ (Horvitz–Thompson; research doc §6.1).
Unweighted means $w_i = 1$.

| Module | Functions | Source |
|---|---|---|
| `confidence.py` | `choice_confidence`, `score_confidence`, `noul_confidence`, `top_label` | TypeSafe *Confidence* [R4] |
| `decision_rule.py` | `bayes_decision` (expected risk per action under loss matrix L), `chow_threshold` (τ = 1 − C_R/C_E), `binary_threshold` (τ* = C_FP/(C_FP+C_FN)), `selective_decision` (accept the top label or abstain), `merge_order_flip` (argmax agreement, averaged vector) | T-Eq. 7–8, [R11], research doc §3 |
| `calibration.py` | `temperature_scale`, `fit_temperature` (weighted NLL, golden-section search over β = 1/T, which is convex in β), `expected_calibration_error` (M equal-width bins on top-label confidence), `brier_score`, `brier_decomposition` (one-vs-rest per class, exact: BS = REL − RES + UNC + WBV − 2·WBC), `effective_sample_size`, `cross_fit_calibration` (k seeded folds; held-out ECE/Brier only), `risk_coverage` | T-Eq. 6, 9, 10; [R8–R10, R12, R13, R37] |
| `reliability.py` | `beta_cdf` (regularized incomplete beta, Lentz continued fraction), `beta_quantile` (bisection), `reliability_posterior` (Beta(α0 + c, β0 + n − c), mean and lower credible bound), `binomial_cdf`, `learn_then_test_threshold` (fixed-sequence testing from the most conservative τ; never returns a τ below τ*) | T-Eq. 14 link; [R16] |
| `ensemble.py` | `error_correlation` (weighted φ of error indicators), `yules_q`, `effective_evaluators` (J_eff = J / (1 + (J − 1)·max(0, ρ̄))), `dawid_skene` (EM with missing labels, Laplace smoothing, majority-vote initialisation) | [R18, R20], research doc §7 |

**Design decisions** (logged as DEC-7):
- **Probabilities only, never logits.** Hosted deciders return probabilities, so temperature
  scaling works on log p̃. Zero probabilities are floored at 1e-12 and renormalised before taking
  logs; that floor is stated in the docstring.
- **Exact Brier decomposition.** Murphy's three-term identity holds exactly only when forecasts
  within a bin are equal. The binned version adds within-bin variance (WBV) and within-bin
  covariance (WBC) (Stephenson et al. 2008 [R37]), so the identity holds to floating-point
  precision and is testable.
- **J_eff is conservative.** Negative mean error correlation is reported, but J_eff is capped at J.
- **Learn-then-Test needs iid labelled pairs.** The function takes (confidence, correct) pairs from a
  uniform random labelled sample. Assembling that sample from audit and routed strata is Phase 2's
  job.

**Fixtures.** The JEV docs' worked examples (choice 0.9/0.06/0.04 → 0.85; score 0/0.57/0.43 →
0.355; score 0/0.5/0.5 → 0.25; score 0.5/0/0.5 → 0); closed-form Beta CDFs (Beta(2,1) = x²,
Beta(1,2) = 1 − (1 − x)²); hand-computed ECE and Brier on small sets; seeded synthetic data with
planted Dawid–Skene confusion matrices and planted miscalibration (temperature 2.5) for the
temperature fit.

**Verification.** `pytest tests/test_decision_math.py -q` in CI (Python 3.12, pytest, ruff). Locally
the owner forbids installing anything on this machine or on the Mac Studio (2026-10-17), and neither has
Python ≥ 3.11, pytest, ruff or Docker. So the package and its tests are written to also run on the
system Python 3.9 (stdlib only, `from __future__ import annotations`, no 3.10+ syntax at runtime), the
tests are plain-assert functions with no pytest import, and local evidence comes from a stdlib runner
that imports the test module and calls every `test_*` function. ruff is not run locally; that gap is
recorded in the evidence and closed by CI.

### Review (S3, self-only)

Independent review: none. The owner's rule allows no subagents, and an independent review only
when the owner starts one, so this review is self-only and carries no independent evidence.
Method: re-reading against the design, plus edge-case probes.

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-1 | Minor | Correctness | `calibration.py` `fit_temperature` | Returns the search bound silently when the likelihood is monotone (separable data), which looks like extreme sharpening | CF-2 | fixed |
| F-2 | Minor | Bugs | `calibration.py`, `ensemble.py` | Zero total weight raised `ZeroDivisionError` | CF-2 | fixed |
| F-3 | Minor | Bugs | `ensemble.py` `dawid_skene` | An out-of-range label raised `IndexError` | CF-2 | fixed |
| F-4 | Nit | Bugs | `calibration.py` | `bins < 1` raised `IndexError` | CF-2 | fixed |
| F-5 | Nit | Docs | `decision_rule.py` `merge_order_flip` | An exact tie can read as order disagreement; abstaining is the conservative outcome, now documented | CF-2 | fixed |
| F-6 | Major | Tests | toolchain | ruff and pytest have not run on this code (no installs allowed locally or on the Mac Studio) | CF-2 | fixed (CI, L-8) |
| F-7 | Major | Integration | `testing/feature_coverage.yml` | The new package was unclassified, so `check_feature_obligations` failed closed | CF-2 | fixed (L-8) |
| CI-1 | Major | Integration (out of scope) | `.github/workflows/ci.yml` feature-obligations step | On `workflow_dispatch` the base SHA is empty and `git rev-parse ''` crashes, so `release-gate` is always red on dispatched runs | — | open: separate task (not this plan's scope) |

### Remediation (S4)

F-1: `CrossFitResult.temperatures_at_bound` counts unidentified fits so the Phase 2 trust gate can
refuse them. F-2/F-3/F-4: consistent `ValueError`s. F-5: docstring. Regression tests:
`test_degenerate_inputs_fail_with_value_errors`, `test_cross_fit_reports_unidentified_temperatures`.

### Ship (S5)

Phase 0 is done. Commits `e72875df` (package, tests, docs) and `4e0c534e` (feature-coverage entry)
are pushed on `feat/decision-model-judge`, with no PR (owner, 2026-10-17). CI on Python 3.12 is green for
every job that judges this change. Review coverage: **self-only** (the owner's no-subagent rule).
The skills library's `docs/build-stream/blind-coverage-registry.md` does not exist, so the row is
recorded here instead. Residual risk: the decider math is unused until Phase 1–4 wire it in;
Dawid–Skene estimates for three-evaluator panels are imprecise by construction (DEC-7).

## Phase 1 — adapter + JEV

### Design (S1)

**Packages.** The math package stays pure. Provider access goes in a separate package,
`backend/app/core/decider/`:

| Module | Contents | Testable without backend deps |
|---|---|---|
| `contract.py` | `Choice`/`Score`/`Noul` question types; `build_request` (JEV `/v1/systemone` body); `parse_response` (strict validation: every requested answer present with the right type; probabilities non-negative, summing to 1 ± 1e-6 and covering exactly the requested options or levels; noul turned into a two-outcome distribution `{"true": p, "false": 1 - p}`); `is_versioned_model_id`; `retry_delay` (honours `retry-after`, else capped exponential backoff); `DecisionOutcome` with `status` `ok` / `not_runnable` and a reason code | yes (stdlib) |
| `registry.py` | `DeciderEndpoint` (stdlib dataclass parsed from the `decider_endpoints_json` setting: `endpoint_id`, `base_url`, `model`, `keychain_service`, `keychain_account`, `api_key_env`, `timeout_s`, `max_retries`); URL validated with `endpoint_security.normalized_service_url` (HTTPS required for public hosts); locality from `classify_host_scope` (loopback/private = local, public = hosted); `require_egress_authorization(endpoint, project_id, authorized_ids)` fails closed for a hosted endpoint without a project opt-in | yes |
| `client.py` | `SystemOneClient` over `httpx.AsyncClient` (imported lazily); bounded retries on 429/529; 400 `max_tokens_exceeded`, 401, 413, 415, 422, transport errors, timeouts, malformed JSON and incomplete answers all become `not_runnable` with a reason. It **never** returns a fabricated verdict. Served-model provenance: for a versioned request, `served != requested` is `not_runnable("served_model_mismatch")` (spine rule on served identity); for an alias the served versioned id is recorded and the outcome is marked `alias_requested` so the Phase 2 trust gate can refuse it | transport tests need httpx (CI) |
| `secrets.py` | API key from macOS Keychain (`/usr/bin/security`, as in `config._read_macos_keychain_secret`) or a named env var; never logged; `repr` of endpoints redacts | yes |

**Per-project egress authorization (DEC-1).** New table `decision_model_project_policies`
(`project_id` PK, `hosted_egress_endpoint_ids` JSON list, `updated_by`, timestamps;
`backend/app/models/decision_policy.py`, alembic `034_decision_model_project_policies.py`). The
default is no row, which means hosted endpoints are denied. Local endpoints need no opt-in. The API
and UI for setting it come in Phase 7, so Phase 1 is backend only.

**Setting.** `decider_endpoints_json: str = ""` in `Settings` (env `DECIDER_ENDPOINTS_JSON`). It
holds no secret; keys come from Keychain or env names only.

**Not in Phase 1.** Telemetry spans and the trajectory store (Phase 2; OpenTelemetry GenAI
attributes are added there with the store); content-guard wrapping of `state` (callers in Phase
4+); OpenAI Decisions / OpenRouter / Cloudflare adapters (Phase 8).

**Security** (AGENTS.md §9: new LLM-provider credential and egress). New control AI-005 in
`security/control_matrix.json`; decider paths added to the benchmark's `changed_path_patterns`;
`security/SECURITY_BENCHMARK.md` and `tests/test_security_benchmark.py` updated if they enumerate
controls; `python3 scripts/security_benchmark.py --fail-on-threshold` run.

**Verification.** `tests/test_decider_contract.py` and `tests/test_decider_registry.py` (stdlib; run
locally with the stdlib runner and in CI), `tests/test_decider_client.py` (`httpx.MockTransport`
stub `/v1/systemone`, covering JEV and a llama.cpp-shaped server; CI only), and
`tests/test_decision_policy_model.py` (CI). CF `gate before`/`gate after` on CF-3.

### Execute, review and remediate (S2–S4)

Implemented as designed, with one structural change (DEC-8): `open_decider` lives in
`app/core/decider/access.py`, and the package `__init__` holds only a docstring.

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-8 | Major | Code | `app/core/decider/__init__.py` | Re-exports created two import cycles (`__init__ → client → __init__`, `__init__ → client → registry → __init__`), flagged by `gate after` | CF-3 | fixed (DEC-8) |
| F-9 | Minor | Integration | `app/models/decision_policy.py` | `type_drift`: the new ORM model has no frontend type yet | CF-3 | accepted-risk: expiring suppression to 2026-12-31; the type arrives with the Phase 7 settings API |
| F-10 | Major | Tests | toolchain | `test_decider_client.py`, the alembic fresh-database test and the security-benchmark pytest tests need httpx/SQLAlchemy/pytest, unavailable locally | CF-3 | fixed (CI, L-10) |
| F-11 | Major | Code | `decider/contract.py` | ruff format wanted a trailing comma on a split single-parameter signature | CF-3 | fixed (`1e25278b`) |
| F-12 | Major | Code | `decider/contract.py`, `decider/registry.py` | N818: exception classes need an `Error` suffix | CF-3 | fixed (`2e28e7d6`) |
| CI-2 | Major | Integration (out of scope) | `.github/workflows/ci.yml` strict-lint step | On `workflow_dispatch` the strict lint covers only files changed in the last commit, so earlier green runs never strictly linted most of Phase 0/1; full coverage comes only with a PR into `testing` | — | open: belongs with CI-1's fix |

Review coverage: self-only (the owner's no-subagent rule).

### Ship (S5)

Phase 1 is done. Pushed commits `bd743f96`, `1222ea27`, `1e25278b`, `2e28e7d6` on
`feat/decision-model-judge`, with no PR (owner). Dispatch run 39091047564 is green for backend-format,
backend-lint and backend-test. CF-3 is finished. Review coverage: self-only. Residual risk: strict lint
has not yet covered `decider/__init__.py`, `decider/credentials.py`, the Phase 0 `decision/` package or
`models/decision_policy.py` (CI-2); my own AST review found no issues, and the first PR into
`testing` will lint them all. The decider is not called by product code until Phase 4.

## Phase 2 — trajectory store + calibration gate

### Design (S1)

Phase 2 adds storage, labels, sampling and the trust gate. It makes **no change to Research Spine
services**: wiring into coding runs and reconciliation is Phase 4, where trajectories start being
written. Pure parts sit in `app/core/decision/`; persistence sits in a model plus a service.

| Unit | Contents |
|---|---|
| `core/decision/labels.py` (pure) | `LABEL_MAPPING_VERSION = "v1"`. Only `ReconciliationDecision` rows with `source == "human_review"` label anything (synthetic benchmark, debate and adversarial sources never do). v1 is **binary**: `accepted` → 1 and `rejected`/`revised` → 0 for the positive event of a question (for example relation-to-span = `supports`, code-applies noul = `true`); `needs_human_review` → no label. The review UI does not yet capture the four-way class (grounded / speculative / hallucination / violation), so v1 cannot claim it; a richer label needs a UI change (Phase 7) and a v2 mapping. |
| `core/decision/sampling.py` (pure) | `audit_draw(project_id, subject_id, rate, salt)`: a deterministic SHA-256 draw, reproducible and independent of the decider's output; returns `(sampled, propensity)`. `inclusion_weight(routed, sampled, rate)`: Horvitz–Thompson weight 1 for routed items, 1/ρ for audit-sampled ones, and unlabelled otherwise. ρ = 0.10 (DEC-4). `scope_key(...)`: a stable hash of provider, served versioned model, question-set version, task family and language. |
| `core/decision/trust.py` (pure) | `TrustPolicy` with the DEC-1 defaults (ECE ≤ 0.05, κ ≥ 0.60, n_eff ≥ 50, order-flip disagreement ≤ 5%). `evaluate_trust(items, policy, alias_scope)` → `TrustReport(trusted, reasons, metrics)`. Metrics on cross-fitted held-out calibrated probabilities: weighted ECE, Brier + decomposition, Cohen κ vs labels, risk–coverage at τ*, order-flip rate, n_eff, folds stopped at the temperature bound. Any reason refuses trust: alias scope, too little data, a ceiling exceeded, or an unidentified temperature. |
| `models/decision_trajectory.py` | `DecisionTrajectory`, content-free per research doc §5: handles (project, subject kind and id, task, coding run, evidence unit), endpoint, requested and served model, alias flag, question-set id/version, task family, language, `scope_key`, status/reason, raw and calibrated distributions (numbers keyed by option names from the versioned question set), T, τ, action, order-flip agreement, audit sampled/propensity/blind, label mapping version, human label, its source decision id and time, latency, tokens. `DecisionTrustEvaluation`: scope key, trusted, reasons, metrics JSON, policy JSON, evaluated time and n. Migration `035_decision_trajectories`. |
| `services/decision_trajectories.py` | `record_trajectory(...)`; `attach_human_label(session, decision)`, which labels every trajectory for that code application and is a no-op for non-human sources; `evaluate_scope(session, scope_key)`, which loads labelled trajectories, runs `evaluate_trust` and stores a `DecisionTrustEvaluation`; `scope_is_trusted(session, scope_key)`, true only for the latest evaluation, so a missing evaluation means shadow mode (DEC-2). |

**Deviation (DEC-9).** The roadmap named the gate `app.evals.decision_eval`. It lives in
`app/core/decision/trust.py` instead, because Phase 4 routing must read trust at request time;
`app/evals/` holds offline measurement harnesses. Same contract, different home.

**Verification.** Pure: `tests/test_decision_trust.py` (labels, sampling, the trust gate on seeded
planted data: a well-calibrated decider is trusted, and over-confidence beyond the ECE ceiling,
small n, alias scope, order-flip disagreement and an unidentified T are each refused with their
reason), run locally and in CI. Persistence: `tests/test_decision_trajectory_store.py` (CI only,
in-memory aiosqlite), plus the alembic fresh-database test bumped to 035. CF `gate before`/`after`
on CF-4.

### Execute, review and remediate (S2–S4)

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-13 | Minor | Tests | `tests/test_decision_trust.py` | First fixtures used an uninformative latent spread (κ ≈ 0.55), and the "weighted small sample" had n_eff 60.8, not below 50 | CF-4 | fixed (DEC-10) |
| F-14 | Major | Product | `core/decision/labels.py` | Mapping v1 is binary because the review control does not capture the four-way class; per-class calibration cannot be measured yet | CF-4 | accepted-risk: Phase 7 review control + v2 mapping; stated in research doc §4 |
| F-15 | Major | Tests | toolchain | `test_decision_trajectory_store.py` and the alembic 035 test need SQLAlchemy/aiosqlite/pytest | CF-4 | open (closes on CI) |

Review coverage: self-only (the owner's no-subagent rule). No Research Spine service was edited in Phase 2.
