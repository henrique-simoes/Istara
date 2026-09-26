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

import { readFileSync } from "node:fs";
import {
  createModels,
  createProvider,
  createAssistantMessageEventStream,
  envApiKeyAuth,
  getSupportedThinkingLevels,
  isRetryableAssistantError,
  fauxProvider,
  fauxAssistantMessage,
  fauxText,
  fauxToolCall,
} from "@earendil-works/pi-ai";
import { openAICompletionsApi } from "@earendil-works/pi-ai/api/openai-completions.lazy";
import { openAIResponsesApi } from "@earendil-works/pi-ai/api/openai-responses.lazy";
import { anthropicMessagesApi } from "@earendil-works/pi-ai/api/anthropic-messages.lazy";
import { openAICodexResponsesApi } from "@earendil-works/pi-ai/api/openai-codex-responses.lazy";

let ENV_KEY_COUNTER = 0;

// ---------------------------------------------------------------------------
// Capability authority (tier law, build-stream 2026-09-08
// pi-capability-inheritance §1.2):
//
//   pi-ai's generated registry is the SOLE authority for provider/model
//   capability semantics. Istara may inherit it, RESTRICT it with operator or
//   deployment truth pi-ai cannot know (tiers 1-3 restrict only — they may
//   never silently enable a capability pi-ai denies), or read it through the
//   generated catalog projection for non-worker consumers. Tiers 5-6 (Istara
//   identity fallback, pi-ai URL detection) apply only when the registry
//   misses.
//
//   A hand-written restatement of registry knowledge anywhere in this tree is
//   architecture debt and fails the architecture_drift gate.
// ---------------------------------------------------------------------------

// Memoised per-process registry accessor (plan W2.1 / S-E4). The dynamic
// import is module-registry cached, so a supervised per-session worker pays
// the ~67 ms / ~60 MB cost once per process, never per turn. `getBuiltinModel`
// and friends live at `@earendil-works/pi-ai/providers/all`, not the package
// root (G1) — do not "fix" this import path.
let piRegistryPromise = null;
export function getPiRegistry() {
  if (!piRegistryPromise) {
    piRegistryPromise = import("@earendil-works/pi-ai/providers/all").then((module) => ({
      getBuiltinModel: module.getBuiltinModel,
      registryGeneratedAt: module.getBuiltinModelDataGeneratedAt() ?? null,
    }));
  }
  return piRegistryPromise;
}

// Test-only seam: drop the memoised accessor so a test can observe a fresh
// import. Never used on production paths.
export function resetPiRegistryForTests() {
  piRegistryPromise = null;
}

let piAiVersionCache = null;
function piAiVersion() {
  if (piAiVersionCache === null) {
    for (const candidate of [
      "../node_modules/@earendil-works/pi-ai/package.json",
      "../../node_modules/@earendil-works/pi-ai/package.json",
    ]) {
      try {
        const pkg = JSON.parse(readFileSync(new URL(candidate, import.meta.url), "utf8"));
        if (pkg?.version) {
          piAiVersionCache = String(pkg.version);
          break;
        }
      } catch {
        // try next candidate
      }
    }
    if (piAiVersionCache === null) piAiVersionCache = "unknown";
  }
  return piAiVersionCache;
}

// Named, fixture-backed proxy exceptions to the typed transport-mismatch
// rejection (plan W2.6 / R10). A registry record's `api` disagreeing with the
// configured `provider_kind` transport means the request would be sent in a
// shape pi-ai's record does not describe — a typed, pre-network rejection is
// correct unless a proxy is KNOWN to translate. Every entry here MUST be
// covered by a wire fixture in test/capability-inheritance.test.mjs proving
// the translation is real. Empty by design: no such proxy is evidenced today.
const PROXY_TRANSPORT_EXCEPTIONS = new Set();

