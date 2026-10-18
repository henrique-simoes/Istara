# Typed Decision Models as Judges in Istara: Mathematics, Learning Loop, and Spine Placement

Spec: CF-SPEC-1 (local Compass Forge state, branch `feat/decision-model-judge`). Lifecycle:
`docs/build-stream/2026-10-17-decision-model-judge.md`. References: `decision-model-references.md`
(numbered `[R#]` below). Status: research design, written at S0 on 2026-10-17. Nothing here is
implemented yet; it states what the implementation must satisfy and why.

This document extends Section "Modelos de decisão tipados e classificação seletiva" of the owner's
specialization thesis [R1] (thesis equations are cited as *T-Eq. n*). Its purpose is to be reusable
in articles and in a revised thesis. Every claim about Istara code cites a file. Every external claim
cites a reference that was read, or is marked as known only from an abstract.

---

## 1. Problem statement

The thesis defines four evaluation layers (Tabela 4): deterministic checks, a typed decider, a
generative judge (advisory, no isolated veto), and human adjudication. As of 2026-10-17 Istara
implements layers 1, 3 and 4, but not layer 2:

| Layer | Present in Istara | Anchor |
|---|---|---|
| 1 Deterministic | yes: exact-substring grounding; coder quote admission | `services/finding_grounding.py`, `services/research_validity_service.py` |
| 2 Typed decider | **no** | none |
| 3 Generative judge | yes: operational validation, adversarial review, answer-eval judges | `core/validation.py`, `core/validation_executor.py`, `evals/answer_eval.py` |
| 4 Human | yes: reconciliation decisions, Done-task gate | `models/research_validity.py`, `CodeReviewQueue.tsx` |

The owner's additional requirements (2026-10-17):

1. JEV is the primary decider, reached through its API. Other decision models must be usable
   through one universal process.
2. Decisions and their human-reviewed outcomes are stored as trajectories that ReasoningBank and
   self-evolution can learn from, so that future decisions improve.
3. Users choose an *assurance mode*: LLM judges only (Self-MoA, two or more judges, ensemble),
   decision models only, or both.
4. Decision models take part in autoresearch hill climbing, and that loop is audited for defects.
5. The whole design reduces hallucinations that originate in deciders or LLM judges, and it is
   monitored as part of ensemble health.

---

## 2. The decider as a function

Following *T-Eq. 5–6*, a decider is a map $f_\theta : X \to \Delta^{K-1}$ from an input (task
context, item state, rubric) to the probability simplex over a closed decision set
$Y=\{y_1,\dots,y_K\}$. Hosted deciders do not expose logits. Istara receives a probability vector
$\tilde p(x)$ (JEV: `answers[id].probabilities`, which sum to 1 [R2]) and recovers scores up to an
additive constant, $z_k = \log \tilde p_k(x)$, which is all softmax needs.

**Calibrated probabilities** (temperature scaling, Guo et al. [R10]; *T-Eq. 6*):

$$
p_k(x;T_s)=\frac{\exp(\log\tilde p_k(x)/T_s)}{\sum_j \exp(\log\tilde p_j(x)/T_s)}=\frac{\tilde p_k(x)^{1/T_s}}{\sum_j \tilde p_j(x)^{1/T_s}}
$$

$T_s>0$ is fitted per **trust scope** $s=(\text{provider},\ \text{versioned model},\ \text{question-set version},\ \text{task family},\ \text{language})$.
The transform is monotone, so it preserves the argmax and therefore accuracy. Only the
probabilities change, as the thesis notes for Laya.

**Why scope includes the model version.** TypeSafe aliases (`jev-latest`, `jev-preview`) move
between releases, and the docs tell clients that tune confidence thresholds to pin the versioned id
[R3]. A new version starts in a new, untrusted scope.

**Why scope includes language.** Laya's model card reports accuracy 0 at mean confidence 0.952 on
Khmer [R1, R19]. JEV documents English as its primary language [R3]. Calibration measured on English
says nothing about Portuguese, the owner's research language.

