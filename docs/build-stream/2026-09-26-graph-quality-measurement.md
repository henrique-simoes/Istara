# Graph quality measurement (2026-09-26)

```yaml
item: graph-quality-measurement
branch: plan/graph-quality-measurement-20260926
cf: { spec: pending }
phase: "—"
stage: S0-frame
status: blocked
blocked_on: "owner approval of this frame (S0 gate): the four decisions under Open decisions"
last: { agent: claude-code, at: 2026-09-26T08:10:00Z, ledger: L-1 }
next_action: "Owner approves or amends the frame and answers the four decisions; then create CF-SPEC, clarify, plan and task it, and start Phase 1."
```

## Plan overview

**Problem.** The research-spine round measured retrieval (M1-M3), answers (M4), provenance (M5)
and learning-loop safety (M6). Every quality number is on the chunk-retrieval path. Istara's graph
systems have only structural checks (M5: every chunk links to its evidence unit; the governed coding
run: gates hold) and functional tests (scenario 24: the Context DAG API works). Nothing measures
whether a graph produces better research outcomes.

**What exists (read from the code on 2026-09-26).**

| Graph | Where | What it does today | Measured today |
|---|---|---|---|
| Evidence Graph | `ResearchEvidenceEdge` (`models/research_validity.py`), `build_evidence_graph_traceability` (`services/research_validity_reconciliation.py`), `GET .../evidence-graph` routes | Links source → evidence unit → code application → nugget → fact → insight → recommendation → report; traceability per report | Structure only (M5 coverage 1.0; gate tests) |
| Context DAG | `core/context_dag.py`, `ContextDAGNode` | Compacts chat history into leaf and internal summary nodes, keeps the fresh tail verbatim; `expand_node` and `grep_history` recall | Functional only (scenario 24, 9/9) |
| "GraphRAG" | contracts (`AGENTS.md`, `research-validity-contract.md`); route-evidence operations `retrieval.graph` / `retrieval.graph_hybrid` declared in `core/research_validity.py` | **No retriever emits these operations.** There is no graph-assisted retrieval in the chat or agent path | Nothing to measure yet |

**Outcome.** Three measurements with harnesses and results, in the same style as M1-M6 (fixed
corpus, span-graded truth, bootstrap intervals, paired randomization tests with Holm, rules
pre-registered before any number):

- **G1 · Evidence-graph traceability.** For every report-eligible artifact, can Istara walk the graph
  back to an exact raw-source span, and is every edge on that walk valid? Metrics: trace
  completeness (share of claims reaching a source span), edge validity (endpoints exist, same
  project, direction allowed by the spine), span fidelity (the quoted text is a contiguous substring
  of the source), and orphan/cycle counts. Also run on seeded faults (a deleted unit, a cross-project
  edge, a paraphrased quote, a cycle) with detection recall as the metric.
- **G2 · Context-DAG recall.** Long synthetic research conversations (Harbor Ledger topics) with
  planted facts at known turns; after compaction, questions about compacted turns are answered
  (a) from the summaries alone, (b) with `expand_node` / `grep_history` recall, (c) with the full
  uncompacted history as the ceiling. Metrics: answer-span recall and faithfulness (M4 judges,
  already validated), token cost, and whether protected blocks survive compaction whole.
- **G3 · Graph-assisted retrieval (experiment).** A multi-hop extension of the Harbor Ledger qrels
  (questions whose answer needs two linked sources or a source plus its coded theme). Compare hybrid
  retrieval against hybrid plus one-hop expansion over evidence-graph edges, behind an eval-only
  flag. Ship graph expansion in the product only if it passes a rule fixed before the run (see
  DEC draft), and only through the spine's gates (GraphRAG cannot create report evidence).

**Non-goals.** Replacing hybrid RAG; any graph path that bypasses coding, reliability, review,
Done-task or report gates; live-model spend beyond the M4 caps; changing the Context DAG's
compaction policy in this plan (G2 measures it; a change would be its own plan).

