# Decision-model judge layer (JEV primary, universal decider interface)

## Status Block

<!-- STATUS BLOCK -->
```yaml
item: decision-model-judge
branch: feat/decision-model-judge
cf: { spec: CF-SPEC-1, tasks: [CF-2, CF-3, CF-4, CF-5, CF-6, CF-7, CF-8, CF-9, CF-10] }
phase: "—"
stage: S5-ship
status: done
blocked_on: null
last: { agent: claude-code, at: 2026-10-18T18:30:00Z, ledger: L-24 }
next_action: "Plan done. Owner: review the branch, run the QA-lane UI walk (F-40) and a live calibration run when ready, then ask for a PR into testing."
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
| 2 | Trajectory store + calibration gate | `DecisionTrajectory` (alembic, content-free handles, §5 of the research doc), versioned human-label mapping from `ReconciliationDecision` / review outcomes / `classify_review_feedback`, blind random audit sampling (rate ρ, propensity π), `app.evals.decision_eval` trust gate per scope with cross-fitting, shadow mode (DEC-2) | **Given** labelled trajectories with a known audit design, **when** a scope is evaluated, **then** weighted ECE/Brier/κ/order-flip/risk–coverage are reported on held-out folds, `trusted` requires n_eff ≥ 50 and the DEC-1 ceilings, audit items hide the decider verdict from the reviewer, and an untrusted scope has no routing effect | `pytest tests/test_decision_trajectory.py tests/test_decision_eval.py -q` | done |
| 3 | Assurance modes | project-level assurance policy (`auto`, `llm_judges`, `decision_models`, `both`, `none`) honoured by `validation.py` and `validation_executor.py`; Self-MoA stays the single-endpoint fallback; AV-1 fix (reward = human outcome, Thompson sampling constrained to the mode); research-validity contract + governance contract + ensemble-method matrix updated | **Given** each mode, **when** a task is validated, **then** only the evaluators the mode allows are called (dispatcher call log proves no LLM-judge call in `decision_models` mode), `none` marks the task `unvalidated` and still requires human review, outputs from `both` are shown side by side and never vote-merged, and the coding-run reliability gate is unchanged in every mode | `pytest tests/test_assurance_modes.py tests/test_adaptive_validation.py tests/pi_production/test_w7_validation.py tests/test_research_validity_contract.py -q` | done |
| 4 | Spine seam (code applications) | decider triage after the deterministic quote check; routing and priority into `CodeReviewQueue`; trajectory written per application | **Given** a governed coding run, **when** applications are admitted, **then** each gets a trajectory; with a trusted scope, abstentions and `factual_hallucination` / `methodological_violation` route to review with priority; no acceptance state changes because of the decider; κ inputs are byte-identical with the decider on vs off; telemetry is content-free | `pytest tests/test_research_validity_contract.py tests/test_code_applications.py tests/test_decision_spine_seam.py -q`; credential-free simulation scenario with a stub decider; UI walk | done |
| 5 | Learning loop + ensemble health | ReasoningBank `decision_review` lessons (aggregate, content-free, after human label only); scheduled recalibration with cross-fitting; CUSUM drift → shadow; self-evolution proposals for question sets and τ overrides via improvement governance (protected values excluded); ensemble health shows per-evaluator calibration, error correlation, Yule's Q, J_eff, Dawid–Skene reliabilities | **Given** a history of labelled trajectories, **when** the loop runs, **then** lessons cite only handles, a recalibration changes T only if held-out ECE improves, drift returns a scope to shadow with a recorded reason, governance refuses proposals that touch κ ≥ 0.60 / the ECE ceiling / n_min / the never-promote rule, and Ensemble Health renders the new metrics in all roles, light/dark, 375px, keyboard | `pytest tests/test_decision_learning_loop.py tests/test_spine_learning_loops.py tests/test_meta_hyperagent.py -q`; ensemble-health scenario; UI walk | done |
| 6 | Autoresearch | fix AR-1…AR-8 (each with a failing regression test first); new `decision_policy` runner (objective: held-out weighted Brier, coverage at fixed risk); decider `score` as an optional measurement instrument per assurance mode; judges pinned away from the endpoint under test | **Given** a deterministic fake runner with known noise, **when** the loop runs, **then** a candidate whose true effect is zero is kept at most at the nominal error rate, the incumbent is re-measured paired, failed measurements are `not_runnable` (never 0.5), `mutation_diff` persists, and a `decision_policy` experiment stays a governed proposal | `pytest tests/test_autoresearch_engine.py tests/test_autoresearch_statistics.py tests/test_decision_policy_runner.py tests/pi_production/test_w6_engine_selection.py -q` | done |
| 7 | Onboarding + configuration UX | general Istara onboarding and first-activation flow for decision models (DEC-1): what a decision model is (closed answers in, label + probabilities out; triage, never authority), when it helps, cloud-egress consequences, where to configure the JEV API key and endpoint or a local `/v1/systemone` server, per-project opt-in, assurance-mode selection, trust status (shadow / calibrating / trusted) and how calibration works | **Given** a new install, **when** the user goes through onboarding, **then** decision models and assurance modes are introduced with skippable guidance and no decider is enabled; **given** a project with none configured, **when** the user first opens decision-model settings, **then** a first-activation flow explains the concept, the egress choice and the two configuration paths, stores the key only in Keychain/env, never enables egress without explicit project opt-in, and shows trust status; walked by role (admin/researcher/viewer), light/dark, 375px, keyboard; empty/loading/error states | new + updated simulation scenarios (onboarding, settings, `09`/`90` sweeps); `python3 scripts/feature_docs.py --seed-missing --generate-site --check`; `python3 scripts/check_a11y_contrast.py`; UI walk with screenshots | done |
| 8 | More adapters, trajectory audit, further integrations | OpenAI Decisions / OpenRouter / Cloudflare adapters; per-transition (s,a,o) tool-call audit (Wang & Gao; benchmark axes 1, 4, 9); integrations I4–I14 (all four groups, DEC-4); decider-coder research arm on the canonical corpus with human gold codes, never counted in the gate (DEC-6, research doc §13); live runs only with owner permission | **Given** each adapter's stub, **then** it passes the shared adapter conformance suite; trajectory audit flags schema-invalid calls and observations that do not support the next state | `pytest tests/test_decider_conformance.py tests/test_trajectory_audit.py -q`; live calibration run **only with owner permission** (AGENTS.md §9) | done |
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

DEC-11 | 2026-10-18 | S2-execute | claude-opus-5-5
Context: Phase 3 needed (a) a learning signal for method selection that is not self-agreement, (b) exact labels for operational decider verdicts, and (c) unchanged behaviour for projects that never choose a mode.
Decision: (a) A method is credited when its verdict (consensus ≥ 0.5) matched the researcher's task review, with Thompson sampling within the mode's methods. (b) Operational deciders answer one `acceptable` noul, labelled by approve vs send-back. (c) No policy row means `auto`; a failed LLM run in `auto` leaves the task fields untouched as before; the validation block moved verbatim into `services/operational_validation.py`.
Why: (a) agreement among copies of one model is what thesis axis 10 measured as uninformative; (b) one question with an exact label beats several with noisy ones; (c) zero-surprise rollout. Rejected: diagnostic multi-question sets for v1 (their labels would be noisy until the review UI captures reasons).

DEC-12 | 2026-10-18 | S1-plan | claude-opus-5-5
Context: The roadmap's Phase 4 acceptance included a UI walk of the review queue. This machine and the Mac Studio have no Docker or QA stack, and the owner forbids installs (2026-10-17).
Decision: Phase 4 delivers the backend and API seam: triage, hooks, the `decider_triage` field and routed-first order, and the frontend type. The queue badge and its UI walk move to Phase 7, where all decision-model UI is designed together (interface-design skill) and walked on a QA stack.
Why: An honest split: nothing visible changes until a decider scope is trusted, and the UI work belongs with the onboarding and settings UI it depends on. Rejected: shipping an unwalked UI change.

DEC-13 | 2026-10-18 | S2-execute | claude-opus-5-5
Context: Phase 5 learning made scope-level trust consequential, and scopes were keyed without the project.
Decision: `scope_key` takes `project_id`; every caller and test updated.
Why: The self-improvement governance contract rejects cross-project learned statistics (critique #5). The cost is that each project needs its own 50 labels before a decider routes anything, which is the conservative choice.

DEC-14 | 2026-10-18 | S2-execute | claude-opus-5-5
Context: The CF-7 `gate before` baseline was not taken before Phase 5 edits began.
Decision: Stash all changes (`git stash -u`), record `gate before --task CF-7` on the clean tree (record 16), restore, then `gate after`.
Why: That baseline is identical to one taken before editing, so the comparison stays honest.

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

### L-12 | 2026-10-18T03:21:17Z | S5-ship | claude-opus-5-5 | executor | Phase 2
Did: Pushed the Phase 2 commits (owner-approved) and dispatched CI run 39092495962; finished CF-4.
Result: Phase 2 done; F-15 fixed.
Verified: run 39092495962 at `ca44d999` → backend-format success, backend-lint success, backend-test "2748 passed, 7 skipped, 1 deselected". PASSED counts: `test_decision_trajectory_store` 4, `test_decision_trust` 15, `test_alembic_fresh_database` 1, `test_decision_math` 25, `test_decider_*` 29. `feature-obligations` failed only with `CalledProcessError: git rev-parse ''` (CI-1). `finish-task CF-4` → finished.
Next: Phase 3 S1.

### L-13 | 2026-10-18T03:35:08Z | S4-remediate | claude-opus-5-5 | executor | Phase 3
Did: Orientation (validation callers, selector, task review, evaluation skill; CF impact: `agent_execution` and `task_review` 30 dependents, `adaptive_validation` 20). S1 design; `gate before --task CF-5` (baseline 10). Implemented `core/assurance.py`, `models/assurance_policy.py`, migration 036 + `init_db` ALTERs, `MethodMetric.human_*`, the selector rewrite (allowed set, Thompson on human outcomes, `record_human_outcome`, stats), `services/operational_validation.py` (the validation block moved out of `agent_execution`), `services/decision_trajectories.label_subject`, the task-review hook, and the evaluation skill honouring the mode. Tests `test_assurance_modes.py` (local + CI) and `test_operational_validation.py` (CI). Docs: research-validity and governance contracts, ensemble-method matrix, research doc §8 correction, Tech.md, persona, Ensemble Health feature docs + regenerated site. Commits `43434f69`, persona, `194011de`, `dadced65` (local).
Result: Phase 3 code complete; F-16…F-19 fixed; F-20 accepted; F-21 waits on CI.
Verified: stdlib runner → assurance "6 passed", trust "15 passed", math "25 passed", contract "8 passed", registry "6 passed"; collapse checker over all branch backend files → 0 candidates (checked against a measured 102-column case); `feature_docs.py --seed-missing --generate-site --check` → "passed for 86 feature(s)"; `check_change_obligations` → passed (failed first on the persona rule, F-18); `check_feature_obligations` → passed; security benchmark → pass 100.0; repo audit → passed; `gate after --task CF-5` → comparable, 0 new failures, 1 warning (F-20).
Next: owner approves push → CI → close F-21 → Phase 3 done.

### L-14 | 2026-10-18T03:52:42Z | S5-ship | claude-opus-5-5 | executor | Phase 3
Did: Pushed the Phase 3 commits (owner-approved), dispatched CI run 39094290764, finished CF-5.
Result: Phase 3 done; F-21 fixed.
Verified: backend-format, backend-lint and backend-test success; "2763 passed, 7 skipped"; PASSED counts: test_operational_validation 9, test_assurance_modes 6, test_alembic_fresh_database 1, test_adaptive_validation 4, test_w7_validation 49, test_evaluation_skill 2, test_task_review_history 6, tests/test_tasks.py 23. feature-obligations failed only from CI-1.
Next: Phase 4 S1.

DEC-15 | 2026-10-18 | S1-plan | claude-opus-5-5
Context: The audit's AR-1 fix says "compare every candidate with a fresh paired measurement of the incumbent". Runners measure live systems (skill runs, judges), so a candidate and the incumbent cannot share random seeds, and a single sample per side has no variance estimate.
Decision: Each iteration measures the incumbent and the candidate `max(2, autoresearch_measurement_repeats)` times in alternating blocks and keeps the candidate only if the lower end of the 95% Welch interval on the difference of means exceeds `autoresearch_min_improvement_delta`, and then again on an independent confirmation block. Unmeasurable samples (`None`) make the iteration `not_runnable`. Accepted mutations are still reverted; stacking them stays a governed proposal, not a loop mode.
Why: Welch is honest about unequal variances without a pairing it cannot guarantee. The confirmation block removes the winner's-curse bias of selecting on the same samples that pass the test (AR-2). Rejected: a z interval (n ≤ 10), a paired t on unpaired draws, and ratcheting `best_score` (AR-1).

DEC-16 | 2026-10-18 | S1-plan | claude-opus-5-5
Context: Phase 7 needs a place to enter a decider key in the UI. The earlier sketch stored it in an encrypted database column; the roadmap acceptance says the key lives only in Keychain/env, and Istara already custodies Pi endpoint keys that way (`pi_runtime.endpoint_policy._custody_api_key`).
Decision: Keys entered in Settings go to macOS Keychain (service `istara-decider`, account = endpoint id) or, without Keychain, to the endpoint-scoped `ISTARA_DECIDER_SECRET_<ID>` runtime env value; endpoints persist in `DECIDER_ENDPOINTS_JSON`, which holds no secret. No new table or migration.
Why: One custody model across providers, matching the acceptance criterion; no second copy of a secret in the database. Rejected: an `EncryptedType` column (a new secret store to rotate and audit).

DEC-17 | 2026-10-18 | S2-execute | claude-opus-5-5
Context: The owner asked that general onboarding and first activation teach decision models. The guided tour indexes its steps by position, with role and team-mode skips.
Decision: Add an informational, skippable last step to the onboarding wizard (assurance modes and the decision-model explainer, nothing enabled), a first-activation guide in Settings → Decision models shown while none is configured, and an expandable explainer in Project Settings → Assurance. The guided tour is unchanged.
Why: Inserting a tour step shifts every index-based skip rule for little gain. Rejected: a tour step for Decision models (fragile), and enabling anything from onboarding (DEC-1: no decider by default).

DEC-18 | 2026-10-18 | S2-execute | claude-opus-5-5
Context: The Phase 7 acceptance asks for a UI walk by role, light/dark, 375px and keyboard. This machine has no Node, Docker or QA stack, and installs are forbidden; `ui-journeys` runs only scenarios listed as proven with dated evidence.
Decision: Register scenario `91-decision-models` (credential-free; never calls a decider) so CI proves it imports and records it as not run; typecheck, lint and unit tests run in CI. The walk itself stays open as F-40 until it runs on the QA lane.
Why: Listing an unrun scenario as proven would violate the lane's honesty contract. Rejected: claiming the walk.

DEC-19 | 2026-10-18 | S1-plan | claude-opus-5-5
Context: Phase 8 named three adapters and eleven integration sites. Official docs: OpenAI's Decisions guide was readable (its API reference returned 404); OpenRouter's Jev guide says it serves TypeSafe's `/v1/systemone`; Cloudflare's model page returned 404 and search found no confirmation. Most integration sites have no exact human label for their question.
Decision: (1) Add an `openai_decisions` protocol from the official guide; unknown response shapes (refusals, usage) fail closed. OpenRouter is a `systemone` preset, not new code. No Cloudflare adapter until an official page is read (R39). (2) All sites go through one advisory seam (`services/decider_advisory.py`): opt-in by assurance mode, a shadow trajectory per answer, never raising, advice only. Only I5 (`task_output`, labelled by task review) can calibrate today; I13 reorders and I14 escalates only from a trusted scope, and I14 can only add caution. I10 (UI audit) was not in the owner's four groups. (3) The trajectory audit (I8) is a deterministic checker plus an advisory decider question, offered as a service function; wiring it into the agent loop needs a transition log that does not exist yet. (4) The decider-coder research arm is an offline eval that never writes code applications or touches the gate (DEC-6).
Why: Building against unread or unreachable documentation would be a fabricated contract. A single seam keeps every site's failure mode identical and testable, and refusing noisy labels keeps calibration honest (DEC-11). Rejected: per-site decider clients; labelling advisory scopes with the whole-task review outcome.

### L-15 | 2026-10-18T05:01:02Z | S4-remediate | claude-opus-5-5 | executor | Phase 4
Did: Orientation (coding-run commit point, review queue, reconciliation, codebook fields); S1 design; `gate before --task CF-6` (baseline 13). Implemented `services/decider_triage.py`, the post-commit hook in `run_independent_coding_run`, the label hook in `create_reconciliation_decision`, `routed_triage` and the pending-route field and order, `CodeApplicationType.decider_triage`, `services/assurance_policies.py`, AI-005 evidence and triggers, docs (Tech.md, research-validity contract, review feature docs + site), and `tests/test_decider_triage.py`. Commits `fc1dab1c`, `b8d1d5f7` (local).
Result: Phase 4 code complete; F-22…F-24 fixed; F-25 waits on CI.
Verified: stdlib runner → assurance 6, trust 15, math 25, contract 8, registry 6 passed; collapse/E501 → 0; `gate after --task CF-6` → comparable, 0 new issues, failures and warnings (after F-23); feature and change obligations → passed; security benchmark → pass 100.0; `feature_docs.py --check` → passed (86); repo audit → passed.
Next: owner approves push → CI → close F-25 → Phase 4 done.

### L-16 | 2026-10-18T05:28:37Z | S5-ship | claude-opus-5-5 | executor | Phase 4
Did: Pushed the Phase 4 commits (owner-approved) and dispatched CI run 39099105094: 2 triage tests failed from F-26. Fixed the fixture in `08d2ad27`, pushed, dispatched run 39099977103; finished CF-6.
Result: Phase 4 done; F-25 and F-26 fixed.
Verified: run 39099977103 → backend-format, backend-lint, backend-test success, "2769 passed, 7 skipped"; `test_decider_triage` 6 PASSED; run 39099105094 → `test_research_validity_contract` 34, `test_code_applications` 13, `test_research_spine_end_to_end` 2, `test_interrupted_coding_runs` 2, `test_operational_validation` 9, `test_security_benchmark` 32 PASSED; `feature-obligations` failed only from CI-1.
Next: Phase 5 S1.

### L-17 | 2026-10-18T05:36:43Z | S4-remediate | claude-opus-5-5 | executor | Phase 5
Did: Implemented Phase 5 as above (drift, health, learning loop, project-scoped scopes, protected terms, metrics route, frontend client and types, docs: Tech.md, governance contract, SECURITY_BENCHMARK route list, research doc scope, Ensemble Health feature docs and site). Tests `test_decision_drift_health.py` (local + CI) and `test_decision_learning.py` (CI).
Result: F-27…F-30 fixed; F-31 waits on CI.
Verified: stdlib runner → drift/health "5 passed", trust "15 passed"; collapse checker → 0; no added backend line over 100 columns; `gate after --task CF-7` → comparable, 0 new issues, failures and warnings (after F-29); `feature_docs.py --seed-missing --generate-site --check` → passed (86).
Next: commit, push, CI.

### L-18 | 2026-10-18T06:20:00Z | S5-ship | claude-opus-5-5 | executor | Phase 5
Did: Pushed Phase 5 (`c1b6ce8b`, `e1486eeb`) and dispatched CI run 39101172867: tests green, backend-format and hygiene failed (formatting, trailing blank line). Fixed in `84690189`, pushed, dispatched run 39101996713; finished CF-7.
Result: Phase 5 done; F-31 fixed.
Verified: run 39101996713 → backend-format, backend-lint, hygiene, backend-test success, "2780 passed, 7 skipped"; `feature-obligations` and the dependent `release-gate` failed only from CI-1.
Next: Phase 6: commit the autoresearch work, push, CI.

### L-19 | 2026-10-18T06:30:00Z | S4-remediate | claude-opus-5-5 | executor | Phase 6
Did: Implemented Phase 6 (see the Phase 6 section): `core/autoresearch_statistics.py`, the engine rewrite, `autoresearch_runners/scoring.py`, strict scoring in every runner, the `decision_policy` runner and its registration, leaderboard lower bound (backend and frontend), docs (Tech.md, audit status, governance contract, autoresearch feature docs + site). Tests `test_autoresearch_statistics.py`, `test_decision_policy_runner.py` (local + CI), `test_autoresearch_hill_climbing.py` and the updated `test_autoresearch_engine.py` (CI).
Result: AR-1…AR-8 fixed in code; F-32…F-34 fixed; F-35 waits on CI.
Verified: stdlib runner → statistics "6 passed", decision-policy runner "3 passed", math "25 passed"; collapse checker → 0 candidates; no added line over 100 columns; `gate after --task CF-8` → comparable, 0 new issues, failures and warnings; `feature_docs.py --seed-missing --generate-site --check` → passed.
Next: commit, push, dispatch CI.

### L-20 | 2026-10-18T08:30:00Z | S4-remediate | claude-opus-5-5 | executor | Phase 6, Phase 7
Did: Phase 6 CI run 39102947318: backend-test failed 14 (F-41 W6 dispatcher contract, F-42 artifact boundary), backend-format failed (F-37); fixed in `a342baf9` and `cd843554`. Implemented Phase 7 (see its section): decision-model settings and project-policy routes, key custody, Settings and Project Settings sections, Ensemble Health panel, review-queue note, onboarding step, feature docs, Tech.md, persona, AI-005, scenario 91. A usage-limit pause interrupted the session mid-Phase 7; work resumed from the working tree.
Result: F-37, F-41, F-42 fixed in code (F-35 still closes on CI); Phase 7 code complete with F-38…F-40 open.
Verified: local boundary scan (same rules as `test_self_improvement_artifact_boundary`) → no hits; stdlib runner → `test_decision_policy_runner` "3 passed"; collapse checker → 0; no line over 100 columns in changed backend files; `gate after --task CF-9` → comparable, 0 new issues (after splitting components and adding route/type hints; first run showed 12 warnings); `feature_docs.py --seed-missing --generate-site --check` → passed (86).
Next: commit Phase 7, push, dispatch CI.

### L-21 | 2026-10-18T09:40:00Z | S5-ship | claude-opus-5-5 | executor | Phase 6, Phase 7
Did: Pushed `a342baf9`, `cd843554`, `ef021948`, `03c093fc` and dispatched CI run 39117088982; finished CF-8 and CF-9.
Result: Phases 6 and 7 done; F-35, F-38, F-39 fixed; F-40 accepted-risk (UI walk needs a QA stack).
Verified: run 39117088982 → backend-format, backend-lint, hygiene, backend-test ("2805 passed, 7 skipped"), frontend-typecheck, frontend-lint, frontend-unit, frontend-build, ui-journeys (scenario 91 imports), governance success; `feature-obligations` and the dependent `release-gate` failed only from CI-1.
Next: Phase 8.

### L-22 | 2026-10-18T10:30:00Z | S4-remediate | claude-opus-5-5 | executor | Phase 8
Did: Read the official OpenAI Decisions guide and OpenRouter Jev guide; Cloudflare page 404 (DEC-19). `gate before --task CF-10` on the clean tree. Implemented `decider/openai_decisions.py`, `protocol` on endpoints, client dispatch, OpenRouter and OpenAI presets (backend and UI), `services/decider_advisory.py` with I4–I9, I11–I14 wired, `core/decision/trajectory_audit.py`, `evals/decider_coding_eval.py`, the saturation fix, docs (Tech.md, research doc §11, references R27/R38/R39, settings feature docs, persona, AI-005, SECURITY_BENCHMARK). Tests: `test_decider_openai_decisions.py`, `test_trajectory_audit.py`, `test_decider_coding_eval.py` (local + CI), `test_decider_conformance.py`, `test_decider_advisory.py` (CI).
Result: Phase 8 code complete; F-43 fixed; F-44 waits on CI.
Verified: stdlib runner → openai_decisions "4 passed", trajectory audit "2 passed", coding eval "3 passed", contract "8 passed", registry "6 passed", decision-policy runner "3 passed"; collapse checker → 0; no added backend line over 100 columns; security benchmark → pass 100.0; `feature_docs.py --seed-missing --generate-site --check` → passed (86).
Next: gate after, commit, push, CI.

### L-23 | 2026-10-18T11:20:00Z | S5-ship | claude-opus-5-5 | executor | Phase 8, —
Did: Pushed `215a26e1` and `4d86a8cb` and dispatched CI run 39118127320; finished CF-10, CF-1 and CF-11; `spec accept CF-SPEC-1` → accepted. Wrote the whole-plan summary.
Result: Phase 8 done; F-44 fixed; plan done with the residual risks listed in the summary.
Verified: run 39118127320 → backend-format, backend-lint, hygiene, backend-test ("2832 passed, 7 skipped"), frontend-typecheck, frontend-lint, frontend-unit, frontend-build, ui-journeys, governance success; `feature-obligations` and `release-gate` failed only from CI-1. Both lifecycle verifiers pass.
Next: none in this plan; owner review, the QA-lane UI walk (F-40), a live calibration run with owner permission, and a PR into `testing` when the owner asks.

### L-24 | 2026-10-18T18:30:00Z | S5-ship | claude-opus-5-5 | executor | Phase 7, Phase 8
Did: Owner asked for testing on the VPS with live models. Deployed PR #69 as a Dokploy compose service (tailnet only, `ISTARA_PUBLISH_HOST`; deploy environment passed whole to the backend), a fresh install (database recreated; Istara created its own first admin), three Pi endpoints (Muse Spark 1.3 contributor, GLM 5.3 Flash, multivac Qwen3.8 27B over the tailnet) and Jev (`jev-latest`) from the deploy environment. Ran the simulation suites by script in disposable Playwright containers (no socket, frontend network only): UI pass on GLM with Jev on, chat and agent turns on Muse, Qwen and the legacy engine. Fixed what the runs found: F-47, F-48, two runner options (`ISTARA_SIM_DEFAULT_ENDPOINT`, `ISTARA_SIM_DECIDER_ENDPOINTS`), scenario 91 and new scenario 92, a URL-aware machine-text rule, and an opt-in certificate bypass for HTTPS test stacks. F-49 recorded.
Result: F-40 fixed; F-47, F-48 fixed; F-49 accepted-risk.
Verified: final run on commit `9351496`: 26 of 27 UI-pass scenarios green (01, 02, 03, 05, 07, 09 80/80, 10, 12, 16, 21 41/41, 26, 32, 35, 37, 47, 67, 70, 79, 81, 82, 83, 88, 90 16/16, 91 10/10, 92 5/5), all turn passes green on all three models and both engines; 84 green 13/13 over HTTPS on `91f0004` (Secure session cookies need HTTPS). Jev: connection check served `jev-1.13.0`; one live verdict recorded (upload injection screen), scope untrusted with `not_evaluated`; no coding-run triage verdict because no scenario starts a governed coding run. Exposure: listeners only on the tailnet address; 13080/13081 unreachable on the public IPv4 (IPv6 not probeable from this Mac; no IPv6 listener). VPS audit chain valid, anchored at event 1874.
Next: owner review of PR #69 with this evidence; a governed coding-run scenario to exercise Jev triage end to end.

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
| CI-1 | Major | Integration (out of scope) | `.github/workflows/ci.yml` feature-obligations step | On `workflow_dispatch` the base SHA is empty and `git rev-parse ''` crashes, so `release-gate` is always red on dispatched runs | — | accepted-risk: outside this plan's scope; handed to the separate CI-fix session; every dispatched run shows it, and every other job is read directly |

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
| CI-2 | Major | Integration (out of scope) | `.github/workflows/ci.yml` strict-lint step | On `workflow_dispatch` the strict lint covers only files changed in the last commit, so earlier green runs never strictly linted most of Phase 0/1; full coverage comes only with a PR into `testing` | — | accepted-risk: outside this plan's scope; a PR into `testing` lints the whole diff, and every changed backend file was checked locally for ruff format shapes and line length |

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
| F-15 | Major | Tests | toolchain | `test_decision_trajectory_store.py` and the alembic 035 test need SQLAlchemy/aiosqlite/pytest | CF-4 | fixed (CI, L-12) |

Review coverage: self-only (the owner's no-subagent rule). No Research Spine service was edited in Phase 2.

### Ship (S5)

Phase 2 is done. Pushed `3821e1c8` and `ca44d999`; dispatch run 39092495962 is green for backend-format,
backend-lint and backend-test, and CF-4 is finished. Review coverage: self-only. Residual risk: the
Phase 2 backend files have not yet been strictly linted (CI-2; the heuristic pass found nothing); the
label mapping is binary (F-14). Nothing routes on trust until Phase 4.

## Phase 3 — assurance modes

### Design (S1)

**What exists (orientation, 2026-10-18).** LLM-as-judge runs in two product places: operational
validation after every skill run (`core/agent_execution.py` → `AdaptiveSelector.select_method` →
`core/validation.py` method), and the research-quality skill (`skills/evaluation_skill.py`, which calls
`adversarial_review` and `full_ensemble` directly). A borderline consensus (0.4–0.6) also starts an A2A
debate that rewrites the summary. `core/validation_executor.py` is **not called by product code**
(only by tests); research doc §8 said otherwise and is corrected. No user setting chooses the method
today: the selector picks it from compute, and when compute is constrained it falls back on history
scored by self-agreement (AV-1).

**Modes** (`core/assurance.py`, pure): `ProjectAssurance(mode, llm_method, llm_judges,
decider_endpoint_ids)` and `plan_validation(policy) -> ValidationPlan(run_llm, llm_methods, llm_judges,
run_deciders, decider_endpoint_ids, reason)`.

| mode | LLM judges | deciders | when nothing can run |
|---|---|---|---|
| `auto` (no policy row: exactly today) | compute-aware choice among all methods | only if the project lists decider endpoints | — |
| `llm_judges` | `llm_method` fixed (`self_moa`, `dual_run`, `full_ensemble` with `llm_judges ≥ 3`, `adversarial_review`, `debate_rounds`) or `auto` | none | Self-MoA stays the single-endpoint fallback inside the methods |
| `decision_models` | **none** (no LLM-as-judge call at all, so no consensus and no A2A debate) | the listed endpoints | `unvalidated`, reason `no_decider_configured` |
| `both` | as `llm_judges` | as `decision_models` | each half reports on its own |
| `none` | none | none | `unvalidated`, reason `assurance_disabled` |

In every mode the task still ends In Review and only a human moves it to Done; the coding-run
reliability gate is untouched (DEC-6). Outputs of `both` sit side by side under `llm` and `deciders` in
`task.validation_result` and are never merged into one verdict.

**Persistence.** `ProjectAssurancePolicy` (`project_assurance_policies`: project_id PK, mode,
llm_method, llm_judges, decider_endpoint_ids_json, updated_by, timestamps). No row = `auto`. Migration
036 also adds `human_agree_count` and `human_disagree_count` to `method_metrics`. The API and UI to set
the policy come in Phase 7 with the egress opt-in.

**Operational validation service** (`services/operational_validation.py`). The validation block moves
out of `agent_execution.py` behind one call, so it can be tested and the agent loop stays readable.
Decider validation uses question set `operational-output` v1: one noul, `acceptable` ("Would a
careful senior UX researcher accept this candidate output as it stands, given the task and its
evidence?"), whose label is exactly the researcher's approve / send-back decision. One question gives
exact labels, where several diagnostic questions would get noisy ones. Each decider verdict is stored
as a `task_output` trajectory; its action is `shadow`, or `advisory` when the scope is trusted.
Operational validation never routes, because every task already goes to human review.

**AV-1 fix.** `AdaptiveSelector.select_method(..., allowed=...)` chooses only among the methods the
mode allows. History counts only **human-verified** outcomes: at task review, a method *agreed* with
the researcher when its verdict (consensus ≥ 0.5 = passed) matched the decision (approved = pass;
needs revision or rejected after Done = fail); `system_failed` gives no label. Selection is a
Beta–Bernoulli Thompson sample over those counts (seeded RNG injectable for tests). With no human
outcomes it uses the compute-aware default within the allowed set. The self-agreement score is
removed. `record_outcome` still records runs and mean consensus for Ensemble Health, but no longer
feeds selection.

**Labels for decider trajectories** at task review: approved → 1, needs revision or rejected after
Done → 0, system failed → none (`task_review.record_review_side_effects` → `services/decision_trajectories`).

**Docs.** Research-validity contract (assurance modes section), self-improvement governance contract
(AV-1: learning signal = human outcome), `docs/scientific_audit/ensemble-method-matrix.md`, research doc
§8 correction, Tech.md.

**Verification.** `tests/test_assurance_modes.py` (pure plan matrix; selector with seeded Thompson;
the agreement rule) runs locally and in CI. `tests/test_operational_validation.py` (CI) monkeypatches
the validation functions and the decider client and records every dispatcher purpose: `decision_models`
and `none` make **zero** `validation.*` LLM calls, `both` returns both halves, `auto` with no policy row
behaves as before, and task-review labelling works. Existing `test_adaptive_validation.py`,
`pi_production/test_w7_validation.py`, `test_evaluation_skill.py`, `test_task_review_history.py` and
`test_tasks.py` must stay green.

### Execute, review and remediate (S2–S4)

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-16 | Major | Docs | research doc §8 | Claimed `validation_executor.py` governs reconciliation assistance; it is not called by product code | CF-5 | fixed (doc corrected) |
| F-17 | Major | Integration | `models/database.py` | Existing databases get new columns only through the `init_db` ALTER list; without it `method_metrics.human_*` would be missing on upgrade | CF-5 | fixed (ALTERs added) |
| F-18 | Major | Governance | `check_change_obligations` | Agent-loop change required a persona update | CF-5 | fixed (`istara-main/SKILLS.md`) |
| F-19 | Minor | Quality | `core/task_review.py` | `record_review_side_effects` complexity rose from 23 to 24 | CF-5 | fixed (`dadced65`, back to 23) |
| F-20 | Minor | Quality | `core/agent_execution.py` `_execute_task` | Complexity 69 over the limit of 20 (inherited; 72 before this phase) | CF-5 | accepted-risk: inherited debt, improved |
| F-21 | Major | Tests | toolchain | `test_operational_validation.py`, alembic 036 and the existing validation suites need the full backend stack | CF-5 | fixed (CI, L-14) |

Review coverage: self-only. Not in Phase 3: the API/UI to set a mode (Phase 7), and trust-based routing (Phase 4).

### Ship (S5)

Phase 3 is done: dispatch run 39094290764 is green for format, lint and tests (2763 passed), and CF-5
is finished. Review coverage: self-only. Residual: strict lint has not covered the Phase 3 backend
files (CI-2); there is no UI for choosing a mode yet (Phase 7).

## Phase 4 — spine seam (code applications)

### Design (S1)

**Where.** `run_independent_coding_run` commits the run's code applications, the reliability gate
result and the item statuses in one transaction. Triage runs **after that commit**, as a separate step
on its own session, so it cannot alter acceptance states or the κ matrix by construction.
Reconciliation (`create_reconciliation_decision`) commits the human decision; the label hook runs
after it, and both hooks never raise.

**Question set `code-application-triage` v1.** A single `choice` per application, `relation`:
"How does the evidence unit relate to applying code ‹name›?", with options `supports` (the unit
expresses the code as defined), `contradicts` (it expresses the opposite or meets an exclusion
criterion) and `says_nothing` (it does not address the code). State: the evidence unit text, the
coder's quote, and the code name, definition and inclusion/exclusion criteria (resolved by code id,
then by name within the project's codebooks; an unresolved code is sent by name only and the
trajectory records it). Asked in both option orders in one request (order-flip). The positive
outcome is `supports`, labelled by the researcher's `human_review` reconciliation (accepted → 1,
rejected or revised → 0).

**Decision** (`services/decider_triage.py`) per application, for each decider listed in the project's
assurance policy when the mode is `auto`, `decision_models` or `both`:
- not runnable → recorded, nothing else;
- untrusted scope → `shadow` (recorded, no effect, verdict never shown to reviewers);
- trusted scope → calibrated with the scope's fitted temperature; the order flip disagrees, or the top
  probability is below τ* = 0.90 → `abstain`; the top outcome is `contradicts` or `says_nothing` →
  `flag`; otherwise `none`. `abstain` and `flag` set `routed`. Audit-sampled items (ρ = 0.10) that were
  not routed are `audit_blind`.

**What routing means.** It changes nothing in the Research Spine. `GET
/api/code-applications/{project}/pending` adds a `decider_triage` field
(`{action, top_outcome, p_supports, endpoint_id}`) **only** for routed, trusted, non-blind items, and
orders routed items first (then the existing lowest-confidence-first order). With no trusted scope,
the response and its order are exactly as before.

**Deviation (DEC-12).** The roadmap's Phase 4 UI walk moves to Phase 7, where all decision-model UI
(onboarding, settings, the review-queue badge) is designed together with the `interface-design` skill
and walked on a QA stack. Phase 4 is backend + API: this machine and the Mac Studio have no Docker or
QA stack, and nothing may be installed (owner, 2026-10-17). `frontend/src/lib/types.ts` gains the
optional field so the type contract stays in step.

**Bound.** At most 200 applications are triaged per coding run (`DECIDER_TRIAGE_MAX_PER_RUN`); the
rest are counted and skipped, never guessed.

**Verification.** `tests/test_decider_triage.py` (CI): the **guard test** runs a coding run's
post-commit triage with a decider that flags everything and asserts every application's
`promotion_status`, `reliability_status`, `review_status` and the run's `matrix_json`/`kappa` are
byte-identical to the run without triage; plus shadow vs trusted actions, order-flip abstention, the
blind audit, the pending-route field and order, the label hook on human vs synthetic reconciliation,
and the per-run bound. Existing `test_research_validity_contract.py`, `test_code_applications.py`,
`test_research_spine_end_to_end.py` and `test_interrupted_coding_runs.py` must stay green. Security
benchmark (research data to hosted deciders goes only through `open_decider`).

### Execute, review and remediate (S2–S4)

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-22 | Major | Code | `services/decider_triage.py` | First draft sent the coder's quote as the evidence unit: `CodeApplication.source_text` holds the quote, not the unit | CF-6 | fixed (unit text loaded from `EvidenceUnit`) |
| F-23 | Major | Code | `decider_triage → operational_validation` | Three new import cycles through the LLM validation stack (gate after) | CF-6 | fixed (`services/assurance_policies.py`) |
| F-24 | Minor | Docs | review feature docs | Queue order and triage not described | CF-6 | fixed (`b8d1d5f7`) |
| F-25 | Major | Tests | toolchain | Guard test and spine suites need the full backend stack | CF-6 | fixed (CI, L-16) |
| F-26 | Major | Tests | `tests/test_decider_triage.py` fixture | `:memory:` SQLite gives each connection its own empty database; concurrent triage sessions failed as `error`, and the bound test summed counts so it passed anyway | CF-6 | fixed (`08d2ad27`: temp-file DB with busy timeout; tests assert no errors) |

Review coverage: self-only. The spine edits are two never-raising calls placed after the existing commits; no gate logic changed.

### Ship (S5)

Phase 4 is done. CI run 39099977103 is green for format, lint and tests (2769 passed; `test_decider_triage`
6/6 including the guard test); the Research Spine suites passed in both runs. CF-6 is finished.
Review coverage: self-only. Residual: the queue badge UI is in Phase 7 (DEC-12); strict lint has not
covered the Phase 4 code on dispatch (CI-2).

## Phase 5 — learning loop + ensemble health

### Design and build (S1–S4; owner asked for autonomous delivery, 2026-10-18)

- **Project-scoped trust (DEC-13).** The scope key now includes the project.
- **Re-evaluation** (`services/decision_learning.py`): after a human label lands (reconciliation →
  `learn_from_reconciliation`; task review → `reevaluate_subject_scopes_safely`), each touched scope is
  evaluated when it first reaches 50 labels and again every 10 new labels. Hooks never raise.
- **Drift** (`core/decision/drift.py`): one-sided CUSUM (slack 0.05, threshold 1.5) on new labels'
  binary Brier contributions of calibrated probabilities against half the trusted held-out Brier
  (the gate reports two-class Brier). An alarm stores an untrusted evaluation with reason
  `calibration_drift`, so the scope returns to shadow.
- **Lessons**: each evaluation records a ReasoningBank memory, source kind `decision_review`
  (added to the process-only kinds), with scope key, trusted flag and headline metrics only.
- **Protected terms**: self-evolution's governed-review check now also covers `decider`,
  `decision model`, `calibration` and `trust gate`.
- **Health** (`core/decision/health.py` pure + `services/decision_health.py` + `GET
  /api/metrics/{project}/decision-models`, project viewer): scopes with trust status and reasons;
  LLM methods' human agreement; on reviewed task outputs, pairwise error correlation, Yule's Q, mean
  correlation, J_eff, and Dawid–Skene for panels of three or more (with the identifiability note).
  Frontend: `metrics.decisionModels` and `DecisionModelHealth` types in `catalogTypes.ts`; the view
  is Phase 7.

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-27 | Major | Governance | `core/decision/sampling.py` | Trust scopes were not project-scoped, so one project's labels could earn a decider routing power in another (governance contract critique #5) | CF-7 | fixed (DEC-13) |
| F-28 | Minor | Process | CF-7 | `gate before` was not recorded before editing | CF-7 | fixed: baseline 16 recorded on the stashed clean tree (DEC-14) |
| F-29 | Minor | Integration | `frontend/src/lib/decisionModelTypes.ts` | A new `*types*.ts` file changed the evidence of 12 inherited type-drift issues, so they read as new | CF-7 | fixed: types moved into `catalogTypes.ts` |
| F-30 | Minor | Tests | `tests/test_decision_drift_health.py` | Exact float equality in a Brier test | CF-7 | fixed (`math.isclose`) |
| F-31 | Major | Tests | toolchain | `test_decision_learning.py` needs the full backend stack | CF-7 | fixed: CI run 39101996713 (L-18) |

## Phase 6 — autoresearch

### Design and build (S1–S4; autonomous, 2026-10-18)

- **Keep rule (AR-1, AR-2; DEC-15).** `core/autoresearch_statistics.py`: `welch_interval` (Welch–
  Satterthwaite df, a two-sided 97.5% t table under `# fmt: off`, fractional df rounded down so the
  interval is conservative) and `keep_decision(incumbent, candidate, min_delta)`, which refuses fewer
  than two samples per side. The engine re-measures the incumbent each iteration through the new
  `BaseLoopRunner.measure_incumbent` (default: `measure` on the reverted state), measures the
  candidate the same number of times, and confirms a passing candidate on a fresh block before
  `proposal_ready`. The persisted `baseline_score` is the incumbent mean of that iteration.
