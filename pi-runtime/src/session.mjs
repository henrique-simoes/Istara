// A single Pi runtime session: owns exactly one pi-agent-core Agent, its
// provider binding, current run, and pending authority tool calls. Maps Agent
// lifecycle events onto protocol frames and guarantees exactly one terminal
// event (run.completed | run.failed | run.aborted) per run.

import { Agent } from "@earendil-works/pi-agent-core";
import { buildProviderBinding } from "./provider.mjs";
import { buildAgentTools } from "./tools.mjs";
import { LIMITS, PROTOCOL_VERSION } from "./protocol.mjs";
import { STRUCTURED_TOOL_NAME, captureParameters, mapToolChoiceForApi, normalizeToolChoice, translateOutputSchema } from "./structured.mjs";

function nowTs() {
  return Date.now();
}

function textBlocks(content) {
  // Never mutate caller-owned history when assistant tool-call blocks are
  // appended below; a retry must receive the same immutable input messages.
  if (Array.isArray(content)) return content.map((block) => ({ ...block }));
  return [{ type: "text", text: String(content || "") }];
}

function toolCallBlock(call, index) {
  const fn = (call && call.function) || {};
  let args = fn.arguments ?? call?.arguments ?? {};
  if (typeof args === "string") {
    try { args = JSON.parse(args || "{}"); } catch { args = {}; }
  }
  return {
    type: "toolCall",
    id: String(call?.id || `legacy-tool-${index}`),
    name: String(fn.name || call?.name || ""),
    arguments: args && typeof args === "object" ? args : {},
  };
}

function providerMessages(messages) {
  return (messages || []).map((message, index) => {
    const timestamp = nowTs();
    if (message.role === "assistant") {
      const content = textBlocks(message.content);
      for (const [toolIndex, call] of (message.tool_calls || []).entries()) {
        content.push(toolCallBlock(call, `${index}-${toolIndex}`));
      }
      return {
        role: "assistant",
        content,
        api: message.api || "openai-completions",
        provider: message.provider || "istara-history",
        model: message.model || "history",
        usage: message.usage || {
          input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
        },
        stopReason: message.stop_reason || "toolUse",
        timestamp,
      };
    }
    if (message.role === "tool" || message.role === "toolResult") {
      return {
        role: "toolResult",
        toolCallId: String(message.tool_call_id || message.toolCallId || `legacy-tool-${index}`),
        toolName: String(message.name || message.toolName || "tool"),
        content: textBlocks(message.content),
        isError: Boolean(message.is_error || message.isError),
        timestamp,
      };
    }
    return { role: "user", content: textBlocks(message.content), timestamp };
  });
}

export class PiSession {
  constructor({ sessionKey, systemPrompt, history, revision, catalog, limits, emit }) {
    this.sessionKey = sessionKey;
    this.systemPrompt = systemPrompt || "";
    this.revision = revision ?? null;
    this._emit = emit;
    this._history = (history || [])
      .slice(-LIMITS.MAX_HISTORY_MESSAGES)
      .map((m) => {
        const content = typeof m.content === "string" ? [{ type: "text", text: m.content }] : (m.content || []);
        if (m.role === "assistant") {
          return {
            role: "assistant",
            content,
            api: m.api || "openai-completions",
            provider: m.provider || "istara-history",
            model: m.model || "history",
            usage: m.usage || {
              input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
              cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
            },
            stopReason: m.stop_reason || m.stopReason || "stop",
            timestamp: nowTs(),
          };
        }
        return {
          role: m.role,
          content,
          timestamp: nowTs(),
        };
      });
    this._catalog = catalog || [];
    this._limits = limits || {}; // {max_turns?, max_wall_clock_ms?, max_cost_usd?}
    this._binding = null; // {models, model, params, stream, dispose}
    this._agent = null;
    this._pendingTools = new Map(); // tool_call_id -> resolve
    this._run = null; // {runId, terminated, aborted, turns, maxTurns, budgetExceeded, forcedError}
    this._tools = buildAgentTools(this._catalog, (id, name, args) => this._requestToolCall(id, name, args));
  }

  _frame(type, extra) {
    this._emit({ v: PROTOCOL_VERSION, type, session_key: this.sessionKey, ...extra });
  }

