import { Type, validateToolCall } from "@earendil-works/pi-ai";

const jsonClone = (value) => JSON.parse(JSON.stringify(value));

function textResult(text, details, terminate = false) {
  return {
    content: [{ type: "text", text }],
    details,
    terminate,
  };
}

function errorEnvelope(action, code, message, details = {}) {
  return {
    ok: false,
    action,
    error: { code, message },
    details,
  };
}

function successEnvelope(action, data) {
  return {
    ok: true,
    action,
    data,
  };
}

export class CanonicalToolFacade {
  constructor(options = {}) {
    this.projectId = options.projectId ?? "lab-project";
    this.actor = options.actor ?? "pi-replacement-lab";
    this.trace = [];
    this.findings = [];
    this.tasks = [];
    this.documents = [
      {
        id: "document-seed-checkout-friction",
        projectId: this.projectId,
        title: "Checkout Friction Interview Extract",
        description: "Seed evidence unit used by the lab replacement harness.",
        source: "lab_fixture",
        file_name: "checkout-friction-interview.md",
        content: "Participant P03 abandoned checkout after surprise shipping and mandatory account creation.",
        tags: ["interview", "checkout", "evidence-unit"],
        phase: "discover",
      },
    ];
    this.plans = [];
    this.memory = [
      {
        id: "mem-ux-research-contract",
        scope: "project",
        text: "Istara keeps projects, permissions, memory stores, research semantics, and telemetry policy while Pi owns the loop.",
      },
      {
        id: "mem-checkout-friction",
        scope: "project",
        text: "Earlier interviews showed checkout friction from hidden shipping costs and account creation pressure.",
      },
    ];
    this.skillRuns = [];
    this.a2aMessages = [];
    this.reports = [];
    this.channels = [];
    this.channelMessages = [];
    this.evalArtifacts = [];
    this.researchSteps = [];
    this.metrics = [];
    this.modelRoutes = [];
    this.autoresearchExperiments = [];
    this.reasoningMemories = [];
    this.mementoSkillMemories = [];
    this.webhookEvents = [];
    this.steeringEvents = [];
    this.systemPromptAudits = [];
    this.benchmarkContracts = [];
    this.calls = [];
  }

