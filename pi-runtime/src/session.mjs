// A single Pi runtime session: owns exactly one pi-agent-core Agent, its
// provider binding, current run, and pending authority tool calls. Maps Agent
// lifecycle events onto protocol frames and guarantees exactly one terminal
// event (run.completed | run.failed | run.aborted) per run.

import { Agent } from "@earendil-works/pi-agent-core";
import { buildProviderBinding } from "./provider.mjs";
import { buildAgentTools } from "./tools.mjs";
import { LIMITS } from "./protocol.mjs";

function nowTs() {
  return Date.now();
}

export class PiSession {
  constructor({ sessionKey, systemPrompt, history, revision, catalog, emit }) {
    this.sessionKey = sessionKey;
    this.systemPrompt = systemPrompt || "";
    this.revision = revision ?? null;
    this._emit = emit;
    this._history = (history || [])
      .slice(-LIMITS.MAX_HISTORY_MESSAGES)
      .map((m) => ({ role: m.role, content: m.content, timestamp: nowTs() }));
    this._catalog = catalog || [];
    this._binding = null; // {models, model, dispose}
    this._agent = null;
    this._pendingTools = new Map(); // tool_call_id -> resolve
    this._run = null; // {runId, terminated, aborted}
    this._tools = buildAgentTools(this._catalog, (id, name, args) => this._requestToolCall(id, name, args));
  }

  _frame(type, extra) {
    this._emit({ v: 1, type, session_key: this.sessionKey, ...extra });
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
      // Always resolve the current models collection so re-binds take effect.
      streamFn: (model, context, options) => this._binding.models.streamSimple(model, context, options),
      sessionId: this.sessionKey,
      toolExecution: "sequential",
    });
    agent.subscribe((event) => this._onAgentEvent(event));
    this._agent = agent;
  }

  _onAgentEvent(event) {
    if (!this._run) return;
    const runId = this._run.runId;
    if (event.type === "message_update") {
      const ame = event.assistantMessageEvent;
      if (ame && ame.type === "text_delta" && ame.delta) {
        this._frame("assistant.delta", { run_id: runId, text: ame.delta });
      } else if (ame && ame.type === "thinking_delta" && ame.delta) {
        this._frame("thinking.delta", { run_id: runId, text: ame.delta });
      }
    }
  }

  async prompt(runId, text) {
    if (!this._agent) {
      this._frame("run.failed", { run_id: runId, error: "no_provider_bound" });
      return;
    }
    if (this._run && !this._run.terminated) {
      this._frame("run.failed", { run_id: runId, error: "session_busy" });
      return;
    }
    this._run = { runId, terminated: false, aborted: false };
    this._frame("run.started", { run_id: runId });
    try {
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

  _settleRun(runId, err) {
    if (!this._run || this._run.runId !== runId || this._run.terminated) return;
    this._run.terminated = true;
    // Clear any pending tool calls — the run is over.
    for (const [id, resolve] of this._pendingTools) {
      resolve({ ok: false, error: "run_terminated" });
      this._pendingTools.delete(id);
    }
    const assistant = this._lastAssistant();
    const errorMessage = this._agent.state.errorMessage;
    if (this._run.aborted) {
      this._frame("run.aborted", { run_id: runId });
      return;
    }
    if (err || errorMessage || (assistant && (assistant.stopReason === "error" || assistant.stopReason === "aborted"))) {
      this._frame("run.failed", { run_id: runId, error: String(errorMessage || (err && err.message) || "run_failed") });
      return;
    }
    const usage = (assistant && assistant.usage) || {};
    this._frame("run.completed", {
      run_id: runId,
      usage: {
        input_tokens: usage.input || 0,
        output_tokens: usage.output || 0,
        cost_usd: (usage.cost && usage.cost.total) || 0,
      },
      stop_reason: (assistant && assistant.stopReason) || "stop",
    });
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
