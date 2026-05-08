# Istara AI Evaluation Strategy

This strategy is the durable Compass Forge record for `CF-SPEC-26`. It defines
how Istara evaluates its local-first AI stack over time: model serving,
retrieval, prompt construction, compression, memory, tool use, agent
orchestration, skill evolution, voice transcription, and governed
self-improvement.

The goal is not a one-time score. The goal is a repeatable evaluation flywheel:
every run records the repository state, Compass spec/task, model id, registry
version, runtime environment, raw case outputs, and summary metrics so changes
can be compared later.

## Research Baseline

Istara's eval design should combine public benchmark patterns with
architecture-specific probes.

- OpenAI Evals: private use-case evals and reusable registries for model and
  LLM-system changes. Reference: https://github.com/openai/evals
- OpenAI trace grading: workflow-level trace scoring for agent decisions, tool
  calls, and final outputs. Reference: https://platform.openai.com/docs/guides/trace-grading
- Inspect AI: task, dataset, solver, scorer, logs, tool use, agents, ReAct,
  multi-agent, sandboxing, and eval-set composition. Reference:
  https://inspect.aisi.org.uk/
- HELM: holistic, transparent evaluation across scenarios and metrics, with
  raw prompts and completions preserved for reproducibility. Reference:
  https://crfm.stanford.edu/helm/
- lm-evaluation-harness: reproducible classic LLM benchmark execution.
  Reference: https://github.com/EleutherAI/lm-evaluation-harness
- Ragas: RAG metrics such as context precision, context recall, faithfulness,
  response relevancy, and agent/tool metrics. Reference:
  https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
- TruLens RAG Triad: context relevance, groundedness, and answer relevance.
  Reference: https://www.trulens.org/getting_started/core_concepts/rag_triad/
- Berkeley Function Calling Leaderboard: function and tool-call correctness.
  Reference: https://sky.cs.berkeley.edu/project/berkeley-function-calling-leaderboard/
- tau-bench: interactive user-agent-tool tasks in real-world domains. Reference:
  https://arxiv.org/abs/2406.12045
- AgentBench: multi-environment agent reasoning and decision-making. Reference:
  https://arxiv.org/abs/2308.03688
- GAIA: general assistant tasks requiring reasoning, file handling, browsing,
  multimodality, and tool use. Reference: https://arxiv.org/abs/2311.12983
- WebArena: realistic web-agent task completion in controlled sites. Reference:
  https://webarena.dev/
- SWE-bench: repository issue resolution through patches and tests. Reference:
  https://www.swebench.com/
- LLMLingua and LongLLMLingua: prompt compression with semantic preservation
  and downstream task retention. References: https://arxiv.org/abs/2310.05736
  and https://www.microsoft.com/en-us/research/project/llmlingua/longllmlingua/
- RULER: synthetic long-context retrieval, multi-hop tracing, and aggregation.
  Reference: https://arxiv.org/abs/2404.06654
- LoCoMo and newer memory benchmarks: long-term conversational memory, temporal
  consistency, and memory-grounded answering. Reference:
  https://arxiv.org/abs/2402.17753
- Memento Skills: persistent skill memory and reflective learning evaluated on
  GAIA and high-difficulty reasoning. Reference:
  https://github.com/Memento-Teams/Memento-Skills

## Istara Evaluation Layers

1. Model serving and local compute
   - One configured OpenAI-compatible live profile.
   - Fixed model id: `google/gemma-4-e4b`.
   - No committed endpoint or token.
   - Live eval calls route through `compute_registry.chat`, not direct HTTP, so
     retries, model-readiness recovery, thinking controls, and output
     sanitization match normal Istara serving.
   - Metrics: readiness, HTTP success, latency, model id match, visible-output
     normalization, no secondary model probing.

2. Classic LLM behavior
   - JSON conformance, instruction following, schema adherence, refusal or
     uncertainty where appropriate, and deterministic short-answer tasks.
   - Metrics: exact-match, JSON validity, required key coverage, latency.

3. RAG and document retrieval
   - Synthetic gold documents with distractors, BM25 fallback, vector/hybrid
     readiness, context precision at k, recall at k, citation/source coverage,
     grounded answer checks.
   - Inspired by Ragas and TruLens, but scoped to Istara's `rag.py` and
     `keyword_index.py` behavior.

4. Prompt RAG
   - Query-aware persona section selection, identity-anchor survival, irrelevant
     section suppression, and token-budget fit.
   - Metrics: anchor survival, relevant section recall, distractor exclusion,
     composed-token estimate.

5. LLMLingua-style compression and context management
   - Protected tag survival, compression ratio, critical term retention,
     final-answer quality after compression, and long-context needle/multi-hop
     probes inspired by LLMLingua, LongLLMLingua, and RULER.
   - Metrics: compression ratio, protected-context survival, critical-term
     recall, answer retention delta.

6. DAG ReAct and tool calling
   - Decomposition into acyclic plans, dependency correctness, tool selection,
     argument schema validity, multi-turn recovery, retry behavior, and final
     response quality.
   - Uses BFCL-style tool correctness, OpenAI/LangSmith-style trajectory
     grading, and Istara's orchestration benchmarks.