  _requestToolCall(toolCallId, name, args) {
    if (this._pendingTools.size >= LIMITS.MAX_INFLIGHT_TOOL_CALLS) {
      return Promise.resolve({ ok: false, error: "too_many_inflight_tool_calls" });
    }
    return new Promise((resolve) => {
      this._pendingTools.set(toolCallId, resolve);
      const runId = this._run ? this._run.runId : null;
      this._frame("tool.call", { run_id: runId, tool_call_id: toolCallId, name, arguments: args });
    });
  }

  resolveToolResult(toolCallId, outcome) {
    const resolve = this._pendingTools.get(toolCallId);
    if (!resolve) return false;
    this._pendingTools.delete(toolCallId);
    resolve(outcome);
    return true;
  }

  bindProvider(endpoint) {
    const previous = this._binding;
    this._binding = buildProviderBinding(endpoint);
    if (previous && previous.dispose) previous.dispose();
    if (!this._agent) {
      this._buildAgent();
    } else {
      this._agent.state.model = this._binding.model;
    }
  }

  _buildAgent() {
    const agent = new Agent({
      initialState: {
        systemPrompt: this.systemPrompt,
        model: this._binding.model,
        thinkingLevel: "off",
        tools: this._tools,
        messages: this._history,
      },
      // Always resolve the current binding so re-binds take effect. The
      // binding's stream applies endpoint params (temperature/maxTokens/
      // reasoning/timeoutMs/maxRetries) and the guarded retry budget.
      streamFn: (model, context, options) => this._stream(model, context, options),
      sessionId: this.sessionKey,
      toolExecution: "sequential",
    });
    agent.subscribe((event) => this._onAgentEvent(event));
    this._agent = agent;
  }

  _onAgentEvent(event) {
    if (!this._run) return;
    const runId = this._run.runId;
    if (event.type === "turn_start") {
      // Worker-side turn budget: count turn starts within the run and abort
      // once the budget is exceeded; settlement emits run.failed with
      // turn_budget_exceeded.
      this._run.turns += 1;
      if (this._run.maxTurns !== null && this._run.turns > this._run.maxTurns) {
        this._run.budgetExceeded = true;
        if (this._agent) this._agent.abort();
      }
      return;
    }
    if (event.type === "message_update") {
      const ame = event.assistantMessageEvent;
      if (ame && ame.type === "text_delta" && ame.delta) {
        this._frame("assistant.delta", { run_id: runId, text: ame.delta });
      } else if (ame && ame.type === "thinking_delta" && ame.delta) {
        this._frame("thinking.delta", { run_id: runId, text: ame.delta });
      }
    }
  }

  /**
   * Stream one assistant turn through the current binding, injecting the
   * run's forced `toolChoice` (structured-output runs force
   * `emit_structured_output`; an explicit `tool_choice` frame value is mapped
   * per provider family at prompt time).
   */
  _stream(model, context, options) {
    const toolChoice = this._run && this._run.toolChoice;
    const merged = toolChoice ? { ...options, toolChoice } : options;
    return this._binding.stream(model, context, merged);
  }

  /**
   * Resolve the structured-output / tool-choice setup for one run. Returns
   * `{ structuredTool, toolChoice }` to install on the run, or emits a typed
   * `run.failed` and returns null when the request cannot be forced
   * (unsupported schema, invalid choice, unforceable provider family).
   */
  _prepareRunShape(runId, outputSchema, toolChoice) {
    const wantsStructured = outputSchema !== undefined && outputSchema !== null;
    let choice = null;
    if (wantsStructured) {
      choice = { kind: "tool", name: STRUCTURED_TOOL_NAME };
    } else if (toolChoice !== undefined && toolChoice !== null) {
      try {
        choice = normalizeToolChoice(toolChoice);
      } catch (err) {
        this._frame("run.failed", { run_id: runId, error: err.message });
        return null;
      }
    }
    let structuredTool = null;
    if (wantsStructured) {
      let parameters;
      try {
        parameters = translateOutputSchema(outputSchema);
      } catch (err) {
        // Typed failure BEFORE any provider call: a schema the worker cannot
        // force mechanically must never degrade into a prompt hint.
        this._frame("run.failed", { run_id: runId, error: err.message });
        return null;
      }
      structuredTool = {
        name: STRUCTURED_TOOL_NAME,
        label: "Emit structured output",
        description: "Return the final answer as a single structured object matching the requested schema.",
        // The provider sees a strict object-root schema. Agent-core validates
        // before capture and Python revalidates against the original contract.
        parameters: captureParameters(parameters),
        execute: async (_toolCallId, params) => {
          // Captured, not executed: the arguments ARE the structured artifact.
          // Nothing round-trips to the authority as a tool.call and no side
          // effect runs; Python revalidates this object against the original
          // schema on run.completed.
          if (this._run) this._run.structuredValue = params;
          return { content: [{ type: "text", text: "ok" }], details: {}, terminate: true };
        },
      };
    }
    let mapped = null;
    if (choice) {
      const api = (this._binding && this._binding.model && this._binding.model.api) || "";
      mapped = mapToolChoiceForApi(api, choice);
      if (mapped === null) {
        if (this._binding && this._binding.isReal) {
          // A real provider family we cannot force must fail closed — an
          // unforced "structured" run would silently accept free-form text.
          this._frame("run.failed", { run_id: runId, error: `tool_choice_unsupported:${api}` });
          return null;
        }
        // Faux test bindings are scripted; forcing is a no-op.
        mapped = null;
      }
    }
    return { structuredTool, toolChoice: mapped, outputSchema: wantsStructured ? outputSchema : null };
  }

