# Evidence: research-spine findings and retrieval measurements (2026-09-25)

Lifecycle: `2026-09-25-spine-findings-and-retrieval-measurements.md`. Each finding has four
parts, written while it runs: what it is for → the flow driven → the output inspected
(quoted) → why that proves it. "Fails on main" means the test ran against `origin/main`'s
backend (`9272d41e`), from a `git archive` in the `istara-test:1` image with `--network none`
on the Mac Studio. "Passes" means the same command ran on this branch.

## F13: truncation cuts through the untrusted-content wrapper

**What it is for.** Retrieved documents and stored memories are untrusted. The guard wraps each
one in `<untrusted_content>` so the model treats it as data (OWASP LLM01 prompt injection;
spotlighting/delimiting, Hines et al. 2024, arXiv:2403.14720). That works only if every
wrapper is closed and nothing retrieved sits outside one.

**Flow driven (pytest, container).**
`tests/test_spine_prompt_boundaries.py` drives `AgentLifecycleMixin._handle_collaboration`
end to end with a 2,700-character chunk, and captures what the dispatcher receives. It drives
`ReasoningMemoryService.context_for_query` at budgets of 300, 700, 1,100 and 1,500
characters, and wraps a document that contains its own `</untrusted_content>` and a fake
opening tag. It also runs the deterministic skill fallback plan over wrapped context.

**Output inspected.** On `origin/main`:
```
test_spine_prompt_boundaries.py:29: AssertionError: (1, 0, 'he invoice screen. Participant P7 described ... Participant')
test_spine_prompt_boundaries.py:29: AssertionError: (1, 0, 'mory:m0">
test_spine_prompt_boundaries.py:156: assert (2 == 1)
```
That is one opening tag with no closing tag for the A2A block and for the ReasoningBank block,
and two closing tags where the document closed its own wrapper. On this branch all pass. The
A2A documents now sit before the collaborator's question, which stays the turn being answered
(`user_text == "What did P7 say about invoices?"`).

**Why that proves it.** The assertions count opening and closing tags and check that no
retrieved text remains outside a wrapper, at every budget tried. The fix removes the cause:
`truncate_preserving_wrappers` closes a cut wrapper or drops a partial one, ReasoningBank
assembles whole lines against its budget and never slices the joined block, and
`neutralize_boundary_markup` entity-escapes wrapper and protected tags inside untrusted text.
Stored text is untouched, so evidence-unit quotes stay exact substrings.

Product drive: the live-lane chat and A2A runs are recorded under Phase 8 below.

## F14: document content can trigger protected-tag pinning; the RAG budget is not enforced

**What it is for.** Protected blocks (`<qualitative_coding_protocol>`, `<codebook>`,
`<promotion_gate>` …) are methodology the services inject. The contract keeps them whole and
in order through compression. Document text must never borrow that privilege, and the RAG
budget (`min(5% of the window, 4,000)` tokens) decides how much evidence the model sees.

**Flow driven (pytest, container).** `build_compressed_rag_context`, the chat and Interfaces
path, runs with a relevant chunk and a hostile document chunk that wraps 900 filler words in
`<instructions>…</instructions>`. It also runs `compress_rag_chunks_indexed` with five
default-sized chunks (1,200 characters) against the default budget (409 tokens) at every
surplus level.

**Output inspected.** On `origin/main` the hostile chunk was pinned first
(`AssertionError: retrieval order kept; no pinning`), and the default case overran the budget
at every surplus level:
```
assert 2160 <= (409 * 4)   # high
assert 2160 <= (409 * 4)   # moderate
assert 2274 <= (409 * 4)   # low
assert 2189 <= (409 * 4)   # constrained
```
On this branch the relevant chunk leads, the block including labels and wrappers is at most
1,636 characters, no `compression.protected_block` telemetry fires for document text, and
service-injected protected blocks still survive in order
(`test_rag_chunk_compression_preserves_all_protected_blocks_in_order` passes).

**Why that proves it.** The budget overrun is a second defect under F14. The helper that
"enforced" the budget, `_trim_preserving_protected_blocks`, returns text without protected
blocks unchanged, so any ordinary chunk longer than the remaining budget passed through
whole. `_fit_to_budget` now trims ordinary text at a word boundary and still lets real
protected blocks overflow, as the contract requires. Retrieved text is neutralised before
compression, so a document can no longer produce a protected block.

Suites run on this branch: `test_spine_prompt_boundaries.py`, `test_data_transformations.py`,
`test_rag_resilience.py`, `test_retrieval_correctness_fixes.py`, `test_reasoning_bank.py`,
`test_content_guard.py`, `pi_production/test_w4_a2a_handlers.py`, `test_prompt_rag.py`,
`test_chat.py`, `test_agent_personas.py`: **110 passed**.

## F5: LLM-written artifacts and agent notes in the source evidence index

**What it is for.** The spine says evidence units come from raw source spans, and that model
output is at most provisional. Hybrid RAG is the exact-evidence retriever. If a skill's own
report or an agent's note sits in the same index as the interviews, `self_check.verify_claim`
can "verify" a claim against the text that asserted it: retrieval-corpus poisoning (PoisonedRAG,
Zou et al. 2024) that the product commits against itself. W3C PROV keeps an entity's generation
by an agent separate from what a source says.

**Flow driven (pytest, container).** `tests/test_spine_evidence_provenance.py` writes a claim
two ways: through `agent_memory.write_note`, and as a pre-fix build stored skill artifacts
(`skill:` rows in the source table). It then runs `verify_claim` on the claim and captures the
exact prompt the dispatcher receives. It writes notes for agents `a1` and `a10` beside 30
similar source chunks and reads them back both ways. It drives `AgentOrchestrator._store_findings`
twice with a 5,800-character artifact.

