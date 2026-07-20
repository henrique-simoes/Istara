// Provider factory for the Pi runtime worker.
//
// A `provider.bind` frame supplies an exact endpoint (openai_compat or
// anthropic_compat) plus a short-lived secret. The secret is injected into the
// worker's own process environment under a per-session variable name and is
// never echoed, logged, or persisted. A `faux` kind is available for Node unit
// tests only (no network, deterministic scripted responses).
//
// `endpoint.params` carries generation/retry knobs resolved by the backend:
//   temperature    -> StreamOptions.temperature
//   max_tokens     -> StreamOptions.maxTokens
//   thinking_level -> SimpleStreamOptions.reasoning ("off" omits the field)
//   timeout_ms     -> StreamOptions.timeoutMs
//   max_retries    -> StreamOptions.maxRetries AND the worker-side retry
//                     budget (retries happen only before the first visible
//                     output event of an attempt, classified by pi-ai's
//                     isRetryableAssistantError).

import {
  createModels,
  createProvider,
  createAssistantMessageEventStream,
  envApiKeyAuth,
  isRetryableAssistantError,
  fauxProvider,
  fauxAssistantMessage,
  fauxText,
  fauxToolCall,
} from "@earendil-works/pi-ai";
import { openAICompletionsApi } from "@earendil-works/pi-ai/api/openai-completions.lazy";
import { anthropicMessagesApi } from "@earendil-works/pi-ai/api/anthropic-messages.lazy";

let ENV_KEY_COUNTER = 0;

function apiForKind(kind) {
  if (kind === "openai_compat") return { api: openAICompletionsApi(), modelApi: "openai-completions" };
  if (kind === "anthropic_compat") return { api: anthropicMessagesApi(), modelApi: "anthropic-messages" };
  throw new Error(`unsupported_provider_kind:${kind}`);
}

function requireNumber(params, key) {
  const value = params[key];
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`invalid_provider_params:${key}`);
  }
  return value;
}

/**
 * Validate endpoint.params and map it onto pi-ai StreamOptions /
 * SimpleStreamOptions fields. Unknown keys are rejected so a misspelled knob
 * fails loudly at bind time instead of being silently ignored.
 */
export function mapProviderParams(params) {
  const mapped = {};
  if (!params) return mapped;
  if (typeof params !== "object") throw new Error("invalid_provider_params:params");
  const KNOWN = new Set(["temperature", "max_tokens", "thinking_level", "timeout_ms", "max_retries"]);
  for (const key of Object.keys(params)) {
    if (!KNOWN.has(key)) throw new Error(`invalid_provider_params:${key}`);
  }
  const temperature = requireNumber(params, "temperature");
  if (temperature !== undefined) mapped.temperature = temperature;
  const maxTokens = requireNumber(params, "max_tokens");
  if (maxTokens !== undefined) mapped.maxTokens = maxTokens;
  const timeoutMs = requireNumber(params, "timeout_ms");
  if (timeoutMs !== undefined) mapped.timeoutMs = timeoutMs;
  const maxRetries = requireNumber(params, "max_retries");
  if (maxRetries !== undefined) {
    if (!Number.isInteger(maxRetries) || maxRetries < 0) throw new Error("invalid_provider_params:max_retries");
    mapped.maxRetries = maxRetries;
  }
  if (params.thinking_level !== undefined && params.thinking_level !== null) {
    if (typeof params.thinking_level !== "string") throw new Error("invalid_provider_params:thinking_level");
    // "off" exists only in agent-core's ModelThinkingLevel; for pi-ai's
    // SimpleStreamOptions.reasoning it means "omit the field".
    if (params.thinking_level !== "off") mapped.reasoning = params.thinking_level;
  }
  return mapped;
}

// Events that make an attempt's output visible to the authority: once any of
// these has been forwarded, restarting the provider call would duplicate
// user-visible output or replay tool calls, so retry is forbidden.
const VISIBLE_EVENT_TYPES = new Set(["text_delta", "thinking_delta", "toolcall_start", "toolcall_delta", "toolcall_end"]);

/**
 * Stream an assistant turn with a bounded worker-side retry budget. A retry
 * is allowed only while no visible output has been emitted for the current
 * attempt AND pi-ai's isRetryableAssistantError classifies the failure as
 * transient. Non-visible events (start/text_start/thinking_start) are
 * buffered so a restarted attempt never leaks partial state downstream.
 */
