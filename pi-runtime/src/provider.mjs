// Provider factory for the Pi runtime worker.
//
// A `provider.bind` frame supplies an exact endpoint (openai_compat or
// anthropic_compat) plus a short-lived secret. The secret is injected into the
// worker's own process environment under a per-session variable name and is
// never echoed, logged, or persisted. A `faux` kind is available for Node unit
// tests only (no network, deterministic scripted responses).

import {
  createModels,
  createProvider,
  envApiKeyAuth,
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

/**
 * Build the `{models, model, dispose}` triple for a real endpoint binding.
 * The returned `dispose()` clears the injected secret from the environment.
 */
export function buildRealProvider(endpoint) {
  const { provider_kind: kind, base_url: baseUrl, model: modelId, api_key: apiKey } = endpoint;
  if (!baseUrl || !modelId || !apiKey) throw new Error("incomplete_provider_binding");
  const { api, modelApi } = apiForKind(kind);

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
  return { models, model: faux.getModel(), dispose: () => {} };
}

export function buildProviderBinding(endpoint) {
  if (endpoint.provider_kind === "faux") return buildFauxProviderBinding(endpoint);
  return buildRealProvider(endpoint);
}
