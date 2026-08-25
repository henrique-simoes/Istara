# LLM/Embedding Call-Site Inventory — <repo-root>-pi-replacement (branch Review_pi_test)

## Key routing fact (load-bearing)

```
backend/app/core/ollama.py:383      ollama = compute_registry
backend/app/core/llm_router.py:73   llm_router = compute_registry
```
Every `ollama.chat`, `ollama.chat_stream`, and `llm_router.chat` site below resolves to the SAME `ComputeRegistry` singleton (`ComputeRegistry.chat` at `backend/app/core/compute_registry_invocation.py:205`, `.chat_stream` at `:546`, `.embed` at `:924`, `.embed_batch` at `:987`). The `OllamaClient` class in ollama.py exists but is not the exported singleton. `coder.node.chat` is `ComputeNode.chat` (`backend/app/core/compute_node_invocation.py:37`) — direct per-donor invocation bypassing registry routing.

## Direct chat-completion call sites (29)

Params column lists only the spec whitelist (model, temperature, max_tokens, response_format, thinking_mode, min_context, stream, tools, require_vision, strict_model_routing) actually present. `project_id` is additionally passed at: chat.py:316, chat.py:505, interfaces.py:143, interfaces.py:588, adaptive_interview.py:308, adaptive_interview.py:363, deployment_service.py:323, research_validity_service.py:556. `system=` is additionally passed at skill_factory.py:717, :755, :794, :863.

