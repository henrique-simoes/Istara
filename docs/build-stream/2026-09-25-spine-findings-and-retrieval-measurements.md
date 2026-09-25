# Research-spine findings and retrieval measurements (2026-09-25)

```yaml
item: spine-findings-and-retrieval-measurements
branch: fix/spine-findings-measurements-20260925
cf: { spec: CF-SPEC-2, tasks: [CF-1, CF-2, CF-3, CF-4, CF-5, CF-6, CF-7, CF-8, CF-9, CF-10, CF-11, CF-12, CF-13, CF-14] }
phase: "Phase 8 — live lane (Muse Spark 1.3 Contributor + local Qwen, DEC-11)"
stage: S2-execute
status: in-progress
blocked_on: null
last: { agent: claude-code, at: 2026-09-25T21:05:00Z, ledger: L-16 }
next_action: "Settle local Qwen sampling (temperature 0 loops in reasoning), restart istara-cs76-live with the two-model env, upload the Harbor corpus through the product and run M4 (answer_eval) with the roles swapped between the two models. Phase 7b (CF-SPEC-3, other session): S3 pending an independent blind review via 2026-09-25-spine-findings-phase7b-blind-pack.md; CF-20/25/26 wait on it."
```

Evidence (four-part records per finding): `2026-09-25-spine-findings-evidence.md` beside this file.
CF state: this worktree's `.compass-forge` (recipe `istara-main`), spec CF-SPEC-2.

## Plan overview

**Problem.** A static map of Istara's retrieval, graph and agentic systems (Compass Forge
evaluation, 2026-09-25) found seventeen defects. F1, F2, F4 and F6 were fixed in PR #42. The
rest break research-spine promises: synthesized prose can confirm itself, the tuning loop has
no relevance labels, project evidence changes other projects' behaviour, learned routing
beats relevance, and truncation or document content can defeat the untrusted-content
boundary. Nothing measures whether retrieval is relevant.

**Outcome.** Every open finding (F3, F5, F7-F17) is fixed toward the contracts in
`docs/architecture/research-validity-contract.md` and
`docs/architecture/self-improvement-governance-contract.md`, each one pinned by a pytest that
fails on `origin/main` and driven through the product (UI scenario or live lane). Six
measurements exist as reusable harnesses with results: qrels (Recall@k, nDCG@10, MRR with
bootstrap CIs), re-indexing ablations with paired randomization tests, budget recall,
judge-validated faithfulness and context precision, provenance coverage, and learning-loop
safety. `testing` takes `main` without undoing PRs #40-#42, and Compass Forge is driven on
every change, with its defects reported.

**Appetite.** Large. One branch and one PR into `main`, with phases committed separately.

**Non-goals.** No new retrieval architecture (reranker, graph algorithms). No change to
coding-run reliability thresholds. No promotion run (owner-approved environment). No new
public workflows naming private hosts.

### Phases

| Phase | Findings / measurements | Acceptance (verification) |
|---|---|---|
| 0 Frame and setup | branch, CF spec, owner decisions | DEC-1..4 logged; CF spec exists |
| 1 Prompt-boundary safety | F13, F14 | pytest: closing tag survives every truncation; document tags neither pin nor escape the wrapper |
| 2 Evidence-index provenance | F5, M5, F7, F15 | pytest: derived text never confirms a claim; note scoping is exact; source chunks carry `evidence_unit_id`; watcher keeps BM25 rows; no ciphertext indexed |
| 3 Ranking semantics | F12, F17 | pytest: model sees rank, not fused value; findings never outrank source evidence by construction; compression keeps retrieval order; zero is not unset; bounds enforced; dead code gone |
| 4 Learning-loop governance | F10, F16, F9, M6 | pytest: irrelevant skill with perfect history never clears the floor; reads have no side effects; old relevant lessons reachable; promotions are project-scoped; planted successful-but-wrong run teaches nothing strong |
| 5 Plan DAG | F8 | pytest: dependents of a failed step do not run; no concurrent use of one AsyncSession |
| 6 Embedding identity | F11 | pytest: a same-dimension embedder swap is detected; stale cache not served |
| 7 Retrieval evaluation | M1, F3, M2, M3 | harness + qrels; F3 objective is qrels nDCG@10 on a sandbox index re-built per chunking; ablation and budget-recall reports |
| 7b M3 follow-up (CF-SPEC-3) | compression only under budget pressure | M3 names each lost span and its step; pytest: chunks that fit reach the prompt verbatim (fails on afe5c307); M3 re-run per window |
| 8 Live lane | M4, coding run, health, M1-M3 with real vectors | QA backend built from this tree; >=3 distinct model identities; judge validated; spend capped |
| 9 UI journeys | all behaviour changes | Playwright scenario(s) across the matrix, container lane, dated verdicts |
| 10 Docs and governance | Tech.md, contracts, personas, feature docs, security benchmark | obligation checkers and security benchmark pass |
| 11 `testing` catch-up | promotion train | `main` merged into `testing` the way the design allows; dry-run promotion diff shows PRs #40-#42 survive |
| 12 Ship | PR into `main` | required CI green; squash merge |

