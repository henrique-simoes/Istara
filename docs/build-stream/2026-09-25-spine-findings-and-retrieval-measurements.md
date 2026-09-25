# Research-spine findings and retrieval measurements (2026-09-25)

```yaml
item: spine-findings-and-retrieval-measurements
branch: fix/spine-findings-measurements-20260925
cf: { spec: CF-SPEC-2, tasks: [] }
phase: "Phase 3 — ranking semantics (F12, F17)"
stage: S2-execute
status: in-progress
blocked_on: null
last: { agent: claude-code, at: 2026-09-25T18:51:00Z, ledger: L-5 }
next_action: "Phase 3: tests for rank labels to the model/tools/MCP, findings search scales and provenance dedupe, compression keeping retrieval order, Prompt-RAG single scale, unbounded top_k, memory pagination without whole-table loads, dead code; run on origin/main first."
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