**Confidence as returned by the provider is not used for decisions.** JEV's `confidence` is a
dispersion statistic of the distribution, not a calibration claim. For a choice it is
$(p_{\max}-1/n)/(1-1/n)$; for a score it is $1-\sum_i p_i|i-m|/\mathrm{MAD_{unif}}$ [R4]. Istara
logs it for audit and recomputes $\hat c(x)=\max_k p_k(x;T_s)$ from the calibrated vector.

---

## 3. Decision rule: Bayes risk with a reject option

Let $L(y_k,y_j)$ be the cost of predicting $y_j$ when the truth is $y_k$ (*T-Eq. 7*). The
minimum-risk prediction is

$$
\hat y^*(x)=\arg\min_j \sum_{k} L(y_k,y_j)\,p_k(x;T_s).
$$

With a reject (abstain-to-human) action of cost $C_R$ and a uniform error cost $C_E$, Chow's rule
[R11] (*T-Eq. 8*) rejects when $1-\hat c(x) > C_R/C_E$, so $\tau = 1 - C_R/C_E$. In the binary case,
with costs $C_{FP}$ (a hallucination accepted as evidence) and $C_{FN}$ (a valid inference sent to an
analyst), the optimal acceptance threshold is $\tau^* = C_{FP}/(C_{FP}+C_{FN})$. The pre-registered
default (DEC-1) is $C_{FP}:C_{FN}=9:1$, so $\tau^*=0.90$.

**Istara-specific asymmetry: a decider never accepts.** In Istara a decider's possible actions are
*route to human review*, *raise priority*, *flag*, or *do nothing*. Acceptance and promotion belong
to the reliability gate ($\kappa \ge 0.60$), reconciliation, and Human-Approved Done
(`docs/architecture/research-validity-contract.md`). An Istara false positive is therefore "the
decider let a bad item pass without extra review". That item still faces the κ gate, so the
decider's error cannot create report evidence by itself. This bounds the worst case of a bad
decider: it can only fail to add scrutiny.

**Order invariance** (thesis LLM-as-judge protocol: blind, inverted order; JEV's documented
first-option bias [R5]). Every choice question is asked with options in order $\pi$ and in reversed
order $\pi^{R}$ in one request (JEV evaluates questions in parallel, in isolation, against the same
state [R2]). Let $\hat y^{\pi}, \hat y^{\pi^R}$ be the two argmaxes. If they differ, the item
abstains. Otherwise Istara uses the averaged vector $\bar p = (p^{\pi}+p^{\pi^R})/2$, which
estimates a position-debiased distribution in the spirit of balanced position calibration [R14].

---

## 4. Calibration as an acceptance gate

A scope is **trusted** only when, on a labelled set of at least $n_{\min}=50$ items (DEC-1):

* **ECE** with $M=10$ equal-width bins (*T-Eq. 9*; Naeini et al. [R12]) is at most 0.05;
* **Brier score** with Murphy's decomposition $BS = REL - RES + UNC$ (*T-Eq. 10*; [R8, R9]) is
  reported, and REL is the calibration term that must stay small. Murphy's identity is exact only
  when forecasts within a bin are equal; Istara reports the binned form with the two within-bin
  terms of Stephenson et al. [R37], $BS = REL - RES + UNC + WBV - 2\,WBC$, which holds exactly;
* **Cohen's κ vs labels** is at least 0.60 (the same bar the existing judge validation uses,
  `evals/answer_eval.py::validate_judges`);
* **order-flip disagreement** is at most 5%;
* the **risk–coverage curve** [R13] is reported at $\tau$.

**Calibration is necessary, not sufficient** (found while testing the Phase 2 gate, 2026-10-18).
On planted data where the reported probability equals the true probability, a decider whose latent
score has spread σ = 2 is perfectly calibrated (held-out ECE 0.013) yet right only 77% of the time,
with κ = 0.55 against labels, so the gate refuses it. At σ = 4 it reaches 87% accuracy and κ = 0.74 and
is trusted. Over-confidence (reported logit ×3) is repaired by the fitted temperature (T ≈ 3.1) and
then trusted; a constant logit shift of 2.5 is not repairable by temperature scaling and is refused on
ECE. The gate therefore separates calibration (ECE, Brier reliability) from discrimination (κ,
Brier resolution), as the thesis's Murphy decomposition suggests.

