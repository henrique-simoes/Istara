# Research-Validity Architecture Contract

Spec: CF-SPEC-124 / CF-1590

This contract is non-negotiable for future Istara changes. It turns the
scientific research workflow into a product architecture contract, not a
best-effort prompt convention.

## System-Wide Research Spine

Audio profiles are governed inputs to this spine, not a shortcut around it:
interview, microphone, and channel transcription preserve raw audio
segments/provenance and remain provisional until reliability, reconciliation,
and human review gates pass.

Istara is a research system before it is a collection of features. Every
feature that ingests, creates, processes, retrieves, summarizes, validates,
visualizes, routes, promotes, or reports research data is an extension of the
same research-validity spine. Features do not get separate research objectives
or parallel shortcuts just because they live under a different menu.

This applies to skills, task creation and execution, ReAct/tool calls, chat,
documents, interviews, surveys, AURA-style research, integrations, deployments,
interfaces, autoresearch, self-evolution, RAG/GraphRAG, compute donation,
benchmarks, simulations, and future feature surfaces. Data enters Istara as
source material, becomes evidence units, is coded independently by model or
human coders, passes reliability/reconciliation gates, and only then can become
accepted evidence for downstream findings, tasks, and reports.

Compass Forge impact output is the starting map for change radius, not a
substitute for architectural judgment. Agents must follow dependencies and
feature relationships until every research-data path is accounted for. If a
path creates raw findings, synthetic benchmark evidence, interface/design
evidence, deployment insights, survey findings, chat claims, or skill outputs
without entering this spine, that path is architecture debt unless it is
explicitly unit-scoped, non-research, or documented as a governed exception.

## Source Of Truth Pipeline

```text
Sources
  -> Evidence Units
  -> Independent Multi-Model Atomic Extraction + Open Coding
  -> Source Span / Claim / Code / Model / Donor Comparison
  -> Fleiss / Cohen / Krippendorff + Grounding Checks
  -> Debate/Adversarial/Human Reconciliation
  -> Accepted Atoms/Nuggets
  -> Facts
  -> Insights
  -> Recommendations
  -> Task In Review
  -> Human-Approved Done
  -> Reports
```

## Hard Rules

- Qualitative coding is not keyword tagging.
- Atomic Research is not a pre-validation summary layer. Candidate atoms and
  nuggets become trusted only after source-grounded independent extraction,
  coding, reliability, and reconciliation gates.
- Models code evidence units: phrases, speaker turns, passages, survey answers,
  observations, transcript spans, tickets, diary entries, and other qualitative
  units with stable IDs and provenance.
- Each model receives the same protected qualitative coding protocol, active
  codebook, code definitions, inclusion criteria, exclusion criteria, examples,
  evidence units, reliability policy, and promotion policy.
- Model coders must work independently before reliability is computed.
- Fleiss' Kappa, Cohen's Kappa, Krippendorff's Alpha, and companion metrics are
  computed on coded evidence-unit matrices, not final-answer keyword buckets.
- A governed Research Spine coding run requires at least three distinct healthy,
  project-authorized **model identities**. Endpoint replicas serving the same
  model do not create independent raters. Public coding-run requests therefore
  require `max_coders` in the range 3–5, and selection fails closed when that
  many distinct models are unavailable.
- Every admitted coder must return a valid application for every selected
  evidence unit. Its quote must be non-empty and an exact contiguous substring
  of that resolved evidence unit's raw `source_text`; a valid unit identifier
  alone is not grounding, and synthesized or paraphrased quotes are rejected.
  One bounded repair is allowed; a still-incomplete coder is excluded. If
  complete, source-grounded coverage from the requested number of distinct
  models is not available, the run cannot accept or promote any code
  application.
- One- or two-model Self-MoA, dual-run, debate, and adversarial checks remain
  useful response-level operational signals, but they are lower-assurance
  validation, not formal Research Spine coding reliability, and cannot promote
  research artifacts.
- Three-or-more-coder runs require numeric Fleiss' Kappa and Krippendorff's
  Alpha calculated from the current run's full evidence-unit coding matrix;
  missing, stale, or non-numeric metrics fail the gate closed. Cohen's Kappa is
  retained for eligible pairwise comparisons, not substituted for the
  multi-rater gate.
- The default promotion threshold is `kappa >= 0.60` unless a governed project
  policy explicitly overrides it.
