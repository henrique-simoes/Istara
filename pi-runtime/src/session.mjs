// A single Pi runtime session: owns exactly one pi-agent-core Agent, its
// provider binding, current run, and pending authority tool calls. Maps Agent
// lifecycle events onto protocol frames and guarantees exactly one terminal
// event (run.completed | run.failed | run.aborted) per run.

import { Agent } from "@earendil-works/pi-agent-core";
import { buildProviderBinding } from "./provider.mjs";
import { buildAgentTools } from "./tools.mjs";
import { LIMITS, PROTOCOL_VERSION } from "./protocol.mjs";

function nowTs() {
  return Date.now();
}

export class PiSession {
  constructor({ sessionKey, systemPrompt, history, revision, catalog, limits, emit }) {
    this.sessionKey = sessionKey;
    this.systemPrompt = systemPrompt || "";
    this.revision = revision ?? null;
    this._emit = emit;
    this._history = (history || [])
      .slice(-LIMITS.MAX_HISTORY_MESSAGES)
      .map((m) => ({
        role: m.role,
        // pi-agent-core message content is a block array; server-persisted
        // history arrives as plain strings, so wrap them as text blocks (a raw
        // string throws `content.map is not a function` on rehydration).
        content: typeof m.content === "string" ? [{ type: "text", text: m.content }] : (m.content || []),
        timestamp: nowTs(),
      }));
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
      streamFn: (model, context, options) => this._binding.stream(model, context, options),
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

  async prompt(runId, text, maxTurns) {
    if (!this._agent) {
      this._frame("run.failed", { run_id: runId, error: "no_provider_bound" });
      return;
    }
    if (this._run && !this._run.terminated) {
      this._frame("run.failed", { run_id: runId, error: "session_busy" });
      return;
    }
    const effectiveMaxTurns = Number.isInteger(maxTurns) && maxTurns > 0 ? maxTurns
      : Number.isInteger(this._limits.max_turns) && this._limits.max_turns > 0 ? this._limits.max_turns
      : null;
    const maxWallClockMs = Number.isFinite(this._limits.max_wall_clock_ms) && this._limits.max_wall_clock_ms > 0
      ? this._limits.max_wall_clock_ms : null;
    // Cost is enforced cumulatively over the whole run: record where this run's
    // assistant messages begin so settlement sums every turn's usage, not just
    // the final assistant message (a tool loop emits several).
    const startMessageCount = (this._agent && this._agent.state.messages.length) || 0;
    this._run = { runId, terminated: false, aborted: false, turns: 0, maxTurns: effectiveMaxTurns, budgetExceeded: false, forcedError: null, timeout: null, startMessageCount };
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
    if (this._agent) this._agent.abort();
    this._settleRun(runId);
    return true;
  }

  _settleRun(runId, err) {
    if (!this._run || this._run.runId !== runId || this._run.terminated) return;
    this._run.terminated = true;
    if (this._run.timeout) clearTimeout(this._run.timeout);
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
      // Fail closed: a real binding that spent tokens but carries no pricing
      // reports $0, which cannot prove the run stayed within budget. Completing
      // it would be fail-open, so surface the misconfiguration as a terminal.
      if (
        scriptedCost === null &&
        this._binding && this._binding.isReal && !this._binding.pricingConfigured &&
        (runUsage.input > 0 || runUsage.output > 0)
      ) {
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
        cost_usd: costUsd,
      },
      stop_reason: (assistant && assistant.stopReason) || "stop",
    });
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
    let cost = 0;
    for (let i = start; i < messages.length; i++) {
      const message = messages[i];
      if (!message || message.role !== "assistant") continue;
      const usage = message.usage || {};
      input += usage.input || 0;
      output += usage.output || 0;
      cost += (usage.cost && usage.cost.total) || 0;
    }
    return { input, output, cost };
  }

  _lastAssistant() {
    const messages = (this._agent && this._agent.state.messages) || [];
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i];
    }
    return null;
  }

  async close() {
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
