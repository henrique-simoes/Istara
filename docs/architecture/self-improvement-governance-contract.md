# Self-Improvement Governance Contract

Spec: CF-SPEC-132

Istara may improve itself only to improve the Research Spine: source evidence
quality, coding reliability, traceability, review quality, route evidence, and
report grounding. Self-improvement artifacts are not report evidence unless
they create research artifacts that pass the normal spine.

## Contract Flow

```text
Telemetry observes process events
  -> ReasoningBank stores process lessons
  -> Memento Skills stores validated skill routing/execution memory
  -> Autoresearch runs sandboxed experiments and produces proposals
  -> Meta-Hyperagent proposes project-scoped policy/parameter variants
  -> Self-evolution promotes only governed, project-scoped improvements
  -> RAG/BM25 retrieves exact evidence with provenance
  -> GraphRAG traces/synthesizes dependencies
  -> Prompt-RAG and LLMLingua manage context
  -> Research Spine gates decide accepted evidence and reports
```

## Non-Negotiable Rules

- Telemetry is content-free observation, not evidence.
- ReasoningBank is process memory only; it may provide weak routing priors but
  cannot become report evidence.
- Memento Skills may learn strongly only from verified or Research
  Spine-valid outcomes, not raw tool success.
- Autoresearch mutations must be sandboxed and reverted after measurement.
  Kept candidates become governance proposals; production changes require
  approval.
- Meta-Hyperagent variants are project-scoped and consulted at read time. They
  must not mutate module globals for project-specific evidence.
- Self-evolution may promote only project-local, governed patterns and must not
  rewrite protected methodology, thresholds, auth constraints, or report gates.
- Hybrid RAG/BM25 retrieves exact source context and must preserve
  `evidence_unit_id`, source span, document id, review status, reliability
  status, and provenance where available. Missing provenance makes keyword
  fallback non-promotional.
- GraphRAG is synthesis and traceability; it fails closed if task/report gates
  or evidence dependencies are missing.
- Prompt-RAG and LLMLingua are context tools. Mandatory coding methodology,
  codebooks, reliability policy, promotion gates, route/evidence schemas, and
  auth constraints are injected deterministically and protected from
  compression.

## Scientific Mapping

| Source | Implementation implication | Istara contract |
|---|---|---|
| ReasoningBank, arXiv:2509.25140 | Distill successful and failed experience into reusable reasoning memory. | Store process lessons with project scope; use them as weak priors only. |
| Memento-Skills / Memento 2, arXiv:2603.18743 | Skills evolve through read-write-reflect memory. | Update skill health from verified/spine-valid outcomes, not raw execution success. |
| Hyperagents / DGM-H, arXiv:2603.19461 | Self-improvement requires evaluation archives and explicit variants. | Meta-Hyperagent creates governed project variants; no silent global mutation. |
| Karpathy autoresearch | Hypothesize, mutate, measure, keep/revert in a bounded loop. | Mutations run in sandbox and are reverted; "kept" means proposal-ready, not live. |
| RAG, arXiv:2005.11401 | Retrieval grounds generation with external knowledge. | Hybrid RAG supports exact evidence lookup; it never validates evidence by itself. |
| Microsoft GraphRAG / DRIFT / LazyGraphRAG | Graph search supports global/local synthesis and relationship traversal. | Evidence Graph/GraphRAG traces dependencies and must backfill exact evidence through Hybrid RAG before promotion. |
| LLMLingua / LongLLMLingua / LLMLingua-2 | Compression reduces context cost while preserving task-critical information. | Protected protocol/codebook/gate/schema blocks survive compression and trimming. |