**Label mapping v1 is binary.** Istara's review control records accept / reject / revise, so v1 labels
the event "the item was acceptable to the researcher" (accept = 1; reject or revise = 0). The four-way
class of §2 (grounded evidence, speculative inference, factual hallucination, methodological
violation) needs a richer review control (Phase 7) and a v2 mapping. Until then, per-class calibration
cannot be measured, and the article should say so.

**Shadow mode** (DEC-2). An untrusted scope records verdicts but has no routing effect. A decider
can only add scrutiny, so shadow mode is the fail-closed state, and turning the feature off restores
today's behaviour exactly.

---

## 5. Trajectories: what is stored

A **decision trajectory** generalizes the agent trajectory of Wang & Gao [R7] (*thesis*:
$T=(s_0,a_0,o_0,\dots,s_H)$) from tool calls to evaluation events. For one subject (a code
application, a claim, a tool transition) it is the ordered record

$$
\mathcal{D}_i = \big(s_i,\ h_i,\ q_i,\ \{(m,\tilde p^{(m)}_i, p^{(m)}_i, T_s, \tau, a^{(m)}_i)\}_{m\in\mathcal{M}},\ \{(j, v^{(j)}_i)\}_{j\in\mathcal{J}},\ \rho_i,\ \pi_i,\ y_i^{H},\ r_i,\ t_i\big)
$$

| Symbol | Meaning | Stored as |
|---|---|---|
| $s_i$ | trust scope | ids and versions |
| $h_i$ | subject handle | project, task, coding run, evidence unit, code application ids. **No text** (telemetry contract) |
| $q_i$ | question-set version | content hash plus version; question text lives in versioned config, not per row |
| $\mathcal{M}$ | deciders run | raw vector $\tilde p$, calibrated $p$, $T_s$, $\tau$, action $a$, served versioned model id, usage, latency |
| $\mathcal{J}$ | LLM judges run (if the mode includes them) | verdict, route evidence, served model |
| $\rho_i$ | audit-sample indicator | bool |
| $\pi_i$ | probability the item reached a human | float (§6) |
| $y_i^{H}$ | human label | from `ReconciliationDecision` and the review outcome; null until reviewed |
| $r_i$ | reviewer and blind flag | reviewer id, whether the decider verdict was hidden |
| $t_i$ | timestamps | decided, reviewed |

Human labels come from records that already exist (`ReconciliationDecision.resolved_state`, code
application review, and `core/task_review.py::classify_review_feedback` categories such as
`hallucination_or_unsupported_claim` and `validation_false_positive`). The mapping from those
records to $Y$ is versioned and is itself part of the scope, so a mapping change cannot silently
re-label history.

---

## 6. Learning from human-reviewed trajectories without fooling ourselves

The owner asked that past human-reviewed decisions form "a learned path that helps increase
confidence for future decisions". Done naively, this produces three biases. Each has a remedy.

### 6.1 Selection bias: humans see only what was routed to them

If humans review only abstentions and flags, labelled data come almost entirely from the
low-confidence region. A calibration fit on them is biased, and the labels are missing not at
random. **Remedy: a blind random audit.** A fraction $\rho$ of non-routed items is sampled
uniformly and sent to review *with the decider verdict hidden* (thesis: blind comparison against a
human-review sample). Each labelled item gets inclusion probability $\pi_i = 1$ if routed, else
$\rho$. Calibration statistics use Horvitz–Thompson weights $w_i = 1/\pi_i$ [R15]:

$$
\mathrm{ECE}_w=\sum_{m=1}^{M}\frac{W_m}{W}\,\big|\mathrm{acc}_w(B_m)-\mathrm{conf}_w(B_m)\big|,\qquad W_m=\sum_{i\in B_m} w_i,
$$