**Output inspected.** On `origin/main`:
```
test_spine_evidence_provenance.py:113: AssertionError: model output confirmed its own claim
test_spine_evidence_provenance.py:128: AssertionError: assert [] == ['Onboarding ...inder email.']
test_spine_evidence_provenance.py:155: AttributeError: module 'app.core.rag' has no attribute 'DERIVED_TABLE'
```
The note reached the verifier's "Source Documents". The agent's own note was crowded out of
its top-3. On this branch the verifier sees only `interview-02.md`, `read_notes("a1")` returns
exactly a1's note, and `get_all_notes("a1")` no longer matches `a10`. The artifact lives whole
in the derived index (the `END-MARKER` past 2,000 characters is present), and a rerun leaves
the row count unchanged.

**Why that proves it.** The claim's supporting text now exists only in the derived index, which
source retrieval never reads. Legacy rows are pre-filtered out by their `agent:`/`skill:`
source. With the fixed code the verifier cannot see its own model's output, whatever the
embedder ranks.

## Measurement 5: provenance coverage

**What it is for.** The retrieval contract makes Hybrid RAG return exact evidence: source,
span and evidence-unit id. The map found 0% of retrieved chunks carrying an
`evidence_unit_id`. The brief asks for provenance to be wired through and made a health
invariant.

**Flow driven.** The test uploads a 40-turn interview through the real route
(`POST /api/files/upload/{pid}`, ASGI), reads every row the upload wrote to the source vector
table, joins each to the document's `EvidenceUnit` rows, then calls `GET /api/memory/{pid}/stats`
and `retrieve_context`.

**Output inspected.** On `origin/main`:
`AssertionError: every source chunk names a real evidence unit of its document`. On this branch
every row's `evidence_unit_id` is a unit of that document, and its span overlaps the unit's span.
`stats["provenance"]["coverage"] == 1.0`. Every hybrid hit carries a unit, and
`provenance_share == 1.0`. Retrieval telemetry now records that share on every
`retrieval.hybrid` event (content-free).

**Why that proves it.** The join is exact: each chunk is located in the text the units were
segmented from, and it takes the unit with the largest overlap. A chunk that cannot be
located is left unstamped and shows up as coverage below 1.0 (`status: degraded`); it is never
guessed. The same helper serves upload, audio, reprocess, documents sync, knowledge sync and the
watcher. Real-corpus coverage on the live lane is recorded in Phase 8.

## F7: the file watcher drops BM25 rows

**What it is for.** A watched project folder is an ingestion surface. An edit must leave the
file searchable by keyword as well as by vector.

**Flow driven.** `FileWatcher._process_file` on a Markdown file in a watched folder. The file
is then edited and processed again, and BM25 is searched for a phrase that only the edit contains.

**Output inspected.** On `origin/main`: `assert ([])`, no keyword hit at all after the
re-index. On this branch the edited sentence is the top BM25 hit, and the keyword row count
equals the vector row count.

**Why that proves it.** The old path deleted by source (clearing both indices) and then called
`embed_chunks` and `store.add_chunks` only. The watcher now registers the document first and
indexes through the same two-index, provenance-stamping helper as uploads.
Runtime drive in the container lane: Phase 9.

## F15: ciphertext indexing and ciphertext search under file encryption

**What it is for.** With `FILE_ENCRYPTION_ENABLED=true`, document text is stored through
`protect_document_text`. Anything that reads it must reveal it first.

**Flow driven.** Encryption on with a fresh Fernet key. A document whose file is missing, so
knowledge sync falls back to the stored text. `KnowledgeSyncService.sync_project`, then BM25
search, then the chat tool `_exec_search_documents`.

**Output inspected.** On `origin/main`: `assert ([])` (the sync indexed ciphertext, so no
plaintext hit), and `"No documents found matching 'variance column' in this project."`. On this
branch the plaintext sentence is the BM25 hit, no indexed row starts with the ciphertext prefix,
and the tool answers "Found 1 document(s)".

**Why that proves it.** Both paths now read `reveal_document_text`, the same function the
Documents full-text route already used.

## F17 (part): backslash paths and zero-as-unset

Delete by a Windows-style source (`C:\Users\research\interview.md`): on `origin/main`
`assert 1 == 0` (the row survived). LanceDB 0.38 was probed directly: the backslash-doubled
literal deleted nothing, and the plain literal deleted the row. An explicit
`score_threshold=0.0` on `origin/main` returned only the chunk above 0.3
(`{'/u/b.md'} == {'/u/a.md', '/u/b.md'}`). Both pass on this branch.

Phase 2 suites on this branch: the two new files plus `test_rag_resilience.py`,
`test_retrieval_correctness_fixes.py`, `test_files.py`, `test_memory.py`, `test_documents.py`,
`test_research_spine_end_to_end.py`, `test_agents.py`,
`test_research_integrity_code_applications.py` and
`pi_production/test_embedding_profile_authority.py`: 125 passed after one seam update. The
provenance-dedupe test's `FakeStore` now provides `keyword_index()`, the paired-index accessor
the store gained.

## F12: score-scale mixing in several rankers

**What it is for.** A score must mean what its reader thinks it means. Reciprocal Rank Fusion
is ordinal (Cormack, Clarke & Büttcher, SIGIR 2009: it fuses ranks, never scores). The best
possible fused value is about 0.016, which a model or a researcher reads as "irrelevant". A
ranking that sorts two score scales together has no meaning.

**Flow driven (pytest, container).** `tests/test_spine_ranking_semantics.py` builds the
compressed chat/interfaces RAG block and a raw `format_context_part` label, and calls the chat
tool `search_memory` with `top_k=100000`. It seeds a project with a model-written nugget and two
source hits that share their text but belong to different evidence units, then runs
`search_project_findings`. It compresses three ranked chunks where rank 3 is keyword-stuffed.
It composes a Prompt-RAG identity where embedding fails after the first section.

