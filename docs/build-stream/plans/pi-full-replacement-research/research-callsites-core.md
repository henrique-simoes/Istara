All data gathered. Compiling the inventory.

## Key aliasing facts (read first)

```
backend/app/core/ollama.py:383      ollama = compute_registry        # every ollama.chat/embed call IS ComputeRegistry
backend/app/core/llm_router.py:73   llm_router = compute_registry    # every llm_router.chat/embed_batch call IS ComputeRegistry
```
All product-level `ollama.*` / `llm_router.*` calls terminate in `ComputeRegistryInvocationMixin.chat/chat_stream/embed/embed_batch` (compute_registry_invocation.py). `embed_text`/`embed_chunks` (embeddings.py:42/55) are the cache-fronted wrappers over `ollama.embed`/`ollama.embed_batch`; their call sites are listed because they are the real product entry points for embeddings.

## Table 1 — Product-logic chat sites

| file:line | enclosing function | kind | loop/single | params passed | output handling | purpose |
|---|---|---|---|---|---|---|
| agent_execution.py:472 | AgentExecutionMixin._execute_task | chat (ollama alias) | single (gated: skill health < 0.5 after 3+ runs) | temperature=0.3 | raw text `message.content` | LLM reflection on why a skill underperforms, feeds skill improvement proposal |
| agent_lifecycle.py:519 | AgentLifecycleMixin._execute_steering_message | chat (ollama alias) | single | (messages only) | raw text, broadcast via WS status | General LLM reply to user steering message when no skill matches |
| agent_lifecycle.py:857 | AgentLifecycleMixin._handle_collaboration | chat (ollama alias) | single | (messages only; thread history + RAG context in messages) | raw text → A2A message + task notes | Agent-to-agent collaboration response |
| agent_lifecycle.py:942 | AgentLifecycleMixin._initiate_debate | chat (ollama alias) | single (inside 10x3s poll loop, fires once on response) | (messages only) | raw text returned | Synthesize own output + peer critique into refined analysis |
| agent_lifecycle.py:996 | AgentLifecycleMixin._handle_debate | chat (ollama alias) | single | (messages only) | raw text → A2A debate_response | Critique another agent's output on debate request |
| agent_research.py:129 | AgentResearchMixin._execute_general_task | chat (ollama alias) | loop (ReAct, up to 6 iterations) | tools=available_tools | raw text + `message.tool_calls` dispatch | Tool-augmented ReAct loop for general tasks |
| agent_research.py:131 | AgentResearchMixin._execute_general_task | chat (ollama alias) | loop (final iteration / no-tools branch) | (messages only) | raw text | Final answer pass of ReAct loop |
| agent_research.py:478 | AgentResearchMixin._create_research_plan | chat (ollama alias) | single | temperature=0.3, response_format=openai_json_schema(strict), max_tokens=900, min_context=computed, thinking_mode="off" | structured schema → `parse_json_object` → ResearchStep list | Decompose task into 2–5 step research plan |
| agent_research.py:667 | AgentResearchMixin._execute_single_step | chat (ollama alias) | per plan step (outer loop over steps) | (messages only; system=context_hierarchy) | raw text → step.result | Execute a skill-less research step by pure reasoning |
| agent_research.py:1062 | AgentResearchMixin._self_verify_output | chat (ollama alias) | single | temperature=0.1 | JSON parsed via regex `{"verified"...}` | LLM self-reflection quality gate on skill output |
| context_dag.py:611 | ContextDAG._summarize_batch | chat (ollama alias) | single (per batch) | temperature=0.2, max_tokens=settings.dag_summary_max_tokens | raw text; mechanical fallback | Summarize conversation segment for DAG context compression |
| context_summarizer.py:72 | ContextSummarizer.summarize_messages | chat (ollama alias) | single (per batch) | temperature=0.3, max_tokens=max_summary_tokens (default 200) | raw text; heuristic fallback | Summarize old messages under context-window pressure |
| self_check.py:75 | verify_claim | chat (ollama alias) | single per claim (check_findings loops claims) | temperature=0.1 | line-structured parse (CONFIDENCE:/SUPPORTING:/...) | Fact-check a claim against RAG sources |
| autoresearch_runners/model_temp.py:158 | ModelTempRunner._evaluate_skill | chat (llm_router) | per experiment trial | model=model, temperature=temperature (swept vars) | raw text | Run skill prompt under candidate model/temperature |
| autoresearch_runners/model_temp.py:203 | ModelTempRunner._score_output | chat (llm_router) | single per output | temperature=0.1, max_tokens=10 | float parsed from text | LLM-as-judge 0–1 score of skill output |
| autoresearch_runners/persona.py:108 | PersonaRunner.hypothesize | chat (llm_router) | single per mutation | temperature=0.7, max_tokens=2000 | raw text (code-fence stripped) → new persona file | LLM-generated persona file mutation |
| autoresearch_runners/persona.py:204 | PersonaRunner._evaluate_agent | chat (llm_router) | single per eval | temperature=0.5, max_tokens=1500 | raw text | Simulated UX task run with agent identity as system prompt |
| autoresearch_runners/persona.py:236 | PersonaRunner._score_response | chat (llm_router) | single | temperature=0.1, max_tokens=10 | float parsed from text | Score simulated agent response 0–1 |
| autoresearch_runners/question_bank.py:93 | QuestionBankRunner.hypothesize | chat (llm_router) | single per mutation | temperature=0.7, max_tokens=1500, project_id | JSON substring parse (`{...}`) | Suggest question-bank improvement (reword/reorder/adaptive) |
| autoresearch_runners/question_bank.py:232 | QuestionBankRunner._evaluate_questions | chat (llm_router) | single per deployment eval | temperature=0.8, max_tokens=1500, project_id | raw text | Simulate participant answering question bank |
| autoresearch_runners/question_bank.py:280 | QuestionBankRunner._score_responses | chat (llm_router) | single | temperature=0.1, max_tokens=10, project_id | float parsed from text | Score elicited responses 0–1 |
| autoresearch_runners/rag_params.py:169 | RAGParamsRunner._llm_hypothesis | chat (llm_router) | single per mutation | temperature=0.7, max_tokens=200, project_id | JSON substring parse; random-perturbation fallback | Suggest next RAG parameter change |
| autoresearch_runners/skill_prompt.py:156 | SkillPromptRunner.hypothesize | chat (llm_router) | single per mutation | temperature=0.7, max_tokens=2000 | raw text (fence-stripped) → new execute_prompt | Mutate skill prompt via named operator |
| autoresearch_runners/skill_prompt.py:252 | SkillPromptRunner._single_eval | chat (llm_router) | per eval run (outer eval loop) | temperature=0.5, max_tokens=1500 | raw text | Execute skill prompt on sample context |
| autoresearch_runners/skill_prompt.py:287 | SkillPromptRunner._score_output | chat (llm_router) | single | temperature=0.1, max_tokens=10 | float parsed from text | Score skill output 0–1 |
| autoresearch_runners/ui_sim.py:103 | UISimRunner.hypothesize | chat (llm_router) | single per mutation | temperature=0.5, max_tokens=3000 | raw text (fence-stripped) → new component code | LLM a11y/UX mutation of UI component file |
| autoresearch_runners/ui_sim.py:199 | UISimRunner._evaluate_component | chat (llm_router) | single per component | temperature=0.1, max_tokens=10 | float parsed from text | WCAG-style 0–1 component score |
| report_manager.py:498 | ReportManager._generate_executive_summary | chat (llm_router) | single | temperature=0.3, project_id | raw text → report.executive_summary | SCR-framework executive summary from findings |
| report_manager.py:555 | ReportManager._generate_mece_categories | chat (llm_router) | single | temperature=0.3, project_id | JSON array regex parse | MECE categorization of findings |
| report_manager.py:754 | ReportManager._compose_full_report | chat (llm_router) | loop (refinement, max 2 passes) | temperature=0.2, project_id | JSON regex parse (`{"weakest"...}`) | Score report sections, pick weakest for re-composition |
| report_manager.py:883 | ReportManager._compose_section | chat (llm_router) | per section (outer loop over REPORT_TEMPLATE) | temperature=0.3, project_id | raw text; evidence-table fallback | Expand insights into narrative section |
| report_manager.py:937 | ReportManager._compose_section | chat (llm_router) | per section | temperature=0.3, project_id | raw text; table fallback | Expand recommendations with justifications |
| report_manager.py:996 | ReportManager._compose_section | chat (llm_router) | per section | temperature=0.3, project_id | raw text | Identify gaps/limitations section |
| validation.py:152 | dual_run | chat (server = per-node direct) | loop over `servers[:2]` | model, temperature=0.7, project_id | raw text list → embeddings → consensus | Same prompt on 2 distinct servers for consensus |
| validation.py:213 | adversarial_review | chat (llm_router) | single | model, temperature=0.3, project_id | raw text → consensus vs original | Second model critiques first response |
| validation.py:314 | full_ensemble | chat (server = per-node direct) | loop over `servers[:min_responses+1]` | model, temperature=0.7, project_id | raw text list → consensus | 3+ server ensemble consensus |
| validation.py:373 | self_moa | chat (llm_router) | loop over temperatures [0.3,0.7,1.0,...] | model, temperature=temp, project_id | raw text list → consensus | Self-MoA temperature-variation ensemble |
| validation.py:431 | debate_rounds | chat (llm_router) | single (initial) | model, temperature=0.7, project_id | raw text | Initial debate response |
| validation.py:470 | debate_rounds | chat (llm_router) | loop over rounds (default 2) | model, temperature=0.5, project_id | raw text appended per round | Multi-round debate refinement |
| validation_executor.py:64 | ValidationExecutor._adversarial_review | chat (compute_registry direct) | single | temperature=0.3, project_id | JSON regex parse — NOTE reads `result.get("content")` not `result["message"]["content"]` (registry returns the latter; likely latent bug) | LLM-as-judge scores coding-output quality dims |