- **No fabricated scores (AR-4, AR-5).** `autoresearch_runners/scoring.py`: `parse_unit_score`
  accepts only a bare number in [0, 1]; `judge_score` pins a judge endpoint distinct from the
  endpoints under test (AR-6) and, when the project's assurance mode excludes LLM judges, asks the
  project's decider a `score` question instead. A failed run or judge call returns `None`, and one
  `None` makes the iteration `not_runnable`; output too short to judge is a real 0.0, not 0.1.
- **Records (AR-3, AR-7).** `mutation_diff` persists `candidate_mutation`; a meta-hyperagent
  conflict is recorded as `skipped_meta_conflict` with telemetry.
- **Leaderboard (AR-8).** Ranked by `quality_lower_bound_95` (mean − t·s/√n, n ≥ 2); `quality_ema`
  is computed as an EMA. The frontend sorts by the same bound.
- **`decision_policy` runner.** Target is a decider endpoint. Variants of the code-application
  triage question are each asked once per labelled trajectory of that project and decider (cached);
  each measurement scores a fresh random half by 1 − binary Brier of P(supports) against the human
  label (a strictly proper scoring rule, so wording cannot inflate it without improving the
  probabilities). It needs at least 20 labels, calls the decider only when a researcher starts the
  experiment, and its results are governed proposals like every other runner. Registered in
  `_RUNNER_SPECS`, the governance evidence mapping and the engine's conflict prefixes.

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-32 | Minor | Integration | `autoresearch_runners/__init__.py` | PEP 604 annotations in the runner base broke import on Python 3.9 (the local stdlib runner) | CF-8 | fixed (`from __future__ import annotations`) |
| F-33 | Minor | Tests | `tests/test_autoresearch_engine.py` | Keep-rule tests asserted the old single-sample guard (δ ≥ 0.01 with one repeat is kept) | CF-8 | fixed: rewritten for the Welch rule |
| F-34 | Minor | Code | `core/autoresearch_statistics.py`, `tests/test_autoresearch_hill_climbing.py` | Two lines over 100 columns | CF-8 | fixed |
| F-36 | Major | Governance | `core/improvement_governance_contracts.py` | `decision_policy` proposals named a `decision_models` surface that governance did not know, so they classified as medium-risk approval instead of admin review | CF-8 | fixed: `decision_models` is an admin, behavioural, high-risk surface (`decider` aliases it); test in `test_improvement_governance.py` |
| F-41 | Major | Integration | `autoresearch_runners/*` | CI run 39102947318: the W6 contract (`tests/pi_production/test_w6_autoresearch_runners.py`) requires each runner's scoring function to call `agentic.completion` itself with its purpose slug, spine phase and `engine=self.engine`; the shared `judge_score` hid that, and `model_temp._score_output` gained a keyword the W6 stubs do not take | CF-8 | fixed: `scoring.plan_judge` decides decider vs pinned LLM judge, each runner keeps its own dispatcher call; the judge exclusion travels as `ModelTempRunner._judge_avoid` |
| F-42 | Major | Governance | `autoresearch_runners/decision_policy.py` | CI run 39102947318: `test_self_improvement_artifact_boundary` forbids self-improvement modules from naming research models; the runner read `CodeApplication`/`EvidenceUnit` | CF-8 | fixed: `services/decider_triage.labelled_triage_states` prepares the labelled states read-only on the spine side |
| F-35 | Major | Tests | toolchain | `test_autoresearch_hill_climbing.py` and `test_autoresearch_engine.py` need the full backend stack | CF-8 | fixed: CI run 39117088982 (L-21) |