  getToolDefinitions() {
    return [
      {
        canonicalId: "tasks.create",
        toolName: "istara_create_task",
        label: "Create Task",
        description: "Create an Istara task through the canonical adapter facade.",
        parameters: Type.Object({
          title: Type.String({ minLength: 1 }),
          description: Type.Optional(Type.String()),
          priority: Type.Optional(Type.Union([Type.Literal("low"), Type.Literal("normal"), Type.Literal("high")])),
          instructions: Type.Optional(Type.String()),
          urls: Type.Optional(Type.Array(Type.String())),
          input_document_ids: Type.Optional(Type.Array(Type.String())),
          output_document_ids: Type.Optional(Type.Array(Type.String())),
        }),
      },
      {
        canonicalId: "tasks.attach_document",
        toolName: "istara_attach_task_document",
        label: "Attach Task Document",
        description: "Attach an Istara document id to a task input or output list.",
        parameters: Type.Object({
          taskId: Type.String({ minLength: 1 }),
          documentId: Type.String({ minLength: 1 }),
          direction: Type.Union([Type.Literal("input"), Type.Literal("output")]),
        }),
      },
      {
        canonicalId: "tasks.update_lifecycle",
        toolName: "istara_update_task_lifecycle",
        label: "Update Task Lifecycle",
        description: "Update plan/review lifecycle fields on an Istara task envelope.",
        parameters: Type.Object({
          taskId: Type.String({ minLength: 1 }),
          status: Type.Union([Type.Literal("open"), Type.Literal("in_progress"), Type.Literal("in_review"), Type.Literal("done")]),
          validation_method: Type.Optional(Type.String()),
          consensus_score: Type.Optional(Type.Number()),
        }),
      },
      {
        canonicalId: "documents.create",
        toolName: "istara_create_document",
        label: "Create Document",
        description: "Create an Istara document envelope for a project-scoped source.",
        parameters: Type.Object({
          title: Type.String({ minLength: 1 }),
          source: Type.Optional(Type.String()),
          file_name: Type.Optional(Type.String()),
          description: Type.Optional(Type.String()),
          content: Type.Optional(Type.String()),
          tags: Type.Optional(Type.Array(Type.String())),
          phase: Type.Optional(Type.String()),
        }),
      },
      {
        canonicalId: "documents.search",
        toolName: "istara_search_documents",
        label: "Search Documents",
        description: "Search project-scoped Istara document envelopes and content.",
        parameters: Type.Object({
          query: Type.String({ minLength: 1 }),
          phase: Type.Optional(Type.String()),
          tag: Type.Optional(Type.String()),
          limit: Type.Optional(Type.Number()),
        }),
      },
      {
        canonicalId: "documents.read",
        toolName: "istara_read_document",
        label: "Read Document",
        description: "Read one Istara document envelope and exact content span by id.",
        parameters: Type.Object({
          documentId: Type.String({ minLength: 1 }),
          span: Type.Optional(Type.String()),
        }),
      },
      {
        canonicalId: "findings.create",
        toolName: "istara_create_finding",
        label: "Create Finding",
        description: "Create a project-scoped Istara finding through the canonical facade.",
        parameters: Type.Object({
          title: Type.String({ minLength: 1 }),
          severity: Type.Union([Type.Literal("low"), Type.Literal("medium"), Type.Literal("high")]),
          evidence: Type.String({ minLength: 1 }),
          source_document_ids: Type.Optional(Type.Array(Type.String())),
          research_step_ids: Type.Optional(Type.Array(Type.String())),
        }),
      },
      {
        canonicalId: "memory.search",
        toolName: "istara_search_memory",
        label: "Search Memory",
        description: "Search Istara-owned memory and return scoped matches to the Pi loop.",
        parameters: Type.Object({
          query: Type.String({ minLength: 1 }),
          scope: Type.Optional(Type.Union([Type.Literal("project"), Type.Literal("user")])),
        }),
      },
      {
        canonicalId: "memory.write",
        toolName: "istara_write_memory",
        label: "Write Memory",
        description: "Persist a scoped Istara memory note through the canonical adapter.",
        parameters: Type.Object({
          text: Type.String({ minLength: 1 }),
          scope: Type.Optional(Type.Union([Type.Literal("project"), Type.Literal("user")])),
          tags: Type.Optional(Type.Array(Type.String())),
        }),
      },
      {
        canonicalId: "plans.create",
        toolName: "istara_create_research_plan",
        label: "Create Research Plan",
        description: "Create a DAG-like research plan attached to an Istara task.",
        parameters: Type.Object({
          taskId: Type.String({ minLength: 1 }),
          steps: Type.Array(Type.Object({
            id: Type.String({ minLength: 1 }),
            description: Type.String({ minLength: 1 }),
            depends_on: Type.Optional(Type.Array(Type.String())),
          })),
        }),
      },
      {
        canonicalId: "skills.apply",
        toolName: "istara_apply_skill",
        label: "Apply Skill",
        description: "Run one of the capped Istara skill adapters in the Pi-owned loop.",
        parameters: Type.Object({
          skillId: Type.Union([
            Type.Literal("competitive-analysis"),
            Type.Literal("thematic-analysis"),
            Type.Literal("research-synthesis"),
          ]),
          input: Type.String({ minLength: 1 }),
        }),
      },
      {
        canonicalId: "a2a.delegate",
        toolName: "istara_delegate_agent",
        label: "Delegate Agent",
        description: "Record an Istara A2A delegation request through canonical policy checks.",
        parameters: Type.Object({
          agentRole: Type.String({ minLength: 1 }),
          instruction: Type.String({ minLength: 1 }),
        }),
      },
      {
        canonicalId: "a2a.report",
        toolName: "istara_record_a2a_report",
        label: "Record A2A Report",
        description: "Record a layered A2A report envelope with MECE and executive-summary fields.",
        parameters: Type.Object({
          layer: Type.Number(),
          executive_summary: Type.String({ minLength: 1 }),
          mece_categories: Type.Array(Type.String()),
        }),
      },
      {
        canonicalId: "channels.create",
        toolName: "istara_create_channel",
        label: "Create Channel",
        description: "Create a simulated Istara channel instance without real credentials.",
        parameters: Type.Object({
          platform: Type.Union([Type.Literal("telegram"), Type.Literal("slack"), Type.Literal("whatsapp"), Type.Literal("google_chat")]),
          name: Type.String({ minLength: 1 }),
        }),
      },
      {
        canonicalId: "channels.receive",
        toolName: "istara_receive_channel_message",
        label: "Receive Channel Message",
        description: "Record an inbound channel message that Pi must handle through the session loop.",
        parameters: Type.Object({
          channelId: Type.String({ minLength: 1 }),
          externalUserId: Type.String({ minLength: 1 }),
          text: Type.String({ minLength: 1 }),
        }),
      },
      {
        canonicalId: "channels.respond",
        toolName: "istara_respond_channel_message",
        label: "Respond Channel Message",
        description: "Record an outbound channel response envelope.",
        parameters: Type.Object({
          channelId: Type.String({ minLength: 1 }),
          inReplyTo: Type.String({ minLength: 1 }),
          text: Type.String({ minLength: 1 }),
        }),
      },
      {
        canonicalId: "evals.emit_structured",
        toolName: "istara_emit_structured_eval",
        label: "Emit Structured Eval",
        description: "Emit a structured-output artifact compatible with Istara core eval checks.",
        parameters: Type.Object({
          caseId: Type.String({ minLength: 1 }),
          payload: Type.Any(),
        }),
      },
      {
        canonicalId: "research.record_step",
        toolName: "istara_record_research_spine_step",
        label: "Record Research Step",
        description: "Record one source-grounded research-spine step and its quality signals.",
        parameters: Type.Object({
          step: Type.Union([
            Type.Literal("source"),
            Type.Literal("evidence_unit"),
            Type.Literal("atomic_extraction"),
            Type.Literal("open_coding"),
            Type.Literal("reliability"),
            Type.Literal("reconciliation"),
            Type.Literal("accepted_atom"),
            Type.Literal("fact"),
            Type.Literal("insight"),
            Type.Literal("recommendation"),
            Type.Literal("review"),
          ]),
          artifact_id: Type.String({ minLength: 1 }),
          source_document_id: Type.Optional(Type.String()),
          source_span: Type.Optional(Type.String()),
          grounding_status: Type.Union([
            Type.Literal("source_grounded"),
            Type.Literal("candidate_only"),
            Type.Literal("validated"),
            Type.Literal("blocked"),
          ]),
          quality_score: Type.Optional(Type.Number()),
          notes: Type.Optional(Type.String()),
        }),
      },
      {
        canonicalId: "telemetry.record_metric",
        toolName: "istara_record_telemetry_metric",
        label: "Record Telemetry Metric",
        description: "Record Istara-shaped telemetry emitted by the Pi-owned loop.",
        parameters: Type.Object({
          name: Type.String({ minLength: 1 }),
          value: Type.Number(),
          unit: Type.Optional(Type.String()),
          labels: Type.Optional(Type.Any()),
        }),
      },
      {
        canonicalId: "autoresearch.propose_experiment",
        toolName: "istara_propose_autoresearch_experiment",
        label: "Propose Autoresearch Experiment",
        description: "Record a governed Istara Autoresearch experiment proposal without mutating production state.",
        parameters: Type.Object({
          loop_type: Type.Union([
            Type.Literal("skill_prompt"),
            Type.Literal("model_temp"),
            Type.Literal("rag_params"),
            Type.Literal("persona"),
            Type.Literal("question_bank"),
            Type.Literal("ui_sim"),
          ]),
          target: Type.String({ minLength: 1 }),
          metric: Type.String({ minLength: 1 }),
          max_iterations: Type.Optional(Type.Number()),
          project_id: Type.Optional(Type.String()),
          report_evidence: Type.Optional(Type.Boolean()),
        }),
      },
      {
        canonicalId: "autoresearch.record_measurement",
        toolName: "istara_record_autoresearch_measurement",
        label: "Record Autoresearch Measurement",
        description: "Attach sandboxed measurement output to a governed Autoresearch proposal.",
        parameters: Type.Object({
          experimentId: Type.String({ minLength: 1 }),
          baseline_score: Type.Number(),
          candidate_score: Type.Number(),
          delta: Type.Optional(Type.Number()),
          kept: Type.Optional(Type.Boolean()),
          notes: Type.Optional(Type.String()),
        }),
      },
      {
        canonicalId: "reasoning_bank.store",
        toolName: "istara_store_reasoning_memory",
        label: "Store Reasoning Memory",
        description: "Store a project-scoped process memory item that remains separate from report evidence.",
        parameters: Type.Object({
          title: Type.String({ minLength: 1 }),
          content: Type.String({ minLength: 1 }),
          source_kind: Type.Optional(Type.String()),
          outcome: Type.Optional(Type.String()),
          tags: Type.Optional(Type.Array(Type.String())),
          confidence: Type.Optional(Type.Number()),
          evidence_refs: Type.Optional(Type.Array(Type.Any())),
        }),
      },
      {
        canonicalId: "reasoning_bank.retrieve",
        toolName: "istara_retrieve_reasoning_memory",
        label: "Retrieve Reasoning Memory",
        description: "Retrieve process-memory candidates from the canonical ReasoningBank adapter.",
        parameters: Type.Object({
          query: Type.String({ minLength: 1 }),
          source_kinds: Type.Optional(Type.Array(Type.String())),
          limit: Type.Optional(Type.Number()),
        }),
      },
      {
        canonicalId: "memento.record_skill_memory",
        toolName: "istara_record_memento_skill_memory",
        label: "Record Memento Skill Memory",
        description: "Record a governed Memento-style skill memory candidate without learning from raw tool success alone.",
        parameters: Type.Object({
          skillId: Type.String({ minLength: 1 }),
          lesson: Type.String({ minLength: 1 }),
          governance_status: Type.Union([
            Type.Literal("candidate"),
            Type.Literal("validated"),
            Type.Literal("rejected"),
          ]),
          evidence_handle: Type.Optional(Type.String()),
          quality_score: Type.Optional(Type.Number()),
        }),
      },
      {
        canonicalId: "webhooks.receive",
        toolName: "istara_receive_webhook_event",
        label: "Receive Webhook Event",
        description: "Record a signed inbound webhook envelope for Telegram-like channel lifecycle tests.",
        parameters: Type.Object({
          platform: Type.Union([
            Type.Literal("telegram"),
            Type.Literal("whatsapp"),
            Type.Literal("google_chat"),
          ]),
          instanceId: Type.String({ minLength: 1 }),
          externalEventId: Type.String({ minLength: 1 }),
          signatureVerified: Type.Boolean(),
          replayAccepted: Type.Optional(Type.Boolean()),
          text: Type.String({ minLength: 1 }),
        }),
      },
      {
        canonicalId: "steering.queue",
        toolName: "istara_queue_steering_message",
        label: "Queue Steering Message",
        description: "Record a project-scoped steering, follow-up, or abort message for the Pi-owned loop.",
        parameters: Type.Object({
          agentId: Type.String({ minLength: 1 }),
          message: Type.String({ minLength: 1 }),
          kind: Type.Union([
            Type.Literal("steering"),
            Type.Literal("follow_up"),
            Type.Literal("abort"),
          ]),
          projectId: Type.Optional(Type.String()),
          mode: Type.Optional(Type.String()),
        }),
      },
      {
        canonicalId: "system_prompt.audit",
        toolName: "istara_audit_system_prompt",
        label: "Audit System Prompt",
        description: "Check whether a candidate prompt preserves Istara's protected loop and research-spine policy blocks.",
        parameters: Type.Object({
          prompt_name: Type.String({ minLength: 1 }),
          required_policy: Type.String({ minLength: 1 }),
          observed_text: Type.String({ minLength: 1 }),
          canonical_tools_only: Type.Boolean(),
          local_models_allowed: Type.Boolean(),
          protected_blocks_present: Type.Boolean(),
        }),
      },
      {
        canonicalId: "benchmarks.map_contract",
        toolName: "istara_map_benchmark_contract",
        label: "Map Benchmark Contract",
        description: "Map Istara benchmark/eval/real-user contracts to candidate bridge scenarios and metrics.",
        parameters: Type.Object({
          harnessPath: Type.String({ minLength: 1 }),
          featureId: Type.String({ minLength: 1 }),
          metrics: Type.Array(Type.String()),
          scenarioIds: Type.Array(Type.String()),
        }),
      },
      {
        canonicalId: "models.route",
        toolName: "istara_record_model_route",
        label: "Record Model Route",
        description: "Record the model/provider route selected for a candidate step.",
        parameters: Type.Object({
          step: Type.String({ minLength: 1 }),
          provider: Type.Union([Type.Literal("deepseek"), Type.Literal("faux")]),
          model: Type.String({ minLength: 1 }),
          reason: Type.String({ minLength: 1 }),
          local_models_allowed: Type.Optional(Type.Boolean()),
        }),
      },
    ];
  }

