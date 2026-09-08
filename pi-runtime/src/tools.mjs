// Dynamic tool construction for the Pi runtime worker.
//
// The authoritative tool catalog is exported from Python at `session.open`
// (name + description + JSON-Schema parameters). The worker builds a real
// pi-agent-core tool per entry whose `execute` round-trips to Python: it asks
// the session to emit a `tool.call` frame and awaits the matching `tool.result`.
// No tool schema is hand-maintained in the worker — drift is a Python-side
// contract test concern, and every argument is re-validated by Istara authority.

import { LIMITS } from "./protocol.mjs";

/**
 * @param {Array<{name, description, parameters}>} catalog
 * @param {(toolCallId: string, name: string, args: unknown) => Promise<{ok: boolean, result?: unknown, error?: string}>} requestToolCall
 */
export function buildAgentTools(catalog, requestToolCall) {
  return (catalog || []).map((entry) => ({
    name: entry.name,
    label: entry.name,
    description: entry.description || entry.name,
    // pi-agent-core accepts a raw JSON Schema object as `parameters` and
    // validates model-supplied arguments against it before `execute`.
    parameters: entry.parameters || { type: "object", properties: {}, additionalProperties: true },
    execute: async (toolCallId, params, signal) => {
      // Honour the AbortSignal pi-agent-core passes as the third argument
      // (agent-loop.js): session.close() aborts the run, and an in-flight
      // tool must settle instead of waiting forever for a tool.result frame
      // that will never arrive. Both paths report a structured authority
      // error so the run continues and is audited — never a throw.
      if (signal?.aborted) {
        const errorText = JSON.stringify({ error: "tool_aborted" });
        return { content: [{ type: "text", text: errorText }], details: { error: "tool_aborted" } };
      }
      const serialized = JSON.stringify(params ?? {});
      if (Buffer.byteLength(serialized, "utf8") > LIMITS.MAX_TOOL_ARGS_BYTES) {
        return {
          content: [{ type: "text", text: JSON.stringify({ error: "tool_arguments_too_large" }) }],
          details: { error: "tool_arguments_too_large" },
        };
      }
      let onAbort;
      const abortPromise = signal
        ? new Promise((resolve) => {
            onAbort = () => resolve({ ok: false, error: "tool_aborted" });
            signal.addEventListener("abort", onAbort, { once: true });
          })
        : null;
      let outcome;
      try {
        outcome = abortPromise
          ? await Promise.race([requestToolCall(toolCallId, entry.name, params ?? {}), abortPromise])
          : await requestToolCall(toolCallId, entry.name, params ?? {});
      } finally {
        if (signal && onAbort) signal.removeEventListener?.("abort", onAbort);
      }
      if (outcome && outcome.ok) {
        const text = typeof outcome.result === "string" ? outcome.result : JSON.stringify(outcome.result ?? {});
        return { content: [{ type: "text", text }], details: outcome.result ?? {} };
      }
      // Structured authority error: surfaced to the model as tool content so the
      // run continues and is audited — it never throws across the pipe or kills
      // the session.
      const errorText = JSON.stringify({ error: (outcome && outcome.error) || "tool_execution_failed" });
      return { content: [{ type: "text", text: errorText }], details: { error: (outcome && outcome.error) || "tool_execution_failed" } };
    },
  }));
}