## Phase 7 — onboarding + configuration UX

### Design and build (S1–S4; autonomous, 2026-10-18)

Mode: interface-design `build` inside Istara's existing system (no Figma file; existing
`ui-panel`, `primary-action`/`secondary-action`, radio-card and badge patterns from
`AgenticCoreSection`).

- **Backend** (`api/routes/decision_models.py`, `decider/credentials.py`): global-admin endpoint
  CRUD and a connection check (one constant probe question); keys write-only (DEC-16). Project
  policy `GET` (viewer) and `PUT` (project admin) over `ProjectAssurancePolicy` and
  `DecisionModelProjectPolicy`; a hosted decider is refused unless the same request lists it in the
  egress opt-in, and the opt-in only accepts hosted endpoints. Trust status reuses
  `decision_health.scope_summaries` (calibrating, shadow, trusted).
- **Frontend**: `lib/decisionModelCopy.ts` (one wording for every surface), `DecisionModelsSection`
  (explainer, first-activation steps, presets for hosted Jev `jev-1.14.0` and a local
  `/v1/systemone` server, alias warning, check, two-step remove), `ProjectAssuranceSection` (mode
  radio cards, LLM method and panel size, decider checklist with a separate consent checkbox per
  hosted endpoint, trust list, explicit save), `DecisionModelHealthPanel` in Ensemble Health, the
  decider note in `CodeReviewQueue` (routed, non-blind items only), and the onboarding step
  (DEC-17).