  toPiAgentTools() {
    return this.getToolDefinitions().map((definition) => ({
      name: definition.toolName,
      label: definition.label,
      description: definition.description,
      parameters: definition.parameters,
      execute: async (toolCallId, params) => {
        const result = this.call(definition.toolName, params, { toolCallId });
        return textResult(JSON.stringify(result), result, false);
      },
    }));
  }

  validate(toolName, args) {
    const definition = this.getToolDefinitions().find((tool) => tool.toolName === toolName);
    if (!definition) {
      return errorEnvelope("unknown", "unsupported_tool", `Unsupported canonical tool: ${toolName}`);
    }
    try {
      validateToolCall(
        [{ name: definition.toolName, description: definition.description, parameters: definition.parameters }],
        { type: "toolCall", id: "validation", name: toolName, arguments: args ?? {} },
      );
      return successEnvelope(definition.canonicalId, { args: jsonClone(args ?? {}) });
    } catch (error) {
      return errorEnvelope(definition.canonicalId, "invalid_arguments", error.message);
    }
  }

  call(toolName, args, metadata = {}) {
    const startedAt = Date.now();
    const validation = this.validate(toolName, args);
    if (!validation.ok) {
      this.recordCall({ toolName, canonicalId: validation.action, ok: false, error: validation.error, metadata, startedAt });
      return validation;
    }

    const definition = this.getToolDefinitions().find((tool) => tool.toolName === toolName);
    const action = definition.canonicalId;
    let data;
    if (action === "tasks.create") {
      data = {
        id: `task-${this.tasks.length + 1}`,
        projectId: this.projectId,
        title: args.title,
        description: args.description ?? "",
        priority: args.priority ?? "normal",
        instructions: args.instructions ?? "",
        urls: args.urls ?? [],
        input_document_ids: args.input_document_ids ?? [],
        output_document_ids: args.output_document_ids ?? [],
        status: "open",
        validation_method: null,
        consensus_score: null,
        agent_notes: "",
      };
      this.tasks.push(data);
    } else if (action === "tasks.attach_document") {
      const task = this.tasks.find((item) => item.id === args.taskId);
      const document = this.documents.find((item) => item.id === args.documentId);
      if (!task || !document) {
        return this.recordError(action, "missing_reference", "Task or document id was not found.", args, metadata, startedAt);
      }
      const field = args.direction === "input" ? "input_document_ids" : "output_document_ids";
      if (!task[field].includes(document.id)) {
        task[field].push(document.id);
      }
      data = { attached: true, taskId: task.id, documentId: document.id, direction: args.direction, task };
    } else if (action === "tasks.update_lifecycle") {
      const task = this.tasks.find((item) => item.id === args.taskId);
      if (!task) {
        return this.recordError(action, "missing_task", "Task id was not found.", args, metadata, startedAt);
      }
      task.status = args.status;
      if (args.validation_method !== undefined) task.validation_method = args.validation_method;
      if (args.consensus_score !== undefined) task.consensus_score = args.consensus_score;
      data = task;
    } else if (action === "documents.create") {
      data = {
        id: `document-${this.documents.length + 1}`,
        projectId: this.projectId,
        title: args.title,
        description: args.description ?? "",
        source: args.source ?? "lab_fixture",
        file_name: args.file_name ?? `${args.title.toLowerCase().replaceAll(" ", "-")}.md`,
        content: args.content ?? args.description ?? "",
        tags: args.tags ?? [],
        phase: args.phase ?? "discover",
      };
      this.documents.push(data);
    } else if (action === "documents.search") {
      const query = args.query.toLowerCase();
      const limit = args.limit ?? 5;
      const matches = this.documents
        .filter((document) => {
          const text = [document.title, document.description, document.content, document.file_name].join(" ").toLowerCase();
          const matchesQuery = text.includes(query) || query.split(/\s+/).some((term) => term && text.includes(term));
          const matchesPhase = !args.phase || document.phase === args.phase;
          const matchesTag = !args.tag || document.tags?.includes(args.tag);
          return matchesQuery && matchesPhase && matchesTag;
        })
        .slice(0, limit)
        .map((document) => ({
          id: document.id,
          title: document.title,
          source: document.source,
          file_name: document.file_name,
          phase: document.phase,
          tags: document.tags ?? [],
          snippet: (document.content || document.description || "").slice(0, 180),
        }));
      data = { query: args.query, matches };
    } else if (action === "documents.read") {
      const document = this.documents.find((item) => item.id === args.documentId);
      if (!document) {
        return this.recordError(action, "missing_document", "Document id was not found.", args, metadata, startedAt);
      }
      data = {
        document,
        span: args.span ?? "full",
        exact_text: document.content,
      };
    } else if (action === "findings.create") {
      data = {
        id: `finding-${this.findings.length + 1}`,
        projectId: this.projectId,
        title: args.title,
        severity: args.severity,
        evidence: args.evidence,
        source_document_ids: args.source_document_ids ?? [],
        research_step_ids: args.research_step_ids ?? [],
        source: "pi-owned-agent-loop",
      };
      this.findings.push(data);
    } else if (action === "memory.search") {
      const query = args.query.toLowerCase();
      data = {
        query: args.query,
        scope: args.scope ?? "project",
        matches: this.memory.filter((item) => item.text.toLowerCase().includes(query) || query.includes("istara")),
      };
    } else if (action === "memory.write") {
      data = {
        id: `mem-${this.memory.length + 1}`,
        scope: args.scope ?? "project",
        text: args.text,
        tags: args.tags ?? [],
      };
      this.memory.push(data);
    } else if (action === "plans.create") {
      const task = this.tasks.find((item) => item.id === args.taskId);
      if (!task) {
        return this.recordError(action, "missing_task", "Task id was not found.", args, metadata, startedAt);
      }
      data = {
        id: `plan-${this.plans.length + 1}`,
        projectId: this.projectId,
        taskId: args.taskId,
        status: "ready",
        steps: args.steps.map((step) => ({ ...step, depends_on: step.depends_on ?? [] })),
      };
      task.agent_notes = `Research Plan\n${JSON.stringify({ status: data.status, steps: data.steps })}`;
      this.plans.push(data);
    } else if (action === "skills.apply") {
      data = {
        id: `skill-run-${this.skillRuns.length + 1}`,
        projectId: this.projectId,
        skillId: args.skillId,
        output: `Applied ${args.skillId} to ${args.input.slice(0, 80)}`,
        lifecycle: "executed",
      };
      this.skillRuns.push(data);
    } else if (action === "a2a.delegate") {
      data = {
        id: `a2a-${this.a2aMessages.length + 1}`,
        projectId: this.projectId,
        agentRole: args.agentRole,
        instruction: args.instruction,
        state: "queued",
      };
      this.a2aMessages.push(data);
    } else if (action === "a2a.report") {
      data = {
        id: `report-${this.reports.length + 1}`,
        projectId: this.projectId,
        layer: args.layer,
        executive_summary: args.executive_summary,
        mece_categories: args.mece_categories,
      };
      this.reports.push(data);
    } else if (action === "channels.create") {
      data = {
        id: `channel-${this.channels.length + 1}`,
        projectId: this.projectId,
        platform: args.platform,
        name: args.name,
        health_status: "simulated_healthy",
        status: "stopped",
      };
      this.channels.push(data);
    } else if (action === "channels.receive") {
      const channel = this.channels.find((item) => item.id === args.channelId);
      if (!channel) {
        return this.recordError(action, "missing_channel", "Channel id was not found.", args, metadata, startedAt);
      }
      data = {
        id: `channel-message-${this.channelMessages.length + 1}`,
        projectId: this.projectId,
        channelId: args.channelId,
        direction: "inbound",
        externalUserId: args.externalUserId,
        text: args.text,
      };
      this.channelMessages.push(data);
    } else if (action === "channels.respond") {
      const channel = this.channels.find((item) => item.id === args.channelId);
      const inbound = this.channelMessages.find((item) => item.id === args.inReplyTo);
      if (!channel || !inbound) {
        return this.recordError(action, "missing_channel_message", "Channel or inbound message id was not found.", args, metadata, startedAt);
      }
      data = {
        id: `channel-message-${this.channelMessages.length + 1}`,
        projectId: this.projectId,
        channelId: args.channelId,
        direction: "outbound",
        inReplyTo: args.inReplyTo,
        text: args.text,
      };
      this.channelMessages.push(data);
    } else if (action === "evals.emit_structured") {
      data = {
        id: `eval-artifact-${this.evalArtifacts.length + 1}`,
        projectId: this.projectId,
        caseId: args.caseId,
        payload: args.payload,
        json_validity: args.payload !== null && typeof args.payload === "object",
      };
      this.evalArtifacts.push(data);
    } else if (action === "research.record_step") {
      data = {
        id: `research-step-${this.researchSteps.length + 1}`,
        projectId: this.projectId,
        step: args.step,
        artifact_id: args.artifact_id,
        source_document_id: args.source_document_id ?? null,
        source_span: args.source_span ?? null,
        grounding_status: args.grounding_status,
        quality_score: args.quality_score ?? null,
        notes: args.notes ?? "",
      };
      this.researchSteps.push(data);
    } else if (action === "telemetry.record_metric") {
      data = {
        id: `metric-${this.metrics.length + 1}`,
        projectId: this.projectId,
        name: args.name,
        value: args.value,
        unit: args.unit ?? "count",
        labels: args.labels ?? {},
      };
      this.metrics.push(data);
    } else if (action === "autoresearch.propose_experiment") {
      data = {
        id: `autoresearch-experiment-${this.autoresearchExperiments.length + 1}`,
        projectId: args.project_id ?? this.projectId,
        loop_type: args.loop_type,
        target: args.target,
        metric: args.metric,
        max_iterations: args.max_iterations ?? 1,
        status: "proposal_ready",
        sandboxed: true,
        report_evidence: args.report_evidence ?? false,
        production_mutation_allowed: false,
        governance: {
          source: "backend/app/core/autoresearch_engine.py:20",
          policy: "Experiment artifacts are governed improvement proposals, not accepted report evidence.",
        },
        measurements: [],
      };
      this.autoresearchExperiments.push(data);
    } else if (action === "autoresearch.record_measurement") {
      const experiment = this.autoresearchExperiments.find((item) => item.id === args.experimentId);
      if (!experiment) {
        return this.recordError(action, "missing_experiment", "Autoresearch experiment id was not found.", args, metadata, startedAt);
      }
      data = {
        id: `autoresearch-measurement-${experiment.measurements.length + 1}`,
        experimentId: experiment.id,
        baseline_score: args.baseline_score,
        candidate_score: args.candidate_score,
        delta: args.delta ?? args.candidate_score - args.baseline_score,
        kept: args.kept ?? args.candidate_score >= args.baseline_score,
        notes: args.notes ?? "",
        report_evidence: false,
      };
      experiment.measurements.push(data);
    } else if (action === "reasoning_bank.store") {
      data = {
        id: `reasoning-memory-${this.reasoningMemories.length + 1}`,
        projectId: this.projectId,
        title: args.title,
        content: args.content,
        source_kind: args.source_kind ?? "manual",
        outcome: args.outcome ?? "unknown",
        tags: [...new Set([...(args.tags ?? []), "process-memory-only"])],
        confidence: args.confidence ?? 0.5,
        evidence_refs: args.evidence_refs ?? [],
        report_evidence: false,
      };
      this.reasoningMemories.push(data);
    } else if (action === "reasoning_bank.retrieve") {
      const query = args.query.toLowerCase();
      const sourceKinds = new Set(args.source_kinds ?? []);
      const limit = args.limit ?? 5;
      data = {
        query: args.query,
        matches: this.reasoningMemories
          .filter((memory) => {
            const text = [memory.title, memory.content, memory.tags.join(" ")].join(" ").toLowerCase();
            const matchesQuery = text.includes(query) || query.split(/\s+/).some((term) => term && text.includes(term));
            const matchesSourceKind = sourceKinds.size === 0 || sourceKinds.has(memory.source_kind);
            return matchesQuery && matchesSourceKind;
          })
          .slice(0, limit),
      };
    } else if (action === "memento.record_skill_memory") {
      data = {
        id: `memento-skill-memory-${this.mementoSkillMemories.length + 1}`,
        projectId: this.projectId,
        skillId: args.skillId,
        lesson: args.lesson,
        governance_status: args.governance_status,
        evidence_handle: args.evidence_handle ?? "",
        quality_score: args.quality_score ?? null,
        learned_from_raw_tool_success: false,
      };
      this.mementoSkillMemories.push(data);
    } else if (action === "webhooks.receive") {
      const channel = this.channels.find((item) => item.id === args.instanceId);
      if (!channel) {
        return this.recordError(action, "missing_channel", "Webhook channel instance id was not found.", args, metadata, startedAt);
      }
      data = {
        id: `webhook-event-${this.webhookEvents.length + 1}`,
        projectId: this.projectId,
        platform: args.platform,
        instanceId: args.instanceId,
        externalEventId: args.externalEventId,
        signatureVerified: args.signatureVerified,
        replayAccepted: args.replayAccepted ?? true,
        accepted: args.signatureVerified && (args.replayAccepted ?? true),
        text: args.text,
      };
      this.webhookEvents.push(data);
    } else if (action === "steering.queue") {
      data = {
        id: `steering-event-${this.steeringEvents.length + 1}`,
        projectId: args.projectId ?? this.projectId,
        agentId: args.agentId,
        kind: args.kind,
        mode: args.mode ?? "append",
        message: args.message,
        status: args.kind === "abort" ? "abort_requested" : "queued",
      };
      this.steeringEvents.push(data);
    } else if (action === "system_prompt.audit") {
      const violations = [];
      if (!args.canonical_tools_only) violations.push("non_canonical_tools_allowed");
      if (args.local_models_allowed) violations.push("local_models_allowed");
      if (!args.protected_blocks_present) violations.push("missing_protected_policy_blocks");
      const policyText = `${args.required_policy}\n${args.observed_text}`.toLowerCase();
      if (!policyText.includes("research spine")) violations.push("missing_research_spine_language");
      data = {
        id: `system-prompt-audit-${this.systemPromptAudits.length + 1}`,
        projectId: this.projectId,
        prompt_name: args.prompt_name,
        required_policy: args.required_policy,
        canonical_tools_only: args.canonical_tools_only,
        local_models_allowed: args.local_models_allowed,
        protected_blocks_present: args.protected_blocks_present,
        violations,
        passed: violations.length === 0,
      };
      this.systemPromptAudits.push(data);
    } else if (action === "benchmarks.map_contract") {
      data = {
        id: `benchmark-contract-${this.benchmarkContracts.length + 1}`,
        projectId: this.projectId,
        harnessPath: args.harnessPath,
        featureId: args.featureId,
        metrics: args.metrics,
        scenarioIds: args.scenarioIds,
        mapped: args.metrics.length > 0 && args.scenarioIds.length > 0,
      };
      this.benchmarkContracts.push(data);
    } else if (action === "models.route") {
      data = {
        id: `model-route-${this.modelRoutes.length + 1}`,
        projectId: this.projectId,
        step: args.step,
        provider: args.provider,
        model: args.model,
        reason: args.reason,
        local_models_allowed: args.local_models_allowed ?? false,
      };
      this.modelRoutes.push(data);
    } else {
      return errorEnvelope(action, "unsupported_action", `No handler for ${action}`);
    }

    const envelope = successEnvelope(action, data);
    this.recordCall({ toolName, canonicalId: action, ok: true, args: jsonClone(args), data, metadata, startedAt });
    return envelope;
  }