/**
 * Map a pi-ai registry `api` value onto the Istara `provider_kind` whose
 * transport speaks it (FIX F-1). This is the worker-side mirror of
 * `backend/app/core/pi_runtime/endpoint_policy.py::provider_kind_for_catalog_api`:
 * the two tables MUST agree on every pi-ai KnownApi value, and
 * `tests/pi_compat/test_transport_conformance.py::test_kind_mapping_parity_node_python`
 * fails the gate if they drift. Registry apis with no Istara transport
 * (bedrock-converse-stream, azure-openai-responses, mistral-conversations,
 * google-generative-ai, google-vertex, pi-messages) fall through to the legacy
 * three-way rule, so a catalog endpoint for them still derives a kind — and the
 * typed `provider_transport_mismatch` rejection in resolveCapabilities fires at
 * bind time, loudly, instead of sending a misshapen body. That is deliberate:
 * those transports need native auth/URL shapes (AWS SigV4, GCP OAuth,
 * Azure resource URLs) PiApiEndpoint does not model; see the F-1 ledger entry.
 */
export function providerKindForRegistryApi(api) {
  const normalized = String(api || "").toLowerCase();
  if (normalized === "openai-codex-responses") return "openai_codex";
  if (normalized === "openai-responses") return "openai_responses";
  if (normalized.includes("anthropic")) return "anthropic_compat";
  return "openai_compat";
}