**Output inspected.** On `origin/main`:
```
test_spine_ranking_semantics.py:51: assert 'relevance:' not in '--- Documen...ted_content>'
test_spine_ranking_semantics.py:98: KeyError: 'kind'          # finding mixed in at score 1.0
test_spine_ranking_semantics.py:134: assert [2, 0, 1] == [0, 1, 2]   # word soup moved to the top
test_spine_ranking_semantics.py:159: AssertionError: '# Istara Res...' == '# Istara Res...'  # mixed cosine/Jaccard selection
```
On this branch the model sees `rank 1`, `rank 2`, and the tool prints `#1 [source]`. Findings
search returns both evidence units first (`eu-1`, `eu-2`, kind `source_evidence`, ranked), then
the nugget as `kind: finding`, `review_status: provisional`, `score: None`. Compression keeps
`[0, 1, 2]`. A partial embedding failure yields exactly the keyword-only selection.

**Why that proves it.** Each assertion is the property itself. No fused value reaches a model
label. A provisional finding cannot sort above source evidence, because the two are no longer
on one sorted list. Retrieval order survives compression. A Prompt-RAG ranking is either all
cosine or all keyword. Measurement 3 below quantifies what the order change does to budget
recall.

## F17: remaining smells

On `origin/main`: `assert 100000 <= 20` (search_memory `top_k` passed through),
`assert 200 == 422` (`/findings/search?top_k=100000` accepted), `{'error': 'whole-table load'}`
(the Memory list loaded the whole LanceDB table, vectors included, into pandas to page it),
`assert not True` (`MetaHyperagent._apply_parameter`, a module-global mutator with no callers,
still present), `TypeError: can only concatenate str (not "NoneType") to str` (`_select_skill`
on a NULL description), and `assert 'create_task' not in ['create_task']` for both the native
and the text-fallback legacy turn: a tool outside the session catalog executed. All pass on
this branch. The legacy loop now refuses uncatalogued tools on every surface and tells the model
`tool_not_allowed`, which the Pi plane already did. The Memory list and stats select only the
listed columns with offset/limit, read the vector dimension from the schema, and still count
sources correctly (`{'/u/doc-0.md': 3, '/u/doc-1.md': 2}`).

Phase 3 suites on this branch: the new file plus 23 test files that touch the changed surfaces
(`_react_loop`, legacy executor, Prompt-RAG, meta-hyperagent, findings search, `search_memory`,
RAG compression, the context formatter) and `test_findings.py`, `test_memory.py`:
**488 passed**.

## F10: learned boosts clear the routing floor for any query

**What it is for.** Skill routing must pick skills relevant to the task. Usage history,
telemetry quality and ReasoningBank lessons are priors. The governance contract allows
ReasoningBank "weak routing priors" and forbids "strong positive skill/model signals from raw
tool success". A boost that can lift an unrelated item over the relevance floor is the
feedback loop recommender research warns about: popularity begets exposure (Chaney, Stewart
& Engelhardt, RecSys 2018).

**Flow driven.** `rank_skill_candidates` for "Summarize participant quotes about invoice
reminders", with `tree-testing` given 500 successes at quality 1.0 and utility 1.0.

**Output inspected.** On `origin/main`:
`assert 'tree-testing' not in ['tree-testing', 'field-studies', 'participant-simulation', 'persona-creation']`.
Tree-testing has nothing to do with quotes, yet it ranked first. On this branch it is absent.
For a relevant task ("heuristic evaluation"), a perfect history still lifts
`heuristic-evaluation`, by at most half of its relevance score.

**Why that proves it.** Candidates now carry `relevance` and `learned` separately.
Eligibility is `relevance >= floor`, and `score = relevance + clamp(learned, -relevance,
0.5·relevance)`. No history can create relevance.

## Measurement 6: learning-loop safety (a planted successful-but-wrong run)

**What it is for.** The brief requires that a successful-but-wrong tool run teach ReasoningBank,
skill routing and self-evolution nothing strong.

**Flow driven.** `test_planted_successful_but_wrong_run_teaches_nothing_strong` registers a
planted skill that succeeds and returns a well-formed synthesis contradicting the evidence
("Invoice chasing is not a problem for owners"). The model's own reflection is stubbed to be
fooled (`verified: true, confidence 0.95`). The harness then runs the real
`AgentOrchestrator._execute_task` (checkpoints, findings storage, self-check, self-verify,
ReasoningBank, Memento usage, hooks) and inspects every learning surface afterwards.

**Output inspected.** On `origin/main` ReasoningBank stored the wrong run as a success:
`assert not [{... 'confidence': 0.85, 'content': 'Reuse this strategy when the new task resembles the origi...` 
On this branch the harness prints:
```
LEARNING-LOOP-SAFETY {"reasoning_bank": [["provisional", 0.55]], "skill_stats": {"executions": 0,
"successes": 0, "failures": 0, ..., "provisional": 1}, "self_evolution_candidates": 0, "failure_memories": 0}
```
The planted skill is not a routing candidate for an unrelated query, and
`scan_for_promotions` finds nothing.

**Why that proves it.** The root cause was a vocabulary slip. "Verified" meant the agent's own
check, and every learning surface treated it as independent verification. The policy now has
a `self_verified_provisional` state that moves no success count, stays at neutral confidence
(capped at 0.6), and adds no routing lift. Only human review (`task_review` APPROVED, already
recorded there) or Research Spine reportability is strong. A self-check that rejects its output
remains a weak failure. This is a pytest harness in the default suite, and it runs on every
change.