  async prompt(runId, text, options = {}) {
    if (!this._agent) {
      this._frame("run.failed", { run_id: runId, error: "no_provider_bound" });
      return;
    }
    if (this._run && !this._run.terminated) {
      this._frame("run.failed", { run_id: runId, error: "session_busy" });
      return;
    }
    const { maxTurns, outputSchema, toolChoice } = options || {};
    const shape = this._prepareRunShape(runId, outputSchema, toolChoice);
    if (shape === null) return; // typed run.failed already emitted
    const effectiveMaxTurns = Number.isInteger(maxTurns) && maxTurns > 0 ? maxTurns
      : Number.isInteger(this._limits.max_turns) && this._limits.max_turns > 0 ? this._limits.max_turns
      : null;
    const maxWallClockMs = Number.isFinite(this._limits.max_wall_clock_ms) && this._limits.max_wall_clock_ms > 0
      ? this._limits.max_wall_clock_ms : null;
    // Cost is enforced cumulatively over the whole run: record where this run's
    // assistant messages begin so settlement sums every turn's usage, not just
    // the final assistant message (a tool loop emits several).
    const startMessageCount = (this._agent && this._agent.state.messages.length) || 0;
    this._run = {
      runId,
      terminated: false,
      aborted: false,
      turns: 0,
      maxTurns: effectiveMaxTurns,
      budgetExceeded: false,
      forcedError: null,
      timeout: null,
      startMessageCount,
      outputSchema: shape.outputSchema,
      structuredValue: undefined,
      toolChoice: shape.toolChoice,
    };
    if (shape.structuredTool) {
      // Install the forced capture tool ahead of the catalog for this run only
      // (shadowing any catalog name collision); _settleRun restores the list.
      this._agent.state.tools = [
        shape.structuredTool,
        ...this._tools.filter((tool) => tool.name !== STRUCTURED_TOOL_NAME),
      ];
      this._run.structuredToolInstalled = true;
    }
    if (maxWallClockMs !== null) {
      this._run.timeout = setTimeout(() => this.failActiveRun("wall_clock_budget_exceeded"), maxWallClockMs);
    }
    this._frame("run.started", { run_id: runId });
    try {
      // Used only by the deterministic faux provider to regression-test the
      // Python authority boundary against a compromised worker.  It is not a
      // real-provider capability and executes through the ordinary protocol.
      for (const call of this._binding.forcedToolCalls || []) {
        await this._requestToolCall(`forced-${runId}-${call.name}`, call.name, call.arguments || {});
      }
      await this._agent.prompt(text);
      this._settleRun(runId);
    } catch (err) {
      this._settleRun(runId, err);
    }
  }