- Low-agreement unreconciled evidence cannot become accepted findings or report
  content.
- Debate and adversarial review operate on coded evidence and disagreements.
  They must carry route evidence, model identity, input/output evidence, and
  reconciliation decisions.
- Operational response-level debate/adversarial validation is allowed as a
  quality signal, but it must be labeled separately and cannot be represented as
  formal coding reliability. Only review calls linked to coding-run and
  evidence-unit handles emit coded-evidence review telemetry.
- Human review of disputed code applications is itself a reconciliation
  decision. Approving, rejecting, or revising low-agreement codes must create a
  durable project-scoped record, update the code application's reconciliation
  state, and add an Evidence Graph edge.
- Human task review is also a project-scoped research-validity signal. Approval,
  revision, and Kanban status transitions emit content-free telemetry so
  dashboards and governed learning can audit review flow without storing private
  feedback text or source content.
- Reports are produced only from accepted/reconciled evidence attached to
  approved Done tasks. In Review tasks are deliberately excluded.
- Evidence units come from raw source spans. If a generated nugget preserves an
  exact original source span it may be linked as provisional source-backed
  material; otherwise synthesized nugget prose cannot be promoted through
  governed coding as if it were raw research data.
- Visible nuggets, facts, insights, and recommendations are not automatically
  accepted report evidence. Findings list and drilldown surfaces must mark
  task-generated or manually created research artifacts as provisional until
  accepted/reconciled coded evidence and approved Done task state make them
  reportable.
- Backend authorization remains strict. Researchers do not call admin-only
  endpoints during normal UI journeys.
- Donor registration, visibility, readiness, selection, serving, and failure are
  separate lifecycle states and must be recorded separately.
- Compute route evidence and donor lifecycle telemetry are tied to the same
  project-scoped routing counters. A visible or registered donor is not proof of
  use; benchmarks must show selection and served-request evidence for actual
  model work.
- Hybrid RAG performs exact evidence retrieval. Evidence Graph / GraphRAG
  performs synthesis and traceability over validated research artifacts.
- GraphRAG cannot bypass coding, reliability gates, human review, Done-task
  gating, or report gating.
- Prompt-RAG may retrieve supporting context, but mandatory coding methodology,
  codebook, reliability policy, and promotion gates are deterministically
  injected by the coding service.
- LLMLingua/compression may reduce context, but protected protocol, codebook,
  evidence-unit, coding-matrix, reliability, promotion, route, and graph blocks
  must remain whole and in order.
- This rule applies to all compression paths, including question-aware
  LongLLMLingua-style RAG compression. If the context budget is too small,
  Istara preserves protected research-validity blocks in original order and
  marks the response over budget instead of silently truncating methodology,
  codebook, evidence schema, reliability policy, or promotion gates.
- ReasoningBank, Memento Skills, Meta-Hyperagent, self-evolution, autoresearch,
  ReAct, DAGs, and telemetry may learn from the corrected process, but they
  cannot silently rewrite methodology or promote unreviewed evidence.
- Self-improvement systems follow
  `docs/architecture/self-improvement-governance-contract.md`: telemetry is
  observation, ReasoningBank is process memory, Memento learns from
  verified/spine-valid outcomes, autoresearch produces sandboxed proposals,
  Meta-Hyperagent variants are project-scoped read-time overrides, and
  self-evolution applies only governed promotions.
- Raw tool success, ReAct success, manual skill success, autoresearch "kept"
  candidates, and graph/retrieval hits are not accepted research quality by
  themselves. They can create process telemetry or candidate/provisional
  artifacts only until verification, reliability/reconciliation, review, and
  report gates accept them.

## Implementation Anchors

- Contract/protocol helpers: `backend/app/core/research_validity.py`
- Evidence/coding graph models: `backend/app/models/research_validity.py`
- Code-application audit handles: `backend/app/models/code_application.py`
- Project-scoped inspection API: `backend/app/api/routes/research_validity.py`
- Governed coding-run orchestration:
  `backend/app/services/research_validity_service.py`
- Protected compression policy: `backend/app/core/context_policy.py`,
  `backend/app/core/prompt_compressor.py`
- Exact-evidence retrieval metadata: `backend/app/core/rag.py`
- Review UI evidence: `frontend/src/components/findings/CodeReviewQueue.tsx`

## Coding-Run Orchestration