## F16: reads with side effects; the 200-newest cap

On `origin/main`:
```
test_spine_learning_loops.py:112: assert 2 == 0      # two retrieve() calls incremented usage_count twice
test_spine_learning_loops.py:144: assert 2 == 0      # the admin API retrieved twice and counted both
test_spine_learning_loops.py:159: assert ([])        # the relevant lesson, older than 210 others, was unreachable
test_spine_learning_loops.py:179: AssertionError: a health read created a manifest
```
On this branch `retrieve` is a pure query with an SQL relevance prefilter before the recency
cap (2,000 candidates that share a query term). `context_for_query`, the path that puts
memories into prompts, counts exactly one use per memory that made it into the text. The API
retrieves once and counts nothing. `check_embedding_dimensions` checks the binding read-only
and reads the stored dimension from the schema (command-query separation, Meyer, *Object-Oriented
Software Construction*).

## F9: project-scoped evidence mutates cross-project state

On `origin/main`: `assert 'Zorblax' not in '# Istara Re...'`. A learning promoted from project
A appeared in project B's Prompt-RAG identity, because promotions wrote the agent-wide
overlay. `AssertionError: stale description served`: the skill-description vector cache was
keyed by skill name only. On this branch promotions go to
`runtime_personas/<agent>/projects/<project>/<FILE>.md`, which is merged only when that
project composes the prompt (Prompt-RAG, `load_agent_identity(project_id=…)`, and the chat
fallbacks), and the agent-wide persona is unchanged. The cache key is
`(embedding space, skill, description digest)`, and a dimension mismatch skips the comparison
instead of `zip`-truncating it. F9's third part, process-global `settings` mutation during RAG
tuning, is fixed with F3 in Phase 7.

Phase 4 suites on this branch: the new file plus the 22 test files that touch ReasoningBank,
routing, learning signals, usage recording, self-evolution, persona loading, vector health and
semantic matching, then `test_task_review_history.py`, `test_tasks.py`, `test_skills.py`,
`test_chat.py`: all passed after one seam update (a persona-append fake now takes the new
`project_id` keyword).

## F8: plan steps share one AsyncSession; a failed step's dependents run anyway

**What it is for.** The plan-and-execute path decomposes a task into a DAG (LLMCompiler, Kim
et al., ICML 2024). A step whose prerequisite failed has no valid input. SQLAlchemy's asyncio
documentation says an `AsyncSession` must not be shared across concurrent tasks.

**Flow driven.** `tests/test_spine_plan_dag.py` drives `_execute_planned_task` with fake skills
and a session stand-in that records concurrent use. It runs three plans: A→B→C with A failing;
four independent steps that all store findings; and C depending on A beside an unrelated B.

**Output inspected.** On `origin/main`:
```
test_spine_plan_dag.py:103: AssertionError: assert ['A', 'B', 'C'] == ['A']
test_spine_plan_dag.py:113: assert 3 == 0
test_spine_plan_dag.py:120: AssertionError: assert 'result of B' not in 'step C\n\nP... result of B'
```
B and C ran after A failed, the shared session saw three overlapping uses, and C was given B's
result. On this branch only A runs. B and C are `blocked` with "prerequisite step(s) A did not
succeed". Overlaps are 0 while the four skills still run concurrently. C sees A's result
only. The existing plan suites (`test_agents.py`, `pi_production/test_w3_research_spine.py`)
pass: 47 passed.

**Why that proves it.** The overlap counter measures the property directly (two tasks inside
the session at once). The lock covers every shared-session use in a step, and model work stays
parallel. Blocking follows from the completed/unsuccessful split, so no dependent can run on a
failed input.

## F11: a same-dimension embedder swap mixes two vector spaces silently

**What it is for.** Cosine similarity is only meaningful between vectors from one model. With the
default profile the embedding identity was the literal `"default"` with dimension 0. If a user
loaded a different embedding model of the same dimension, the store manifest still matched, the
cache served the old model's vectors, and queries were compared against documents from another
space. `vector_health` compared dimensions only.

**Flow driven.** `tests/test_spine_embedding_identity.py` swaps between two deterministic
8-dimensional embedders (different seeds are different models of the same dimension), and resets
the known dimension the way a restart or the health probe does. It then (1) re-embeds a text
cached under the old model, (2) queries a store written by the old model, and (3) runs
`check_embedding_dimensions`.

**Output inspected.** On `origin/main`:
```
test_spine_embedding_identity.py:76: assert ([0.0, -0.8671....2109375, ...] == [0.6640625, -...-0.84375, ...]
test_spine_embedding_identity.py:95: Failed: DID NOT RAISE <class 'app.core.rag.VectorProfileMismatchError'>
test_spine_embedding_identity.py:113: AssertionError: {'engine': None, 'message': 'All vector dimensions match', 'model': None, 'model_dim': 8, ...}
3 failed in 0.86s
```
The old model's cached vector came back, the old store answered the new model's query, and health
said "All vector dimensions match". On this branch all three pass. The cache is keyed by
`base#fingerprint`, where the fingerprint hashes the vectors a fixed probe text produces, so the
new model misses the old entries. `add_chunks` binds the store to the fingerprint it was written
with, a query from a different fingerprint raises `embedding_fingerprint_mismatch`, and health
reports `fingerprint_mismatch`. The W8 gateway suite needed one seam update: its cache-trust test
now seeds a known fingerprint, because a cache hit is only trusted for the model that wrote it.

**Why that proves it.** The two embedders share a dimension, so every dimension check passes on
both. Only an identity derived from behaviour can tell them apart. The three assertions cover the
three places the spaces met: the cache, the store, and the health report.

## F3 (and F9's settings part): the RAG tuning loop optimised its own weights