  /**
   * Execute exactly one provider turn without entering pi-agent-core's tool
   * loop. This is the compatibility primitive for Istara's legacy ReAct loop:
   * Pi still owns endpoint/model binding, retries, accounting and secrets, but
   * raw tool calls return to the outer legacy loop for execution exactly once.
   */
  async providerTurn(runId, messages, tools = []) {
    if (!this._binding) {
      this._frame("run.failed", { run_id: runId, error: "no_provider_bound" });
      return;
    }
    if (this._run && !this._run.terminated) {
      this._frame("run.failed", { run_id: runId, error: "session_busy" });
      return;
    }
    const controller = new AbortController();
    const maxWallClockMs = Number.isFinite(this._limits.max_wall_clock_ms) && this._limits.max_wall_clock_ms > 0
      ? this._limits.max_wall_clock_ms : null;
    this._run = {
      runId,
      terminated: false,
      aborted: false,
      directProvider: true,
      controller,
      timeout: null,
    };
    if (maxWallClockMs !== null) {
      this._run.timeout = setTimeout(() => {
        if (this._run && this._run.runId === runId && !this._run.terminated) {
          this._run.forcedError = "wall_clock_budget_exceeded";
          controller.abort();
        }
      }, maxWallClockMs);
    }
    this._frame("run.started", { run_id: runId });
    let terminalMessage = null;
    try {
      const stream = this._binding.stream(
        this._binding.model,
        {
          systemPrompt: this.systemPrompt,
          messages: providerMessages(messages),
          tools: Array.isArray(tools) ? tools : [],
        },
        { signal: controller.signal },
      );
      for await (const event of stream) {
        if (event.type === "text_delta" && event.delta) {
          this._frame("assistant.delta", { run_id: runId, text: event.delta });
        } else if (event.type === "thinking_delta" && event.delta) {
          this._frame("thinking.delta", { run_id: runId, text: event.delta });
        } else if (event.type === "done") {
          terminalMessage = event.message;
        } else if (event.type === "error") {
          terminalMessage = event.error;
        }
      }
    } catch (err) {
      if (this._run && !this._run.forcedError) this._run.forcedError = String(err?.message || "provider_turn_failed");
    }
    if (!this._run || this._run.runId !== runId || this._run.terminated) return;
    this._run.terminated = true;
    if (this._run.timeout) clearTimeout(this._run.timeout);
    if (this._run.forcedError) {
      this._frame("run.failed", { run_id: runId, error: this._run.forcedError });
      return;
    }
    if (this._run.aborted) {
      this._frame("run.aborted", { run_id: runId });
      return;
    }
    if (!terminalMessage || terminalMessage.stopReason === "error" || terminalMessage.stopReason === "aborted") {
      this._frame("run.failed", {
        run_id: runId,
        error: String(terminalMessage?.errorMessage || "provider_turn_failed"),
      });
      return;
    }
    const usage = terminalMessage.usage || {};
    const runUsage = {
      input: usage.input || 0,
      output: usage.output || 0,
      cacheRead: usage.cacheRead || 0,
      cacheWrite: usage.cacheWrite || 0,
      cost: (usage.cost && usage.cost.total) || 0,
    };
    const scriptedCost = Number.isFinite(this._binding.forcedCostUsd)
      ? this._binding.forcedCostUsd : null;
    const costUsd = scriptedCost !== null ? scriptedCost : runUsage.cost;
    if (Number.isFinite(this._limits.max_cost_usd)) {
      if (scriptedCost === null && this._binding.isReal && this._hasUnpricedSpend(runUsage)) {
        this._frame("run.failed", { run_id: runId, error: "cost_budget_unpriced" });
        return;
      }
      if (costUsd > this._limits.max_cost_usd) {
        this._frame("run.failed", { run_id: runId, error: "cost_budget_exceeded" });
        return;
      }
    }
    this._frame("run.completed", {
      run_id: runId,
      usage: {
        input_tokens: runUsage.input,
        output_tokens: runUsage.output,
        cache_read: runUsage.cacheRead,
        cache_write: runUsage.cacheWrite,
        total_tokens: runUsage.input + runUsage.output + runUsage.cacheRead + runUsage.cacheWrite,
        cost_usd: costUsd,
        turns: 1,
      },
      stop_reason: terminalMessage.stopReason || "stop",
      // `model` on pi-ai's assistant message is the configured request model;
      // `responseModel` is the provider-reported identity captured by the
      // binding's fetch observer. Keep the two meanings separate so Research
      // Spine ensemble coding never treats a request label as proof of service.
      ...(terminalMessage.responseModel ? { served_model: terminalMessage.responseModel } : {}),
      provider_message: terminalMessage,
    });
  }

