# Graph quality measurement (2026-09-26)

```yaml
item: graph-quality-measurement
branch: plan/graph-quality-measurement-20260926
phase: "—"
stage: S5-ship
status: done
blocked_on: null
last: { agent: claude-code, at: 2026-09-26T18:20:00Z, ledger: L-3 }
next_action: "Nothing left in this plan: the PR carries it into main."
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

DEC-1 | 2026-09-26 | S0-frame | owner
Context: this frame and its four open decisions.
Decision: the owner said to follow Claude's recommendations and finish: (1) all three
measurements; (2) the draft G3 rule, fixed below before any number; (3) G1 runs on the graph the
product itself builds: Harbor interviews uploaded, the product's interview skill producing nuggets,
facts, insights and recommendations on the live lane (the lane's default model, Muse Spark 1.3
Contributor, runs the skill; amended before any run), plus
seeded-fault fixtures in pytest; no separate coding of a large slice; (4) G2 with five synthetic
conversations of 300 messages.
Why: owner instruction ("follow your recommendations, complete these open things").

DEC-2 | 2026-09-26 | S1-plan | claude-code (pre-registered before any G2/G3 number)
Context: G3 needs thematic questions; the Harbor corpus reuses each theme's quotes across many
files, so "multi-hop" is defined as thematic (global) questions whose relevant set is all of a
theme's planted quotes (qrels `harbor-ledger-qrels-thematic.json`, 30 questions, 3 per theme).
Decision: G3 compares hybrid retrieval with hybrid plus graph expansion (hits -> nuggets they
contain -> facts -> sibling nuggets -> the chunks that contain them, fused by reciprocal rank).
Primary metric: theme coverage@10 on the 30 thematic questions; guard metric: nDCG@10 on each qrels
v2 style. Expansion ships (default on) only if coverage@10 is significantly higher (paired
sign-flip randomization, two-sided p < 0.05) and no v2 style is significantly worse (Holm across the
four styles). Otherwise it stays in the code behind `rag_graph_expansion = False` and the result is
reported. G2: primary metric exact-value recall of planted facts in three arms (summaries only,
summaries + `grep_history` recall, full history as the ceiling); also count summaries that fell back
to the mechanical summary. No ship rule: G2 measures, it does not change compaction.
Why: fixed before the numbers, like DEC-15 and DEC-14 in the spine plan.

## Ledger

### L-1 | 2026-09-26T08:10:00Z | S0-frame | claude-code | framer | —
Did: read the graph code paths (Evidence Graph edges and traceability, Context DAG, the declared
GraphRAG route operations) and the M1-M6 harnesses; found no graph-assisted retriever in the product;
drafted the frame, acceptance and decisions.
Result: frame ready for the owner gate.
Verified: `grep -rn "retrieval.graph" backend/app` (declared only, no emitter);
`ls backend/app/evals/` (no graph harness).
Next: owner approval (S0).

### L-2 | 2026-09-26T12:40:00Z | S1-plan | claude-code | planner | Phase 1
Did: owner decisions recorded (DEC-1); G3 rule and G2 metrics pre-registered (DEC-2); G1 harness
`app/evals/graph_eval.py trace` with seeded-fault tests; thematic qrels for G3. Read the DAG
compaction path: a failed summary falls back to a mechanical "topics" line silently; nugget evidence
units are segmented from the nugget's own text, so a document chunk has no edge to the nuggets drawn
from it (G3 links them by verbatim containment).
Result: ready for the live runs.
Verified: `pytest tests/test_graph_eval_trace.py` 8 passed.
Next: live lane, skills on Harbor interviews, G1/G3/G2.

## Results (live lane, 2026-09-26)

Harbor Ledger corpus (67 files) uploaded into a fresh project; the product's `user-interviews`
skill run on each of the 16 interviews, then on four groups of four (cross-interview synthesis
produces facts, insights and recommendations). Skill model: Muse Spark 1.3 Contributor; embedder:
BGE-M3; link judge: DeepSeek V4 Flash. "Before" is main's code; "after" is this branch, on a new
project built the same way. Reports in `~/cf-remote/eval/measure/open-items-2026-09-26/` (Studio).

| Measurement | Before | After |
|---|---|---|
| G1 structure: verbatim quotes, valid links and edges, complete chains, cycles | 1.00 / 1.00 / 1.00 / 1.00, 0 cycles | same |
| G1 fact → nugget links the nugget supports (judged) | 0.12 [0.07–0.18], n 115 | **0.65 [0.54–0.75]**, n 85 |
| G1 insight → fact links the fact supports (judged) | 0.31 [0.19–0.46], n 48 | **0.81 [0.65–0.94]**, n 31 |
| G2 planted facts recalled from DAG summaries | 0.00, n 50 | **0.48 [0.34–0.62]** |
| G2 summaries that fell back to the mechanical line | 50 of 50 | **0 of 50** |
| G2 with `grep_history` recall / full history | 1.00 / 0.62 | 1.00 / 0.62 |
| G3 theme coverage@10, hybrid vs + graph expansion | 0.76 vs 0.65 (p 0.0004) | 0.76 vs 0.66 (p 0.009) |

What was wrong, and fixed:

- **Recency links.** A skill's facts named no nuggets, so storage linked each fact to the last five
  nuggets, each insight to the last three facts, each recommendation to the last two insights. The
  graph looked complete and was 88% wrong at the first hop. Links now go to the findings closest in
  meaning (BGE-M3, lexical fallback), planned from the skill output before the write transaction;
  nothing close enough means no link. (The first version embedded inside the transaction and every
  embed waited on SQLite's write lock: grouped runs took 560 s instead of 99 s; fixed.)
- **Empty DAG summaries.** Every summary call on the reasoning default model stopped at the
  300-token cap with no text, even with thinking off, and each batch silently became a "topics"
  line. Summaries now retry once with 8,192 tokens, log an empty result, and can be routed to a
  chosen endpoint (`dag_summary_endpoint_id`).
- **G3 does not ship (DEC-2).** One-hop expansion through facts lowers theme coverage and every
  single-hop style, before and after the link fix. Hybrid retrieval already finds 76% of a theme's
  distinct quotes in the top 10; the facts are too few and too coarse to add better chunks.
  Expansion stays in the code behind `rag_graph_expansion = False`.

Residual: the full-history ceiling (0.62) is below the recall-tool arm (1.00): with 300 near-identical
turns the answer model misses facts it can see, so `grep_history` is the better path for old facts.
Summaries still lose half of the planted codes; a longer summary budget or a dedicated summary model
would be the next lever.

### L-3 | 2026-09-26T18:20:00Z | S2-execute | claude-code | executor | Phases 1-3
Did: live lane rebuilt (BGE-M3, agents paused); baseline and after graphs built through the
product's skills; G1, G2, G3 run on both; fixed recency links (finding_links), the lock contention
the first link fix caused, empty DAG summaries (retry, endpoint setting), the G3 nDCG double-count;
added seeded-fault, link, DAG and expansion tests.
Result: see Results. G3 does not ship.
Verified: `python -m app.evals.graph_eval trace --judge pi-deepseek-flash` / `expand`,
`python -m app.evals.dag_eval --endpoint pi-deepseek-flash` (Studio); pytest graph/DAG/link suites
and 170 related tests pass.
Next: ship.