- **Tests**: `tests/test_decision_model_settings.py` (keys never returned, admin-only, egress rule,
  role split), `frontend/src/lib/decisionModelCopy.test.ts`, scenario `91-decision-models` (DEC-18).

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-37 | Minor | Code | `autoresearch_runners/decision_policy.py` | Phase 6 CI run 39102947318: `ruff format` wanted the query chain split; the local collapse heuristic misses this shape | CF-8 | fixed (`a342baf9`) |
| F-38 | Major | Tests | toolchain | No Node here: typecheck, lint and the new unit test run only in CI | CF-9 | fixed: CI run 39117088982 frontend-typecheck, lint, unit, build success (L-21) |
| F-39 | Major | Tests | toolchain | `test_decision_model_settings.py` needs the full backend stack | CF-9 | fixed: CI run 39117088982 backend-test success (L-21) |
| F-40 | Major | Quality | UI | No UI walk by role, theme, 375px and keyboard yet (DEC-18) | CF-9 | fixed: the owner's VPS testing stack (Dokploy, tailnet only) ran the simulation suites by script on 2026-10-18 (L-24): every view and sub-tab in light and dark for admin, researcher, viewer and stranger with axe WCAG AA (90, 16/16), every view at 375 px (88, 11/11), decision-model settings and project assurance (91, 10/10), decider evidence in Ensemble Health (92, 5/5) |