export function streamWithGuardedRetry(models, model, context, options, maxRetries = 0) {
  const out = createAssistantMessageEventStream();
  let attempt = 0;
  const runAttempt = () => {
    attempt += 1;
    const inner = models.streamSimple(model, context, options);
    let buffered = [];
    let visible = false;
    const flush = () => {
      for (const event of buffered) out.push(event);
      buffered = [];
    };
    (async () => {
      try {
        for await (const event of inner) {
          if (event.type === "error") {
            const message = event.error;
            if (!visible && attempt <= maxRetries && message && isRetryableAssistantError(message)) {
              runAttempt();
              return;
            }
            flush();
            out.push(event);
            out.end(message);
            return;
          }
          if (event.type === "done") {
            flush();
            out.push(event);
            out.end(event.message);
            return;
          }
          if (!visible && VISIBLE_EVENT_TYPES.has(event.type)) {
            visible = true;
            flush();
          }
          if (visible) out.push(event);
          else buffered.push(event);
        }
        // Stream ended without a terminal event: flush what we have.
        flush();
        out.end();
      } catch {
        // pi-ai APIs convert failures into `error` events; a throw here is a
        // transport-level anomaly. Retry only while nothing was visible.
        if (!visible && attempt <= maxRetries) {
          runAttempt();
          return;
        }
        flush();
        out.end();
      }
    })();
  };
  runAttempt();
  return out;
}

/**
 * Build the `{models, model, params, stream, dispose}` binding for a real
 * endpoint. The returned `dispose()` clears the injected secret from the
 * environment. `stream` wraps models.streamSimple with the guarded retry
 * budget from endpoint.params.max_retries.
 */
export function buildRealProvider(endpoint) {
  const { provider_kind: kind, base_url: baseUrl, model: modelId, api_key: apiKey } = endpoint;
  if (!baseUrl || !modelId || !apiKey) throw new Error("incomplete_provider_binding");
  const { api, modelApi } = apiForKind(kind);
  const params = mapProviderParams(endpoint.params);
  const maxRetries = params.maxRetries ?? 0;

  const providerId = `pi-endpoint-${endpoint.endpoint_id || "default"}`;
  const envVar = `PI_RUNTIME_KEY_${ENV_KEY_COUNTER++}`;
  process.env[envVar] = apiKey;

  const model = {
    id: modelId,
    name: modelId,
    api: modelApi,
    provider: providerId,
    baseUrl,
    reasoning: false,
    input: ["text"],
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    contextWindow: 128000,
    maxTokens: 4096,
  };
  const provider = createProvider({
    id: providerId,
    name: providerId,
    baseUrl,
    auth: { apiKey: envApiKeyAuth("Pi endpoint key", [envVar]) },
    models: [model],
    api,
  });
  const models = createModels();
  models.setProvider(provider);
  const resolved = models.getModel(providerId, modelId);
  return {
    models,
    model: resolved,
    params,
    stream: (streamModel, context, options) =>
      // Endpoint params are operator policy and win over agent defaults; the
      // agent-supplied abort signal is always preserved.
      streamWithGuardedRetry(models, streamModel, context, { ...options, ...params }, maxRetries),
    dispose: () => {
      delete process.env[envVar];
    },
  };
}

/** Convert a serialized faux-response spec into a pi-ai faux assistant message. */
function buildFauxResponse(spec) {
  if (spec.text !== undefined && !spec.tool_calls) {
    return fauxAssistantMessage(fauxText(spec.text), { stopReason: spec.stop_reason || "stop" });
  }
  const blocks = [];
  for (const call of spec.tool_calls || []) {
    blocks.push(fauxToolCall(call.name, call.arguments || {}));
  }
  if (spec.text) blocks.push(fauxText(spec.text));
  return fauxAssistantMessage(blocks, { stopReason: spec.stop_reason || "toolUse" });
}

/** Build a deterministic faux provider for Node unit tests only. */
export function buildFauxProviderBinding(endpoint) {
  const faux = fauxProvider({ tokensPerSecond: 0 });
  faux.setResponses((endpoint.faux_responses || []).map(buildFauxResponse));
  const models = createModels();
  models.setProvider(faux.provider);
  return {
    models,
    model: faux.getModel(),
    params: {},
    stream: (model, context, options) => models.streamSimple(model, context, options),
    dispose: () => {},
  };
}

export function buildProviderBinding(endpoint) {
  if (endpoint.provider_kind === "faux") return buildFauxProviderBinding(endpoint);
  return buildRealProvider(endpoint);
}