## Table 2 — Product-logic embedding sites

| file:line | enclosing function | kind | loop/single | params passed | output handling | purpose |
|---|---|---|---|---|---|---|
| embeddings.py:50 | embed_text | embed (ollama alias → registry.embed) | single (cache-fronted) | text only (model resolved by registry) | vector list; cached | Canonical single-text embed wrapper |
| embeddings.py:90 | embed_chunks | embed_batch (ollama alias) | loop over batches of 32 | texts only | vector lists; per-chunk cached | Canonical batch embed wrapper |
| validation.py:522 | _get_embeddings | embed_batch (llm_router) | single batch | texts, project_id | vectors → cosine consensus; `[]` on error | Embeddings for response-agreement scoring |
| agent_execution.py:824 | _semantic_skill_match | embed (via embed_text) | single per task | text[:1200] | vector | Task-text vector for skill routing |
| agent_execution.py:832 | _semantic_skill_match | embed (via embed_text) | loop over all_skills (in-memory cached) | desc[:512] | vector | Skill-description vectors for cosine match |
| agent_memory.py:64 | AgentMemoryManager.read_notes | embed (via embed_text) | single | query | vector → VectorStore.search | Semantic search of agent private notes |
| agent_memory.py:74 | AgentMemoryManager.read_notes | embed (via embed_text) | single | synthetic query string | vector → VectorStore.search | Recent-notes retrieval fallback |
| agent_skill_tools.py:338 | rank_skill_candidates | embed (via embed_text) | single | query[:1200] | vector | Query vector for skill candidate ranking |
| agent_skill_tools.py:341 | rank_skill_candidates | embed (via embed_text) | loop over all_skills (uncached) | desc[:512] | vector → cosine boost | Skill-description vectors per ranking call |
| autoresearch_runners/rag_params.py:234 | RAGParamsRunner._score_single_query | embed (via embed_text) | loop over TEST_QUERIES (outer) | query | vector → hybrid_search | Retrieval-quality eval for RAG param tuning |
| prompt_rag.py:316 | _embedding_similarity | embed (via embed_text) | single (when query_vector not precomputed) | query | vector | Query vector for persona-section relevance |
| prompt_rag.py:319 | _embedding_similarity | embed (via embed_text) | per section (called in loop from compose_dynamic_prompt:504) | header+content[:500] | vector → cosine; keyword fallback | Section vector for prompt-RAG selection |
| prompt_rag.py:494 | compose_dynamic_prompt | embed (via embed_text) | single | query | vector reused across sections | Precompute query vector for dynamic prompt assembly |
| rag.py:604 | ingest_chunks | embed_batch (via embed_chunks) | single call (internal 32-batching) | chunks | EmbeddedChunk list → VectorStore.add_chunks; non-fatal on failure | Document ingestion embedding |
| rag.py:639 | retrieve_context | embed (via embed_text) | single | query | vector → hybrid_search; keyword fallback on error | Main RAG retrieval query embedding |
| file_watcher.py:398 | FileWatcher._process_file | embed_batch (via embed_chunks) | single per file | result.chunks | EmbeddedChunk list → VectorStore | Auto-index watched files |
| vector_health.py:19 | check_embedding_dimensions | embed (via embed_text) | single | fixed probe string | `len(vector)` only | Detect stored-vs-model dimension mismatch |