`run_independent_coding_run` is the product path for model coding over
evidence units. It selects distinct healthy project-authorized model identities
through Compute Manager, injects the protected protocol/codebook/evidence-unit
blocks, asks each coder to return structured qualitative code applications,
admits only applications whose returned quote exactly occurs in the referenced
raw evidence unit, persists coder route evidence, computes the reliability gate, and marks code
applications as accepted, needs reconciliation, needs human review, or blocked.
Researchers may start project-scoped runs through
`POST /api/research-validity/{project_id}/coding-runs`; the route requires
researcher project access and carries no admin-only dependency.

## Reconciliation Decisions

`ReconciliationDecision` records are the durable substrate for human,
debate, or adversarial resolution. A decision records the project, task,
coding run, evidence unit, code application, previous state, resolved state,
reviewer, rationale, and route evidence inherited from the original code
application. Review actions in `CodeReviewQueue` call the project-scoped code
application review route, which creates the reconciliation decision and links it
back into the Evidence Graph with a `reconciled_by` edge.

A low-agreement task remains blocked while any task-linked code application is
still unreconciled. Once researchers accept at least one grounded code and
reject or revise the conflicting alternatives, the coding run can move to
`accepted_after_reconciliation`; reports may then use the accepted/reconciled
evidence while rejected alternatives remain audit-visible.

Task-generated research carries the same chain as first-class data. When an
agent skill stores nuggets for a task, Istara creates task-linked evidence
units and evidence-graph edges, then starts a governed coding run over those
units. The run writes its reliability status into task validation metadata and
sets `what_to_review` when reconciliation or human review is needed. Task
atomic snapshots expose coding runs, accepted code counts, and blocked review
items so the Kanban review surface can explain why work is awaiting review.

All task creation surfaces share the same project-scope premise. API, Kanban,
chat, and LLM-callable system-action tools create project-bound work items;
they do not create report evidence by themselves. Attached input documents must
belong to the active project before a task can reference them, and legacy tool
priority names are normalized to the canonical task priority set before storage.
Evidence units, coding runs, and reportability begin only when a task execution
or governed coding action produces task-linked research artifacts.

Report routing checks the same gate. Human approval still controls Done, but
Done alone is not enough for report content when a task has task-linked coding
runs, code applications, or task-linked findings. Aggregate run-level kappa,
task-level accepted counts, and "one accepted code exists" diagnostics never
bulk-promote every finding on the task. Each report dependency must trace
through accepted/reconciled evidence units and any nugget/fact/insight/
recommendation parent chain before it can be included. If code applications are
still unreconciled, if any requested report dependency lacks accepted support,
or if no accepted/reconciled coded evidence remains after review, report routing
and explicit task-report creation are blocked until review/reconciliation fixes
the research-validity state.

## Retrieval Contract

Hybrid RAG is responsible for exact evidence recall: source, page/section,
span/offset, participant, method, evidence-unit ID, codebook version, review
status, and reliability status. Evidence Graph / GraphRAG is responsible for
cross-document synthesis: themes, contradictions, dependencies, and traceability
queries such as which reports depend on a codebook version or low-agreement
codes. Graph answers must backfill exact evidence through Hybrid RAG before
promotion.

The project-scoped traceability route
`GET /api/research-validity/{project_id}/traceability` is the audit substrate
for those GraphRAG questions. It joins reports, finding IDs, task-linked coding
runs, code applications, reconciliation decisions, and evidence graph edges so
Istara can answer which reports or tasks still depend on low-agreement evidence.
It is read-only, honors project access, records `graph+hybrid` retrieval
telemetry, and does not promote or synthesize new findings by itself.

## Telemetry Contract

Research-validity telemetry is content-free. Spans may store handles such as
project ID, task ID, coding run ID, evidence unit ID, codebook version ID,
route ID, donor ID, model name, retrieval mode, reliability score, operation,
status, and timestamps. They must not store prompts, responses, source quotes,
document bodies, URLs, tokens, or connection strings.

The canonical telemetry taxonomy is exposed from
`GET /api/research-validity/contract` as `telemetry_contract`. Project-scoped
audit summaries are exposed from
`GET /api/research-validity/{project_id}/telemetry-audit`; the route requires
project viewer access and returns operation counts, category counts, donor
lifecycle counts, retrieval modes, route evidence handles, coding run IDs,
evidence unit IDs, codebook version IDs, and reliability-score summaries.