| file:line | enclosing function | kind | loop/single | params passed (whitelist only) | output handling | purpose |
|---|---|---|---|---|---|---|
| backend/app/api/routes/chat.py:316 | `_generate_native_tools` | `ollama.chat_stream` (streaming) | **ReAct loop #1 — main chat, native tools** (`for iteration in range(MAX_TOOL_ITERATIONS+1)`, MAX=8, chat.py:77) | model=`effective_model` (pi override via `pi_chat_model`), temperature, max_tokens, tools=`OPENAI_TOOLS`, strict_model_routing=`True if pi_candidate else None` | str chunks → SSE `chunk` events + accumulate; dict w/ `tool_calls` → filter hallucinated names → `execute_tool()` → `role:"tool"` msgs appended, loop continues | Main chat SSE endpoint, native OpenAI-style tool loop |
| backend/app/api/routes/chat.py:505 | `_generate_text_fallback` | `ollama.chat_stream` (streaming) | **ReAct loop #1 fallback — main chat, text-parsed tools** (MAX=8) | model=`effective_model`, temperature, max_tokens, strict_model_routing=`True if pi_candidate else None` (no tools) | full text collected → `_extract_tool_call` regex → `execute_tool()` → tool result re-injected as `role:"user"` msg; SSE chunks | Legacy text-based tool parsing when native tools unsupported |
| backend/app/api/routes/interfaces.py:143 | `_generate_native_design_tools` | `ollama.chat_stream` (streaming) | **ReAct loop #2 — design chat, native tools** (MAX_TOOL_ITERATIONS=3, interfaces.py:48) | model, temperature, max_tokens, tools=`OPENAI_DESIGN_TOOLS` | str chunks → SSE; `tool_calls` dict → `execute_design_tool()` → `role:"tool"` msgs, loop continues | Interfaces Design Chat native tool loop |
| backend/app/api/routes/interfaces.py:588 | `design_chat` → nested `generate()` (route at :286, generator at :530) | `ollama.chat_stream` (streaming) | **ReAct loop #2 fallback — design chat, text-parsed tools** (MAX=3, loop at :586) | model, temperature, max_tokens | accumulate text → `_extract_tool_call` → `execute_design_tool()` → result as `role:"user"` msg; SSE; `_fallback_design_answer` on failure | Design chat text-fallback tool loop |
| backend/app/api/routes/presentation.py:71 | `get_slide_instructions` (route at :34) | `llm_router.chat` | single-shot | temperature=0.3 | `response["message"]["content"]`; exception → `_fallback_slide_instructions` | Generate slide-deck instruction package from report |
| backend/app/agents/ui_audit_agent.py:499 | `UIAuditAgent._evaluate_heuristics_with_data` | `ollama.chat` | single-shot | temperature=0.3 | `resp["message"]["content"]` → JSON substring parse → `UIIssue` list (max 5); errors swallowed | LLM heuristic evaluation in UI audit cycle |
| backend/app/services/adaptive_interview.py:308 | `generate_clarification` | `llm_router.chat` | single-shot | (none from whitelist) | `result.get("content")` top-level; "NONE" sentinel → None | Probing follow-up question for channel interview |
| backend/app/services/adaptive_interview.py:363 | `_is_saturated` | `llm_router.chat` | single-shot (gated by `saturation_check_llm` config) | (none from whitelist) | `result.get("content")` → check "SATURATED" substring; fallback word-count heuristic | LLM saturation judgment for probing |
| backend/app/services/deployment_service.py:323 | `_generate_adaptive_followup` | `llm_router.chat` | single-shot (capped by `max_followups`) | (none from whitelist) | `result.get("content")`; "NONE" → None | Adaptive follow-up question for research deployment |
| backend/app/services/research_validity_service.py:556 | `_default_coder_runner` (invoked per-coder in `run_independent_coding_run` loop at :1130, call :1144 + repair retry :1155) | `coder.node.chat` (**direct ComputeNode, pinned donor+model**) | loop (1–2 calls × up to `max_coders`=3 coders) | model=`model_name or None`, temperature=0.2, response_format=`openai_json_schema_response_format(name="qualitative_code_applications", strict=False)` | raw dict returned; caller reads `message.content` → `_extract_json_payload` → coding applications; empty → repair-prompt retry | Independent multi-model qualitative coding (IRR) |
| backend/app/skills/discover/channel_deployment.py:180 | `ChannelResearchDeploymentSkill.plan` | `ollama.chat` | single-shot | temperature=0.7 | `message.content` → JSON substring parse → deployment plan | Generate channel deployment plan + questions |
| backend/app/skills/discover/channel_deployment.py:261 | `ChannelResearchDeploymentSkill._analyze` | `ollama.chat` | single-shot | temperature=0.3 | `message.content` → JSON substring parse → analysis dict (candidate/provisional) | Analyze collected deployment responses |
| backend/app/skills/discover/contextual_inquiry.py:36 | `ContextualInquirySkill.plan` | `ollama.chat` | single-shot | temperature=0.7 | `message.content` as markdown plan | Contextual inquiry observation plan |
| backend/app/skills/discover/contextual_inquiry.py:83 | `ContextualInquirySkill.execute` | `ollama.chat` | single-shot | temperature=0.3 | `message.content` → JSON substring parse → nuggets/artifacts | Analyze observation notes (AEIOU) |
| backend/app/skills/discover/diary_studies.py:28 | `DiaryStudiesSkill.plan` | `ollama.chat` | single-shot | temperature=0.7 | `message.content` as markdown plan | Diary study design plan |
| backend/app/skills/discover/diary_studies.py:70 | `DiaryStudiesSkill.execute` | `ollama.chat` | single-shot | temperature=0.3 | `message.content` → JSON substring parse → nuggets | Analyze diary entries (temporal/emotional patterns) |
| backend/app/skills/discover/user_interviews.py:201 | `UserInterviewsSkill.plan` (:178) | `ollama.chat` | single-shot | temperature=0.7 | `message.content` as interview guide markdown | Generate interview guide |
| backend/app/skills/discover/user_interviews.py:297 | `UserInterviewsSkill.execute` (:225) | `ollama.chat` | **loop — one call per transcript** (`for idx, transcript in enumerate(transcripts_to_analyze)` at :288) | temperature=0.3 | `message.content` → JSON substring parse per transcript → analyses + nuggets | Per-transcript analysis |
| backend/app/skills/discover/user_interviews.py:337 | `UserInterviewsSkill.execute` | `ollama.chat` | single-shot (only if >1 transcript) | temperature=0.3 | `message.content` → JSON substring parse → synthesis (facts/insights/recommendations) | Cross-transcript synthesis |
| backend/app/skills/intercoder.py:390 | `KappaIntercoderSkill.plan` (:378) | `ollama.chat` | single-shot | temperature=0.7 | `message.content` as markdown plan | Kappa-validated analysis process plan |
| backend/app/skills/intercoder.py:411 | `KappaIntercoderSkill.execute` (:393) | `ollama.chat` | single-shot (step 1 of sequential pipeline) | temperature=0.3 | `_parse_json_response(message.content)` → codebook + coding_results A; empty → abort | Coder A open coding |
| backend/app/skills/intercoder.py:438 | `KappaIntercoderSkill.execute` | `ollama.chat` | single-shot (step 2) | temperature=0.3 | `_parse_json_response` → coding_results B | Coder B independent re-coding |
| backend/app/skills/intercoder.py:496 | `KappaIntercoderSkill.execute` | `ollama.chat` | single-shot (step 4, only if disagreements) | temperature=0.3 | `_parse_json_response` → reconciled codes, themes, codebook_refinements | Disagreement reconciliation |
| backend/app/skills/intercoder.py:520 | `KappaIntercoderSkill.execute` | `ollama.chat` | single-shot (only if zero disagreements) | temperature=0.3 | `_parse_json_response` → themes | Theme extraction when all coders agreed |
| backend/app/skills/skill_factory.py:508 | `create_skill` (:447) → nested `GeneratedSkill.plan` (:491) | `ollama.chat` | single-shot | temperature=0.7, thinking_mode="off" | `message.content` stripped; exception/empty → deterministic `_fallback_plan` | Plan for factory-generated (definition JSON) skill |
| backend/app/skills/skill_factory.py:717 | `create_skill` → `GeneratedSkill.execute` (:524) | `ollama.chat` | single-shot (primary call of 4-stage fallback chain) | temperature=0.2, max_tokens=`max_output_tokens`, response_format=`schema_dict` (strict json_schema, token-budgeted), min_context=`estimated_context_tokens`, thinking_mode="off" | `message.content` → `strip_thinking_markers` → `_parse_json_response`; failure cascades to repairs | Structured skill execution over research data |
| backend/app/skills/skill_factory.py:755 | `GeneratedSkill.execute` | `ollama.chat` | single-shot (repair #1, if non-JSON and provider ≠ lmstudio) | temperature=0.0, max_tokens, response_format=`repair_response_format` (`_normalized_skill_output_response_format`, :627), min_context, thinking_mode="off" | repaired content → JSON parse | Native JSON repair of failed output |
| backend/app/skills/skill_factory.py:794 | `GeneratedSkill.execute` | `ollama.chat` | single-shot (repair #2, if still no JSON) | temperature=0.0, max_tokens, min_context, thinking_mode="off" (no response_format) | JSON parse; failure → SkillOutput(success=False) w/ raw artifacts | Plain-prompt JSON repair fallback |
| backend/app/skills/skill_factory.py:863 | `GeneratedSkill.execute` | `ollama.chat` | single-shot (repair #3, valid JSON but zero findings) | temperature=0.0, max_tokens=`max(512, min(max_output_tokens, 768))`, min_context, thinking_mode="off" | JSON parse → re-normalize findings; else deterministic fallback (:892) | Empty-findings repair |

## Direct embed call sites in the four trees

**None.** `rg "\.embed\(|embed_batch\("` over the four trees (excl. tests): 0 hits. All embedding happens in `app/core/` (rag.py, prompt_rag.py, embeddings.py, compute_registry_invocation.py:924/:987), reached indirectly:

| file:line | enclosing function | indirect embedding trigger |
|---|---|---|
| backend/app/api/routes/chat.py:726 | `chat` (route :621) | `compose_dynamic_prompt(..., use_embeddings=True)` — persona prompt-RAG query embed |
| backend/app/api/routes/chat.py:754 | `chat` | same, istara-main fallback |
| backend/app/api/routes/chat.py:764 | `chat` | `retrieve_context(project_id, message)` — RAG query embed |
| backend/app/api/routes/chat.py:779 | `chat` | `compose_dynamic_prompt(..., max_tokens=budget.identity_tokens, use_embeddings=True)` budget re-compose |
| backend/app/api/routes/interfaces.py:400 | `design_chat` (:286) | `compose_dynamic_prompt(..., use_embeddings=True)` |
| backend/app/api/routes/interfaces.py:414 | `design_chat` | `retrieve_context(...)` |
| backend/app/api/routes/interfaces.py:429 | `design_chat` | `compose_dynamic_prompt(..., use_embeddings=True)` |
| backend/app/api/routes/agents.py:984 | `compose_prompt_for_query` (:955) | `compose_dynamic_prompt(..., use_embeddings=data.use_embeddings)` |
| backend/app/api/routes/memory.py:95 | `search_memory` (:75) | `retrieve_context(...)` |
| backend/app/api/routes/findings.py:566 | `search_findings` (:552) | `retrieve_context(project_id, query, top_k=top_k)` |
| backend/app/skills/system_actions.py:1116 | `_exec_search_memory` (:1114) | `retrieve_context(project_id, query, top_k)` — chat tool `search_memory` |
| backend/app/api/routes/files.py:679 | `reprocess_files` | re-embed + re-index pipeline via core file processing |

## Other model invocations discovered via imports

| file:line | enclosing function | kind | loop/single | params | notes |
|---|---|---|---|---|---|
| backend/app/services/browser_service.py:83 (LLM built at :29/:36/:43 in `_get_llm`) | `browse_website` | `langchain_openai.ChatOpenAI` driven by `browser_use.Agent.run()` | **internal multi-step agent loop** (max_steps=10, max_actions_per_step=3) | model=settings.lmstudio_model/ollama_model, temperature=0.3, base_url=provider `/v1` | Bypasses compute_registry entirely — direct OpenAI-compat HTTP. Reached from chat tool `browse_website` (`system_actions.py:1208` → `system_web_context_actions.py:106`) and `backend/app/skills/browser_skills.py:40` |
| backend/app/api/routes/chat.py:1188 | `transcribe_voice` (:1158) | Whisper STT via `app.core.transcription.transcribe_audio` | single-shot | language | Voice input transcription (not chat/embed) |
| backend/app/skills/design_tools.py:175, :338, :444 | `_generate_screen`/`_edit_screen`/`_generate_variants` (design tools) | external Google Stitch generative design API via `stitch_service._call_tool` (`generate_screen_from_text` stitch_service.py:128, `edit_screens` :259, `generate_variants` :289) | single-shot each | prompt, device, model (Stitch-side) | External SaaS model, not via llm_router; invoked from design ReAct loop #2 tools |

## system_actions.py tool inventory

`OPENAI_TOOLS` (backend/app/skills/system_actions.py:79) — 17 names: create_task, search_documents, list_tasks, move_task, attach_document, search_findings, list_project_files, assign_agent, send_agent_message, get_document_content, search_memory, update_task, sync_project_documents, web_fetch, browse_website, context_expand, context_grep

`TOOL_EXECUTORS` (backend/app/skills/system_actions.py:1193) — same 17 keys: create_task, search_documents, list_tasks, move_task, attach_document, search_findings, list_project_files, assign_agent, send_agent_message, get_document_content, search_memory, update_task, sync_project_documents, web_fetch, browse_website, context_expand, context_grep

Of these, tools that themselves trigger model calls: `browse_website` (LLM browser agent loop), `search_memory` (embedding via retrieve_context). `search_documents` is pure SQL ILIKE (system_actions.py:829) — no embedding.

## run_skill → skills making their own LLM calls

`run_skill` is NOT in OPENAI_TOOLS; it is built per-run by `build_run_skill_tool` (backend/app/core/agent_skill_tools.py:383) for the agent-research ReAct loop (backend/app/core/agent_research.py:179, outside the four trees) and executes `registry.get(skill_name).execute()` via `execute_ranked_skill_tool` (agent_skill_tools.py:451). Registered skills (backend/app/skills/registry.py:104 `load_default_skills`) that make their own `ollama.chat` (= compute_registry) calls when invoked:

- `user-interviews` (UserInterviewsSkill — 2 LLM calls in execute, 1 in plan; per-transcript loop)
- `contextual-inquiry` (ContextualInquirySkill — 1 execute, 1 plan)
- `diary-studies` (DiaryStudiesSkill — 1 execute, 1 plan)
- `channel-research-deployment` (ChannelResearchDeploymentSkill — plan + analyze modes)
- `kappa-thematic-analysis` (KappaIntercoderSkill — up to 4 sequential LLM calls in execute)
- ALL factory-generated skills from `backend/app/skills/definitions/*.json` (each is a `GeneratedSkill` from skill_factory.py `create_skill` — 1 plan call + up to 4-call execute fallback chain)
- `browse-website` skill (browser_skills.py:40) — LLM via browser-use, not ollama

Non-LLM: `backend/app/skills/discover/user_interviews.py:15` imports `retrieve_context` but never uses it (dead import). `backend/app/agents/devops_agent.py` imports ollama but only calls `ollama.health()` (:380).

## Totals

- Direct chat-completion sites (ollama.chat / ollama.chat_stream / llm_router.chat / node.chat): **29**
- Direct embed/embed_batch sites in the four trees: **0**
- Other model invocations (browser-use ChatOpenAI loop, Whisper STT, Stitch generative x3): **5**
- Indirect embedding-trigger sites (compose_dynamic_prompt use_embeddings / retrieve_context / reprocess): **12**
- Sites inside the two chat ReAct loops: **4** (chat.py:316, chat.py:505, interfaces.py:143, interfaces.py:588)