## Phase 8 — protocols, advisory integrations, research arm

### Design and build (S1–S4; autonomous, 2026-10-18; DEC-19)

- **Protocols.** `DeciderEndpoint.protocol` is `systemone` (TypeSafe JEV, OpenRouter, llama.cpp,
  Kev, Laya, OpenJev) or `openai_decisions`. `decider/openai_decisions.py` maps Istara's choice,
  score and yes/no questions to OpenAI's named `choice` / `score` / `predicate` questions and back
  to the same canonical distributions; a dated snapshot of the requested model counts as served.
  `tests/test_decider_conformance.py` runs one set of assertions over TypeSafe, OpenRouter and
  OpenAI stubs (same answer, key only in the header, partial vector and wrong model refused,
  429 retried with `retry-after`).
- **Advisory seam** (`services/decider_advisory.py`): `advise(project, site, subject, state,
  question)` returns `Advice` or None. Sites: I4 grounding (`agent_research._record_grounding_advice`),
  I5 `spine.verify` (and its verbalized confidence is now logged as uncalibrated, audit SV-1),
  I6 `self_check.verify_claim` (`decider_advice` on the result), I7 interview saturation, I9
  report weakest section, I11 task routing (`decider_advice` in the routing result), I12 review
  feedback, I13 ReasoningBank relevance (reorders only from trusted scopes), I14 upload
  prompt-injection screen (adds caution only, trusted scope, P ≥ 0.9).