  recordError(action, code, message, args, metadata, startedAt) {
    const envelope = errorEnvelope(action, code, message, { args });
    this.recordCall({ toolName: metadata.toolName ?? action, canonicalId: action, ok: false, args: jsonClone(args), error: envelope.error, metadata, startedAt });
    return envelope;
  }

  recordCall(call) {
    const durationMs = Date.now() - call.startedAt;
    const row = {
      toolName: call.toolName,
      canonicalId: call.canonicalId,
      ok: call.ok,
      args: call.args,
      data: call.data,
      error: call.error,
      metadata: call.metadata,
      durationMs,
    };
    this.calls.push(row);
    this.trace.push({
      type: "canonical_tool_call",
      projectId: this.projectId,
      canonicalId: row.canonicalId,
      ok: row.ok,
      durationMs,
      toolCallId: call.metadata?.toolCallId,
    });
    return row;
  }

  snapshot() {
    return {
      projectId: this.projectId,
      actor: this.actor,
      calls: jsonClone(this.calls),
      tasks: jsonClone(this.tasks),
      documents: jsonClone(this.documents),
      findings: jsonClone(this.findings),
      plans: jsonClone(this.plans),
      memory: jsonClone(this.memory),
      skillRuns: jsonClone(this.skillRuns),
      a2aMessages: jsonClone(this.a2aMessages),
      reports: jsonClone(this.reports),
      channels: jsonClone(this.channels),
      channelMessages: jsonClone(this.channelMessages),
      evalArtifacts: jsonClone(this.evalArtifacts),
      researchSteps: jsonClone(this.researchSteps),
      metrics: jsonClone(this.metrics),
      modelRoutes: jsonClone(this.modelRoutes),
      autoresearchExperiments: jsonClone(this.autoresearchExperiments),
      reasoningMemories: jsonClone(this.reasoningMemories),
      mementoSkillMemories: jsonClone(this.mementoSkillMemories),
      webhookEvents: jsonClone(this.webhookEvents),
      steeringEvents: jsonClone(this.steeringEvents),
      systemPromptAudits: jsonClone(this.systemPromptAudits),
      benchmarkContracts: jsonClone(this.benchmarkContracts),
      telemetry: {
        trace: jsonClone(this.trace),
        toolCallCount: this.calls.length,
        successfulToolCallCount: this.calls.filter((call) => call.ok).length,
        emittedMetricCount: this.metrics.length,
        researchStepCount: this.researchSteps.length,
        modelRouteCount: this.modelRoutes.length,
        autoresearchExperimentCount: this.autoresearchExperiments.length,
        reasoningMemoryCount: this.reasoningMemories.length,
        mementoSkillMemoryCount: this.mementoSkillMemories.length,
        webhookEventCount: this.webhookEvents.length,
        steeringEventCount: this.steeringEvents.length,
        systemPromptAuditCount: this.systemPromptAudits.length,
        benchmarkContractCount: this.benchmarkContracts.length,
      },
    };
  }
}