The taxonomy covers the corrected lifecycle:

- Evidence extraction: `evidence_unit.extract`
- Codebook governance: `codebook.generate`, `codebook.freeze`,
  `codebook.revise`
- Coding reliability: `coding_run.start`, `coding_run.model_selected`,
  `coding_run.reliability`, `coding_run.low_consensus`,
  `coding_run.complete`
- Review/reconciliation: `debate.review`, `adversarial.review`,
  `reconciliation_decision.create`, `human_review.decision`,
  `kanban.status_transition`
- Donor lifecycle: `donor.registered`, `donor.visible`, `donor.reachable`,
  `donor.ready`, `donor.selected`, `donor.served`, `donor.failed`
- Retrieval traceability: `retrieval.hybrid`, `retrieval.graph`,
  `retrieval.graph_hybrid`, `evidence_graph.traceability`,
  `prompt_rag.context`
- Context safety: `compression.protected_block`
- Promotion gates: `finding.promotion`, `report.promotion_gate`
- Governed learning: `autoresearch.validity_update`,
  `self_evolution.proposal`, `reasoning_bank.lesson`,
  `memento_skill.health`, `meta_hyperagent.proposal`

`finding.promotion` is emitted only when a task-backed finding has crossed the
approved Done-task/reportability gate. Raw finding creation and In Review work
remain visible for review, but they are not promoted report evidence.

This telemetry can inform Quality Dashboard, Autoresearch, ReasoningBank,
Memento Skills, Meta-Hyperagent, and self-evolution. It is audit evidence and
process feedback; it is not report evidence and cannot bypass coding,
reliability, reconciliation, human review, or Done-task gates.

## Bibliography Anchors

- Fleiss, J. L. (1971). "Measuring nominal scale agreement among many raters."
  DOI: https://doi.org/10.1037/h0031619
- Cohen, J. (1960). "A coefficient of agreement for nominal scales."
  DOI: https://doi.org/10.1177/001316446002000104
- O'Connor, C., & Joffe, H. (2020). "Intercoder Reliability in Qualitative
  Research: Debates and Practical Guidelines."
  DOI: https://doi.org/10.1177/1609406919899220
- MacQueen, K. M., McLellan, E., Kay, K., & Milstein, B. (1998). "Codebook
  Development for Team-Based Qualitative Analysis."
  DOI: https://doi.org/10.1177/1525822X980100020301
- Wang et al. (2024). "Mixture-of-Agents Enhances Large Language Model
  Capabilities." https://arxiv.org/abs/2406.04692
- Du et al. (2023). "Improving Factuality and Reasoning in Language Models
  through Multiagent Debate." https://arxiv.org/abs/2305.14325
- Li et al. (2025). "Rethinking Mixture-of-Agents: Is Mixing Different Large
  Language Models Beneficial?" https://arxiv.org/abs/2502.00674
- Borzunov et al. (2022). "Petals: Collaborative Inference and Fine-tuning of
  Large Models." https://arxiv.org/abs/2209.01188
- Lewis et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive
  NLP Tasks." https://arxiv.org/abs/2005.11401
- Edge et al. (2024). "From Local to Global: A Graph RAG Approach to
  Query-Focused Summarization." https://arxiv.org/abs/2404.16130
- Microsoft Research GraphRAG / LazyGraphRAG / DRIFT documentation:
  https://www.microsoft.com/en-us/research/project/graphrag/
- Jiang et al. (2023). "LLMLingua: Compressing Prompts for Accelerated
  Inference of Large Language Models." https://arxiv.org/abs/2310.05736
- Jiang et al. (2023). "LongLLMLingua: Accelerating and Enhancing LLMs in Long
  Context Scenarios via Prompt Compression." https://arxiv.org/abs/2310.06839
- Sharon & Gadbaw, "Atomic Research." https://www.atomicresearch.io/

## Test Contract

Product-level synthetic UX research tests use
`tests/document_corpus/canonical/` through `tests/document_corpus/shared-corpus.mjs`.
Tiny fixtures are allowed only for parser/unit tests and must be labeled that
way. Tests that exercise findings, coding, reports, simulations, benchmarks,
skills, RAG, GraphRAG, or real-user flows must validate evidence-chain,
reliability, route-evidence, review, and report-gate behavior against this
contract.