## Table 3 — Infrastructure/transport sites (inside registry, node, provider clients)

| file:line | enclosing function | kind | loop/single | params passed | output handling | purpose |
|---|---|---|---|---|---|---|
| compute_registry_invocation.py:289 | ComputeRegistryInvocationMixin.chat | chat → node.chat (relay/browser WS) | inside node-failover loop + retry loop (TRANSIENT_CHAT_MAX_ATTEMPTS) | model=resolved, temperature, max_tokens, tools, response_format, thinking_mode=None, project_id | dict passthrough + route evidence | Dispatch chat to donated-compute node over websocket |
| compute_registry_invocation.py:332 | (same fn, ollama branch) | chat, raw POST /api/chat | same loops | model, messages, stream=False, options{temperature,num_predict}, response_format fields | JSON, thinking-filtered message | Direct Ollama-node chat |
| compute_registry_invocation.py:353 | (same fn, anthropic branch) | chat → node.chat | same loops | model, temperature, max_tokens, tools, response_format, thinking_mode=None, project_id | dict passthrough | Anthropic-compatible node chat |
| compute_registry_invocation.py:394 | (same fn, openai branch) | chat, raw POST chat/completions | same loops | model, messages, temperature, stream=False, max_tokens, tools, response_format fields | JSON → normalized `{message:{content,tool_calls}}` | OpenAI-compatible node chat |
| compute_registry_invocation.py:629 | ComputeRegistryInvocationMixin.chat_stream | chat_stream → node.chat (relay fallback) | node-failover + retry loops | model, temperature, max_tokens, tools, thinking_mode=None, project_id (NO response_format) | whole content yielded as one chunk (pseudo-SSE) | Streaming emulation for websocket donors |
| compute_registry_invocation.py:662 | (same fn, ollama branch) | chat_stream, raw streamed POST /api/chat | same loops | model, messages, stream=True, options{temperature,num_predict} | SSE line-JSON → filtered chunks yielded | True token streaming from Ollama node |
| compute_registry_invocation.py:683 | (same fn, anthropic branch) | chat_stream → node.chat | same loops | model, temperature, max_tokens, tools, thinking_mode=None, project_id | content + tool_calls dict yielded | Stream fallback for Anthropic nodes |
| compute_registry_invocation.py:720 | (same fn, openai branch) | chat_stream, raw streamed POST | same loops | model, messages, temperature, stream=True, max_tokens, tools | SSE deltas → chunks + accumulated tool_calls | True streaming for OpenAI-compatible nodes |
| compute_registry_invocation.py:941 | ComputeRegistryInvocationMixin.embed | embed → node.embed (relay WS) | node-failover loop | text, model, project_id | vector list | Embedding via donated node |
| compute_registry_invocation.py:949/954 | (same fn, http branches) | embed, raw POST /api/embed or embeddings | same loop | model=resolved embed model, input | JSON → first vector | Direct node embedding |
| compute_registry_invocation.py:1004 | ComputeRegistryInvocationMixin.embed_batch | embed_batch → node.embed_batch (relay WS) | node-failover loop | texts, model, project_id | list of vectors | Batch embedding via donated node |
| compute_registry_invocation.py:1014/1022 | (same fn, http branches) | embed_batch, raw POST | same loop | model, input=texts | JSON → vectors | Direct node batch embedding |
| compute_registry_lifecycle.py:568 | ComputeRegistryLifecycleMixin.ensure_chat_ready | chat → node.chat (probe) | loop over candidate nodes | "Reply ok." message, model=resolved, temperature=0, max_tokens=1 | discarded (success/failure only) | LM Studio chat-readiness health probe |
| compute_registry_lifecycle.py:586 | ComputeRegistryLifecycleMixin.ensure_chat_ready | chat → node.chat (probe retry) | single, after model-load recovery | same, model=recovered | discarded | Re-probe after auto model load |
| compute_node_invocation.py:37 | ComputeNodeInvocationMixin.chat | chat transport def (WS `llm_request`:58 / ollama:93 / anthropic:115 / openai:137) | single | messages, model, temperature, max_tokens, tools, response_format, thinking_mode, project_id | normalized `{message:{content,tool_calls}}` + route evidence | Per-node wire-level chat; WS path is donated-compute; project auth gate at :20–35 |
| compute_node_invocation.py:179 | ComputeNodeInvocationMixin.chat_stream | chat_stream → self.chat (relay fallback) | single | model, temperature, max_tokens, tools, thinking_mode=None, project_id | content yielded as one chunk | Non-streaming fallback for relay/browser donors |
| compute_node_invocation.py:196 | ComputeNodeInvocationMixin.chat_stream | chat_stream → self.chat (anthropic fallback) | single | same | content + tool_calls yielded | Non-streaming fallback for Anthropic nodes |
| compute_node_invocation.py:159 | ComputeNodeInvocationMixin.chat_stream | chat_stream transport def (ollama stream:225, openai stream after) | single | messages, model, temperature, max_tokens, tools, min_context, thinking_mode, project_id | SSE chunks yielded | Per-node wire-level streaming |
| compute_node_invocation.py:315 | ComputeNodeInvocationMixin.embed | embed transport def (WS `embed_request`:324 / http:341/346) | single | text, model, project_id | vector | Per-node wire-level embedding |
| compute_node_invocation.py:354 | ComputeNodeInvocationMixin.embed_batch | embed_batch transport def (WS:363 / http:380/384) | single | texts, model, project_id | vectors | Per-node wire-level batch embedding |
| model_capabilities.py:590 | detect_capabilities_generic | chat, raw POST (api/chat or chat/completions) | single per host | model=first detected, dummy tool, max_tokens=5 | status code only → `supports_tools` flag | Active tool-support capability probe |
| ollama.py:88/122 | OllamaClient.chat | chat, raw POST /api/chat | single | messages, model(default settings.ollama_model), system, temperature, max_tokens, tools, response_format, thinking_mode | JSON, thinking-filtered | Legacy direct client — module singleton `ollama` is NOT this class (ollama.py:383); `_raw_client` (ollama.py:374) is created but never invoked in core |
| ollama.py:130/165 | OllamaClient.chat_stream | chat_stream, raw streamed POST | single | same as above | SSE chunks | Legacy direct streaming |
| ollama.py:179/183 | OllamaClient.embed | embed, raw POST /api/embed | single | text, model(default ollama_embed_model) | vector | Legacy direct embed |
| ollama.py:196/200 | OllamaClient.embed_batch | embed_batch, raw POST /api/embed | single | texts, model | vectors | Legacy direct batch embed |
| lmstudio.py:69/97 | LMStudioClient.detect_loaded_model | chat, raw POST /v1/chat/completions (probe) | single, 60s cached | "hi", max_tokens=1, stream=False, model if configured | reads `model` field only | Detect which model LM Studio actually loaded |
| lmstudio.py:161/196 | LMStudioClient.chat | chat, raw POST /v1/chat/completions | single | messages, model(default lmstudio_model), system, temperature, max_tokens, tools, response_format | JSON → Ollama-shaped dict | LM Studio direct chat |
| lmstudio.py:217/261 | LMStudioClient.chat_stream | chat_stream, raw streamed POST | single | same | SSE deltas | LM Studio direct streaming |
| lmstudio.py:323/327 | LMStudioClient.embed | embed, raw POST /v1/embeddings | single | text, model | vector | LM Studio direct embed |
| lmstudio.py:340/344 | LMStudioClient.embed_batch | embed_batch, raw POST /v1/embeddings | single | texts, model | vectors | LM Studio direct batch embed |

