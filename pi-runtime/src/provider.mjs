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
//
// `endpoint.pricing` carries the backend-resolved model rates (USD per 1M
// tokens: input_per_mtok/output_per_mtok/cache_read_per_mtok/cache_write_per_mtok)
// onto the pi-ai model `cost` object so real usage is priced and the per-run
// cost ceiling can fail closed. A real binding with no pricing is flagged so the
// session fails a budgeted run closed rather than reporting an untrusted $0.

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
import { openAICodexResponsesApi } from "@earendil-works/pi-ai/api/openai-codex-responses.lazy";

let ENV_KEY_COUNTER = 0;

function apiForKind(kind) {
  if (kind === "openai_compat") return { api: openAICompletionsApi(), modelApi: "openai-completions" };
  if (kind === "anthropic_compat") return { api: anthropicMessagesApi(), modelApi: "anthropic-messages" };
  if (kind === "openai_codex") return { api: openAICodexResponsesApi(), modelApi: "openai-codex-responses" };
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

// pi-ai's calculateCost reads model.cost.{input,output,cacheRead,cacheWrite} as
// USD-per-million-token rates and derives usage.cost.total from them. The
// backend resolves an endpoint's trustworthy rates (operator/contract pricing)
// and passes them in `endpoint.pricing`; without them a real endpoint would
// report $0 for any usage and the per-run cost ceiling could never fail closed.
const PRICING_FIELDS = [
  ["input_per_mtok", "input"],
  ["output_per_mtok", "output"],
  ["cache_read_per_mtok", "cacheRead"],
  ["cache_write_per_mtok", "cacheWrite"],
];

/**
 * Validate endpoint.pricing and map it onto a pi-ai model `cost` object
 * (per-million-token USD rates). Unknown keys and non-finite/negative values are
 * rejected so a misconfigured price fails the bind loudly instead of silently
 * pricing usage at $0. Absent pricing yields all-zero rates; the caller reports
 * whether any positive rate was configured so the cost ceiling can fail closed.
 */
export function mapProviderPricing(pricing) {
  const cost = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
  if (pricing === undefined || pricing === null) return cost;
  if (typeof pricing !== "object") throw new Error("invalid_provider_pricing:pricing");
  const KNOWN = new Set(PRICING_FIELDS.map(([src]) => src));
  for (const key of Object.keys(pricing)) {
    if (!KNOWN.has(key)) throw new Error(`invalid_provider_pricing:${key}`);
  }
  for (const [srcKey, dstKey] of PRICING_FIELDS) {
    const value = pricing[srcKey];
    if (value === undefined || value === null) continue;
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
      throw new Error(`invalid_provider_pricing:${srcKey}`);
    }
    cost[dstKey] = value;
  }
  return cost;
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
    let buffered = [];
    let visible = false;
    const flush = () => {
      for (const event of buffered) out.push(event);
      buffered = [];
    };
    (async () => {
      try {
        // Keep provider construction inside the guarded section. Some adapters
        // throw synchronously before returning an async iterable; letting that
        // escape would leave the outer event stream unresolved and the run
        // without a terminal frame.
        const inner = models.streamSimple(model, context, options);
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
      } catch (error) {
        // pi-ai APIs normally convert failures into `error` events; a throw
        // here is a transport-level anomaly. Apply the same classifier as
        // event-shaped failures so programmer/configuration errors are not
        // retried as if they were transient provider outages.
        const errorMessage = String(error?.message || error || "provider_stream_failed");
        const retryable = isRetryableAssistantError({
          stopReason: "error",
          errorMessage,
        });
        if (!visible && attempt <= maxRetries && retryable) {
          runAttempt();
          return;
        }
        flush();
        const failure = {
          stopReason: "error",
          errorMessage,
          timestamp: Date.now(),
          content: [],
        };
        out.push({ type: "error", reason: "error", error: failure });
        out.end(failure);
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
/**
 * Strip API-unsupported controls. The OpenAI Codex Responses API rejects
 * sampling controls ("Unsupported parameter: temperature"); keep this
 * knowledge in one tested place.
 */
export function filterParamsForApi(params, modelApi) {
  if (modelApi === "openai-codex-responses") {
    return Object.fromEntries(Object.entries(params || {}).filter(([key]) => key !== "temperature"));
  }
  return { ...(params || {}) };
}

export function modelLimits(endpoint, params = {}) {
  const declaredContext = Number(endpoint?.context_window || 0);
  const declaredOutput = Number(endpoint?.max_tokens || 0);
  const requestedOutput = Number(params?.maxTokens || 0);
  const maxTokens = declaredOutput > 0
    ? declaredOutput
    : requestedOutput > 0
      ? requestedOutput
      : 4096;
  return {
    contextWindow: declaredContext > 0 ? declaredContext : Math.max(128000, maxTokens),
    maxTokens,
  };
}

/**
 * Resolve provider-specific model semantics independently from the transport
 * protocol. Pi Model Management sends its non-secret provider identity because
 * an OpenAI-compatible URL alone is insufficient: DeepSeek requires an
 * explicit `thinking: {type: "disabled"}` whenever structured extraction
 * forces a tool choice. pi-ai emits that control only for a reasoning-capable
 * model with DeepSeek compatibility.
 */
export function modelCapabilities(endpoint, modelApi) {
  if (modelApi === "openai-codex-responses") {
    return {
      reasoning: true,
      thinkingLevels: ["xhigh", "max", "minimal"],
      compat: undefined,
    };
  }
  const provider = String(endpoint?.pi_provider || "").trim().toLowerCase();
  if (provider === "deepseek") {
    return {
      reasoning: true,
      thinkingLevels: undefined,
      compat: { thinkingFormat: "deepseek" },
    };
  }
  return { reasoning: false, thinkingLevels: undefined, compat: undefined };
}

export function buildRealProvider(endpoint) {
  const { provider_kind: kind, base_url: baseUrl, model: modelId, api_key: apiKey } = endpoint;
  if (!baseUrl || !modelId || !apiKey) throw new Error("incomplete_provider_binding");
  const { api, modelApi } = apiForKind(kind);
  const params = mapProviderParams(endpoint.params);
  const wireParams = filterParamsForApi(params, modelApi);
  const maxRetries = params.maxRetries ?? 0;
  // Real model rates come from the backend-resolved endpoint pricing, not a
  // hardcoded zero — otherwise pi-ai prices every real turn at $0 and the
  // per-run cost ceiling can never fail closed (see session.mjs). pi-ai prices
  // each usage category (input/output/cacheRead/cacheWrite) independently, so
  // the session receives the full per-category rate map and fails a budgeted
  // run closed when it spent tokens in ANY category left at a $0 rate. A single
  // "some rate is set" flag would let a cache-read turn on an endpoint priced
  // only for input/output settle at an untrusted $0.
  const cost = mapProviderPricing(endpoint.pricing);
  const limits = modelLimits(endpoint, params);
  const capabilities = modelCapabilities(endpoint, modelApi);

  const providerId = `pi-endpoint-${endpoint.endpoint_id || "default"}`;
  const envVar = `PI_RUNTIME_KEY_${ENV_KEY_COUNTER++}`;
  process.env[envVar] = apiKey;

  const model = {
    id: modelId,
    name: modelId,
    api: modelApi,
    provider: providerId,
    baseUrl,
    reasoning: capabilities.reasoning,
    thinkingLevels: capabilities.thinkingLevels,
    compat: capabilities.compat,
    input: ["text"],
    cost,
    contextWindow: limits.contextWindow,
    maxTokens: limits.maxTokens,
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
    // Real network binding: usage is priced by `model.cost` above. `pricing` is
    // the per-category rate map the session checks against actual per-category
    // usage — a budgeted run that spent tokens in any $0-rated category fails
    // closed rather than reporting an untrusted under-count (see session.mjs).
    isReal: true,
    pricing: cost,
    stream: (streamModel, context, options) =>
      // Endpoint params are operator policy and win over agent defaults; the
      // agent-supplied abort signal is always preserved. wireParams excludes
      // API-unsupported controls (see above).
      streamWithGuardedRetry(models, streamModel, context, { ...options, ...wireParams }, maxRetries),
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
    // Deterministic test double, not a network binding: the cost ceiling reads
    // `forcedCostUsd` (below) rather than the unpriced-real fail-closed path.
    isReal: false,
    pricing: null,
    stream: (model, context, options) => models.streamSimple(model, context, options),
    dispose: () => {},
    // Test-only adversarial seam: lets the production Python authority
    // boundary receive a raw tool.call that is intentionally absent from the
    // worker catalog.  Real provider bindings never carry this field.
    forcedToolCalls: Array.isArray(endpoint.faux_forced_tool_calls) ? endpoint.faux_forced_tool_calls : [],
    // Test-only seam: the faux provider's usage estimate always reports zero
    // cost, so it cannot exercise the worker's per-run cost ceiling. A scripted
    // cost lets that terminal path have a deterministic behavioral regression;
    // real bindings report cost via usage and never set this field.
    forcedCostUsd: Number.isFinite(endpoint.faux_cost_usd) ? endpoint.faux_cost_usd : null,
  };
}

export function buildProviderBinding(endpoint) {
  if (endpoint.provider_kind === "faux") return buildFauxProviderBinding(endpoint);
  return buildRealProvider(endpoint);
}