7. Memory systems and ReasoningBank
   - Trace distillation, redaction, source/outcome tagging, retrieval precision,
     temporal consistency, failure-memory reuse, and project/agent scoping.
   - Metrics: memory distillation traceability, retrieval precision at k,
     secret redaction, project isolation, success/failure reuse.

8. Memento Skills and skill evolution
   - Skill definition schema, enabled/toggle coverage, proposal quality,
     approval visibility, skill execution success, usage stats, and rollback.
   - Metrics: schema validity, skill coverage, approval lineage,
     execution-quality score, rollback availability.

9. Meta Hyperagent and governed improvement
   - Observation quality, proposal generation, parameter bounds, risk class,
     sandbox evidence, approval state, variant limit, rollback/confirm path.
   - Metrics: observation completeness, proposal precision, bounds enforcement,
     max-active-variant enforcement, governance registration.

10. Voice and transcription
    - Dependency status, missing/decode failure typing, local Whisper readiness,
      ICR confidence, spoken-style tagging, and review flag behavior.
    - Metrics: dependency readiness, typed failure coverage, tag precision,
      ICR confidence classification.

11. Product acceptance and resource behavior
    - Simulation scenarios for settings, compute pool, memory, context DAG,
      prompt compression, Meta Hyperagent, model sessions, voice, and UI tours.
    - Metrics: scenario pass rate, menu coverage, accessibility, latency,
      pooled-compute state, RAM/VRAM reporting, and user-visible recovery.

## Result Storage

Tracked files:

- `testing/AI_EVALS_STRATEGY.md`: this strategy.
- `testing/TEST_HISTORY.md`: curated release-baseline summaries.
- `tests/evals/registry.json`: machine-readable suites, metrics, thresholds,
  references, and commands.
- `tests/evals/cases/core_eval_cases.json`: small core live/static cases.
- `scripts/run_istara_evals.py`: runner.

Ignored run artifacts:

- `tests/evals/.results/<timestamp>-<git-sha>/manifest.json`
- `tests/evals/.results/<timestamp>-<git-sha>/summary.json`
- `tests/evals/.results/<timestamp>-<git-sha>/results.jsonl`
- `tests/evals/.results/<timestamp>-<git-sha>/report.md`

The runner rejects custom output directories outside `tests/evals/.results/`
unless `--allow-unignored-output` is explicit, because static evals may create
temporary RAG/persona/runtime data under the selected output directory.

The manifest must include:

- UTC timestamp.
- Git branch, HEAD, dirty flag, changed path count, and status hash.
- Compass spec and task ids when supplied.
- Registry hash and case-file hash.
- Python/platform metadata.
- Model id and boolean endpoint/key configuration flags.
- A private endpoint fingerprint may be stored, but never the endpoint or token.
- Exact command arguments and suite selection.

When an eval run becomes a release baseline, summarize it in
`testing/TEST_HISTORY.md` with the artifact path and residual risks instead of
copying raw result markdown into tracked docs.

## Operating Commands

Core static and live Istara evals:

```bash
python scripts/run_istara_evals.py --suite all --require-live-llm
```

Strict gating mode:

```bash
python scripts/run_istara_evals.py --suite all --require-live-llm --fail-on-threshold
```

Static-only smoke for CI or development:

```bash
python scripts/run_istara_evals.py --suite static
```

Existing orchestration benchmark export:

```bash
python tests/benchmarks/run_benchmarks.py --json tests/evals/.results/orchestration-benchmark.json
```

Live orchestration integration:

```bash
ISTARA_RUN_REAL_LLM_BENCHMARK=1 pytest tests/integration/test_llm_orchestration_real.py -q
```

## Compass Forge Rules

When a future request asks to rerun, extend, compare, or analyze AI evals:

1. Run `compass-forge status` and `compass-forge agent-brief`.
2. Use this file plus `tests/evals/registry.json` as the durable eval map.
3. If suites or thresholds change, update the registry and add tests.
4. Save raw results under `tests/evals/.results/`.
5. Attach command/gate evidence to the active Compass task before closing it.
6. Never commit live endpoint addresses, API tokens, model weights, raw audio, or
   local result payloads.

## Next Evaluation Additions

- Add an Inspect-compatible adapter once `inspect-ai` is accepted as a
  dependency or optional extra.
- Add Ragas-compatible scorers when a judge model policy is agreed for
  faithfulness and answer relevance.
- Add a trace-diff format for production agent sessions: final answer, steps,
  tool calls, parameters, retries, retrieved documents, memories, and
  governance actions.
- Add a small GAIA-style private dataset for Istara research workflows:
  multi-step questions requiring files, retrieval, synthesis, tools, and
  citations.
- Add a WebArena-inspired local UI benchmark for admin/researcher onboarding
  flows and permission request paths.
- Add long-context RULER-style cases for prompt RAG plus DAG context summaries.
- Add memory arena cases where earlier feedback must change later action, not
  merely be recalled.
