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