- **I8 trajectory audit**: `core/decision/trajectory_audit.py` (pure) plus
  `decider_advisory.audit_trajectory_with_decider`.
- **Research arm** (`evals/decider_coding_eval.py`, DEC-6): yes/no per code from the codebook,
  per-code ECE/Brier/coverage at risk 0.10, error correlation and Yule's Q with each LLM coder,
  Fleiss κ without and with the decider; `counted_in_reliability_gate: false`.

| ID | Sev | Dim | Where | Finding | CF task | Status |
|----|-----|-----|-------|---------|---------|--------|
| F-43 | Major | Bugs | `services/adaptive_interview._is_saturated` | `"SATURATED" in content` is true for "NOT_SATURATED", so with the LLM saturation check on, every probe ended as saturated (the W5 test noted it) | CF-10 | fixed: `saturation_verdict` reads only an explicit SATURATED; regression in `test_decider_advisory.py` |
| F-44 | Major | Tests | toolchain | conformance and advisory tests need httpx and the database | CF-10 | fixed: CI run 39118127320 backend-test success (L-23) |
| F-45 | Minor | Integration | I8 | No per-transition tool log exists to feed the trajectory audit automatically | CF-10 | accepted-risk: service function shipped; wiring is follow-up work |
| F-47 | Major | Bugs | `api/routes/settings.py` `_cached_llm_readiness` | On a stub-marked stack with credentialed Pi endpoints, `/api/settings/status` reported `chat_ready: false` (it read only legacy model-server nodes), so status bars and the simulation suite treated a chat-capable stack as unable to chat | CF-10 | fixed (`76d248dc`): passive credential check of configured endpoints; local ones skipped on stub stacks, as the legacy resolver does; test in `test_settings.py` |
| F-48 | Minor | Quality | `settings/UpdateChecker.tsx` | "Up to date" line was `text-green-600` on white (about 3.3:1, below WCAG AA) | CF-10 | fixed (`9351496d`) |
| F-49 | Minor | Integration | `frontend/src/lib/runtimeConfig.ts` | With no `NEXT_PUBLIC_API_URL`, a page on a default port (80/443) calls the API at `:8000`; behind Caddy on 443 that host has no API. Pinned by `runtimeConfig.test.ts`, so it is a product decision, not a silent fix | — | false-positive for production: `docker-compose.yml` and `frontend/Dockerfile` always set `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`), so the port fallback only applies to builds without it, such as the VPS testing stack, which uses explicit ports |
| F-46 | Minor | Integration | Cloudflare | No adapter: official page unreachable (R39) | CF-10 | accepted-risk (DEC-19) |