References: [ReasoningBank](https://arxiv.org/abs/2509.25140),
[Memento-Skills](https://arxiv.org/abs/2603.18743),
[Hyperagents](https://arxiv.org/abs/2603.19461),
[Karpathy autoresearch](https://github.com/karpathy/autoresearch),
[RAG](https://arxiv.org/abs/2005.11401),
[Microsoft GraphRAG DRIFT](https://microsoft.github.io/graphrag/query/drift_search/),
[LLMLingua](https://arxiv.org/abs/2310.05736),
[LLMLingua-2](https://arxiv.org/abs/2403.12968).

## Design Critique Log

1. Proposed design: let autoresearch keep live successful mutations.
   Failure mode: a noisy experiment rewires prompts/RAG before approval.
   Scientific concern: keep/revert requires bounded evaluation and rollback.
   Engineering concern: production state changes are hard to audit.
   Integration concern: Memento/telemetry may learn from unapproved behavior.
   Decision: reject. Final reason: kept means proposal-ready, not live.

2. Proposed design: let Meta-Hyperagent apply project variants to module
   globals.
   Failure mode: project A changes project B.
   Scientific concern: variant evidence is project-local.
   Engineering concern: globals cannot carry project provenance.
   Integration concern: self-evolution thresholds leak across projects.
   Decision: reject. Final reason: variants are read-time project overrides.

3. Proposed design: record skill health from `output.success`.
   Failure mode: verification-failed output boosts Memento.
   Scientific concern: success is not research validity.
   Engineering concern: skill routing learns from false positives.
   Integration concern: ReAct/manual runs bypass review gates.
   Decision: reject. Final reason: split execution, verification, quality, and reportability.

4. Proposed design: treat ReAct skill output as a successful reasoning memory.
   Failure mode: provisional claims become positive priors.
   Scientific concern: raw model synthesis is not accepted evidence.
   Engineering concern: routing bias compounds over time.
   Integration concern: chat can over-select a weak skill.
   Decision: revise. Final reason: provisional outcomes are stored but not success-boosting.

5. Proposed design: keep ModelSkillStats global.
   Failure mode: one project's model quality steers another.
   Scientific concern: model performance is context and corpus dependent.
   Engineering concern: no authorization boundary in rankings.
   Integration concern: telemetry boosts become cross-project leakage.
   Decision: reject. Final reason: stats are project-scoped.

6. Proposed design: GraphRAG allows reports when no task gate exists.
   Failure mode: taskless legacy findings look reportable.
   Scientific concern: synthesis cannot replace review.
   Engineering concern: missing data should not default allow.
   Integration concern: reports can bypass Done tasks.
   Decision: reject. Final reason: graph traceability fails closed.

7. Proposed design: BM25 fallback returns source/page only.
   Failure mode: exact evidence lookup loses reliability state.
   Scientific concern: retrieval without provenance cannot support claims.
   Engineering concern: fallback hides promotion risk.
   Integration concern: report paths cannot distinguish accepted from legacy.
   Decision: revise. Final reason: preserve provenance or mark non-promotional.

8. Proposed design: ReasoningBank can improve routing from all memories.
   Failure mode: untrusted memories become hidden evidence.
   Scientific concern: memory is process learning, not data.
   Engineering concern: weak priors need outcome classification.
   Integration concern: autoresearch proposals become skill success signals.
   Decision: revise. Final reason: only verified success/failure drives boosts.

9. Proposed design: Prompt-RAG can retrieve methodology on demand.
   Failure mode: retrieval miss removes coding protocol.
   Scientific concern: methodology must be controlled and reproducible.
   Engineering concern: opportunistic context is nondeterministic.
   Integration concern: compression may drop gates.
   Decision: reject. Final reason: services inject protected methodology deterministically.

10. Proposed design: self-evolution may auto-promote protected method changes.
    Failure mode: thresholds/auth/report gates weaken silently.
    Scientific concern: methodology changes require governance.
    Engineering concern: irreversible persona edits are hard to audit.
    Integration concern: agents can optimize around gates.
    Decision: reject. Final reason: protected Research Spine changes require governed review.

## Implementation Anchors

- Policy helper: `backend/app/core/self_improvement_policy.py`
- Autoresearch sandbox/proposal flow: `backend/app/core/autoresearch_engine.py`
- Governance evidence: `backend/app/core/improvement_governance_evidence.py`
- Meta-Hyperagent project overrides: `backend/app/core/meta_hyperagent.py`
- Self-evolution read-time thresholds: `backend/app/core/self_evolution.py`
- Skill/ReAct learning separation: `backend/app/core/agent_execution.py`,
  `backend/app/core/agent_research.py`, `backend/app/core/agent_skill_tools.py`
- Project-scoped model quality stats: `backend/app/models/model_skill_stats.py`,
  `backend/app/core/telemetry.py`
- RAG/BM25 provenance: `backend/app/core/rag.py`,
  `backend/app/core/keyword_index.py`
- Graph fail-closed report traceability:
  `backend/app/services/research_validity_service.py`

## Verification Contract

Focused tests must cover sandboxed autoresearch, project-scoped meta variants,
failed/provisional skill learning, project-scoped model rankings, BM25
provenance, GraphRAG fail-closed gates, protected compression blocks,
Prompt-RAG deterministic methodology injection, and report exclusion of
self-improvement artifacts.