with $\mathrm{acc}_w$ and $\mathrm{conf}_w$ the weighted means in bin $B_m$. Precision is reported
through the effective sample size $n_{\mathrm{eff}}=(\sum w_i)^2/\sum w_i^2$, and the trust gate
counts $n_{\mathrm{eff}}$, not $n$, against $n_{\min}$. The audit also guards against automation
bias: a reviewer who sees the machine verdict is not an independent label.

### 6.2 Optimism: evaluating on the data used to fit

$T_s$ is fitted by weighted negative log-likelihood,

$$
T_s^{*}=\arg\min_{T>0}\ -\sum_i w_i \log p_{y_i^H}(x_i;T),
$$

using **cross-fitting**: fit on $k-1$ folds, measure ECE and Brier on the held-out fold. The gate
uses the held-out numbers only.

### 6.3 Self-confirmation: "past agreement raises confidence"

Raising a decider's confidence because humans previously agreed with it on *similar* items uses
labels as features, and that inflates confidence on exactly the items where history is
unrepresentative. Istara therefore allows three legitimate channels and no others:

1. **Recalibration.** History updates $T_s$ (§6.2). Confidence rises only if held-out calibration
   shows the model was under-confident.
2. **A reliability posterior per (scope, predicted class, confidence bin)** with a Beta prior,
   which connects to the thesis's beta-binomial model (*T-Eq. 14*):
   $\text{correct}\sim\text{Binomial}(n,\pi)$, $\pi\sim\text{Beta}(\alpha_0,\beta_0)$, giving the
   posterior $\text{Beta}(\alpha_0+c,\ \beta_0+n-c)$. The routing rule uses the **lower credible
   bound** $\pi_{0.05}$ rather than the mean, so a bin with little evidence cannot look reliable.
3. **Precedents as an evaluated variant.** The $k$ nearest human-reviewed decisions (by
   question-set and codebook code, never by raw text similarity alone) may be added to the
   decider's `state` as labelled precedents. This changes the input distribution, so
   "decider + precedents (k)" is a **separate trust scope** that must earn its own calibration, and
   it is evaluated in autoresearch (§9) against plain "decider". JEV warns that irrelevant state
   costs accuracy [R5], which is exactly what the experiment measures.

### 6.4 Guaranteed thresholds (optional strengthening)

Chow's $\tau$ is optimal *if* probabilities are calibrated. When calibration uncertainty is large
(small $n_{\mathrm{eff}}$), Istara can choose $\tau$ with a finite-sample guarantee using Learn then
Test [R16]. For a grid $\tau_1>\tau_2>\dots$, test $H_{\tau}: R(\tau)>\alpha$, where $R(\tau)$ is
the error rate among non-routed items, with binomial p-values and fixed-sequence testing from the
most conservative $\tau$ downward. The result is $\Pr[R(\hat\tau)\le\alpha]\ge 1-\delta$. The
effective threshold is $\tau_{\mathrm{eff}}=\max(\tau^*,\hat\tau_{\mathrm{LTT}})$, so the guarantee
can only add caution.

### 6.5 Drift

Each trusted scope keeps a rolling weighted Brier score on new labels. A sustained rise (a one-sided
CUSUM on per-label Brier contributions, with the reference value set from the trusting evaluation)
returns the scope to shadow mode and records why. Drift detection is observation; it never
loosens a gate.

---

## 7. Ensemble health: deciders and LLM judges share one error model

Rao & Callison-Burch [R6] report that over 85% of flash-tier LLM verdicts on a decision model's most
confident errors *repeat* that error (independence would give about half), and that a decider→LLM
cascade gains at most 2.7 points over the best single judge, even with oracle thresholds. Kim et
al. [R17] find that models agree on 60% of items where both are wrong. Istara's own benchmark found
Self-MoA committees reach a mean consensus of 0.1245 (thesis axis 10). Agreement is therefore not
evidence of correctness, and "both" mode is not independent double-checking.

**What ensemble health measures**, on human-labelled items, for every evaluator $e$ in the active
mode (deciders and LLM judges alike):

* error indicator $\epsilon_{e,i} = \mathbb{1}[\hat y_{e,i}\ne y^H_i]$, weighted by $w_i$;
* pairwise error correlation $\rho_{ef}=\mathrm{corr}_w(\epsilon_e,\epsilon_f)$ and Yule's Q
  diversity statistic [R18];