Rollback: every phase is a separate commit; revert the phase commit.

## Decision log

DEC-1 | 2026-09-25 | S0 | owner
Context: the owner's brief (`~/Documents/Istara fix session brief.md`) lists findings F3, F5,
F7-F17, six measurements, the `testing` catch-up, and continuous Compass Forge use.
Decision: that brief is the S0 frame. Its hard rules, its Studio-only execution and its
secret-handling rules are acceptance constraints.
Why: the owner wrote it and asked for it to be carried out as written.

DEC-2 | 2026-09-25 | S0 | owner
Context: real vector retrieval needs an embedder. The local server serves none.
Decision: use a local `nomic-embed-text` (Istara's own default profile) in a labelled
container on the Mac Studio.
Why: the owner chose it over DashScope embeddings and over restarting the local server.

DEC-3 | 2026-09-25 | S0 | owner
Context: the brief offers Luna, Terra, GLM-5.3-flash, GLM-5.2, Qwen3.7-max, local
Qwen3.8-27B and DeepSeek-v4-pro.
Decision: live runs use only gpt-5.6-luna, a GLM and the owner's local Qwen3.8-27B server.
DeepSeek is not used.
Why: the owner's answer: "Use Luna, GLM and Qwen (local 3.8-27B) only."

DEC-4 | 2026-09-25 | S0 | owner
Context: `2026-08-22-istara-pi-model-management-migration.md` DEC-2 calls the owner's local server retired.
Decision: that decision is superseded for live evaluation lanes. The owner's local llama.cpp server
joins ensembles as an `openai_compat` Pi endpoint. Its host, IP and port reach the stack only
through local environment files, never through a committed file, workflow or artifact
(CHANGE_CHECKLIST: private hosts).
Why: the owner's instruction in the brief.

DEC-5 | 2026-09-25 | S0 | owner
Context: M3 lost one answer span at every window of 16k tokens and above; the evidence file filed
the rank-based compressor as the likely cause and deferred the design change.
Decision: Phase 7b takes it now: instrument `budget_recall` to name each lost span and the step
that lost it; if compression under an ample budget is confirmed, pass chunks through uncompressed
when their total fits `max_tokens * 4` and compress only under budget pressure, keeping protected
blocks and retrieval order; a failing-first pytest; M3 re-run per window.
Why: the owner's request of 2026-09-25 (session of this phase), with the research-spine rationale
that compressing exact evidence the budget has room for harms faithfulness.

DEC-6 | 2026-09-25 | S1 | claude-code
Context: `compute_surplus_level` picks a compression strategy by compute cost ("constrained" = hard
trim only, zero LLM cost), and the low/constrained levels shrank every chunk further (x0.8, x0.6).
Decision: pass-through applies at every surplus level; the surplus level shapes compression only
under budget pressure. Protected chunks keep their place in front, in original order, in the
pass-through path too, so the output order does not depend on the budget.
Why: passing text through costs no compute, so it is consistent with every strategy; the budget
coordinator already sized the RAG budget. Rejected: keeping the x0.6/x0.8 shrink for low surplus,
which removes evidence to save prompt tokens the budget already granted.

DEC-7 | 2026-09-25 | S1 | claude-code
Context: `compass-forge classify` and `spec create` scored no change type for this request
(`basis: fallback`, `lite`).
Decision: Phase 7b is its own spec, CF-SPEC-3 (tasks CF-15..CF-26), run at Standard level (impact
graph, gate before/after, tests and living docs, independent review), not Lite.
Why: it changes what evidence the chat and interface prompts carry (research-spine behaviour), so
the fallback level understates it. A separate spec lets it close without waiting for CF-SPEC-2.

DEC-8 | 2026-09-25 | S1 | claude-code
Context: AGENTS.md asks every behaviour change for coverage in the container user-journey suite.
Phase 7b changes only the text of the RAG block inside the chat/interface prompt. In the
credential-free QA lane the provider stub neither records the prompt nor answers from it
(`qa/scripts/provider_stub.py`), and the chat's source list is the same with or without the
change, so no browser act can observe it there.
Decision: no Playwright scenario in Phase 7b. The behaviour is pinned by pytest through
`build_compressed_rag_context` (the chat and interface path) and measured by M3. Browser coverage
moves to Phase 8/9: M4 on the live lane (answer faithfulness with the verbatim block), or a
prompt-recording provider stub so a scenario can assert the block the chat sent. Reported as open
coverage, not as done.
Why: a scenario that cannot observe the change would pass on both sides and certify nothing.
Starting the QA stack from this tree also needs the owner's go-ahead in this session (AGENTS.md
live-server rule).

