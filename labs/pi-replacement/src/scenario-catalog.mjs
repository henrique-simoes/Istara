import {
  fauxAssistantMessage,
  fauxText,
  fauxToolCall,
} from "@earendil-works/pi-ai";

export const ISTARA_PI_SCENARIOS = [
  {
    id: "chat.tool_loop.task_and_finding",
    family: "chat_tool_loop",
    sourceAssets: ["tests/agentic_eval_contract.json", "tests/simulation/scenarios/31-task-documents-tools.mjs"],
    surfaces: ["chat/tool loop", "tasks", "findings", "telemetry"],
    istaraSurfaceIds: ["chat_react_loop", "tasks_findings_documents", "telemetry_tokens_tool_metrics"],
    prompt: "Create task and finding through Istara tools.",
    expectedCanonicalTools: ["tasks.create", "findings.create"],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_task", {
            title: "Review Pi replacement adapter boundary",
            description: "Confirm Pi owns the loop while Istara owns feature contracts.",
            priority: "high",
          }),
          fauxToolCall("istara_create_finding", {
            title: "Pi adapter executed an Istara feature contract",
            severity: "medium",
            evidence: "The deterministic Pi Agent loop invoked canonical Istara task and finding tools.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Created a task and finding through Istara canonical tools.")),
    ],
  },
  {
    id: "task.plan_execute.lifecycle",
    family: "plan_and_execute",
    sourceAssets: ["tests/benchmarks/test_orchestration.py", "tests/simulation/scenarios/71-plan-and-execute.mjs"],
    surfaces: ["task lifecycle", "plan DAG", "review state", "skills endpoint representative"],
    istaraSurfaceIds: ["plan_review_state", "tasks_findings_documents"],
    prompt: "Plan and execute a complex UX analysis task with dependencies and validation metadata.",
    expectedCanonicalTools: ["tasks.create", "plans.create", "tasks.update_lifecycle"],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_task", {
            title: "Comprehensive UX Analysis",
            description: "Analyze interview transcripts, survey friction, and competitor onboarding.",
            priority: "high",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_research_plan", {
            taskId: "task-1",
            steps: [
              { id: "retrieve", description: "Retrieve transcripts and survey snippets", depends_on: [] },
              { id: "analyze", description: "Theme usability issues", depends_on: ["retrieve"] },
              { id: "synthesize", description: "Produce recommendations", depends_on: ["analyze"] },
            ],
          }),
          fauxToolCall("istara_update_task_lifecycle", {
            taskId: "task-1",
            status: "in_review",
            validation_method: "pi-candidate-deterministic-consensus",
            consensus_score: 0.82,
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Created a DAG research plan and moved the task into review.")),
    ],
  },
  {
    id: "documents.tools.slice",
    family: "documents_tools",
    sourceAssets: [
      "tests/simulation/scenarios/29-documents-system.mjs",
      "tests/simulation/scenarios/31-task-documents-tools.mjs",
    ],
    surfaces: ["documents", "document search/read", "task document links", "tool schema validation"],
    istaraSurfaceIds: ["chat_react_loop", "tasks_findings_documents"],
    prompt: "Create a competitor document, search/read the evidence, attach it to a task, and record a finding.",
    expectedCanonicalTools: [
      "documents.create",
      "documents.search",
      "documents.read",
      "tasks.create",
      "tasks.attach_document",
      "findings.create",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_document", {
            title: "Competitor Report Draft",
            description: "Input for competitive analysis",
            source: "user_upload",
            file_name: "competitor-report.pdf",
            content: "Competitor A exposes pricing early. Competitor B defers account creation until after checkout.",
            tags: ["competitive-analysis", "pricing"],
            phase: "discover",
          }),
          fauxToolCall("istara_search_documents", {
            query: "pricing checkout",
            phase: "discover",
            limit: 3,
          }),
          fauxToolCall("istara_read_document", {
            documentId: "document-2",
            span: "full",
          }),
          fauxToolCall("istara_create_task", {
            title: "Analyze competitor websites",
            description: "Run competitive analysis on key competitors",
            instructions: "Focus on pricing pages and onboarding flows",
            urls: ["https://competitor-a.example", "https://competitor-b.example"],
            input_document_ids: ["document-2"],
            priority: "high",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_attach_task_document", {
            taskId: "task-1",
            documentId: "document-2",
            direction: "input",
          }),
          fauxToolCall("istara_create_finding", {
            title: "Document-linked competitor analysis ready",
            severity: "medium",
            evidence: "The Pi loop created and attached a project-scoped document envelope.",
            source_document_ids: ["document-2"],
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Created the document, linked it to a task, and recorded the finding.")),
    ],
  },
  {
    id: "structured_outputs.core_eval",
    family: "structured_outputs",
    sourceAssets: ["tests/evals/cases/core_eval_cases.json", "scripts/run_istara_evals.py"],
    surfaces: ["core evals", "JSON contract", "DAG/ReAct structured output"],
    istaraSurfaceIds: ["benchmarks_evals_simulations_real_user_contract"],
    prompt: "Emit the structured output expected by Istara's classic JSON and DAG evals.",
    expectedCanonicalTools: ["evals.emit_structured"],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_emit_structured_eval", {
            caseId: "dag_react_json_plan",
            payload: {
              nodes: [
                { id: "retrieve", action: "retrieve documents" },
                { id: "analyze", action: "theme evidence" },
                { id: "synthesize", action: "write synthesis" },
              ],
              edges: [["retrieve", "analyze"], ["analyze", "synthesize"]],
            },
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Structured eval artifact emitted as JSON-compatible payload.")),
    ],
  },
  {
    id: "memory.rag.slice",
    family: "memory_rag",
    sourceAssets: ["tests/agentic_eval_contract.json", "tests/simulation/scenarios/23-memory-view.mjs"],
    surfaces: ["memory search", "memory write", "RAG grounding proxy"],
    istaraSurfaceIds: ["memory_rag_reasoning_memento_skills"],
    prompt: "Search memory for checkout friction, ground a finding, and write a reusable memory.",
    expectedCanonicalTools: ["memory.search", "findings.create", "memory.write"],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_search_memory", {
            query: "checkout friction",
            scope: "project",
          }),
          fauxToolCall("istara_create_finding", {
            title: "Checkout friction persisted in research memory",
            severity: "high",
            evidence: "Memory search returned earlier checkout friction evidence.",
          }),
          fauxToolCall("istara_write_memory", {
            text: "Pi replacement run reused checkout-friction memory before creating a finding.",
            scope: "project",
            tags: ["pi-replacement", "rag"],
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Memory search, grounded finding, and memory write completed.")),
    ],
  },
  {
    id: "skills.three_skill_slice",
    family: "skills",
    sourceAssets: ["tests/agentic_eval_contract.json", "tests/simulation/scenarios/20-all-skills-comprehensive.mjs"],
    surfaces: ["skills", "prompt adherence", "research spine"],
    istaraSurfaceIds: ["memory_rag_reasoning_memento_skills", "steering_system_prompt"],
    prompt: "Apply at most three Istara skill adapters and synthesize their outputs.",
    expectedCanonicalTools: ["skills.apply", "skills.apply", "skills.apply", "findings.create"],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_apply_skill", {
            skillId: "competitive-analysis",
            input: "Compare onboarding and pricing-page friction.",
          }),
          fauxToolCall("istara_apply_skill", {
            skillId: "thematic-analysis",
            input: "Theme transcript snippets about checkout and onboarding.",
          }),
          fauxToolCall("istara_apply_skill", {
            skillId: "research-synthesis",
            input: "Synthesize competitive and thematic findings.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_finding", {
            title: "Three-skill synthesis completed",
            severity: "medium",
            evidence: "Pi executed exactly three approved Istara skill adapters.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Applied three skills and recorded the synthesis finding.")),
    ],
  },
  {
    id: "a2a.debate_report.slice",
    family: "a2a",
    sourceAssets: ["tests/simulation/scenarios/73-a2a-debate-and-reports.mjs"],
    surfaces: ["A2A delegation", "layered reports", "MECE summary"],
    istaraSurfaceIds: ["a2a_delegation_reports"],
    prompt: "Delegate a debate, then record an L3 report with MECE categories.",
    expectedCanonicalTools: ["a2a.delegate", "a2a.delegate", "a2a.report"],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_delegate_agent", {
            agentRole: "istara-ux-eval",
            instruction: "Assess usability risk in checkout findings.",
          }),
          fauxToolCall("istara_delegate_agent", {
            agentRole: "istara-ui-audit",
            instruction: "Assess interface implementation risk in checkout findings.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_record_a2a_report", {
            layer: 3,
            executive_summary: "Checkout friction is a conversion and trust risk.",
            mece_categories: ["pricing transparency", "account creation", "mobile flow"],
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Delegated the A2A debate and recorded the L3 report envelope.")),
    ],
  },
  {
    id: "channel.lifecycle.simulated_slice",
    family: "channels",
    sourceAssets: ["tests/simulation/scenarios/53-channel-lifecycle.mjs"],
    surfaces: ["channel lifecycle", "inbound turn", "outbound response", "session scoping"],
    istaraSurfaceIds: ["channels_webhooks_telegram_lifecycle"],
    prompt: "Create a simulated Telegram channel, process one inbound message, and respond.",
    expectedCanonicalTools: ["channels.create", "channels.receive", "channels.respond"],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_channel", {
            platform: "telegram",
            name: "SIM: Pi Replacement Telegram Bot",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_receive_channel_message", {
            channelId: "channel-1",
            externalUserId: "sim-user-1",
            text: "Summarize checkout friction evidence.",
          }),
          fauxToolCall("istara_respond_channel_message", {
            channelId: "channel-1",
            inReplyTo: "channel-message-1",
            text: "Checkout friction centers on hidden costs and account creation pressure.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Processed the simulated channel turn through Pi and Istara channel envelopes.")),
    ],
  },
  {
    id: "research.spine.step_tracker",
    family: "research_spine",
    sourceAssets: [
      "docs/architecture/research-validity-contract.md",
      "tests/real_user_benchmark/lib/research-spine-probes.mjs",
      "tests/agentic_eval_contract.json",
    ],
    surfaces: ["research spine", "evidence units", "quality scoring", "human-review gate proxy"],
    istaraSurfaceIds: ["chat_react_loop", "tasks_findings_documents", "plan_review_state"],
    prompt: "Record source-grounded research-spine steps from source to recommendation.",
    expectedCanonicalTools: [
      "documents.search",
      "documents.read",
      "research.record_step",
      "research.record_step",
      "research.record_step",
      "research.record_step",
      "findings.create",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_search_documents", {
            query: "checkout friction",
            tag: "evidence-unit",
            limit: 2,
          }),
          fauxToolCall("istara_read_document", {
            documentId: "document-seed-checkout-friction",
            span: "P03 checkout quote",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_record_research_spine_step", {
            step: "evidence_unit",
            artifact_id: "eu-checkout-p03",
            source_document_id: "document-seed-checkout-friction",
            source_span: "Participant P03 abandoned checkout after surprise shipping and mandatory account creation.",
            grounding_status: "source_grounded",
            quality_score: 0.94,
            notes: "Exact source span preserved.",
          }),
          fauxToolCall("istara_record_research_spine_step", {
            step: "atomic_extraction",
            artifact_id: "atom-hidden-cost-account-pressure",
            source_document_id: "document-seed-checkout-friction",
            source_span: "surprise shipping and mandatory account creation",
            grounding_status: "source_grounded",
            quality_score: 0.9,
          }),
          fauxToolCall("istara_record_research_spine_step", {
            step: "reliability",
            artifact_id: "rel-hidden-cost-account-pressure",
            source_document_id: "document-seed-checkout-friction",
            source_span: "surprise shipping and mandatory account creation",
            grounding_status: "validated",
            quality_score: 0.83,
            notes: "Proxy reliability score; true multi-model reconciliation remains future work.",
          }),
          fauxToolCall("istara_record_research_spine_step", {
            step: "recommendation",
            artifact_id: "rec-transparent-checkout",
            source_document_id: "document-seed-checkout-friction",
            source_span: "surprise shipping and mandatory account creation",
            grounding_status: "candidate_only",
            quality_score: 0.72,
            notes: "Not reportable until human Done review in production Istara.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_finding", {
            title: "Checkout friction is source-grounded but not report-approved",
            severity: "high",
            evidence: "Exact source span preserved through evidence_unit, extraction, reliability, and recommendation records.",
            source_document_ids: ["document-seed-checkout-friction"],
            research_step_ids: [
              "research-step-1",
              "research-step-2",
              "research-step-3",
              "research-step-4",
            ],
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Recorded the research-spine trace and kept the recommendation provisional.")),
    ],
  },
  {
    id: "autoresearch.governed_experiment.slice",
    family: "autoresearch",
    sourceAssets: [
      "backend/app/api/routes/autoresearch.py",
      "backend/app/core/autoresearch_engine.py",
      "backend/app/core/autoresearch_isolation.py",
      "tests/simulation/scenarios/61-autoresearch-isolation.mjs",
      "tests/agentic_eval_contract.json",
    ],
    surfaces: ["autoresearch route", "sandbox isolation", "governed promotion", "research-spine safety"],
    istaraSurfaceIds: ["autoresearch_governance", "telemetry_tokens_tool_metrics"],
    prompt: "Represent a governed Autoresearch proposal and measurement without letting it become report evidence.",
    expectedCanonicalTools: [
      "autoresearch.propose_experiment",
      "autoresearch.record_measurement",
      "research.record_step",
      "telemetry.record_metric",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_propose_autoresearch_experiment", {
            loop_type: "rag_params",
            target: "improve checkout-friction retrieval precision",
            metric: "grounded_retrieval_precision",
            max_iterations: 1,
            report_evidence: false,
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_record_autoresearch_measurement", {
            experimentId: "autoresearch-experiment-1",
            baseline_score: 0.68,
            candidate_score: 0.73,
            delta: 0.05,
            kept: true,
            notes: "Sandboxed measurement only; proposal still needs governed promotion.",
          }),
          fauxToolCall("istara_record_research_spine_step", {
            step: "reliability",
            artifact_id: "autoresearch-rag-params-proposal",
            grounding_status: "candidate_only",
            quality_score: 0.64,
            notes: "Autoresearch output is process evidence, not report evidence.",
          }),
          fauxToolCall("istara_record_telemetry_metric", {
            name: "autoresearch.proposal_delta",
            value: 0.05,
            unit: "score_delta",
            labels: { loop_type: "rag_params", report_evidence: false },
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Recorded the governed Autoresearch proposal, sandbox measurement, and telemetry.")),
    ],
  },
  {
    id: "memory.reasoningbank.memento.slice",
    family: "memory_reasoning_memento",
    sourceAssets: [
      "backend/app/api/routes/memory.py",
      "backend/app/api/routes/reasoning_bank.py",
      "backend/app/core/rag.py",
      "backend/app/core/reasoning_bank.py",
      "backend/app/core/agent_skill_tools.py",
      "tests/evals/cases/core_eval_cases.json",
      "tests/agentic_eval_contract.json",
    ],
    surfaces: ["memory/RAG", "ReasoningBank", "Memento skills", "learned skill routing"],
    istaraSurfaceIds: ["memory_rag_reasoning_memento_skills"],
    prompt: "Load project memory, write/retrieve process reasoning, and record a governed skill-memory candidate.",
    expectedCanonicalTools: [
      "memory.search",
      "reasoning_bank.store",
      "reasoning_bank.retrieve",
      "memento.record_skill_memory",
      "skills.apply",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_search_memory", {
            query: "checkout friction",
            scope: "project",
          }),
          fauxToolCall("istara_store_reasoning_memory", {
            title: "Use source spans before synthesis",
            content: "When checkout-friction memory appears, retrieve exact document spans before creating findings.",
            source_kind: "agent_trace",
            outcome: "success",
            tags: ["memento", "research-spine"],
            confidence: 0.72,
            evidence_refs: [{ source_kind: "scenario", source_id: "memory.reasoningbank.memento.slice" }],
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_retrieve_reasoning_memory", {
            query: "source spans checkout findings",
            source_kinds: ["agent_trace"],
            limit: 3,
          }),
          fauxToolCall("istara_record_memento_skill_memory", {
            skillId: "research-synthesis",
            lesson: "Prefer source-span retrieval before synthesis when memory hits mention checkout friction.",
            governance_status: "candidate",
            evidence_handle: "reasoning-memory-1",
            quality_score: 0.71,
          }),
          fauxToolCall("istara_apply_skill", {
            skillId: "research-synthesis",
            input: "Synthesize only after process memory confirms source-span retrieval.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Loaded memory, recorded process reasoning, and kept skill memory governed.")),
    ],
  },
  {
    id: "channels.webhook.telegram.lifecycle",
    family: "channels_webhooks",
    sourceAssets: [
      "backend/app/api/routes/channels.py",
      "backend/app/api/routes/webhooks.py",
      "backend/app/channels/telegram.py",
      "tests/simulation/scenarios/53-channel-lifecycle.mjs",
      "tests/test_webhooks_security.py",
    ],
    surfaces: ["channel lifecycle", "webhook replay/signature envelope", "Telegram-like inbound turn"],
    istaraSurfaceIds: ["channels_webhooks_telegram_lifecycle"],
    prompt: "Represent a signed Telegram-like inbound webhook, channel receive, and response lifecycle.",
    expectedCanonicalTools: [
      "channels.create",
      "webhooks.receive",
      "channels.receive",
      "channels.respond",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_create_channel", {
            platform: "telegram",
            name: "SIM: Signed webhook bridge",
          }),
          fauxToolCall("istara_receive_webhook_event", {
            platform: "telegram",
            instanceId: "channel-1",
            externalEventId: "telegram-update-1001",
            signatureVerified: true,
            replayAccepted: true,
            text: "Participant asks for a checkout-friction summary.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_receive_channel_message", {
            channelId: "channel-1",
            externalUserId: "telegram-user-42",
            text: "Participant asks for a checkout-friction summary.",
          }),
          fauxToolCall("istara_respond_channel_message", {
            channelId: "channel-1",
            inReplyTo: "channel-message-1",
            text: "I can summarize only provisional source-grounded evidence until Istara review approves it.",
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Recorded signed webhook receipt, channel turn, and outbound response.")),
    ],
  },
  {
    id: "steering.system_prompt.loop.slice",
    family: "steering_system_prompt",
    sourceAssets: [
      "backend/app/api/routes/steering.py",
      "backend/app/core/prompt_rag.py",
      "backend/app/api/routes/chat.py",
      "tests/simulation/scenarios/70-mid-execution-steering.mjs",
      "tests/benchmarks/test_orchestration.py",
    ],
    surfaces: ["mid-execution steering", "follow-up queue", "system prompt policy", "local-model safety"],
    istaraSurfaceIds: ["steering_system_prompt", "chat_react_loop"],
    prompt: "Queue a steering message and audit the Pi candidate prompt for Istara protected-policy adherence.",
    expectedCanonicalTools: [
      "steering.queue",
      "system_prompt.audit",
      "models.route",
      "telemetry.record_metric",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_queue_steering_message", {
            agentId: "istara-main",
            message: "Keep recommendation provisional until source-grounded reliability and human Done gates pass.",
            kind: "steering",
            projectId: "lab-project",
            mode: "append",
          }),
          fauxToolCall("istara_audit_system_prompt", {
            prompt_name: "pi-replacement-default",
            required_policy: "Pi owns loop execution; Istara owns project contracts and the research spine.",
            observed_text: "Canonical tools only. No local models. Research spine output remains provisional until governed review.",
            canonical_tools_only: true,
            local_models_allowed: false,
            protected_blocks_present: true,
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(
        [
          fauxToolCall("istara_record_model_route", {
            step: "steered_loop",
            provider: "faux",
            model: "deterministic-fixture",
            reason: "No-model deterministic test path for steering contract.",
            local_models_allowed: false,
          }),
          fauxToolCall("istara_record_telemetry_metric", {
            name: "steering.prompt_policy_pass",
            value: 1,
            unit: "pass_fail",
            labels: { scenario: "steering.system_prompt.loop.slice" },
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Queued steering and passed the protected prompt-policy audit.")),
    ],
  },
  {
    id: "benchmarks.evals.real_user.contract",
    family: "benchmark_contracts",
    sourceAssets: [
      "tests/benchmarks/run_benchmarks.py",
      "tests/evals/registry.json",
      "tests/real_user_benchmark/benchmark-registry.json",
      "tests/agentic_eval_contract.json",
    ],
    surfaces: ["benchmarks", "core evals", "simulations", "real-user benchmark", "agentic eval contract"],
    istaraSurfaceIds: ["benchmarks_evals_simulations_real_user_contract", "telemetry_tokens_tool_metrics"],
    prompt: "Map benchmark and eval harness expectations to bridge scenarios and emit a structured readiness artifact.",
    expectedCanonicalTools: [
      "benchmarks.map_contract",
      "evals.emit_structured",
      "telemetry.record_metric",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_map_benchmark_contract", {
            harnessPath: "tests/benchmarks/run_benchmarks.py",
            featureId: "pi_replacement_real_loop_bridge",
            metrics: ["tool_selection_quality", "consensus_accuracy", "steering_latency_ms", "json_validity"],
            scenarioIds: [
              "chat.tool_loop.task_and_finding",
              "autoresearch.governed_experiment.slice",
              "steering.system_prompt.loop.slice",
            ],
          }),
          fauxToolCall("istara_emit_structured_eval", {
            caseId: "agentic_eval_contract_bridge_readiness",
            payload: {
              benchmarks_mapped: true,
              simulations_mapped: true,
              real_user_benchmark_mapped: true,
              production_credentials_required: true,
            },
          }),
          fauxToolCall("istara_record_telemetry_metric", {
            name: "benchmark.contract_surfaces_mapped",
            value: 4,
            unit: "surface_count",
            labels: { candidate: "pi-replacement" },
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Mapped benchmark/eval/real-user contracts to bridge scenarios.")),
    ],
  },
  {
    id: "model.routing.telemetry.slice",
    family: "model_routing_telemetry",
    sourceAssets: [
      "tests/agentic_eval_contract.json",
      "tests/evals/registry.json",
      "tests/test_telemetry.py",
      "tests/test_telemetry_export.py",
    ],
    surfaces: ["model routing", "telemetry", "tokens", "tool calls versus quality"],
    istaraSurfaceIds: ["telemetry_tokens_tool_metrics", "benchmarks_evals_simulations_real_user_contract"],
    prompt: "Record DeepSeek-only model routing and telemetry for a bounded candidate step.",
    expectedCanonicalTools: [
      "models.route",
      "telemetry.record_metric",
      "telemetry.record_metric",
      "evals.emit_structured",
    ],
    responses: [
      fauxAssistantMessage(
        [
          fauxToolCall("istara_record_model_route", {
            step: "candidate_live_sample",
            provider: "deepseek",
            model: "deepseek-v4-pro",
            reason: "Owner-approved cloud model route; local models are disallowed.",
            local_models_allowed: false,
          }),
          fauxToolCall("istara_record_telemetry_metric", {
            name: "pi_candidate.tool_calls",
            value: 4,
            unit: "count",
            labels: { scenario: "model.routing.telemetry.slice" },
          }),
          fauxToolCall("istara_record_telemetry_metric", {
            name: "pi_candidate.output_quality_proxy",
            value: 1,
            unit: "pass_fail",
            labels: { scenario: "model.routing.telemetry.slice" },
          }),
          fauxToolCall("istara_emit_structured_eval", {
            caseId: "model_route_telemetry_contract",
            payload: {
              provider: "deepseek",
              model: "deepseek-v4-pro",
              local_models_allowed: false,
              telemetry_emitted: true,
            },
          }),
        ],
        { stopReason: "toolUse" },
      ),
      fauxAssistantMessage(fauxText("Recorded the DeepSeek-only route and telemetry contract.")),
    ],
  },
];

export function getScenarioDefinition(scenarioId) {
  const scenario = ISTARA_PI_SCENARIOS.find((item) => item.id === scenarioId);
  if (!scenario) {
    throw new Error(`Unknown Istara Pi scenario: ${scenarioId}`);
  }
  return scenario;
}