**What it is for.** Autoresearch loop 4 tunes chunking and hybrid weights. Its objective was
`0.6 x mean(fused score) + 0.4 x coverage` over five fixed queries. The fused Reciprocal Rank
Fusion score is a weighted sum of `1/(k + rank)` terms, so it grows with the weights being tuned,
whatever is retrieved (Goodhart's law). There were no relevance labels, chunk-size candidates
never re-indexed, and each candidate was a `setattr` on the process-wide settings while other
projects' requests read them (F9).

**Flow driven.** `tests/test_spine_retrieval_eval.py` builds a three-document benchmark with
qrels, ingests the same documents as a project, and drives `RAGParamsRunner` through
`measure_baseline` → `apply_mutation` → `measure` → revert. The candidates are both weights
multiplied by 1.25 (RRF ranking is invariant to a common factor), a vector weight of 0.31 (the
test reads `settings` during the measurement), and a chunk size of 400. It also runs the
shipped Harbor Ledger qrels through the BM25 lane, and checks the metric maths by hand.

**Output inspected.** On `origin/main`:
```
test_spine_retrieval_eval.py:167: assert 0.10112228979375995 == 0.10009783183500795 ± 1.0e-07
test_spine_retrieval_eval.py:182: assert 0.31 == 0.7
test_spine_retrieval_eval.py:194: AttributeError: 'RAGParamsRunner' object has no attribute 'objective'
test_spine_retrieval_eval.py:28: ModuleNotFoundError: No module named 'app.evals'   (x5)
8 failed in 1.14s
```
Scaling both weights raised the old objective from 0.1001 to 0.1011 with an identical ranking.
Every other project read a vector weight of 0.31 mid-measurement. No re-indexed sandbox existed.
On this branch all 8 pass. The objective is mean nDCG@10 on span-graded qrels, and the scaled
candidate scores exactly the baseline. `settings` still reads 0.7 during the measurement. The
400-character candidate is measured on its own sandbox, which has more chunks than the default
one. A missing benchmark raises `BenchmarkUnavailableError` instead of optimising a proxy. On the
shipped qrels, BM25 answers the lexical questions better than the paraphrase ones (MRR), as it
should.

The W6 suite pinned the old objective's internals (`_score_single_query`, and an
`_evaluate_retrieval(project_id)` seam), so its two tests failed in the full-suite run.
They now pin the same two contracts at the new sites: every measurement runs under the
authorised binding (the test records `self._project_id` inside the evaluation), and the eval's
embeddings go through `embed_text` with the W8 note in-line. W6, spine-eval, pi_migration and
autoresearch: 98 passed, 1 skipped.

**Why that proves it.** The equal-scaling candidate is the sharpest test of the Goodhart defect:
it cannot change what is retrieved, so any objective that moves is measuring the knobs rather
than relevance. The settings read happens inside the measurement window, where the old code's
mutation was visible to every project.

## Found in passing: uploads held a write transaction open while embedding

**What it is for.** SQLite allows one writer. Upload, audio transcription and document sync
added the document and its evidence units in the request's session, then indexed before
committing. Indexing embeds, and each embedding dispatch writes a usage-ledger row in its own
session, so each of those writes waited out the 30-second busy timeout behind the request's own
open transaction.

**Flow driven.** The branch's full backend suite, run in `istara-test:1` on the Studio with
`-v` and a stall watcher.

**Output inspected.** Before the fix the verbose log stopped growing in the upload tests (the
watcher reported `STALLED`). After committing before indexing, the same full run completed:
`6 failed, 2425 passed, 15 skipped, 1 deselected, 1 error in 187.67s`. The 6 failures were the
4 that also fail on `origin/main` (`test_bump_diff_proof`, `test_invite_redeem_rejects_breached_password`,
`test_public_repo_quality_audit_passes`, `test_local_update_apply_accepts_matching_confirmation`)
plus the two W6 tests above. The collection error (`test_property_contracts.py`, a dependency
missing from the image) also occurs on main.

**Why that proves it.** The suite hung only once indexing embedded inside the request's
transaction, and it completes once the transaction is closed before that. The dispatch still
records its usage rows, now without blocking.

## F17 residue, found by measurement 2: an explicit zero overlap was 180, and large overlaps never ended

**What it is for.** Chunking parameters must mean what they say, or the tuning loop and the
ablations measure something other than what they report. `chunk_text` read
`chunk_overlap or settings.rag_chunk_overlap`, the zero-as-unset pattern F17 removed elsewhere.
Its loop set `start = end - overlap` without checking progress.

**Flow driven.** The first M2 run reported `chunk_overlap=0` as identical to the default:
the same 1097 chunks and nDCG@10 0.6996. A sandbox comparison then showed that overlaps 0 and 180
cut identical spans (0 differing) while 400 changed 102. `tests/test_spine_chunking_parameters.py`
pins the defect. It checks an explicit 0 in `chunk_text` and in `chunk_by_heading`. It runs three
large-overlap pairs in a child process that is killed after 5 seconds. It also checks that a chunk
size of 0 is refused.

**Output inspected.** On `origin/main`:
```
test_spine_chunking_parameters.py:43: AssertionError: chunks overlap by 178 characters with overlap=0
test_spine_chunking_parameters.py:69: AssertionError: chunk_text(size=400, overlap=400) did not finish in 5 s
test_spine_chunking_parameters.py:69: AssertionError: chunk_text(size=400, overlap=399) did not finish in 5 s
test_spine_chunking_parameters.py:69: AssertionError: chunk_text(size=300, overlap=1000) did not finish in 5 s
test_spine_chunking_parameters.py:74: Failed: DID NOT RAISE <class 'ValueError'>
6 failed in 15.17s
```
On this branch all 6 pass. `None` means "use the setting", 0 is 0, the loop steps back only
while that still moves it forward, and a non-positive size raises. 25 upload and chunking suites:
263 passed, 1 skipped. The re-run M2 shows overlap 0 as its own index (1087 chunks, nDCG@10
0.7035).