**Appetite.** One build-stream plan, three phases plus ship, Studio-only execution, synthetic data
only. Live models only for G2's answers and judges (the three live identities, $1 cap per run).

**Acceptance (Given/When/Then, each with its verification command).**
1. Given the Harbor Ledger project coded through the governed run, when `python -m
   app.evals.graph_eval trace` runs, then it reports trace completeness, edge validity, span fidelity
   with bootstrap intervals, and seeded-fault detection recall per fault kind. Verify: pytest
   `tests/test_graph_eval_trace.py` (faults are detected on a fixture graph) plus the Studio run.
2. Given N synthetic conversations with planted facts, when `python -m app.evals.graph_eval dag`
   runs, then it reports recall and faithfulness for summaries-only, with-recall-tools and
   full-history, and protected-block integrity. Verify: pytest on a fixture DAG; Studio live run.
3. Given qrels v3 (multi-hop), when `python -m app.evals.graph_eval expand` runs, then it reports
   nDCG@10 / Recall@10 for hybrid vs hybrid+expansion with paired tests, and the pre-registered rule's
   verdict. Verify: `embedder_compare`-style decision module with its own pytest.
4. The spine contract holds: no graph path creates report evidence; graph expansion results enter the
   prompt through the untrusted-content boundary. Verify: existing spine tests plus a new one.

**Rollback.** Harnesses and qrels are additive; G3's expansion ships behind a setting defaulting to
off unless the rule passes. Each phase is its own commit set.

**Top risks.** The evidence graph on the Harbor corpus is small (six coded units per governed run
today), so G1 may need a larger coded slice (cost: live coder calls). Multi-hop questions are hard to
write without leaking the answer into the question; they need the same span grading as v2. G2's
answers depend on live models' variance; three generators and two judges each bound that.

## Phases

| Phase | Goal | Acceptance | Verification |
|---|---|---|---|
| 1 Traceability (G1) | harness + seeded faults; code a larger Harbor slice through the governed run | acceptance 1 | pytest + Studio run |
| 2 Context DAG (G2) | synthetic long conversations, compaction, three recall arms, M4 judges | acceptance 2 | pytest + live run |
| 3 Graph-assisted retrieval (G3) | qrels v3 multi-hop; eval-only one-hop expansion; decision module | acceptance 3, 4 | pytest + Studio run |
| 4 Ship | docs, map, evidence records, PR | CI green | PR into `main` |

## Open decisions (S0: owner)

1. **Scope.** All three (G1-G3), or start with G1 and G2 (measure what exists) and decide G3 after?
2. **G3 ship rule (draft, to fix before any run).** Expansion ships only if it is significantly
   better than hybrid on multi-hop questions (Holm, p < 0.05) and not significantly worse on any
   single-hop style of qrels v2. Accept, or set a different bar?
3. **Coded slice for G1.** Code a larger Harbor slice with the three live identities (roughly 30-60
   evidence units, a few dollars and some hours of the local model), or use a synthetic,
   construction-labelled graph only?
4. **G2 conversation length.** Enough turns to force at least two DAG levels (about 300 messages per
   conversation, synthetic), five conversations: acceptable?

## Decision log

DEC-1 | pending | S0-frame | owner
Context: this frame.
Decision: pending owner approval.
Why: —

## Ledger

### L-1 | 2026-09-26T08:10:00Z | S0-frame | claude-code | framer | —
Did: read the graph code paths (Evidence Graph edges and traceability, Context DAG, the declared
GraphRAG route operations) and the M1-M6 harnesses; found no graph-assisted retriever in the product;
drafted the frame, acceptance and decisions.
Result: frame ready for the owner gate.
Verified: `grep -rn "retrieval.graph" backend/app` (declared only, no emitter);
`ls backend/app/evals/` (no graph harness).
Next: owner approval (S0).