## Summary (whole plan)

**Outcome against the S0 goal.** Istara now has the thesis's missing Layer 2: a provider-neutral
typed-decider layer with JEV primary. Deciders are reached through one adapter
(`systemone`: TypeSafe JEV, OpenRouter, llama.cpp-style servers with Kev, Laya or OpenJev;
`openai_decisions`: OpenAI) under a per-project cloud-egress opt-in, every verdict is a stored
trajectory, trust is earned per project scope from human labels (n_eff ≥ 50, ECE ≤ 0.05,
κ ≥ 0.60, order flip ≤ 5%, τ* = 0.90) with drift returning a scope to shadow, and deciders
never accept or promote evidence or count as coders. Researchers choose an assurance mode per
project (Automatic, LLM judges, decision models, both side by side, none), configure deciders in
Settings and Project Settings with onboarding and first-activation guidance, and see evaluator
health against their own reviews. Autoresearch's keep rule is now a confirmed Welch interval
over a re-measured incumbent, with no fabricated scores, and has a `decision_policy` loop.

| Phase | Shipped | CI evidence |
|---|---|---|
| 0 Math core | calibration, decision rule, reliability, ensemble estimators | L-8 |
| 1 Adapter + JEV | contract, client, registry, Keychain/env keys, egress rule | L-10 |
| 2 Trajectories + trust gate | store, labels, blind audit, cross-fitted gate | L-12 |
| 3 Assurance modes | five modes, Thompson sampling on human outcome (AV-1) | L-14 |
| 4 Spine seam | code-application triage, routed-first review queue | L-16 |
| 5 Learning + health | re-evaluation, CUSUM drift, lessons, health metrics | L-18 |
| 6 Autoresearch | AR-1…AR-8 fixed, `decision_policy` runner | L-21 |
| 7 Onboarding + UX | settings, project assurance panel, onboarding, health panel | L-21 |
| 8 Protocols + integrations | OpenAI Decisions, advisory seam I4–I14, trajectory audit, research arm | L-23 |