  async followUp(runId, text) {
    if (!this._agent) return;
    this._agent.followUp({ role: "user", content: text, timestamp: nowTs() });
  }

  async steer(runId, text) {
    if (!this._agent) return;
    this._agent.steer({ role: "user", content: text, timestamp: nowTs() });
  }

  abort(runId) {
    if (this._run && this._run.runId === runId) {
      this._run.aborted = true;
    }
    if (this._agent) this._agent.abort();
    if (this._run && this._run.directProvider && this._run.controller) {
      this._run.controller.abort();
    }
  }

  /**
   * Terminate the active run with a run-scoped failure (used for inbound
   * protocol violations that cannot be attributed finer than the session).
   * Returns true when a run was actually terminated.
   */
  failActiveRun(error) {
    if (!this._run || this._run.terminated) return false;
    const runId = this._run.runId;
    this._run.forcedError = error;
    if (this._run.directProvider && this._run.controller) {
      this._run.terminated = true;
      if (this._run.timeout) clearTimeout(this._run.timeout);
      this._run.controller.abort();
      this._frame("run.failed", { run_id: runId, error });
      return true;
    }
    if (this._agent) this._agent.abort();
    this._settleRun(runId);
    return true;
  }

  _settleRun(runId, err) {
    if (!this._run || this._run.runId !== runId || this._run.terminated) return;
    this._run.terminated = true;
    if (this._run.timeout) clearTimeout(this._run.timeout);
    if (this._run.structuredToolInstalled && this._agent) {
      // The forced capture tool lives only for the structured run.
      this._agent.state.tools = this._tools;
    }
    // Clear any pending tool calls — the run is over.
    for (const [id, resolve] of this._pendingTools) {
      resolve({ ok: false, error: "run_terminated" });
      this._pendingTools.delete(id);
    }
    const assistant = this._lastAssistant();
    // The agent may already be gone (concurrent session.close); never deref it blindly.
    const errorMessage = this._agent ? this._agent.state.errorMessage : null;
    if (this._run.budgetExceeded) {
      this._frame("run.failed", { run_id: runId, error: "turn_budget_exceeded" });
      return;
    }
    if (this._run.forcedError) {
      this._frame("run.failed", { run_id: runId, error: this._run.forcedError });
      return;
    }
    if (this._run.aborted) {
      this._frame("run.aborted", { run_id: runId });
      return;
    }
    if (err || errorMessage || (assistant && (assistant.stopReason === "error" || assistant.stopReason === "aborted"))) {
      this._frame("run.failed", { run_id: runId, error: String(errorMessage || (err && err.message) || "run_failed") });
      return;
    }
    // Cumulative per-run usage: sum every assistant message this run produced
    // (input/output tokens and priced cost), not just the last turn.
    const runUsage = this._runUsage();
    // Real bindings price usage via the provider model rates; faux test bindings
    // can script a deterministic per-run cost (forcedCostUsd) so the cost
    // ceiling has a behavioral regression. Production bindings never set it.
    const scriptedCost = this._binding && Number.isFinite(this._binding.forcedCostUsd) ? this._binding.forcedCostUsd : null;
    const costUsd = scriptedCost !== null ? scriptedCost : runUsage.cost;
    if (Number.isFinite(this._limits.max_cost_usd)) {
      // Fail closed: pi-ai prices each usage category (input/output/cacheRead/
      // cacheWrite) independently, so a real binding must carry a trustworthy
      // positive rate for every category it actually spent tokens in. A category
      // spent at a $0 rate (e.g. cache reads on an endpoint priced only for
      // input/output, or an entirely unpriced endpoint) prices that usage at $0,
      // which cannot prove the run stayed within budget. Completing it would be
      // fail-open, so surface the misconfiguration as a terminal.
      if (scriptedCost === null && this._binding && this._binding.isReal && this._hasUnpricedSpend(runUsage)) {
        this._frame("run.failed", { run_id: runId, error: "cost_budget_unpriced" });
        return;
      }
      if (costUsd > this._limits.max_cost_usd) {
        this._frame("run.failed", { run_id: runId, error: "cost_budget_exceeded" });
        return;
      }
    }
    if (this._run.outputSchema) {
      // Forced structured contract: the run only succeeds when the model's
      // emit_structured_output call was captured. Free-form JSON text (or a
      // missing/incorrect tool call) is NEVER accepted as structured output —
      // it settles as a typed failure and Python may schedule its one bounded
      // repair.
      if (this._run.structuredValue === undefined) {
        this._frame("run.failed", { run_id: runId, error: "structured_output_missing" });
        return;
      }
      this._frame("run.completed", {
        run_id: runId,
        usage: this._completedUsage(runUsage, costUsd),
        stop_reason: (assistant && assistant.stopReason) || "stop",
        ...(assistant?.responseModel ? { served_model: assistant.responseModel } : {}),
        structured: this._run.structuredValue,
      });
      return;
    }
    this._frame("run.completed", {
      run_id: runId,
      usage: this._completedUsage(runUsage, costUsd),
      stop_reason: (assistant && assistant.stopReason) || "stop",
      ...(assistant?.responseModel ? { served_model: assistant.responseModel } : {}),
    });
  }