DEC-9 | 2026-09-25 | S2-execute | owner
Context: Probing the live lane: the OpenAI OAuth credential no longer resolves (the owner cancelled
the subscription); Z.ai GLM-5.3-flash failed because Istara ignored the endpoint's thinking level;
The owner's local Qwen3.8-27B streams steadily at ~15 tokens/s but every run was killed at 120 s.
Decision: The live-lane models are Meta Muse Spark 1.3 Contributor (endpoint pi-muse-spark, pinned to
muse-spark-1.3-contributor only, Meta direct), GLM-5.3-flash (pi-zai-glm) and local Qwen3.8-27B
(pi-local-qwen). The owner's local server supersedes the "retired" note of DEC-2 in the Pi model-management
migration doc. The pi-ai bump to 0.87.1 (which adds Meta as a provider) is done in this session.
The owner ruled that the 120 s limit is Istara's defect, not the model's: local models are
paramount. Istara adopts per-endpoint liveness (see DEC-10).
Why: Owner instruction; judges must differ from the model under test, which needs three working
identities.

DEC-10 | 2026-09-25 | S2-execute | claude-code
Context: Three 120 s limits stack in the Pi path: the worker's fixed wall clock per run, the
supervisor's wait between frames, and `timeout_ms` (<= 120 s, pi-ai's request timeout, which the
provider SDKs apply until the response starts). A local model that streams thinking tokens
steadily for more than two minutes is killed however healthy it is.
Decision: Liveness is per endpoint and progress-based. An idle timeout bounds the silence between
streamed events (text, thinking and tool frames all count). A total run budget is a generous
backstop. Defaults depend on locality: remote idle 120 s / total 600 s (the OpenAI and Anthropic
SDK default of 10 minutes); local idle 300 s (Open WebUI's 300 s Ollama default and Ollama's
load-stall window) / total 3,600 s (llama.cpp server's default read/write timeout). Locality is
inferred from the base URL host (loopback, RFC 1918, CGNAT 100.64/10 used by Tailscale, link-local,
IPv6 ULA, `localhost`, `*.local`, `*.ts.net`, `host.docker.internal`, single-label service
names) and can be set explicitly. `timeout_ms` keeps its meaning (response start) with a 600 s
ceiling. The supervisor waits the idle budget plus a margin, so the worker reports the precise
error (`idle_timeout_exceeded` or `wall_clock_budget_exceeded`).
Why: Progress-based liveness is the industry pattern (OpenAI SDK read timeout 600 s, Anthropic SDK
10 min with streaming, LiteLLM time-to-first-chunk vs request timeout, Open WebUI and llama.cpp
defaults). Rejected: raising the one global limit (it would delay failure detection for remote
providers too) and per-model prompt hacks such as /no_think (the local server's non-thinking output
degenerates, and it would not help other local models).

DEC-11 | 2026-09-25 | S2-execute | owner
Context: With the per-endpoint liveness fix, three identities answer through Istara (Muse Spark 1.3
Contributor, GLM-5.3-flash, local Qwen3.8-27B). The brief asked for coding runs with at least
three distinct identities.
Decision: Owner instruction: use only Meta Muse Spark 1.3 Contributor (pi-muse-spark) and
The owner's local Qwen3.8-27B (pi-local-qwen). No other model. The live env removes every other
endpoint (default pi-muse-spark; research ensemble = these two). Embeddings stay on the local
nomic-embed-text container the owner chose earlier (the local server serves no embeddings). Consequences:
the governed coding run uses two identities, not three, and every judge-generator pair is these two
with roles swapped, so a judge is never the model under test.
Why: Owner instruction supersedes the brief's three-identity default.

## Phase 8 — live lane (Muse Spark 1.3 Contributor + local Qwen)

Goal: measure answers on the live lane with the owner's two models (DEC-11): M4 faithfulness and
context precision with the judge never the model under test (roles swapped between the two), a
governed coding run with both identities, and the F13/F14 hostile-document chat.
Setup: `istara-cs76-live` built from this branch, env carried from the stopped w4 container into a
0600 file (never printed), Meta key pasted by the owner in a hidden terminal, the local server's address
read from the Studio's Tailscale at run time (never committed), embeddings on the local
nomic-embed-text container.
Found and fixed on the way (each with a test that fails on origin/main): the endpoint thinking level
was ignored and failed turns had no reason (ecdf7d3e); every run had a fixed 120 s stopwatch
(3d1a052d, DEC-10); Meta needed pi-ai 0.87.1 (daebba8b).
Open: local Qwen loops in reasoning at temperature 0 (Qwen's model card forbids greedy decoding
in thinking mode). Acceptance: both models answer the M4 questions within their budgets, and the M4
report lists judge agreement with the planted labels (Cohen's kappa) before any score is trusted.
Verification: `python -m app.evals.answer_eval --project-id <harbor> --generator <A> --judges <B>
--max-usd <cap>` in istara-cs76-live, then with A and B swapped.

## Ledger

### L-1 | 2026-09-25T18:05:00Z | S0-frame | claude-code | framer | —
Did: read AGENTS.md, both architecture contracts, Tech.md (prompt management, context and
memory, RAG pipeline, self-evolution), TESTING.md, CHANGE_CHECKLIST.md,
SYSTEM_CHANGE_MATRIX.md, both architecture HTML pages and the static map. Read the code behind
every finding.
Result: all findings reproduce on reading. Line numbers moved after PR #42, and the evidence
file cites the current ones.
Verified: none — reading only.
Next: owner decisions on the embedder and DeepSeek.

### L-2 | 2026-09-25T18:21:00Z | S0-frame | claude-code | framer | —
Did: asked the owner two questions (embedder, DeepSeek). Created branch
`fix/spine-findings-measurements-20260925` from `origin/main` @ `9272d41e`. Switched this
worktree's CF recipe to `istara-main`, refreshed the index, and created CF-SPEC-2 (classified
Full, `security_or_architecture`).
Result: DEC-2 and DEC-3 recorded. CF defects IST-CF-1..5 sent to the Compass Forge session.
Verified: `compass-forge index status` graph_usable true after the second refresh;
`compass-forge classify` basis scored, kind security_or_architecture.
Next: plan Phase 1.

### L-3 | 2026-09-25T18:27:00Z | S1-plan | claude-code | planner | —
Did: wrote this roadmap. Set up the Studio test lane: rsync to
`~/cf-remote/eval/istara-work`, pytest in `istara-test:1` with `--network none`.
Result: baseline `tests/test_retrieval_correctness_fixes.py tests/test_rag_resilience.py`: 17
passed.
Verified: `pytest ../tests/test_retrieval_correctness_fixes.py ../tests/test_rag_resilience.py -q`
-> 17 passed (istara-test:1, network none).
Next: Phase 1 tests first.

### L-4 | 2026-09-25T18:34:00Z | S2-execute | claude-code | executor | Phase 1
Did: F13: `content_guard.truncate_preserving_wrappers` and `neutralize_boundary_markup`, applied in
`wrap_untrusted` (plus a sanitised source attribute); A2A collaboration puts wrapper-safe
documents before the question; ReasoningBank `format_memory_context` builds line by line
against the budget; skill fallback plan and simulation skill truncate wrapper-safely. F14:
retrieved text is neutralised before RAG compression; `_fit_to_budget` makes the budget a hard
limit for ordinary text (a second defect found by the F14 test: `_trim_preserving_protected_blocks`
never trimmed plain text); `build_compressed_rag_context` measures label and wrapper cost per
result and keeps the whole block inside `max_tokens`. Files: content_guard.py, rag.py,
reasoning_bank.py, agent_lifecycle.py, prompt_compressor.py, skill_factory.py,
simulation_skill.py, tests/test_spine_prompt_boundaries.py.
Result: new tests fail on origin/main (14 failed / 2 passed) and pass here. Related suites
110 passed. ruff 0.16.6: backend format check clean after formatting rag.py; correctness and
strict lint clean. CF refresh picked up the new edges (content_guard → context_policy; three
new importers).
Verified: `pytest ../tests/test_spine_prompt_boundaries.py ../tests/test_data_transformations.py ../tests/test_rag_resilience.py ../tests/test_retrieval_correctness_fixes.py ../tests/test_reasoning_bank.py ../tests/test_content_guard.py ../tests/pi_production/test_w4_a2a_handlers.py ../tests/test_prompt_rag.py ../tests/test_chat.py ../tests/test_agent_personas.py -q` → 110 passed (istara-test:1, network none); the same new file on origin/main → 14 failed, 2 passed.
Next: Phase 2.

### L-5 | 2026-09-25T18:51:00Z | S2-execute | claude-code | executor | Phase 2
Did: F5 derived index (rag DERIVED_TABLE/namespace, ingest_derived_chunks, retrieve_derived_context;
legacy agent:/skill: rows pre-filtered from source retrieval), exact agent-note scoping, skill
artifacts chunked whole and replaced on rerun; M5 services/retrieval_provenance.py (annotate,
index_document_source_chunks, provenance_coverage) wired into upload, audio, reprocess,
documents sync, knowledge sync and the watcher; F7 watcher indexes both indices; F15 reveal
before indexing/matching; F17 part (backslash delete, zero threshold, honest telemetry mode).
Commit 2b762a63.
Result: tests/test_spine_evidence_provenance.py 9/9 fail on origin/main for their stated
reasons and pass here; related suites 125 passed (one seam update in test_rag_resilience).
Verified: `pytest ../tests/test_spine_evidence_provenance.py -q` on origin/main → 9 failed; on
2b762a63 → pass; `pytest` of the 12 related files → 125 passed (istara-test:1, network none).
ruff 0.16.6 backend format/correctness/strict clean.
CF: IST-CF-4 refined by a clean-clone reproduction (see L-6 note in the CF report).
Next: Phase 3.

### L-6 | 2026-09-25T18:57:39Z | S2-execute | claude-code | executor | Phase 3
Did: F12 rank labels (rag, persona protocols), retrieval-order compression, findings search on
separate scales with provenance-keyed dedupe, Prompt-RAG single-scale fallback; F17 bounded
top_k (tool + route), memory paging without whole-table loads, dead mutator removed, NULL
description, legacy catalog admission on every surface. Commit 5b742c52.
Result: tests/test_spine_ranking_semantics.py 11/11 fail on origin/main, 11/11 pass here; 25
related files 488 passed. ruff clean.
Verified: `pytest ../tests/test_spine_ranking_semantics.py -q` → origin/main 11 failed; branch
11 passed; 25-file related run → 488 passed (istara-test:1, network none).
Next: Phase 4.

### L-7 | 2026-09-25T19:05:50Z | S2-execute | claude-code | executor | Phase 4
Did: F10 relevance-gated routing with bounded priors; M6 self-verification is provisional
(policy, usage stats, ReasoningBank, neutral confidence cap); F16 pure retrieve with SQL
relevance prefilter, usage counted on prompt use, single-retrieve API, read-only vector health;
F9 per-project persona learnings, cache keyed by space+description. Commit 15d21121.
Result: tests/test_spine_learning_loops.py 8/9 fail on origin/main (the 9th is the weak-prior
guard), 9/9 pass here; 22 related files plus task/skill/chat suites pass (one seam update).
Verified: branch `pytest ../tests/test_spine_learning_loops.py -q` → 9 passed; origin/main → 8
failed, 1 passed; related runs all green (istara-test:1, network none). ruff clean.
Next: Phase 5.

### L-8 | 2026-09-25T19:07:50Z | S2-execute | claude-code | executor | Phase 5
Did: F8 DAG blocking, per-plan session lock, dependency-scoped context. Commit in git log (fix(plan-dag)).
Result: tests/test_spine_plan_dag.py 3/3 fail on origin/main, pass here; plan suites 47 passed.
Verified: `pytest ../tests/test_spine_plan_dag.py ../tests/test_agents.py ../tests/pi_production/test_w3_research_spine.py -q` → 47 passed (istara-test:1, network none); origin/main → 3 failed.
Next: Phase 6.

### L-9 | 2026-09-25T19:39:38Z | S2-execute | claude-code | executor | Phase 6
Did: F11 embedder fingerprint (probe-vector hash) in the cache namespace, the store binding and
vector health; W8 cache-trust test seeded with a known fingerprint. Upload, audio and document
sync commit before indexing (found in passing: the branch full suite stalled on the SQLite write
lock while indexing embedded inside the request's transaction). Commit ec093015 (with Phase 7).
Result: tests/test_spine_embedding_identity.py 3/3 fail on origin/main (old cached vector served,
old store answered, health "All vector dimensions match"), 3/3 pass here. Full branch suite: 6
failed, 2425 passed, 15 skipped, 1 error. 4 failures and the error also occur on main; the other 2
were W6 tests pinned to the old objective, now moved to its new seams.
Verified: `pytest ../tests/test_spine_embedding_identity.py -q` origin/main → 3 failed; branch →
3 passed. Full suite `pytest ../tests -v --continue-on-collection-errors` in istara-test:1 → as
above. `pytest ../tests/pi_production/test_w6_autoresearch_runners.py ../tests/test_spine_retrieval_eval.py ../tests/pi_migration ../tests/test_autoresearch.py -q` → 98 passed, 1 skipped. ruff 0.16.6 format/check clean.
Next: Phase 7.

### L-10 | 2026-09-25T19:39:38Z | S2-execute | claude-code | executor | Phase 7
Did: F3 objective = nDCG@10 on span-graded qrels over sandbox indices rebuilt per chunking;
candidates staged on the runner, never on settings; fail closed without a benchmark; engine
closes runner sandboxes. Harnesses app.evals.retrieval_eval (M1-M3) and answer_eval (M4); 76
qrels over the committed Harbor Ledger corpus; rag_rrf_k setting; explicit chunk sizes in
file_processor. Commit ec093015; CLI model-registry fix 64ccc469.
Result: tests/test_spine_retrieval_eval.py 8/8 fail on origin/main (weight scaling moved the old
objective 0.1001 → 0.1011; settings read 0.31 mid-measurement; no sandbox), 8/8 pass here.
M1 with real nomic-embed-text (768-d, fingerprint ff22f761301f81f0), 1097 chunks, 76 questions:
nDCG@10 BM25 0.717 [0.636, 0.795], vector 0.571 [0.497, 0.645], hybrid 0.700 [0.627, 0.771];
hybrid vs BM25 p = 0.50 (not better), vector worse than both (p ≤ 0.0003).
Verified: `pytest ../tests/test_spine_retrieval_eval.py -q` origin/main → 8 failed; branch → 8
passed. `python -m app.evals.retrieval_eval evaluate` (istara-test:1 on istara-cs76-live, Ollama
istara-cs76-embed) → 39.8 s, results above.
Next: M2 ablations and M3 budget recall; then Phase 8 live lane.

### L-11 | 2026-09-25T19:48:01Z | S2-execute | claude-code | executor | Phase 9
Did: M5 Evidence Provenance card on Memory → Health; tab row wraps at 375px, aria-pressed, dark
contrast for tab and Health labels. Scenario 86 registered in scenario-registry and the coverage
matrix. Commit 13dfdaac.
Result: first QA run 86 19/22 (axe dark: color-contrast on 16 nodes at 4.23:1); after the fix
86 22/22, 85 10/10, 23 13/13. tsc clean; eslint 0 errors (warnings pre-existing); simulation
static checks 41/41.
Verified: `~/cf-remote/eval/istara-qa-run-cs76.sh sim 86-evidence-provenance-health,85-retrieval-correctness,23-memory-view`
(QA_RUN_ID cs76-sept25, ports 8320/3320, loopback) → 45/45; run 2026-09-25T19-43-40-637Z.
`npx tsc --noEmit` → 0; `npm run lint` → 0 errors.
Next: M2/M3 results, then Phase 8 (live lane).

### L-12 | 2026-09-25T20:24:17Z | S1-plan | claude-code | planner | Phase 7b
Did: took the M3 follow-up the evidence file filed (DEC-5). At session start the working tree
held uncommitted edits to this file and the evidence file (M2/M3 results, L-9..L-11); they are
kept as found. CF-SPEC-3 created, clarified (`verification-bar`, `scope-boundary`), planned and
tasked (CF-15..CF-26); `classify` fell back to lite, level chosen as Standard (DEC-7). Impact:
`compress_rag_chunks_indexed` has one production caller, `rag.build_compressed_rag_context`
(chat, interfaces, answer_eval, retrieval_eval); Tech.md and the research-validity contract
document it. `gate before --task CF-15` recorded baseline record 4. Studio lane: own copies
`~/cf-remote/eval/istara-m3fix` (change), `istara-m3fix-before` (afe5c307 compressor),
`istara-m3fix-head` (afe5c307 compressor and eval), scripts `m3fix-measure.sh`,
`m3fix-pytest.sh`, `m3fix-wait-measure.sh`; the previous session's `istara-work` untouched.
Result: plan = instrument, confirm, test first, fix, re-measure. No UI scenario (DEC-8).
Verified: `compass-forge index status` graph_usable true, no blocking or unindexed paths;
`intelligence impact/why/test-impact` resolved (impact partial: cut at depth bound).
Next: instrument `budget_recall` and run M3 on the unchanged compressor.

### L-13 | 2026-09-25T20:24:17Z | S2-execute | claude-code | executor | Phase 7b
Did: `budget_recall` now lists every lost answer span (question, style, path, offsets, first 80
characters, hit rank, uncompressed block size, RAG budget) with the step that lost it
(`retrieved_chunk`, `prompt_formatting`, `budget_drop`, `compression`), `lost_by_step`, and
`answer_spans_verbatim`. Ran it on the afe5c307 compressor. Reproduced the compression of the
answer chunk in isolation (`compress_with_question(chunk, T2-P1, 0.85)`, network none).
Result: 16k, 32k and 128k each lose the same span: T2-P1 (paraphrase),
`sources/interview/HB-IV-09-P09.md` 24464-24554, hit rank 2, step `compression`, uncompressed
labelled block 3,065 characters against budgets of 3,276, 6,552 and 16,000. The rank-2 chunk
(469 characters) came out at 288: the participant's answer line was removed whole, because it
shares no word with the question. At 8k the same span is lost to compression under real
pressure (3,065 > 1,636). At 4k the strict count shows 166 spans verbatim against 173 counted
by the lenient `_survives`. Cause confirmed.
Verified: `WS=istara-m3fix-before ~/cf-remote/eval/m3fix-measure.sh before` (istara-test:1 on
istara-cs76-live, nomic-embed-text) → exit 0, 68.7 s, `measure-m3fix/m-budget-before.json`.
Next: failing-first pytest, then the compressor change.

### L-14 | 2026-09-25T21:04:00Z | S2-execute | claude-code | executor | Phase 7b
Did: failing-first pytest (`tests/test_spine_rag_budget_passthrough.py`, two `budget_recall` tests
in `tests/test_spine_retrieval_eval.py`); `compress_rag_chunks_indexed` passes chunks through
verbatim when their total fits `max_tokens * 4`, protected first then retrieval order, at every
surplus level (DEC-6); rank ratios moved to `_rank_keep_ratio` and two eval helpers folded in
after `gate after` flagged complexity 21 > 20 and 81 > 80 symbols. Tech.md pipeline block and a
research-validity contract bullet. Blind pack for the independent reviewer. Commit de0e5c17.
Result: on afe5c307 sources the new tests give 9 failed, 12 passed; on the change 21 passed.
M3 after: 2k 38, 4k 173, 8k 218 (lost-span lists identical to the baseline), 16k/32k/128k
227/227 (T2-P1 recovered, verbatim 227). `gate after`: 0 new failures, 0 new warnings. Full
suite 2,466 passed, 22 skipped; 3 failed and 1 error, all failing identically without the
change. `check_feature_obligations.py` fails on `backend/app/evals/**` for the whole branch
(inherited from Phase 7; comment on CF-11). CF-15..CF-19 and CF-21..CF-24 done with evidence;
CF-20, CF-25 and CF-26 wait for the review.
Verified: `WS=istara-m3fix-head m3fix-pytest.sh ../tests/test_spine_retrieval_eval.py ../tests/test_spine_rag_budget_passthrough.py -q` → 9 failed, 12 passed;
same on `istara-m3fix` → 21 passed; 14-target related run → 239 passed, 1 skipped;
`m3fix-retry.sh istara-m3fix after m3fix-embcache-after` → `measure-m3fix/m-budget-after.json`;
`pytest ../tests -q --continue-on-collection-errors` (istara-test:1, network none) → as above;
`compass-forge gate after --task CF-15 --summary`; `python3 scripts/check_change_obligations.py`
→ passed; `python3 scripts/security_benchmark.py --fail-on-threshold` → pass, 100%, not
triggered; `python3 scripts/public_repo_quality_audit.py --check` → passed. ruff 0.16.6 clean.
Next: Phase 7b S3: an independent reviewer (a different agent and model) takes only
`2026-09-25-spine-findings-phase7b-blind-pack.md`, freezes its sheet, then reconciles against
this ledger; then `compass-forge spec accept CF-SPEC-3`. The plan's Status Block (owned by the
other session) still names Phase 8 as next.

### L-15 | 2026-09-25T21:05:00Z | S2-execute | claude-code | executor | Phase 7
Did: M2 re-run after fixing the chunk overlap (F17 residue found by M2: explicit 0 became 180;
large overlaps never terminated), M3 budget recall; the complexity drift CF's gate after reported
(refactor commit afe5c307; chunking fix 74c167ce).
Result: M2 (hybrid nDCG@10, baseline 0.6996): no single-factor change beats the defaults after
Holm; chunk_size=800 (-0.022, Holm p 0.0065), vector_weight=0.9 (-0.047, 0.0006) and rrf_k=10
(-0.034, 0.0006) are significantly worse. M3 budget recall 0.167 at a 2k window, 0.762 at 4k,
0.960 at 8k, 0.996 at 16k and above. tests/test_spine_chunking_parameters.py 6/6 fail on
origin/main, pass here. gate after: new_failures 0; new warnings 10 -> 5 (all pre-existing
hotspots with +1/+2, and rag.search 30 -> 25 reported as "new" because its value changed).
Verified: `python -m app.evals.retrieval_eval ablate|budget` via measure-run.sh (istara-test:1,
nomic-embed-text 768-d, fingerprint ff22f761301f81f0); pytest chunking + 25 upload/chunking suites
263 passed; 36 suites for the refactored modules 493 passed; QA lane 86 22/22, 24 9/9, 85 10/10,
23 13/13 (run 2026-09-25T19-58-53-943Z).
Next: live lane.

### L-16 | 2026-09-25T21:05:00Z | S2-execute | claude-code | executor | Phase 8
Did: live lane on the Studio: backend built from this branch (istara-cs76-live, loopback 8330,
network istara-cs76-live), env carried from the stopped w4 live container into a 0600 file never
printed; the local server added as pi-local-qwen (address from the Studio's Tailscale at run time);
owner's Meta key pasted in a hidden terminal (0600 file). Probes found three product defects,
fixed with tests that fail on origin/main: endpoint thinking level ignored and failed turns
without a reason (ecdf7d3e), a fixed 120 s stopwatch on every run (3d1a052d, DEC-10). pi-ai
0.87.1 bump for Meta (daebba8b). Owner narrowed the models to Muse Spark 1.3 Contributor and
local Qwen (DEC-11).
Result: pi-muse-spark answers (served muse-spark-1.3-contributor, 4.6 s); pi-zai-glm answered
after the thinking fix (now excluded by DEC-11); pi-local-qwen no longer dies at 120 s but at
temperature 0 it loops in reasoning (16,384 tokens, 1,124 s, no answer; Qwen's model card forbids
greedy decoding in thinking mode). Re-probe at temperature 0.6 running.
Verified: probe.py/frame_probe.py through Istara's dispatcher in istara-cs76-live; pytest Pi
suites 833 passed (liveness) and 827 passed, 6 skipped (bump); worker 103/103; security benchmark
100% (28/28, 28 triggered paths).
Next: settle the local server's sampling, restart the live backend with the two-model env, then M4 and the
governed coding run.