**Why that proves it.** The spans (not the scores) showed that two settings built one index. The
killed child process shows that a hang is not slowness: the same text finishes in milliseconds
with a smaller overlap. The tuning ranges allow chunk size 400 with overlap 400, so the old loop
could hang a tuning run.

## Measurements 1-3: retrieval quality with the real embedder

**What it is for.** Istara had no relevance judgments. These measurements establish what hybrid
retrieval actually achieves, which settings matter, and how much retrieved evidence survives the
prompt budget. They also give F3's tuning loop its objective.

**Flow driven.** The `app.evals.retrieval_eval` CLI ran in `istara-test:1` on the Studio
(network `istara-cs76-live`) against nomic-embed-text in a labelled Ollama container: 768
dimensions, fingerprint `ff22f761301f81f0`. Corpus: the committed Harbor Ledger rich corpus
(67 files). Qrels: 76 questions (30 lexical, 30 paraphrase, 12 fact, 4 Spanish), graded by span
occurrence. Intervals are 95% percentile bootstrap (10,000 resamples). Comparisons use a paired
sign-flip randomization test (20,000 permutations) with Holm correction across the 12 ablations.

**Output inspected.**

M1 (`evaluate`, 1097 chunks, 39.8 s):

| system | nDCG@10 | Recall@10 | MRR@10 | Success@10 |
|---|---|---|---|---|
| BM25 | 0.717 [0.636, 0.795] | 0.618 | 0.778 | 0.868 |
| vector | 0.571 [0.497, 0.645] | 0.499 | 0.661 | 0.882 |
| hybrid (0.7/0.3, k=60) | 0.700 [0.627, 0.771] | 0.585 | 0.785 | 0.934 |

Hybrid vs BM25: mean difference in nDCG@10 is 0.018 in BM25's favour, p = 0.50. Vector is worse
than BM25 (−0.146, p = 0.0003) and than hybrid (−0.128, p = 0.00005). By style, hybrid wins on
paraphrase (0.523 vs BM25 0.471) and fact questions (0.848 vs 0.818), and loses on lexical (0.852
vs 0.932) and Spanish (0.433 vs 0.648). nomic-embed-text is English-only: vector nDCG@10 on
Spanish is 0.028. The pooled top-10 of the three systems catches 70.8% of the index's
answer-bearing chunks (mean pool size 16.7), so a judge panel that labels only the pool would miss
about 29% of them.

M2 (`ablate`, hybrid, nDCG@10, baseline 0.6996; after the overlap fix above):

| variant | chunks | nDCG@10 | Δ | p | Holm p |
|---|---|---|---|---|---|
| chunk_size=400 | 3195 | 0.750 | +0.051 | 0.048 | 0.386 |
| chunk_size=800 | 1163 | 0.678 | −0.022 | 0.0007 | **0.0065** |
| chunk_size=1600 | 1074 | 0.706 | +0.007 | 0.095 | 0.668 |
| chunk_size=2400 | 1052 | 0.708 | +0.009 | 0.018 | 0.164 |
| chunk_overlap=0 | 1087 | 0.704 | +0.004 | 0.377 | 1.0 |
| chunk_overlap=400 | 1128 | 0.698 | −0.002 | 0.692 | 1.0 |
| vector_weight=0.3 | 1097 | 0.731 | +0.031 | 0.123 | 0.739 |
| vector_weight=0.5 | 1097 | 0.713 | +0.013 | 0.257 | 1.0 |
| vector_weight=0.9 | 1097 | 0.653 | −0.047 | 0.00005 | **0.0006** |
| rrf_k=10 | 1097 | 0.665 | −0.034 | 0.00005 | **0.0006** |
| rrf_k=30 | 1097 | 0.699 | −0.001 | 0.423 | 1.0 |
| rrf_k=100 | 1097 | 0.700 | 0.000 | 1.0 | 1.0 |

M3 (`budget`, hybrid, 5 retrieved chunks, moderate surplus; the RAG budget is
min(5% of the window, 4000) tokens):

| window | RAG budget | answer spans retrieved | in the prompt | budget recall |
|---|---|---|---|---|
| 2,048 | 102 | 227 | 38 | 0.167 |
| 4,096 | 204 | 227 | 173 | 0.762 |
| 8,192 | 409 | 227 | 218 | 0.960 |
| 16,384 | 819 | 227 | 226 | 0.996 |
| 32,768 | 1,638 | 227 | 226 | 0.996 |
| 131,072 | 4,000 | 227 | 226 | 0.996 |

**Why that proves it.** The judgments are spans in the committed corpus, so every number can be
re-run. The intervals and the paired tests separate effects from noise over 76 questions: only
three ablations survive Holm correction, and all three make retrieval worse. Three conclusions
follow. The default weighting leans on the weaker retriever, so hybrid does not beat BM25 on this
English-heavy benchmark. No single-factor change significantly improves on the defaults. A model
with a 2k window sees about one answer span in six that retrieval found. The benchmark is
synthetic, with generator-planted quotes (lexical questions share words with their answers by
construction), so these are Istara's numbers on this corpus, not general claims. One answer span
is lost at every budget. `compress_rag_chunks_indexed` compresses every chunk after the first by
rank (0.85, 0.7, 0.5) even when all of them fit, which is the likely cause. That is a design
change to the compressor, so it is filed as a follow-up task rather than changed here.

## Found probing the live lane: an endpoint's thinking level was ignored, and failed turns did not say why

