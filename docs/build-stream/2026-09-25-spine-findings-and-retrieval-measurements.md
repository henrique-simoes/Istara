# Research-spine findings and retrieval measurements (2026-09-25)

```yaml
item: spine-findings-and-retrieval-measurements
branch: fix/spine-open-items-20260926
cf: { spec: CF-SPEC-4, tasks: [CF-27, CF-28, CF-29, CF-30, CF-31, CF-32, CF-33, CF-34, CF-35, CF-36, CF-37, CF-38, CF-39, CF-40, CF-41, CF-42, CF-43, CF-44] }
phase: "Phases 13-17 — open items (CF-SPEC-4)"
stage: S2-execute
status: in-progress
blocked_on: null
last: { agent: claude-code, at: 2026-09-26T02:38:48Z, ledger: L-23 }
next_action: "Extend the qrels with Spanish questions, implement role-aware embedding prompts with the prompt scheme in the vector-space identity, then run the DEC-15 embedder comparison on the Studio."
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
| 13 Third model (CF-SPEC-4) | DeepSeek V4 Flash through Pi; three-identity governed coding run | probe: served model; W3 A-E with 3 distinct served identities, Fleiss kappa + Krippendorff alpha, reconciliation and report gate |
| 14 Embedder | role-aware prompts; multilingual candidates; default by DEC-15 | pytest (prompt scheme in the vector-space identity, profile migration re-index); extended M1 comparison; scenario for any UI change |
| 15 Judges and faithfulness | M4 v2 (DEC-14) with three models | judge validation report; faithfulness per generator from trusted judges |
| 16 Complexity | seven gate-after warnings | `gate after` reports no new warnings |
| 17 Ship | PR into `main` | required CI green; squash merge |

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

DEC-12 | 2026-09-26 | S2-execute | claude-code
Context: M4 ran in both directions. Neither judge met the pre-registered trust rule (Cohen's kappa at
least 0.60 on both the relevance items and the planted claims): local Qwen 0.568 / 1.000, Muse Spark
0.453 / 0.926. Faithfulness only uses the claim task, which both judges pass.
Decision: Keep the rule and report faithfulness as not measured. Record the claim-task results and
the likely cause (exact 0/1/2 agreement against span grades) as findings, and name the calibration
that would settle it (a small human-labelled relevance set; a third identity is ruled out by DEC-11).
Why: Loosening a validation rule after seeing which way it fell is outcome-driven analysis; the
spine's point is that unvalidated judgments never become evidence. Rejected: scoring faithfulness
with the claim-validated judges as a secondary analysis (it would read as a result).

DEC-13 | 2026-09-26 | S1-plan | owner
Context: The plan shipped (PR #44) with open items: no independent review, faithfulness unmeasured,
governed coding limited to two identities, an English-only embedder, and seven complexity warnings.
Decision: Owner instructions: forget independent reviews (none will be run for this plan, and Phase
7b's blind pack is withdrawn); add DeepSeek V4 Flash as the third live model (DEC-11 extended: Muse
Spark 1.3 Contributor, local Qwen, DeepSeek V4 Flash); find, download and serve a better embedding
model (EmbeddingGemma suggested); complete every other open item. The plan reopens as Phases 13-17
under CF-SPEC-4.
Why: Owner instruction.

DEC-14 | 2026-09-26 | S1-plan | claude-code
Context: M4 v1 trusted a judge only if it matched the qrels on 0/1/2 relevance grades and on planted
claims (kappa >= 0.60 each). No reported score uses a judge's relevance grades (context precision
comes from the qrels), and the qrels can give grade 1 only to planted related quotes, so a judge that
calls ordinary on-topic text "1" is scored wrong by construction. Both judges passed the claim task
(1.000, 0.926) and failed relevance (0.568, 0.453). This rule change is prompted by that outcome, and
is recorded before any v2 run.
Decision (pre-registered, M4 v2): (a) a judge is trusted for faithfulness when Cohen's kappa is at
least 0.60 on at least 50 construction-labelled claims (verbatim supported, first-sentence supported,
other-theme unsupported, number-altered contradiction, negated contradiction where a deterministic
negation exists); (b) relevance is validated on a balanced, construction-labelled set as a binary
"contains the answer" task (a chunk carrying a target span versus a chunk of another theme or a
related quote of the same theme), kappa reported beside the trust decision, not gating it, because no
score uses it; (c) each generator is judged by the two other models, never by itself, and the two
judges' agreement on claims is reported; (d) the v1 rule's outcome is reported for the same run.
Faithfulness is reported only for trusted judges.
Why: Validate a judge on the task it performs (UMBRELA's point), with truth known by construction on a
synthetic corpus. Rejected: human labels (none available in this session; construction labels are the
ground truth for planted answers), scoring faithfulness from untrusted judges.

DEC-15 | 2026-09-26 | S1-plan | claude-code
Context: nomic-embed-text is English-only (vector nDCG@10 on the 4 Spanish questions: 0.028), and
Istara sends raw text to every embedder although the model cards specify query/document prompts.
Decision (pre-registered selection rule): candidates EmbeddingGemma-300m, Qwen3-Embedding-0.6B and
BGE-M3, each with its model card's prompts, against the shipped nomic-embed-text (raw) and
nomic-embed-text with its own prefixes. Qrels extended with at least 30 new Spanish questions written
against the corpus's planted Spanish quotes. Metric: hybrid nDCG@10 (the product's retrieval) and
vector nDCG@10, paired sign-flip randomization tests against the shipped baseline, Holm correction
across candidates. A candidate qualifies if it is significantly better than the shipped baseline on
hybrid nDCG@10 overall and on the Spanish subset, and not significantly worse on any English style.
The default becomes the qualifying candidate with the highest hybrid nDCG@10; when the top two do not
differ significantly, EmbeddingGemma (owner's suggestion, smallest) is preferred. If none qualifies,
the default stays and the result is reported. Existing installs change model only through a new
embedding-profile version and a re-index.
Why: A default embedder is a product-wide decision; it needs a rule fixed before the numbers exist.

DEC-16 | 2026-09-26 | S2-execute | claude-code (by the DEC-15 rule)
Context: the five-arm comparison ran on qrels v2 (118 questions, 46 Spanish) on the Studio. The
rule's code (`app/evals/embedder_compare.py`, 1a25f1e6, 03:17Z) was committed after the two nomic
arms and before any candidate result (EmbeddingGemma 03:40Z, Qwen3 03:45Z, BGE-M3 03:48Z).
Decision: BGE-M3 is the default embedder. All four candidates qualify (Holm p 0.0002 overall and in
Spanish; no English style significantly worse). Hybrid nDCG@10: BGE-M3 0.788, Qwen3-Embedding-0.6B
0.781, EmbeddingGemma 0.741, prompted nomic 0.632, shipped nomic 0.523. The top two do not differ
(p = 0.68), so the higher mean wins; the EmbeddingGemma preference applies only when it is one of
the tied pair, which it is not (it is lower than BGE-M3, p = 0.035 unadjusted, supplementary).
Why: the rule fixed before the numbers. Caveat recorded: every candidate is lower than nomic on the
12 fact questions (BGE-M3 0.718 vs 0.848), not significant after Holm (p 0.50).

DEC-17 | 2026-09-26 | S2-execute | owner
Context: scenario 87's 375 px check found the Settings column 527 px wide and clipped; the same sizing
defect sat in six more views, and a probe of every view found Chat, Interviews, Documents and
Notifications cut off in other ways. I raised the six-view fix as a separate task.
Decision: the owner adopted it into this plan. Every view is fixed and a stricter shared 375 px check
(nothing inside `main` cut off, not only no page scroll) plus scenario 88 cover them.
Why: owner instruction.

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

## Phase 12 — ship

**Outcome vs the S0 goal.** Every open finding (F3, F5, F7-F17) is fixed, each pinned by a pytest
that fails on `origin/main` and driven through the product (QA `ui` lane scenarios, live lane). The
six measurements exist as harnesses with results (M1-M3 with the real embedder; M4 on the owner's two
models; M5 as a Health-tab invariant; M6 in the default suite). `testing` took `main` (PR #43, merge
commit 611d7a21); the promotion itself was not run. Compass Forge was driven throughout; CF-SPEC-2 is
accepted with command evidence on all 14 tasks, and six CF defects were reported (IST-CF-1..6).

**Residual risk.** Faithfulness (M4) is unmeasured until the judges are calibrated on human labels.
Governed coding cannot promote with two model identities (DEC-11). The embedder is English-only.
Seven complexity warnings from `gate after` are recorded, not fixed (the moved sync loop, Pi runtime
methods touched by liveness and structured output, one test module's symbol count). Phase 7b
(CF-SPEC-3, other session) still waits for its independent blind review. No independent S3 reviewer
ran on this plan (the owner does not allow subagents); its review coverage is self-only.

**Retro (blameless).** What worked: pinning each finding with a test that fails on `main` before the
fix, and driving the product afterwards; the live lane and the UI suite found nine defects the static
map had not listed (double indexing, uuid classification, sticky suggestions at 375 px, a
spine-bypassing agent sync, markup escaping tool output, Pi thinking level, liveness, structured
output on Meta, harness exits). What to do differently: validate a measurement harness against the
product's real storage before its first number (M4's first run graded uploads by path, and uploads
are stored under uuids); run `gate after` straight after every refactor, not at the end (it caught an
import cycle a quick fix introduced); record owner decisions about models before building live env
files, so the env and the plan agree from the start.

## Phases 13-17 — open items (CF-SPEC-4)

Goal: close every item Phase 12 left open (DEC-13): a third live model identity and a governed
coding run with three identities; judge-validated faithfulness (DEC-14); a measured multilingual
embedder with role-aware prompts and a safe migration (DEC-15); the seven complexity warnings.
Setup: branch `fix/spine-open-items-20260926` from `main` at 169128dc; Studio embedder container
`istara-cs76-embed` (labelled) serving nomic-embed-text, embeddinggemma, qwen3-embedding:0.6b and
bge-m3; the owner's DeepSeek key from the macOS Keychain and the Meta key re-entered in a hidden
terminal (both only in 0600 files on the Studio, never printed).
Acceptance: as in the phase table rows 13-17. Verification: pytest failing on origin/main first per
behaviour change; extended M1 on the Studio; live-lane runs; security benchmark; obligations; CF
gate after with no new failures or warnings; CI green on the PR.

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

### L-17 | 2026-09-25T21:29:37Z | S2-execute | claude-code | executor | Phase 8
Did: diagnosed the local server. At temperature 0 Istara's probe ran 16,384 tokens (1,124 s) with no
answer; at temperature 0.6 the same. Direct requests without Istara, at the Qwen model card's
sampling (0.6 / 0.95 / 20) and with thinking off, return only `/` characters. Server props
(read-only): llama.cpp b10975-4c9233c03, Qwen3.8-27B-UD-Q4_K_XL.gguf, proper Qwen chat template.
Captured the exact request body Istara's worker sends (OpenAI Chat Completions streaming,
max_completion_tokens, temperature; no top_p/top_k/chat_template_kwargs). Wrote a self-contained
handoff for the local server's agent (owner's ~/Documents/istara-local-qwen-handoff.md; address
omitted); the owner is sending it and asked this session to wait.
Result: the fault is in the owner's local model server, not Istara (Istara's own defects on this path
are fixed: ecdf7d3e, 3d1a052d). Istara-side follow-up once it is sane: callers that send
temperature 0 to a reasoning model contradict Qwen's card; endpoints cannot pass top_p/top_k.
Verified: curl to /v1/chat/completions (17.0 s, 19.9 s; all `/`); GET /props and /v1/models.
Next: when the owner returns with the local server fixed, re-probe pi-local-qwen once, restart
istara-cs76-live with the two-model env (live-run.sh), then M4 with roles swapped.

### L-18 | 2026-09-25T22:32:26Z | S2-execute | claude-code | executor | Phase 8
Did: resumed after the owner fixed the local server. Sampling/thinking matrix through Istara's
dispatcher on both models (temperature 0, 0.6, 1.0; thinking off, low, high). Renamed the local
endpoint to pi-local-qwen and removed the host name from committed files (801677c3); earlier
commits on this unpushed branch still carry it (owner decision pending before any push). Found
and fixed structured output on Meta (82572cdd) and M4's grading of uploaded files (09ee4045).
Live backend now keeps /app/data on a labelled volume; agents paused (maintenance) during
ingestion; Harbor corpus re-uploading through the upload route.
Result: both models answer "Paris" in all 6 configurations (local Qwen 0.6-1.6 s, Muse Spark
2.0-3.9 s); structured output works on both; ingestion ~25 s per file (local embedder under
Studio load).
Verified: probe_matrix.py and structured_probe.py in istara-cs76-live; worker suite 107/107;
pytest tests/test_spine_answer_eval.py tests/test_spine_retrieval_eval.py -> 12 passed.
Next: when ingestion finishes, M4 twice (generator Muse Spark / judge local Qwen, then swapped).

### L-19 | 2026-09-25T23:48:34Z | S2-execute | claude-code | executor | Phase 8
Did: owner approved rewriting the unpushed history so no commit names the local server (filter-branch
over origin/main..HEAD, hash map kept in the session scratchpad; every hash in this file is the
rewritten one). Found on the live lane: every upload was indexed twice, by the upload route and by the
file watcher reacting to the new file (Harbor corpus: 2,126 vector rows for 1,097 keyword rows). The
upload route now owns the whole ingestion of its files and creates the research tasks the watcher used
to create; the watcher skips managed upload paths (8ee0a83a). Governance for the measurement harness
(feature `research.retrieval-evaluation`), AI-001 evidence for the liveness bounds, and two
self-improvement tests the review asked for (3b3b1686). Feature docs, Tech.md and both contracts
(6ab79206, 2f74297e). M4's first run graded every chunk 0 (uploads are stored as `<uuid>.<ext>`) and
counted Muse Spark's spend as $0 (a chat turn reports tokens, not cost); both fixed (71ca4220).
Scenario 86 now checks that the Vector Chunks and Keyword Chunks cards agree after an upload
(f60f393b).
Result: after the fix and the product's reprocess route, the Harbor project holds 1,097 vector and
1,097 keyword chunks with provenance coverage 1.0. M4 mapping check: 59 of 60 retrieved chunks map to
a corpus file, 33 grade above 0. Full suite on the Studio: 3 failed, 2,480 passed, 14 skipped, 1
error, all from the test container: the public-repo audit fails on `git ls-files` (no checkout
in the container), the invite and update-confirmation tests fail there, and the error is the
container's missing `hypothesis`. All three failing tests pass locally on this branch.
Verified: `pytest tests/test_spine_single_ingestion.py` 2 passed (2 fail on origin/main);
`pytest tests/test_spine_answer_eval.py` 4 passed; `python scripts/security_benchmark.py
--fail-on-threshold` 100% (28/28); check_feature_obligations and check_change_obligations pass;
`python scripts/feature_docs.py --seed-missing --generate-site --check` pass (86 features);
`python3 scripts/public_repo_quality_audit.py` passed; `pytest
tests/test_connections.py::test_invite_redeem_rejects_breached_password
tests/test_updates_security.py::test_local_update_apply_accepts_matching_confirmation` 2 passed; `git log -p origin/main..HEAD | grep -ci
<host>` 0.
Next: read M4 (both directions), then the hostile-document chat and the governed coding run.

### L-20 | 2026-09-26T01:22:08Z | S2-execute | claude-code | executor | Phase 8
Did: M4 both directions on the live lane; the owner approved merging PR #43 (testing catch-up), merged
as a merge commit (611d7a21). Scenario 86 failed on the rebuilt stack (20/23): sticky upload
suggestions covered the tab row at 375 px, a side effect of 8ee0a83a; uploads now skip that
suggestion and are classified by the researcher's file name (c6921068). The hostile-document chat
found two more defects: the agent's folder-sync tool registered every upload again and bypassed the
spine (0f2d8ff4), and document markup escaped the tool-output block (1095ce1e). Harness fixes:
the M4 CLI and the W3 harness stop the Pi worker in their loop (99f0d50c, 63d0e32f). Governed coding
run with the two models (W3 A, B, E). DEC-12.
Result: M4 context precision 0.75 [0.58, 0.92] (n 24); no judge trusted (Qwen relevance kappa 0.568,
claim 1.000; Muse Spark 0.453, 0.926), so faithfulness not measured; spend $0.0069 and $0.0080 against
a $1.00 cap. Hostile chat: prompt block and tool block each balanced, no raw protected tag, canary only
inside wrappers and escaped, no canary in any of 4 answers. Coding run: blocked, no codes, all 5
fail-closed probes pass; its recorded reason is misleading (follow-up task filed). testing now differs
from main only by AGENTS.md (+13, #39).
Verified: QA lane 2026-09-26T01-09-32-847Z 86 23/23, 85 10/10, 24 9/9, 23 13/13;
2026-09-26T01-16-25-274Z 29 33/33 (shared linked folder); `pytest tests/test_spine_single_ingestion.py`
6 passed (6 fail on origin/main); `pytest tests/test_spine_prompt_boundaries.py` 17 passed (the new
test fails on origin/main); `pytest tests/test_spine_answer_eval.py` 6 passed; Studio container: 167
passed (sync, documents, Pi tool-loop suites), 251 passed (tool, boundary, content-guard suites);
`git diff --stat origin/main origin/testing` AGENTS.md only.
Next: governance checks, full suite at HEAD, docs, CF closeout, push and PR into main.

### L-21 | 2026-09-26T01:46:09Z | S2-execute | claude-code | executor | Phase 8
Did: the owner asked this session to fix the coding run's misleading refusal instead of filing it
(L-20 said "follow-up task filed"; that task was withdrawn). Coder selection now names the usable
identities and the required count, and a run in which no coder ran says so (ffe09529); live re-run
shows the corrected reason. Compass Forge's `gate after` then reported six new import cycles from the
agent tool importing the Documents route module; the routes now register their folder sync in
`app/core/project_folder_sync.py` and the tool calls it there, and this round's additions to
already-complex functions moved into helpers (762d55d3). Feature docs (documents library, memory
knowledge, chat overview), Tech.md and the research-validity contract updated; systems map updated and
copied to the owner's Documents folder; CF evidence rows recorded for CF-3, CF-6..CF-13. The long-form
benchmark's blocker for a refused coding run now quotes the backend's reason (148939d4), and TESTING.md
lists the measurement harnesses.
Result: no selection change (an uncredentialed catalog entry is never used to make up the count).
`gate after` 0 new failures; 7 complexity warnings recorded (the moved sync loop under its new name,
`_project_llm_server`, four `session.mjs` methods from the liveness and structured-output work,
`tests/test_autoresearch.py` symbol count).
Verified: full backend suite at 762d55d3 in `istara-test:1`: 3 failed, 2,492 passed, 14 skipped, 1
error (container-only, unchanged from main); QA lane 2026-09-26T01-39-07-546Z 86 23/23, 85 10/10, 24 9/9, 23 13/13 and 2026-09-26T01-40-57-667Z 29 33/33; `pytest tests/pi_production/test_w7_validation.py`
49 passed (2 new fail on origin/main); research-validity suites 168 passed in the Studio container;
security benchmark 100% (125 changed paths, 36 triggered); change and feature obligations pass;
feature docs 86; simulation static 124 files and lib 41/41; real-user benchmark `npm run check` 108/0.
Next: CF closeout and S5.

### L-22 | 2026-09-26T01:46:09Z | S5-ship | claude-code | executor | Phase 12
Did: Compass Forge closeout: evidence rows for CF-9 (full suite) and CF-14, `finish-task` CF-1..CF-14,
`spec accept CF-SPEC-2`, `evaluation record --outcome mixed`. Phase 12 section with the plan summary,
residual risk and retro. Status Block set to done.
Result: CF-SPEC-2 accepted; all 14 tasks done with command evidence (asserted, not run by Compass
Forge). The PR into `main` carries the delivery; its required CI decides the squash merge.
Verified: `compass-forge spec accept CF-SPEC-2` -> status accepted; `verify_lifecycle.py` on this file
(run after this entry).
Next: stage exit: plan done; delivery is the PR into `main`.

### L-23 | 2026-09-26T02:38:48Z | S1-plan | claude-code | planner | Phase 13
Did: owner decisions recorded (DEC-13); the skills library's blind-coverage row committed on its own
branch (`docs/istara-blind-coverage-20260926`, c695716) with the owner's waiver; the DeepSeek key
located by name in the MacBook Keychain (service `istara-pi-deepseek`; no value read yet); pi-ai
0.87.1 serves DeepSeek's Flash as `deepseek-flash` ("DeepSeek V4.1 Flash", $0.30/$1.20 per Mtok);
EmbeddingGemma-300m is the only Gemma embedding model (Google releases page); four candidate
embedders pulled into a labelled Ollama container on the Studio. Pre-registered M4 v2 (DEC-14) and
the embedder selection rule (DEC-15) before any new run. CF-SPEC-4 created, clarified, planned and
tasked (CF-27..CF-44).
Result: plan reopened; branch `fix/spine-open-items-20260926`.
Verified: `compass-forge spec plan CF-SPEC-4` -> planned; `ollama list` in istara-cs76-embed shows the
four models.
Next: gate before; extend the qrels with Spanish questions; implement role-aware embedding prompts.

### L-24 | 2026-09-26T03:03:21Z | S2-execute | claude-code | executor | Phase 13
Did: DeepSeek V4 Flash wired as the third live identity through Pi's own `deepseek` provider
(`pi-deepseek-flash`, key only in a 0600 file on the Studio). Its structured output failed ("Thinking
mode does not support this tool_choice"); DeepSeek and Anthropic thinking runs now get `auto` with the
capture tool, still fail-closed (18f14145, `pi-runtime/src/structured.mjs`).
Result: live probe returned the schema-valid object in 1.2 s.
Verified: `node --test` (pi-runtime) 109/109 then; live `structured_probe.py pi-deepseek-flash`.
Next: prompts and the embedder comparison.

### L-25 | 2026-09-26T03:48:35Z | S2-execute | claude-code | executor | Phase 14
Did: role-aware prompts from each model card, part of the vector-space identity (7cbc6cd3; alembic
033); qrels v2 with 42 Spanish questions (8548b856); the DEC-15 rule as code (1a25f1e6); the admin
switch with a full re-index (0dd67a3d; Settings > Embedding model, scenario 87 b6f2fc41); M4 v2
judge validation (2b7b96cb); the seven gate-after complexity warnings cleared (aebfc271); five-arm
comparison on the Studio.
Result: DEC-16 (BGE-M3). Arms: see DEC-16; reports in the evidence file.
Verified: `python -m app.evals.embedder_compare --baseline nomic-raw --prefer embeddinggemma ...`
(istara-test:1) -> winner bge-m3, qualifying [bge-m3, qwen3-0.6b, embeddinggemma, nomic-prompted];
`compass-forge gate after` -> 0 new warnings (416 -> 405).
Next: default change and the live migration.

### L-26 | 2026-09-26T04:11:25Z | S2-execute | claude-code | executor | Phase 14
Did: BGE-M3 default (24e5a1b9); the local model load wait (b11ba0d7: the owner's local server
answered 503 "Loading model" and the worker failed in 0.3 s); the fresh-database head test at 033
(ff2e4030). The live migration of the Harbor project found two defects no stub could: the probe asked
the gateway for a non-active model, and the local Ollama plane accepted only OLLAMA_EMBED_MODEL, so no
switch could run and every existing install would have failed closed on upgrade to the new default
(53f4722d).
Result: live switch nomic -> BGE-M3 through `POST /api/settings/embedding-profile`: 1,099 rows in
211 s, profile v2, 1024 dims, provenance 1.0; the product's search then found the answer span in the
top 10 for 114 of 118 questions (Spanish 44 of 46).
Verified: full backend suite (istara-test:1, network none) 2,515 passed, 4 failed + 1 error, all
environmental and failing on main too except the alembic head test, fixed in ff2e4030; worker
115/115; `migrate_live.py bge-m3`; `live_hits.py` over qrels v2.
Next: governance, then QA scenarios.

### L-27 | 2026-09-26T04:23:13Z | S2-execute | claude-code | executor | Phase 16
Did: security package revalidated (AI-001, AUTHZ-002) and personas updated (7f4a7d6a); a coding run
cut off by a restart settles as blocked at startup (3ecb32d8; the live lane had one stuck "running"
since 03:06Z); scenario 87's failed switch traced to the probe pulling first on a provider without a
pull route, and its refusal showing the provider URL: the probe embeds first and reasons carry the
status, never an address (41becb0c); Settings clipped at 375 px (c3189e5d).
Result: CF-SPEC-3 accepted (its blind review waived by DEC-13; CF-20, CF-25, CF-26 closed with the
M3 re-run and `test_spine_rag_budget_passthrough.py` 11 passed); CF-SPEC-1 withdrawn as superseded by
PR #42.
Verified: `python3 scripts/security_benchmark.py --fail-on-threshold --changed-paths-file ...` ->
pass; `check_change_obligations.py` -> passed; `check_feature_obligations.py` -> passed;
`public_repo_quality_audit.py` -> passed; QA run 2026-09-26T04-15-47-927Z: 23 13/13, 24 9/9,
29 33/33, 85 10/10, 86 23/23, 87 16/22 (the two defects above).
Next: phone layout (DEC-17), QA re-run, M4 v2, governed coding run.


### L-28 | 2026-09-26T05:47:00Z | S2-execute | claude-code | executor | Phase 16
Did: DEC-17 phone layout (7de5c3bb, 00b10cc0): the content column of Settings, Quality, Skills,
Backup, Ensemble health and Meta-Hyperagent sized to its widest card; Chat's list is a drawer below
md; Interviews' list and interview take turns, tags open over it, the banner sits above the columns,
and the coding gutter stacks under the text; Documents and Notifications headers wrap. The shared
375 px check fails on anything cut off inside `main`; scenario 88 drives every shell view at
375 px. Scenario 85 scans both themes through the app toggle, which found Memory's grey text below
AA in dark mode (fixed). The gate budgets were restored (6290bd50): gate after 0 new failures,
0 new warnings (403 inherited, from 416). Live agents were paused after the backend restart (they had
run skills on the live models alongside M4); `live-run.sh` now pauses them on every start.
Result: QA ui lane 22 scenarios 318/320 on the first pass (run 2026-09-26T04-51-06-707Z), both
failures fixed and re-run green (85 11/11, 88 11/11, 29 33/33, 23, 86, 75, 19 green); full backend
suite 2,525 passed (3 failures + 1 error container-only, same on main).
Verified: `istara-qa-run-cs76.sh sim <22 scenarios>`; `fullrun.sh istara-work open-items-2`;
`compass-forge gate after --task CF-29 --summary`; CF-27..CF-31, CF-33, CF-35..CF-42 finished with
command evidence.
Next: M4 v2 directions 2 and 3, then the governed coding run with three identities.