// Exported for scripts/dump-resolved-capabilities.mjs (F-1 regression sweep):
// the dump must derive the CONFIGURED transport exactly as the backend
// endpoint policy does, never feed the record's own api back in.
export function apiForKind(kind) {
  if (kind === "openai_compat") return { api: openAICompletionsApi(), modelApi: "openai-completions" };
  // OpenAI-protocol Responses transport (FIX F-1): records whose registry api
  // is `openai-responses` (openai/*, xai/*, and gateway-proxied OpenAI models)
  // bind through pi-ai's own Responses adapter on the same host + Bearer-key
  // auth shape — the pre-change chat-completions binding for these models was
  // functional but silently downgraded the record's canonical wire contract.
  if (kind === "openai_responses") return { api: openAIResponsesApi(), modelApi: "openai-responses" };
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
 * Capture the model identity reported in a provider's streamed response.
 *
 * The configured endpoint model is a request label, not proof of what an
 * OpenAI-compatible proxy, Anthropic gateway, or Codex relay actually served.
 * pi-ai exposes `responseModel` only for some adapters (and only when it
 * differs from the request model), so observe the provider response body at
 * the fetch boundary and attach the identity to the terminal assistant
 * message. This keeps the normal configured model intact while giving the
 * Research Spine a fail-closed, provider-reported identity receipt.
 */
function providerModelObservation() {
  const models = new Set();
  return {
    add(model) {
      if (typeof model !== "string" || model.trim().length === 0) return;
      models.add(model.trim());
    },
    value() {
      return models.size === 1 ? [...models][0] : null;
    },
  };
}

function reportedModel(payload) {
  if (!payload || typeof payload !== "object") return null;
  const candidates = [
    payload.model,
    payload.response?.model,
    payload.message?.model,
  ];
  return candidates.find((candidate) => typeof candidate === "string" && candidate.trim().length > 0) || null;
}

/** Wrap a provider Response body while preserving every byte for pi-ai. */
export function captureProviderFetch(fetchImpl, observation) {
  return async (input, init) => {
    const response = await fetchImpl(input, init);
    if (!response?.body || typeof response.body.pipeThrough !== "function") return response;
    const decoder = new TextDecoder();
    let pending = "";
    let jsonPending = "";
    const contentType = String(response.headers?.get?.("content-type") || "").toLowerCase();
    const isJsonBody = contentType.includes("application/json") || contentType.includes("+json");
    const parseJsonBody = (raw) => {
      try {
        const payload = JSON.parse(raw);
        if (Array.isArray(payload)) {
          for (const item of payload) observation.add(reportedModel(item));
        } else {
          observation.add(reportedModel(payload));
        }
      } catch {
        // The adapter/parser remains authoritative; observation is best effort.
      }
    };
    const parseLine = (line) => {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) return;
      const raw = trimmed.slice(5).trim();
      if (!raw || raw === "[DONE]") return;
      try {
        observation.add(reportedModel(JSON.parse(raw)));
      } catch {
        // The provider parser remains authoritative; this observer must never
        // alter or reject a response merely because a data line is non-JSON.
      }
    };
    const body = response.body.pipeThrough(new TransformStream({
      transform(chunk, controller) {
        const decoded = decoder.decode(chunk, { stream: true });
        if (isJsonBody) {
          // Non-SSE adapters may split or pretty-print one JSON document across
          // arbitrary chunks/newlines. Buffer only the observer copy while
          // forwarding each original byte chunk unchanged to pi-ai.
          jsonPending += decoded;
          controller.enqueue(chunk);
          return;
        }
        pending += decoded;
        let newline;
        while ((newline = pending.indexOf("\n")) !== -1) {
          parseLine(pending.slice(0, newline));
          pending = pending.slice(newline + 1);
        }
        controller.enqueue(chunk);
      },
      flush(controller) {
        const tail = decoder.decode();
        if (isJsonBody) {
          jsonPending += tail;
          if (jsonPending.trim()) parseJsonBody(jsonPending);
        } else {
          pending += tail;
          if (pending) parseLine(pending);
        }
        controller.terminate();
      },
    }));
    return new Response(body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  };
}

function attachProviderModel(stream, observation) {
  // Keep the AssistantMessageEventStream contract intact. Agent-core calls
  // `.result()` on every stream; returning a bare async generator here would
  // silently turn every real-provider completion into `response.result is not
  // a function` (and hide the actual budget/served-identity outcome).
  const out = createAssistantMessageEventStream();
  (async () => {
    try {
      for await (const event of stream) {
        if (event.type === "done" && event.message) {
          const model = observation.value();
          if (model) {
            const enriched = { ...event, message: { ...event.message, responseModel: model } };
            out.push(enriched);
            out.end(enriched.message);
            continue;
          }
        }
        out.push(event);
        if (event.type === "error") {
          out.end(event.error);
        } else if (event.type === "done") {
          out.end(event.message);
        }
      }
      // A guarded stream can end without a terminal event on a transport
      // anomaly. Preserve that completion rather than leaving agent-core's
      // `.result()` promise pending forever.
      out.end();
    } catch (error) {
      out.push({ type: "error", reason: "error", error });
      out.end(error);
    }
  })();
  return out;
}

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
 * endpoint. Async: capability resolution may lazily import the pi-ai registry
 * (memoised, once per worker process). The returned `dispose()` clears the
 * injected secret from the environment. `stream` wraps models.streamSimple
 * with the guarded retry budget from endpoint.params.max_retries.
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
 * Tier-5/6 identity fallback (plan W2.3): today's provider-identity handling,
 * moved VERBATIM from the former `modelCapabilities`. Applied only when the
 * pi-ai registry misses (governed custom providers like dashscope, unknown
 * proxy gateways, legacy bindings, or registry models pi-ai does not list).
 * This is the ONLY hand-written provider-knowledge list permitted in the tree;
 * entries here must carry catalog provenance and a wire fixture
 * (test/fixtures/wire/pre-change/ pins their behavior byte-identically).
 */
export function legacyIdentityCapabilities(endpoint, modelApi) {
  if (modelApi === "openai-codex-responses") {
    return {
      reasoning: true,
      thinkingLevels: ["xhigh", "max", "minimal"],
      compat: undefined,
    };
  }
  const provider = String(endpoint?.pi_provider || "").trim().toLowerCase();
  // Catalog-managed endpoints advertise this per-model capability. Legacy
  // bindings leave it null/undefined, so retain the provider default for
  // backwards compatibility while honoring an explicit false value.
  const advertisedReasoning = endpoint?.supports_reasoning;
  const reasoning = advertisedReasoning == null ? true : Boolean(advertisedReasoning);
  if (provider === "deepseek") {
    return {
      reasoning,
      thinkingLevels: undefined,
      compat: reasoning ? { thinkingFormat: "deepseek" } : undefined,
    };
  }
  // Qwen's OpenAI-compatible APIs use a provider-specific thinking contract:
  // `enable_thinking` is emitted only when pi-ai sees both reasoning support
  // and the Qwen compatibility marker. Custom Pi Model Management endpoints
  // do not use pi-ai's static provider catalog, so preserve that contract from
  // the non-secret provider identity resolved by the backend. Qwen accepts a
  // boolean enable flag rather than OpenAI's `reasoning_effort`; suppress the
  // latter to avoid sending an unsupported field to DashScope/Token Plan.
  const qwenProviders = new Set([
    "qwen",
    "qwen-cloud",
    "qwen-token-plan",
    "qwen-token-plan-cn",
    "qwen-token-plan-individual",
    "dashscope",
  ]);
  if (qwenProviders.has(provider)) {
    return {
      reasoning,
      thinkingLevels: undefined,
      compat: reasoning ? { thinkingFormat: "qwen", supportsReasoningEffort: false } : undefined,
    };
  }
  // Zai/Zhipu GLM endpoints: pass our identity (thinkingFormat) through and
  // let pi-ai own the support matrix — getCompat merges per-field, so an
  // unspecified supportsReasoningEffort falls back to pi-ai's detected value
  // (false for zai). We name the format because gateway/proxy base URLs may
  // not reveal the provider; we never restate pi-ai's per-provider constants.
  const zaiProviders = new Set(["zai", "zhipu", "zhipuai", "zhipu-ai", "bigmodel"]);
  if (zaiProviders.has(provider)) {
    return { reasoning, thinkingLevels: undefined, compat: reasoning ? { thinkingFormat: "zai" } : undefined };
  }
  return { reasoning: false, thinkingLevels: undefined, compat: undefined };
}

/**
 * Deprecated alias for the tier-5/6 identity fallback, kept for tests and any
 * caller that has not migrated to the async resolver. New code MUST call
 * {@link resolveCapabilities} — calling this on a registry-known model
 * silently discards the authority record.
 */
export const modelCapabilities = legacyIdentityCapabilities;

// DashScope/DeepSeek and non-OpenAI gateways reject the `developer` role.
// When building a real OpenAI-protocol provider outside api.openai.com,
// ensure `compat.supportsDeveloperRole` is explicitly false so system prompts
// are sent as `role: "system"`. This URL rule is a tier-5 DEFAULT: on a
// tier-4 registry hit it only fills fields the inherited compat does not name.
// It covers BOTH OpenAI-protocol transports (FIX F-1): third-party hosts
// serving `openai-responses` records (xai, gateways) keep the exact pre-change
// chat-path default, so the transport upgrade changes the envelope, not the
// role contract. api.openai.com stays excluded on both (inherits the record).
function isCustomOpenAICompat(baseUrl, modelApi) {
  return (
    (modelApi === "openai-completions" || modelApi === "openai-responses") &&
    baseUrl &&
    !baseUrl.includes("api.openai.com") &&
    !baseUrl.includes("azure.com")
  );
}

/**
 * Resolve the effective capability record for a real endpoint (plan W2.2,
 * §1.2 per-field precedence law). Async because the registry is lazily
 * imported once per process.
 *
 * Tiers 1-3 (safety overlay, operator endpoint overrides, catalog advertised
 * restrictions) may only RESTRICT the tier-4 pi-ai record — never enable a
 * capability the record denies. On a registry miss the tier-5/6 identity
 * fallback applies unchanged. Every resolution returns a content-free receipt
 * (observability evidence only — never a report or self-improvement signal).
 */
export async function resolveCapabilities(endpoint, modelApi) {
  const provider = String(endpoint?.pi_provider || "").trim().toLowerCase();
  const modelId = String(endpoint?.model || "").trim();
  const baseUrl = String(endpoint?.base_url || "");
  const receipt = {
    capability_source: "legacy_detection",
    pi_ai_version: piAiVersion(),
    registry_generated_at: null,
    pi_provider: provider || null,
    model: modelId || null,
    api: modelApi,
    reasoning: false,
    supported_pi_levels: ["off"],
    applied_override_names: [],
    fallback_reason: null,
  };

  let registry = null;
  try {
    registry = await getPiRegistry();
  } catch {
    registry = null; // guarded: a broken install degrades to legacy behavior
  }
  let record = null;
  if (registry && provider && modelId) {
    try {
      // One exact, guarded lookup — no fuzzy matching, no normalization
      // beyond trimming, no per-provider heuristics (plan W2.2).
      record = registry.getBuiltinModel(provider, modelId) || null;
    } catch {
      record = null;
    }
  }

  if (!record) {
    const legacy = legacyIdentityCapabilities(endpoint, modelApi);
    const urlDefault = isCustomOpenAICompat(baseUrl, modelApi);
    // Exactly today's buildRealProvider semantics: the URL default sits UNDER
    // the identity compat (identity compat wins when it names the field).
    const compat = legacy.compat
      ? { ...(urlDefault ? { supportsDeveloperRole: false } : {}), ...legacy.compat }
      : urlDefault
        ? { supportsDeveloperRole: false }
        : undefined;
    receipt.capability_source = legacy.compat || legacy.reasoning ? "legacy_identity" : "legacy_detection";
    receipt.reasoning = Boolean(legacy.reasoning);
    receipt.supported_pi_levels = getSupportedThinkingLevels({ reasoning: Boolean(legacy.reasoning) });
    receipt.fallback_reason = !registry
      ? "registry_unavailable"
      : !provider || !modelId
        ? "missing_provider_identity"
        : "registry_miss";
    if (registry?.registryGeneratedAt) receipt.registry_generated_at = registry.registryGeneratedAt;
    return { capabilities: { ...legacy, compat }, receipt };
  }

  // Tier-4 hit. First gate: the record's transport must agree with the
  // configured kind, or the request would be sent in a shape the record does
  // not describe. Typed, pre-network rejection (W2.6) unless a named,
  // fixture-backed proxy exception authorizes the translation. Reachable only
  // for registry apis with no Istara transport (bedrock/google/mistral/azure
  // natives — F-1 keeps this loud by design) or a genuinely misconfigured
  // kind; same-protocol pairs (e.g. openai-responses records) have their own
  // kind via providerKindForRegistryApi and never reach this throw.
  if (record.api !== modelApi && !PROXY_TRANSPORT_EXCEPTIONS.has(`${provider}:${modelId}`)) {
    throw new Error(
      `provider_transport_mismatch:${provider}:${modelId}:registry_api=${record.api}:configured=${modelApi}`,
    );
  }

  const appliedOverrideNames = [];
  // `reasoning`: tier-4 authority, restricted by the tier-2/3 advertised
  // tri-state. An explicit false restricts; null restricts nothing; true can
  // never enable a record that denies reasoning (monotonic restriction).
  let reasoning = Boolean(record.reasoning);
  if (endpoint?.supports_reasoning === false) {
    if (reasoning) appliedOverrideNames.push("supports_reasoning");
    reasoning = false;
  }
  // `thinkingLevelMap`: verbatim from the record (tier 4). A tier-2
  // reasoning restriction silences it on the wire — every pi-ai thinkingFormat
  // branch gates on model.reasoning — so the record stays intact and the
  // restriction is carried by `reasoning` alone (never hand-rewrite the map).
  const thinkingLevelMap = record.thinkingLevelMap;
  // `compat`: verbatim record (tier 4); the tier-5 URL default fills ONLY when
  // the inherited compat does not name supportsDeveloperRole (§5.2).
  let compat = record.compat ? { ...record.compat } : undefined;
  if (isCustomOpenAICompat(baseUrl, modelApi) && !(compat && "supportsDeveloperRole" in compat)) {
    compat = { ...(compat || {}), supportsDeveloperRole: false };
    appliedOverrideNames.push("supportsDeveloperRole:url_default");
  }
  // `input`: seeded from the record (tier 4); the advertised vision tri-state
  // restricts only — an explicit false narrows to text, null/true keep the
  // record's modalities (an advertisement may never ADD a modality).
  let input = Array.isArray(record.input) && record.input.length > 0 ? [...record.input] : ["text"];
  if (endpoint?.supports_vision === false) {
    if (input.includes("image")) appliedOverrideNames.push("supports_vision");
    input = ["text"];
  }

  receipt.capability_source = "pi_builtin";
  receipt.registry_generated_at = registry?.registryGeneratedAt ?? null;
  receipt.reasoning = reasoning;
  receipt.supported_pi_levels = getSupportedThinkingLevels({ reasoning, thinkingLevelMap });
  receipt.applied_override_names = appliedOverrideNames;
  return {
    capabilities: {
      reasoning,
      thinkingLevelMap,
      compat,
      input,
      // pi-ai computes the supported level menu; never reimplemented here
      // (DEC-M2). Exposed for the receipt and tests, not set on the model —
      // the `thinkingLevels` field is dead in pi-ai 0.84.x (G3).
      supportedPiLevels: receipt.supported_pi_levels,
    },
    receipt,
  };
}

export async function buildRealProvider(endpoint) {
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
  // Capability authority: pi-ai's registry record when it knows the model
  // (tier 4, restricted by advertised tri-states), else the tier-5/6 identity
  // fallback. Throws a typed pre-network error on a builtin/endpoint transport
  // disagreement. The receipt is content-free observability evidence only.
  const { capabilities, receipt } = await resolveCapabilities(endpoint, modelApi);

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
    // pi-ai 0.84.x reads `thinkingLevelMap` and never reads `thinkingLevels`
    // on the model record (G3) — the dead field is no longer set. pi-ai's own
    // clampThinkingLevel + adapter mapping do all level translation at stream
    // time (DEC-M2); Istara never pre-maps provider strings.
    thinkingLevelMap: capabilities.thinkingLevelMap,
    compat: capabilities.compat,
    // Tier-4 hits inherit the record's modalities (restricted by the
    // advertised tri-state); fallback bindings keep today's advertised-vision
    // derivation byte-identically (AC-1).
    input: capabilities.input ?? (endpoint.supports_vision ? ["text", "image"] : ["text"]),
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
    capability_receipt: receipt,
    // Real network binding: usage is priced by `model.cost` above. `pricing` is
    // the per-category rate map the session checks against actual per-category
    // usage — a budgeted run that spent tokens in any $0-rated category fails
    // closed rather than reporting an untrusted under-count (see session.mjs).
    isReal: true,
    pricing: cost,
    stream: (streamModel, context, options) => {
      // Endpoint params are operator policy and win over agent defaults; the
      // agent-supplied abort signal is always preserved. wireParams excludes
      // API-unsupported controls (see above). The wrapped fetch captures the
      // provider-reported response model without changing the response bytes.
      // Codex also has a WebSocket transport, but that path does not expose
      // terminal response metadata to this observer. Research Spine identity
      // receipts therefore use the observable SSE transport; without this
      // pin, a successful OAuth turn can be promoted without proof of the
      // model actually served.
      const observation = providerModelObservation();
      const fetchImpl = options?.fetch || globalThis.fetch;
      const stream = streamWithGuardedRetry(
        models,
        streamModel,
        context,
        {
          ...options,
          ...(modelApi === "openai-codex-responses" ? { transport: "sse" } : {}),
          fetch: captureProviderFetch(fetchImpl, observation),
          ...wireParams,
        },
        maxRetries,
      );
      return attachProviderModel(stream, observation);
    },
    dispose: () => {
      delete process.env[envVar];
    },
  };
}