**What it is for.** Some models always reason. Z.ai's GLM-5.3-flash refuses a request with thinking
off (HTTP 400, code 1210: "This model always engages in thinking and cannot be disabled"). The
endpoint config said `thinking_level: low`. A failed turn must tell its caller the reason, or no
one can act on it.

**Flow driven.** One short completion per endpoint through Istara's dispatcher in the live backend
(`istara-cs76-live`, built from this branch), then a spy on the engine's frame mapper to read the
worker's terminal frame. `tests/test_pi_turn_failures_and_thinking.py` pins both defects offline
with a scripted failing Pi service and the resolver.

**Output inspected.** Live, before the fix: `pi-zai-glm: status=error text='' error=` (empty). The
worker's frame said `run.failed ... "error": "400: {\"code\":\"1210\", ...}"`. With a per-turn
`thinking_mode="low"` the same call returned `success 'ready'`. On `origin/main` the new tests fail:
```
test_pi_turn_failures_and_thinking.py:78: assert None == '400: {"code":"1210","message":"This model always engages in thinking ...'
test_pi_turn_failures_and_thinking.py:97: AssertionError: assert None == 'low'
test_pi_turn_failures_and_thinking.py:104: AssertionError: assert None == 'low'
test_pi_turn_failures_and_thinking.py:115: Failed: DID NOT RAISE <class 'ValueError'>
4 failed, 1 passed
```
`PiApiEndpoint` had no `thinking_level` field (pydantic dropped the configured value), only the
chat controls send a per-turn level, and the dispatcher built every `TurnResult` without `error`.
On this branch the endpoint's level is validated, carried by the resolver and used when a turn sets
none. Live: `pi-zai-glm: status=success text='ready' model=glm-5.3-flash ... 2.5s` with no per-turn
level. Errors now arrive, for example `error=wall_clock_budget_exceeded`.

**Why that proves it.** The provider's 400 names the cause, and the same request succeeds once the
configured level is honoured. The offline tests need no network: `None == '400: …'` is exactly the
dropped reason.

## Local models were killed by a two-minute stopwatch (DEC-10)

**What it is for.** Istara is local-first. The owner's local Qwen3.8-27B streams steadily at ~15 tokens/s,
and every run died at 120 s: the worker's fixed wall clock, the supervisor's 120 s wait between
frames and a 120 s cap on `timeout_ms` all applied to every endpoint. The built-in Ollama entry
gave a response 30 s to start, which embed batches exceeded under ordinary load (reported by the
Phase 7b session).