Non-LLM model invocation (discovered, note only): `transcription.py:187` (`transcribe_audio`) and `transcription.py:264` (`_compute_transcription_icr`) call local Whisper `model.transcribe(...)` — speech-to-text, not routed through the registry.

## Table 4 — Donated-compute/infra-only vs product logic

| Category | Sites |
|---|---|
| Donated-compute / relay-transport ONLY | compute_node_invocation.py:37 (WS `llm_request` branch :58), :179, :315 (WS :324), :354 (WS :363); compute_registry_invocation.py:289, :629, :941, :1004 (all `node.source in ("relay","browser") and node.websocket` branches); project-auth gate `_authorized_project_for_content_dispatch` compute_node_invocation.py:20–35 |
| Health-probe / capability-probe infrastructure | compute_registry_lifecycle.py:568, :586 (chat readiness probe); model_capabilities.py:590 (tool-support probe); lmstudio.py:97 (loaded-model detect probe); vector_health.py:19 (embed dimension probe — infra-purpose but goes through product embed path) |
| Provider transport (local/direct, not donor-specific) | compute_registry_invocation.py:332/353/394/662/683/720/949/954/1014/1022; compute_node_invocation.py http branches; ollama.py:122/165/183/200; lmstudio.py:196/261/327/344 |
| Product logic | Everything in Tables 1 and 2 (validation.py:152/314 call `server.chat` per-node directly, bypassing registry routing, but for a product purpose: ensemble diversity) |

No Petals-specific call sites exist in `backend/app/core/` outside `pi_runtime/` — donated compute is the relay/browser websocket path above.

## Counts

- Product chat call sites (Table 1): **39**
- Product embedding call sites (Table 2): **17** (3 direct alias/router calls + 14 wrapper call sites)
- Infrastructure/transport/probe sites (Table 3): **30** rows (6 registry-internal `node.chat/embed` dispatches, 8 registry raw-HTTP branches, 2 lifecycle probes, 2 node self.chat fallbacks, 4 node transport defs, 4 OllamaClient defs, 5 LMStudioClient defs incl. probe, 1 capability probe)
- Whisper (non-LLM, local): 2
- **Total model-invocation sites inventoried: 88** (39 + 17 + 30 + 2)
- `chat_stream` has ZERO product callers inside `backend/app/core/` — all four `chat_stream` definitions (ollama.py:130, lmstudio.py:217, compute_node_invocation.py:159, compute_registry_invocation.py:546) are consumed from outside core.
- Files importing router/registry but NOT invoking models: adaptive_validation.py:51, network_discovery.py:211–251, compute_pool.py:28, agent_lifecycle.py:249–251 (server listing / registration / status only).