  /**
   * Build the terminal usage block for run.completed. The ledger records exact
   * per-run accounting, so this carries the full cumulative usage pi-ai reports
   * across every assistant turn — input AND output tokens, the cache-read and
   * cache-write tokens (which the ledger prices and audits separately), the
   * summed total, the priced cost, and the actual turn count. Emitting only
   * input/output/cost would silently drop cache usage and record every
   * multi-turn tool loop as a single turn.
   */
  _completedUsage(runUsage, costUsd) {
    const turns = this._run && Number.isInteger(this._run.turns) ? this._run.turns : 0;
    return {
      input_tokens: runUsage.input,
      output_tokens: runUsage.output,
      cache_read: runUsage.cacheRead,
      cache_write: runUsage.cacheWrite,
      total_tokens: runUsage.input + runUsage.output + runUsage.cacheRead + runUsage.cacheWrite,
      cost_usd: costUsd,
      turns,
    };
  }

  /**
   * Sum the usage of every assistant message produced during the active run
   * (from the message index captured at prompt start). A tool loop emits one
   * assistant message per turn, each with its own usage, so the per-run cost
   * ceiling must aggregate them rather than reading only the final turn.
   */
  _runUsage() {
    const messages = (this._agent && this._agent.state.messages) || [];
    const start = this._run && Number.isInteger(this._run.startMessageCount) ? this._run.startMessageCount : 0;
    let input = 0;
    let output = 0;
    let cacheRead = 0;
    let cacheWrite = 0;
    let cost = 0;
    for (let i = start; i < messages.length; i++) {
      const message = messages[i];
      if (!message || message.role !== "assistant") continue;
      const usage = message.usage || {};
      input += usage.input || 0;
      output += usage.output || 0;
      cacheRead += usage.cacheRead || 0;
      cacheWrite += usage.cacheWrite || 0;
      cost += (usage.cost && usage.cost.total) || 0;
    }
    return { input, output, cacheRead, cacheWrite, cost };
  }

  /**
   * True when a real run spent tokens in a usage category whose per-million-token
   * rate is not a trustworthy positive number. pi-ai prices input, output, cache
   * reads, and cache writes independently, so any spent-but-$0-rated category
   * (including an entirely unpriced binding) makes the computed cost an
   * untrustworthy under-count that cannot prove the run stayed within budget.
   */
  _hasUnpricedSpend(runUsage) {
    const rates = (this._binding && this._binding.pricing) || {};
    for (const category of ["input", "output", "cacheRead", "cacheWrite"]) {
      if ((runUsage[category] || 0) > 0 && !(rates[category] > 0)) return true;
    }
    return false;
  }

  _lastAssistant() {
    const messages = (this._agent && this._agent.state.messages) || [];
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i];
    }
    return null;
  }

  async close() {
    if (this._run && this._run.directProvider && !this._run.terminated && this._run.controller) {
      this._run.aborted = true;
      this._run.controller.abort();
    }
    if (this._agent && this._run && !this._run.terminated) {
      this._agent.abort();
      try {
        await this._agent.waitForIdle();
      } catch {
        /* best-effort */
      }
    }
    for (const [id, resolve] of this._pendingTools) {
      resolve({ ok: false, error: "session_closed" });
      this._pendingTools.delete(id);
    }
    if (this._binding && this._binding.dispose) this._binding.dispose();
    this._binding = null;
    this._agent = null;
  }
}