**Flow driven.** The live probe of `pi-local-qwen` with a 4,096-token budget, before and after
the change. `tests/test_pi_local_liveness.py` (locality inference over 16 URLs, defaults,
overrides, the supervisor carrying the session limits) and `pi-runtime/test/liveness.test.mjs`
(a worker session with a faux provider streaming at a set rate: a silent provider, a steady one,
and a run waiting on Istara's own tool).

**Output inspected.** Live, before: `pi-local-qwen: status=error error=wall_clock_budget_exceeded
120.4s`. After (commit 3d1a052d): `status=success model=qwen3.8-27b-ud-q4k-xl stop=length`, the
full 4,096 tokens. The model spent them all thinking, so the text was empty: that is the model's
reasoning length, not Istara's limit. On `origin/main`: `tests/test_pi_local_liveness.py` 20 failed
of 20. `liveness.test.mjs`: "a provider that goes silent" failed (`'run.completed' !== 'run.failed'`,
there was no idle watch) and "a model that keeps streaming" failed (the faux stream had no rate). The
tool-wait guard passed. On this branch: 20/20 and 3/3, worker suite 103/103, 74 Pi-touching suites
833 passed.

**Why that proves it.** The live run shows the stopwatch was the cause: the same request at the same
rate completes once liveness is judged by progress. The worker tests separate the three situations
that a single wall clock conflated: silence is caught quickly, steady progress runs past the idle
limit, and tool time does not count as silence.

## pi-ai / pi-agent-core 0.85.1 -> 0.87.1 (owner request: Meta directly through Pi)

**What it is for.** The owner asked for Meta Muse Spark 1.3 Contributor directly through Pi. The
pinned 0.85.1 has no `meta` provider, so Settings (which lists the catalog projected from the pin)
could not offer it.

**Flow driven.** `scripts/pi_bump_diff_proof.py proof 0.87.1 --expect-model
meta/muse-spark-1.3-contributor` (first unclassified, then with every surface and removal
classified after review), `scripts/generate_pi_catalog.py` then `--check`, `pi_bump_diff_proof.py
verify`, the worker suite on a clean `npm ci`, labs `npm run validate`, the Pi Python suites and the
frontend unit tests.

**Output inspected.** First proof: `50 changed surface(s), gate FAILED` (all unclassified), with
`meta/muse-spark-1.3-contributor present: true`. Worker suite on 0.87.1: 100/103. The three failures
were one Codex request fixture (thinking off now sends `reasoning: {"effort": "none"}`) and the
Codex record's new `supportsMidConvoSystemMessages` flag. Both are upstream-intended. Classified
proof: `gate PASSED`. `verify: pins={...0.87.1...} gate PASSED`. Catalog: `42 providers; meta True
['muse-spark-1.1', ..., 'muse-spark-1.3-contributor']`, and the thinking maps of the models Istara
uses are unchanged. Pi suites: 6 failed until four tests stopped using removed models
(`deepseek-v4-flash` is now `deepseek-flash`; `gpt-5.4` was removed) and the diff-proof fixtures
tracked the pin. Then `827 passed, 6 skipped`. Worker 103/103, frontend unit 121/121.

**Why that proves it.** The gate is mechanical and passes only when every changed surface is
classified. The request-wire fixtures show exactly what changes on the wire (one field for Codex
with thinking off). The Meta model is asserted present by name. Commit daebba8b.

## Phase 7b (M3 follow-up): compression removed exact evidence the budget had room for

**What it is for.** Retrieval returns exact source evidence, and the research spine needs the
model to see that evidence as the source says it. M3 found one answer-bearing span that never
reached the prompt at any window of 16k tokens and above, the largest RAG budget (4,000 tokens)
included. The rank-based compressor was the suspected cause (see the M3 paragraph above).

**Flow driven.** `budget_recall` now attributes every lost span to the chat-path step that lost
it: the retrieved chunk, prompt formatting (sanitise, neutralise, wrap), the budget (chunk never
reached the prompt), or compression (chunk reached the prompt shortened). It also counts spans
present verbatim. M3 ran on the Studio lane in `istara-test:1` on `istara-cs76-live` with
nomic-embed-text, first on the afe5c307 compressor, then on the change. The compression of the
answer chunk was then reproduced alone with `compress_with_question(chunk, question, 0.85)`, the
call the compressor makes for rank 2 at moderate surplus. pytest ran with `--network none`.

**Output inspected.** On the afe5c307 compressor:

| window | RAG budget | retrieved | in prompt | verbatim | lost by step |
|---|---|---|---|---|---|
| 2,048 | 102 | 227 | 38 | 38 | budget_drop 189 |
| 4,096 | 204 | 227 | 173 | 166 | compression 11, budget_drop 43 |
| 8,192 | 409 | 227 | 218 | 217 | compression 1, budget_drop 8 |
| 16,384 | 819 | 227 | 226 | 226 | compression 1 |
| 32,768 | 1,638 | 227 | 226 | 226 | compression 1 |
| 131,072 | 4,000 | 227 | 226 | 226 | compression 1 |

The loss at 16k, 32k and 128k is one span, every time:
```
{"question": "T2-P1", "style": "paraphrase", "path": "sources/interview/HB-IV-09-P09.md",
 "start": 24464, "end": 24554, "hit_rank": 2, "step": "compression",
 "uncompressed_block_chars": 3065, "rag_budget_chars": 3276 | 6552 | 16000}
```
The question is "Where do paper slips end up before anyone records them, according to a food
business owner?" The rank-2 chunk (469 characters) came out of compression at 288. The removed
lines were the answer and the interviewer's next question:
```
"removed_lines": [
  "**Jenny Lindqvist:** The receipt is in my apron pocket, then the van, then the laundry. By Friday it's a rumor.",
  "**Interviewer:** Can you anchor that in a specific week or incident?"]
```
(The corpus is synthetic; the participant is a generated persona.)

On the change (attempt 6 of a retry loop that keeps Istara's embedding cache between attempts,
because 32-chunk embed batches exceeded the local endpoint's 30-second timeout under Studio load;
same chunk order and batch boundaries as the baseline):

| window | RAG budget | retrieved | in prompt | verbatim | lost by step |
|---|---|---|---|---|---|
| 2,048 | 102 | 227 | 38 | 38 | budget_drop 189 |
| 4,096 | 204 | 227 | 173 | 166 | compression 11, budget_drop 43 |
| 8,192 | 409 | 227 | 218 | 217 | compression 1, budget_drop 8 |
| 16,384 | 819 | 227 | **227** | **227** | none |
| 32,768 | 1,638 | 227 | **227** | **227** | none |
| 131,072 | 4,000 | 227 | **227** | **227** | none |

T2-P1 is recovered at 16k, 32k and 128k. At 2k, 4k and 8k the lost-span lists are identical to
the baseline, span for span: the budget-pressure path is unchanged, and the cached vectors
retrieved the same chunks as the fresh baseline run.

pytest: `tests/test_spine_rag_budget_passthrough.py` and the two new tests in
`tests/test_spine_retrieval_eval.py` against the afe5c307 sources: 9 failed, 12 passed (the 8
earlier eval tests and the 4 budget-pressure guards pass on both sides). One failure shows the
harm directly: the rank-2 chunk lost "It is important to note that" and "in order to" became
"to", with about 9,000 characters of the 16,000-character block budget spare. On the change: 21 passed. The compressor, RAG,
chat, interface, context, prompt-RAG, contract, autoresearch-runner and migration suites:
239 passed, 1 skipped.

**Why that proves it.** The attribution rules out every other step: the span is in the
retrieved chunk, survives formatting, and its chunk reached the prompt, shortened. The whole
uncompressed block fit each budget, so nothing needed removing. Question-aware scoring keeps
lines that share words with the question, and a paraphrase question's answer shares none, so
the compressor removes the answer first. That is the opposite of faithfulness. After the
change, chunks that fit reach the prompt byte-for-byte, which the pytest pins through
`build_compressed_rag_context` (the chat and interface path). Under budget pressure the code
path and its output are unchanged; the guards pass on both sides. The 8k loss is the same span
under real pressure (3,065 > 1,636) and is not this defect.

Also measured: `_survives` counts a span as present when half its words appear consecutively in
the span and each appears anywhere in the prompt. At 4k it counts 173 spans; 166 are verbatim.
The published M3 column keeps the lenient reading for comparability; `answer_spans_verbatim` is
the strict one.

Commit de0e5c17 (code, tests, Tech.md, the contract bullet, the blind pack). Full backend suite
on 3d1a052d plus the change: 2,466 passed, 22 skipped; 3 failures and 1 collection error fail the
same way without the change (no network, no .git in the copy, no hypothesis in the image).

Open: independent blind review (`2026-09-25-spine-findings-phase7b-blind-pack.md`); no browser
scenario (DEC-8); `check_feature_obligations.py` fails for
`backend/app/evals/**` on the whole branch (inherited from Phase 7, noted on CF-11 for Phase 10).