* **effective number of independent evaluators**, by analogy to the design effect:
  $J_{\mathrm{eff}} = J/(1+(J-1)\bar\rho)$, where $\bar\rho$ is the mean pairwise error correlation.
  This is Istara's formulation; the 2026 preprint "Nine Judges, Two Effective Votes" [R25] studies
  the same phenomenon, but only its title was seen, so its method is not claimed here;
* per-evaluator confusion matrices estimated with Dawid–Skene EM [R20], which tolerates
  missing labels and gives each evaluator a class-conditional reliability. **Identifiability caveat
  (found in Phase 0 testing, 2026-10-17):** with binary classes, a three-evaluator panel has exactly
  as many free parameters (one prior, six error rates) as observable answer patterns, so the
  likelihood is nearly flat. On 3,000 simulated items, EM converged to a prior of 0.59 against a
  planted 0.65, with error rates off by up to 0.05. Five evaluators recovered every planted rate
  within 0.04. Estimates for small panels are therefore reported with the panel size and are never
  used for routing alone.

**Combination policy.** The default is *no automated vote has authority*: each evaluator's output is
shown, and disagreement between layers is itself a review trigger (thesis: "divergence between
agents signals the need for review; convergence without verifiable evidence is only statistical
repetition"). A learned combiner (Dawid–Skene posterior, or stacking) may only become a routing
input after it passes the same trust gate as a single decider.

**Fixing the adaptive selector.** `core/adaptive_validation.py` records an outcome as successful
when `consensus.agreement_score >= 0.5` (`core/agent_execution.py`). That rewards self-agreement, so
the selector learns to prefer the method whose outputs agree most, which is Self-MoA (copies of one
model). This conflicts with the governance rule that learning signals are "never self-certified"
(`docs/architecture/self-improvement-governance-contract.md`). The reward must come from the human
outcome of the task: approved without a `validation_false_positive` or
`hallucination_or_unsupported_claim` review category. Method choice becomes a Beta–Bernoulli
Thompson-sampling bandit [R21] per (project, skill, mode), constrained to the methods the user's
assurance mode allows (§8).

---

## 8. Assurance modes (user-selectable)

| Mode | LLM judges | Deciders | Notes |
|---|---|---|---|
| `auto` (today) | adaptive (Self-MoA / dual / ensemble by available models) | per project config | current behaviour plus deciders when trusted |
| `llm_judges` | user-chosen: Self-MoA, 2 judges, N ≥ 3 judges, debate, adversarial | off | Self-MoA remains the automatic fallback with one endpoint |
| `decision_models` | off | user-chosen deciders | no LLM-as-judge calls at all; uncertain items go to human review |
| `both` | user-chosen | user-chosen | outputs reported side by side; error correlation shown in ensemble health |
| `none` | off | off | validation skipped and labelled `unvalidated`; human review still required (agents never mark Done) |

Scope (DEC-6, corrected 2026-10-18): modes govern *operational validation* of skill outputs
(`services/operational_validation.py`, which calls `core/validation.py`) and the research-quality
skill's LLM-judge calls. An earlier draft also named `core/validation_executor.py`; Phase 3
orientation found that it is not called by product code. Modes do not replace the formal coding-run
reliability gate, which requires three or more distinct model coders
and computes Fleiss/Krippendorff on evidence-unit matrices. A decider is not a coder (Invariant 2 in
the lifecycle file; [R6]).

---

## 9. Autoresearch: deciders as both subject and instrument

**As subject.** A new runner, `decision_policy`, mutates question wording, criteria, option order,
selected `state` fields, and precedent count $k$ for a scope. Its objective is the **held-out
weighted Brier score** on human-labelled trajectories, which is a strictly proper scoring rule
[R8]: the knobs cannot raise it without improving probability quality. This follows governance
critique #11, which rejected objectives the tuned parameters can inflate. Coverage at fixed risk
$\alpha$ is reported beside it. Kept candidates remain governance proposals.

**As instrument.** Several runners score candidates by asking an LLM for "ONLY a decimal number"
and parsing the first float (`autoresearch_runners/skill_prompt.py`, `model_temp.py`,
`question_bank.py`). A decider `score` question returns a full distribution over declared rubric
levels, which removes the parsing failure mode and gives a variance estimate per measurement. Which
instrument scores a runner follows the project's assurance mode.

The audit of the current loop is in `autoresearch-hill-climbing-audit.md`. Its statistical fix
uses paired measurement of the incumbent and the candidate under common inputs, a
t-distribution interval on the *paired difference*, and confirmation of the best candidate on
held-out inputs to counter the winner's curse of taking a maximum over noisy iterations.

---

## 10. ReasoningBank and self-evolution

* **ReasoningBank** (`core/reasoning_bank.py`) receives *decision lessons* only after a human label
  exists, under a new process-only source kind `decision_review`. Lessons are aggregate and
  content-free, for example "scope S over-confident on negated statements; order-flip rate 9%".
  They are weak priors for question design and routing, never evidence (spine notice in
  `reasoning_bank.py`).
* **Self-evolution** may *propose* question-set revisions and project-scoped τ policy overrides
  through improvement governance. The protected values (κ ≥ 0.60, the ECE ceiling, $n_{\min}$, and
  the rule that deciders never promote) are research methodology and cannot be auto-promoted
  (governance contract rule on protected methodology; critique #10).
* **Telemetry** follows OpenTelemetry GenAI conventions (AGENTS.md §7). Span names and attributes
  are a design detail for S1, under `gen_ai.operation.name` plus `gen_ai.evaluation.*` for verdicts.

---

## 11. Other integration points found in the architecture survey

Ranked by research-validity value. The first three are in this plan; the rest are candidates
(owner question Q2).

| # | Site | Today | Decider form | Spine relevance |
|---|---|---|---|---|
| I1 | code-application triage (`research_validity_service.py`) | none | choice: relation-to-span; choice: epistemic status; noul: codebook criteria | direct |
| I2 | autoresearch scoring (`autoresearch_runners/*`) | free-text float parse; 0.5 on failure | score | process |
| I3 | ensemble health / validation modes (`validation.py`, `adaptive_validation.py`) | self-agreement reward | deciders as evaluators | direct |
| I4 | claim/citation check after exact match (`finding_grounding.py`, chat answers) | exact match only | choice: supports / contradicts / says_nothing [R2 cookbook] | direct |
| I5 | `spine.verify` (`agent_research.py`) | LLM verbalized `"confidence": 0.85`; verbalized confidence is poorly calibrated [R22] | noul / choice with calibrated p | direct |
| I6 | `spine.self_check` (`self_check.py`) | HIGH/MEDIUM/LOW enum | score | direct |
| I7 | interview saturation (`adaptive_interview.py`, `channel.saturation`) | "SATURATED"/"NOT_SATURATED" text | noul | data collection |
| I8 | agent trajectory audit (Wang & Gao [R7]) | none | per-transition noul/choice | process |
| I9 | report weakest-section loop (`report_manager.py`) | LLM 0–10 score | score | report (after gates) |
| I10 | UI audit heuristics (`ui_audit_agent.py`) | LLM | score per heuristic | non-research |
| I11 | task specialty routing (`task_router.py`) | keyword counts | choice (intent routing) | process |
| I12 | review-feedback categories (`task_review.py`) | keyword rules (deliberately deterministic) | choice as a refinement, never replacing the deterministic floor | learning labels |
| I13 | ReasoningBank retrieval relevance | lexical overlap | noul rerank | process |
| I14 | prompt-injection screening (`content_guard.py`) | rules | noul (alignment-failure detection [R24]) | security; needs the security benchmark |

---

## 12. Threats to validity (for the article)

* **Correlated errors** between deciders and judges [R6, R17] limit what any automated layer adds.
  Human adjudication stays the final authority.
* **Vendor opacity.** JEV's weights and RLCD objective are not public [R3, R24]. Istara treats it as
  a black box and validates it empirically per scope.
* **Label quality.** Human reconciliation labels are themselves fallible (O'Connor & Joffe: agreement
  is not validity [thesis refs]). Audit-sample reviews are blind to reduce anchoring.
* **Small samples.** Per-scope trust needs $n_{\mathrm{eff}}\ge 50$. Many projects will stay in
  shadow mode for a long time, which is the intended safe behaviour.
* **Conflict of interest.** As in the thesis, the author builds and evaluates the system. Code and
  data stay public, and runs that could not execute stay visible as `not_runnable`.

---

## 13. Can a decider *code*? (owner question Q1, researched 2026-10-17)

**Mechanics.** Yes, for **deductive** coding. A codebook code is already a closed decision. Istara's
codebook carries exactly what a decider question needs (spine hard rule: code definitions,
inclusion criteria, exclusion criteria, examples):

* **Multi-label codes:** one `noul` per code over the evidence unit. `instructions`: "Does this
  evidence unit express code ‹label›?"; `criteria.true` = definition + include examples;
  `criteria.false` = exclusion criteria + exclude examples [R2]. Each code gets an independent
  $P(\text{code}\mid u)$, which is not a distribution over codes.
* **Mutually exclusive code sets:** one `choice` over the codes plus `none_of_these`, asked in both
  option orders (§3).
* **Selective coding:** apply a code when its calibrated probability clears $\tau$ (§3), abstain to
  human in a review band, and never apply below it. This is the reject option applied per code.

**What a decider cannot do.** It cannot do *open/inductive* coding (create codes) or produce the
*quote* the spine requires. Spine hard rule: every application carries an exact contiguous substring
of the evidence unit. A decider can only **select among candidate spans** (a `choice` over
pre-segmented spans, the "extraction becomes choice over options" pattern [R5]). So a decider
coder would need deterministic span segmentation first.

**Prior art.**

| Line of work | Representative sources | Relevance |
|---|---|---|
| LLM deductive coding with a codebook | Xiao et al. 2023, IUI [R30]; Chew et al. 2023, LACA [R31]; QualiGPT 2024 [R32] | fair-to-substantial agreement with experts; codebooks need rewording for models; LACA flags codes where the model is guessing |
| Encoder (non-generative) zero-shot classification with codebook hypotheses | Laurer, van Atteveldt, Casas & Welbers 2023, *Political Analysis*, DOI 10.1017/pan.2023.20 [R33]; Hu et al. ACL 2024 [R34]; codebook-LLMs (PolMeth 2024) [R35] | closest methodological ancestor of typed deciders: closed-set scoring of hypotheses built from codebook definitions |
| Typed decision model applied to a codebook | `gbesse/jev-codebook` (MIT, independent, 2026) [R36] | the same noul-per-code / choice mechanics as above; per-code thresholds tuned on labelled data; **no benchmark claimed** |

**Novelty.** No peer-reviewed evaluation of *typed decision models* (JEV-class, RLCD-trained, with
calibrated probabilities) for qualitative coding was found on 2026-10-17. The literature covers
generative LLM coders and NLI encoders. Three contributions appear open:

1. **Selective deductive coding with calibrated abstention.** Code-level risk–coverage curves,
   showing which codes a decider can apply reliably and which must stay with human or LLM coders
   (LACA's "random-guessing codes" made quantitative with ECE/Brier).
2. **Reliability with a non-independent rater.** Measuring how much a decider rater inflates Fleiss'
   κ or Krippendorff's α when its errors correlate with the LLM coders' errors [R6, R17]. Concretely:
   compare κ computed with and without the decider, and compare against human gold codes.
3. **Portuguese-language calibration** of decider coders, which the thesis lists as future work.

**Recommendation.** Do not change the spine gate yet. Add a **decider-coder research arm**: on the
canonical corpus with human gold codes, run decider coding alongside the LLM coders and report
per-code calibration, risk–coverage, error correlation with each LLM coder, and κ/α with and without
the decider. The decider codes are recorded and never counted in the gate. A spine change (for
example, allowing a trusted decider as one of three raters) is decided later from that evidence.