**Findings.** F-1…F-46 are disposed in their phase registers: all Blocker and Major findings are
fixed except F-40 (accepted-risk). Accepted risks: F-40, F-45, F-46, and CI-1 and CI-2 (CI
defects outside this plan, handed to the separate CI-fix session).

**Residual risk (read before relying on it).**
1. **No live run yet.** Every decider call in tests is a stub; no JEV, OpenRouter, OpenAI or local
   server has been called (AGENTS.md §9). A first calibration run needs owner permission and a key.
2. **No UI walk** by role, theme, 375px and keyboard (F-40). Typecheck, lint, unit tests, build and
   scenario import are green; the walk needs the QA lane.
3. **Self-review only.** The owner forbids subagents; no independent S3 review was run, so review
   coverage is self-only (CLAUDE.md). Security-relevant parts (AI-005: egress, keys, injection
   screen) are self-verified.
4. **Advisory scopes mostly unlabelled.** Only `task_output` advice (I5) and code-application
   triage get exact human labels; the other sites record measurements that cannot become trusted
   until a label path exists (DEC-11, DEC-19).
5. **OpenAI Decisions is a public beta** read from its guide only; its reference page returned 404,
   so refusal and usage shapes are unconfirmed (fail closed). No Cloudflare adapter (F-46).
6. **Branch not merged.** All work is on `feat/decision-model-judge`; no PR was opened.

**Retro (blameless).** Worked: one lifecycle file and one ledger let the work resume after a
usage-limit pause from the working tree alone; pure math first made later phases cheap to test
locally; a single advisory seam kept eleven integrations to one failure mode. Did not work: the
local stand-ins for CI (collapse heuristic, Python 3.9 runner) missed two ruff shapes and two
source-contract tests (F-37, F-41, F-42), costing three CI rounds; scanning the repository's own
guard tests (`tests/pi_production/`, `test_self_improvement_artifact_boundary.py`) before
refactoring a shared surface would have caught them. Change obligations (persona, governed tests)
were met reactively; checking `check_change_obligations.py` before the first commit of a phase
is cheaper.