/** Convert a serialized faux-response spec into a pi-ai faux assistant message. */
function buildFauxResponse(spec) {
  // A serialized response can require proof that the authority's tool result
  // made it back into the model context. This is deliberately test-only: real
  // providers are never built from faux response specs. Without this guard a
  // scripted final answer could make a broken tool-result round trip look green.
  if (spec.requires_tool_result) {
    const requirement = typeof spec.requires_tool_result === "object"
      ? spec.requires_tool_result
      : {};
    return (context) => {
      const expectedTool = String(requirement.tool_name || "").trim();
      const expectedText = String(requirement.contains || "");
      const observed = (context?.messages || []).some((message) => {
        if (message?.role !== "toolResult") return false;
        if (expectedTool && String(message.toolName || "") !== expectedTool) return false;
        if (!expectedText) return true;
        return (message.content || []).some((block) =>
          String(block?.text || "").includes(expectedText));
      });
      if (!observed) {
        return fauxAssistantMessage([], {
          stopReason: "error",
          errorMessage: `required_tool_result_missing:${expectedTool || "any"}`,
        });
      }
      return buildFauxResponse({
        ...spec,
        requires_tool_result: undefined,
      });
    };
  }
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
  // `faux_tokens_per_second` (tests only) streams the scripted text at a set rate, so liveness can
  // be tested against a slow but steady model.
  const rate = Number.isFinite(endpoint.faux_tokens_per_second) && endpoint.faux_tokens_per_second > 0
    ? endpoint.faux_tokens_per_second : 0;
  const faux = fauxProvider({ tokensPerSecond: rate });
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

export async function buildProviderBinding(endpoint) {
  if (endpoint.provider_kind === "faux") return buildFauxProviderBinding(endpoint);
  return buildRealProvider(endpoint);
}
