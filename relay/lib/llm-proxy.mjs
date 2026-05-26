/**
 * LLM Proxy — forwards LLM requests to local and OpenAI-compatible model servers.
 * Supports optional API key for servers that require authentication.
 */

export const ANTHROPIC_VERSION = "2023-06-01";
export const ANTHROPIC_PROVIDERS = new Set(["anthropic", "anthropic_compat"]);
const THINK_OPEN = "<think>";
const THINK_CLOSE = "</think>";
const GEMMA_THOUGHT_OPEN = "<|channel>thought";
const GEMMA_THOUGHT_CLOSE = "<channel|>";
const THINKING_BLOCKS = [
  [THINK_OPEN, THINK_CLOSE],
  [GEMMA_THOUGHT_OPEN, GEMMA_THOUGHT_CLOSE],
];
const VISIBLE_CONTROL_TOKENS = [
  "<|think|>",
  "<turn|>",
  "<end_of_turn>",
  "<bos>",
  "<eos>",
];
const NON_VISIBLE_CONTENT_TYPES = new Set([
  "thinking",
  "redacted_thinking",
  "reasoning",
  "reasoning_content",
  "thought",
  "thought_signature",
]);
const NON_VISIBLE_MESSAGE_KEYS = new Set([
  ...NON_VISIBLE_CONTENT_TYPES,
  "thoughtSignature",
]);
const THINKING_MODES = new Set(["server_default", "off", "auto", "on"]);
const THINKING_DIRECTIVES = {
  off: "Istara thinking mode is OFF. Answer directly. Do not emit chain-of-thought, hidden reasoning, scratchpads, <think> blocks, or thought-channel markup. Return only the final user-visible answer.",
  auto: "Istara thinking mode is AUTO. Follow the model/server default for any private reasoning, but never reveal raw reasoning, scratchpads, <think> blocks, or thought-channel markup. Return only the final answer.",
  on: "Istara thinking mode is ON. Use private reasoning internally if this model/server supports it, but never reveal raw reasoning, scratchpads, <think> blocks, or thought-channel markup. Return only the final answer.",
};
const PROVIDER_ALIASES = new Map([
  ["openai", "openai_compat"],
  ["openai-compatible", "openai_compat"],
  ["openai_compatible", "openai_compat"],
  ["lm_studio", "lmstudio"],
  ["lm-studio", "lmstudio"],
  ["llama.cpp", "llamacpp"],
  ["llama-cpp", "llamacpp"],
  ["mlx_lm", "mlx"],
  ["anthropic-compatible", "anthropic_compat"],
  ["anthropic_compatible", "anthropic_compat"],
]);

export function stripThinkingBlocks(text = "") {
  if (!text) return text || "";
  if (!THINKING_BLOCKS.some(([open]) => text.includes(open))) {
    return stripVisibleControlTokens(text);
  }

  let output = "";
  let index = 0;
  while (index < text.length) {
    const found = firstThinkingOpen(text, index);
    if (!found) {
      output += text.slice(index);
      break;
    }
    const { start, open, close } = found;
    output += text.slice(index, start);
    const end = text.indexOf(close, start + open.length);
    if (end === -1) break;
    index = end + close.length;
    while (index < text.length && /\s/.test(text[index])) index += 1;
  }
  return stripVisibleControlTokens(output);
}

function firstThinkingOpen(text, index) {
  let found = null;
  for (const [open, close] of THINKING_BLOCKS) {
    const start = text.indexOf(open, index);
    if (start === -1) continue;
    if (!found || start < found.start) found = { start, open, close };
  }
  return found;
}

function stripVisibleControlTokens(text = "") {
  let output = text;
  for (const token of VISIBLE_CONTROL_TOKENS) {
    output = output.replaceAll(token, "");
  }
  return output;
}

function visibleContentFromMessage(message = {}) {
  const content = message?.content;
  if (typeof content === "string") return stripThinkingBlocks(content).trim();
  if (!Array.isArray(content)) return content == null ? "" : stripThinkingBlocks(String(content)).trim();

  const visible = [];
  for (const block of content) {
    if (!block || typeof block !== "object") {
      visible.push(String(block));
      continue;
    }
    const type = String(block.type || "").toLowerCase();
    if (NON_VISIBLE_CONTENT_TYPES.has(type)) continue;
    if (block.thought === true || block.thinking === true) continue;
    if (["text", "output_text", "input_text", ""].includes(type)) {
      const text = block.text ?? block.content ?? "";
      if (text) visible.push(String(text));
    }
  }
  return stripThinkingBlocks(visible.join("")).trim();
}

function visibleMessageFromMessage(message = {}) {
  const normalized = { ...(message || {}) };
  normalized.role = normalized.role || "assistant";
  normalized.content = visibleContentFromMessage(message);
  for (const key of NON_VISIBLE_MESSAGE_KEYS) {
    delete normalized[key];
  }
  return normalized;
}

export function normalizeThinkingMode(value) {
  const mode = String(value || "server_default").trim().toLowerCase().replaceAll("-", "_");
  return THINKING_MODES.has(mode) ? mode : "server_default";
}

export function applyThinkingControl(messages = [], thinkingMode = "server_default") {
  const mode = normalizeThinkingMode(thinkingMode);
  const directive = THINKING_DIRECTIVES[mode];
  const controlled = (messages || []).map((message) => ({ ...(message || {}) }));
  if (!directive) return controlled;
  if (controlled.some((message) => (
    message.role === "system" && String(message.content || "").includes("Istara thinking mode is ")
  ))) {
    return controlled;
  }
  if (controlled[0]?.role === "system") {
    controlled[0].content = `${controlled[0].content || ""}\n\n${directive}`;
  } else {
    controlled.unshift({ role: "system", content: directive });
  }
  return controlled;
}

export function normalizeProviderType(providerType) {
  const requested = (providerType || "").trim().toLowerCase();
  return PROVIDER_ALIASES.get(requested) || requested;
}

export function inferProviderType(providerType, host) {
  const requested = normalizeProviderType(providerType);
  const rawHost = (host || "").trim();
  if (requested && requested !== "ollama") return requested;
  if (!rawHost) return requested || "openai_compat";

  let parsed;
  try {
    parsed = new URL(rawHost.includes("://") ? rawHost : `http://${rawHost}`);
  } catch {
    return requested || "openai_compat";
  }

  const path = parsed.pathname.replace(/\/+$/, "");
  if (parsed.hostname.includes("generativelanguage.googleapis.com") || path.endsWith("/openai")) {
    return "gemini_openai";
  }
  if (parsed.hostname.includes("anthropic.com")) return "anthropic";
  if (parsed.port === "1234") return "lmstudio";
  if (path.endsWith("/v1")) return "openai_compat";
  if (parsed.port === "11434") return "ollama";
  return requested || "openai_compat";
}

export const DEFAULT_LOCAL_LLM_CANDIDATES = [
  { providerType: "lmstudio", host: "http://localhost:1234" },
  { providerType: "lmstudio", host: "http://127.0.0.1:1234" },
  { providerType: "ollama", host: "http://localhost:11434" },
  { providerType: "ollama", host: "http://127.0.0.1:11434" },
  { providerType: "llamacpp", host: "http://localhost:8080" },
  { providerType: "llamacpp", host: "http://127.0.0.1:8080" },
  { providerType: "vllm", host: "http://localhost:8000" },
  { providerType: "sglang", host: "http://localhost:30000" },
];

export class LLMProxy {
  constructor(providerType, host, apiKey) {
    this.host = (host || "").replace(/\/+$/, "");
    this.providerType = inferProviderType(providerType, this.host);
    this.apiKey = apiKey || "";
  }

  _openAIUrl(suffix) {
    const cleanSuffix = suffix.replace(/^\/+/, "");
    let parsed;
    try {
      parsed = new URL(this.host.includes("://") ? this.host : `http://${this.host}`);
    } catch {
      return `${this.host}/v1/${cleanSuffix}`;
    }
    const basePath = parsed.pathname.replace(/\/+$/, "");
    const hasOpenAIBase = (
      this.providerType === "gemini_openai"
      || parsed.hostname.includes("generativelanguage.googleapis.com")
      || basePath.endsWith("/openai")
      || basePath.endsWith("/v1")
    );
    return hasOpenAIBase
      ? `${this.host}/${cleanSuffix}`
      : `${this.host}/v1/${cleanSuffix}`;
  }

  /** Build headers with optional auth. */
  _headers() {
    const h = { "Content-Type": "application/json" };
    if (this.apiKey) {
      if (ANTHROPIC_PROVIDERS.has(this.providerType)) {
        h["x-api-key"] = this.apiKey;
        h["anthropic-version"] = ANTHROPIC_VERSION;
      } else {
        h["Authorization"] = `Bearer ${this.apiKey}`;
      }
    }
    return h;
  }

  _nativeLMStudioUrl(suffix) {
    return `${this.host}/api/v1/${suffix.replace(/^\/+/, "")}`;
  }

  _capabilityFromName(modelId) {
    const name = String(modelId || "");
    const lower = name.toLowerCase();
    const paramMatch = name.match(/(\d+\.?\d*)\s*b/i);
    const param = paramMatch ? `${paramMatch[1]}B` : "unknown";
    const paramNum = paramMatch ? Number.parseFloat(paramMatch[1]) : 0;
    const cap = {
      name,
      parameter_count: param,
      context_length: lower.includes("claude")
        ? 200000
        : paramNum > 12 ? 32768 : paramNum > 4 ? 8192 : 4096,
      supports_tools: paramNum >= 7 || ["qwen", "llama-3", "llama-4", "mistral", "gemma", "gpt", "claude"]
        .some((family) => lower.includes(family)),
      supports_vision: [
        "vl",
        "vision",
        "visual",
        "multimodal",
        "llava",
        "moondream",
        "minicpm-v",
        "pixtral",
        "qwen3.6",
        "claude-3",
        "claude-sonnet",
        "claude-opus",
        "claude-haiku",
      ].some((token) => lower.includes(token)),
      supports_audio: ["audio", "omni", "whisper", "ultravox"]
        .some((token) => lower.includes(token)),
      supports_json: ["json", "instruct", "gpt", "claude"]
        .some((token) => lower.includes(token)),
      quantization: "",
      source: this.providerType,
      is_loaded: null,
      trained_context_length: null,
      loaded_context_length: null,
      loadable: this.providerType === "lmstudio",
      endpoint_family: ANTHROPIC_PROVIDERS.has(this.providerType) ? "anthropic" : "openai",
      modalities: {
        text: true,
        vision: false,
        audio: false,
      },
    };
    cap.trained_context_length = cap.context_length;
    if (cap.supports_tools) cap.supports_json = true;
    cap.modalities.vision = cap.supports_vision;
    cap.modalities.audio = cap.supports_audio;
    return cap;
  }

  _applyCapabilityMetadata(cap, metadata) {
    if (!metadata) return;
    if (Array.isArray(metadata)) {
      const normalized = metadata.map((item) => String(item).toLowerCase());
      cap.supports_tools = cap.supports_tools
        || normalized.some((item) => ["tool", "tools", "tool_use", "function_calling"].includes(item));
      cap.supports_vision = cap.supports_vision
        || normalized.some((item) => ["vision", "image", "images", "multimodal"].includes(item));
      cap.supports_audio = cap.supports_audio
        || normalized.some((item) => ["audio", "input_audio", "audio_input"].includes(item));
      cap.supports_json = cap.supports_json
        || normalized.some((item) => ["json", "json_mode", "structured_outputs"].includes(item));
    } else if (typeof metadata === "object") {
      cap.supports_vision = Boolean(
        metadata.vision || metadata.image || metadata.images || metadata.multimodal || cap.supports_vision,
      );
      cap.supports_audio = Boolean(
        metadata.audio || metadata.input_audio || metadata.audio_input || cap.supports_audio,
      );
      cap.supports_tools = Boolean(
        metadata.trained_for_tool_use
        || metadata.tool_use
        || metadata.tools
        || metadata.function_calling
        || cap.supports_tools,
      );
      cap.supports_json = Boolean(
        metadata.json
        || metadata.json_mode
        || metadata.structured_outputs
        || metadata.response_format
        || cap.supports_json,
      );
    }
    cap.modalities.vision = cap.supports_vision;
    cap.modalities.audio = cap.supports_audio;
  }

  _contextFromObject(value) {
    if (!value || typeof value !== "object") return null;
    const exact = new Set([
      "context_length",
      "max_context_length",
      "max_model_len",
      "max_seq_len",
      "context_window",
      "n_ctx",
      "num_ctx",
      "ctx_size",
    ]);
    for (const [key, raw] of Object.entries(value)) {
      const normalized = String(key).toLowerCase();
      const parsed = Number.parseInt(raw, 10);
      if ((exact.has(normalized) || normalized.endsWith(".context_length"))
        && Number.isFinite(parsed)
        && parsed > 0) {
        return parsed;
      }
    }
    return null;
  }

  _applyContext(cap, value, { loaded = false } = {}) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) return;
    cap.context_length = parsed;
    if (loaded) cap.loaded_context_length = parsed;
    else cap.trained_context_length = parsed;
  }

  _capabilityFromOllamaModel(model) {
    const id = model?.name || model?.model || "";
    if (!id) return null;
    const cap = this._capabilityFromName(id);
    cap.source = "ollama";
    cap.endpoint_family = "ollama";
    cap.loadable = true;
    cap.is_loaded = false;
    if (model?.details) {
      cap.parameter_count = model.details.parameter_size || cap.parameter_count;
      cap.quantization = model.details.quantization_level || cap.quantization;
    }
    return cap;
  }

  _capabilityFromLMStudioModel(model) {
    const id = model?.key || model?.id || model?.name || "";
    if (!id) return null;
    const cap = this._capabilityFromName(id);
    cap.source = "lmstudio";
    cap.context_length = model.max_context_length || model.context_length || cap.context_length;
    cap.trained_context_length = cap.context_length;
    cap.loadable = true;
    if (Array.isArray(model.loaded_instances)) {
      cap.is_loaded = model.loaded_instances.length > 0;
      const loadedContext = model.loaded_instances
        .map((instance) => instance?.config?.context_length)
        .find((value) => Number.isFinite(value));
      if (loadedContext) cap.context_length = loadedContext;
      if (loadedContext) cap.loaded_context_length = loadedContext;
    }
    if (model.type === "vlm") cap.supports_vision = true;
    if (model.type === "audio") cap.supports_audio = true;
    this._applyCapabilityMetadata(cap, model.capabilities);
    if (typeof model.quantization === "string") {
      cap.quantization = model.quantization;
    } else if (model.quantization?.name) {
      cap.quantization = model.quantization.name;
    }
    return cap;
  }

  _parseOpenAIModels(data) {
    const rawModels = Array.isArray(data) ? data : data?.data || [];
    const models = [];
    const modelCapabilities = {};
    for (const model of rawModels) {
      const id = model?.id || model?.name || "";
      if (!id) continue;
      const cap = this._capabilityFromName(id);
      this._applyContext(
        cap,
        model?.max_model_len
          || model?.max_context_length
          || model?.max_tokens
          || model?.context_length
          || model?.context_window
          || model?.n_ctx,
      );
      this._applyContext(cap, this._contextFromObject(model?.metadata));
      this._applyCapabilityMetadata(cap, model?.capabilities);
      this._applyCapabilityMetadata(cap, model?.metadata?.capabilities);
      if (model?.type === "vlm") cap.supports_vision = true;
      if (model?.type === "audio") cap.supports_audio = true;
      if (model?.loaded != null) cap.is_loaded = Boolean(model.loaded);
      models.push(id);
      modelCapabilities[id] = cap;
    }
    return { models, modelCapabilities };
  }

  _parseLMStudioModels(data) {
    const rawModels = data?.models || [];
    const models = [];
    const modelCapabilities = {};
    const addCapability = (cap) => {
      if (!cap?.name || modelCapabilities[cap.name]) return;
      models.push(cap.name);
      modelCapabilities[cap.name] = cap;
    };
    for (const model of rawModels) {
      const cap = this._capabilityFromLMStudioModel(model);
      if (!cap) continue;
      addCapability(cap);
      for (const instance of model?.loaded_instances || []) {
        const instanceId = String(instance?.id || "").trim();
        if (!instanceId || instanceId === cap.name) continue;
        const instanceCap = {
          ...cap,
          name: instanceId,
          is_loaded: true,
          loaded_instance_alias: true,
        };
        const loadedContext = instance?.config?.context_length;
        if (Number.isFinite(loadedContext)) {
          instanceCap.context_length = loadedContext;
          instanceCap.loaded_context_length = loadedContext;
        }
        addCapability(instanceCap);
      }
    }
    return { models, modelCapabilities };
  }

  async _parseOllamaModels(data) {
    const rawModels = data?.models || [];
    const models = [];
    const modelCapabilities = {};
    for (const model of rawModels) {
      const cap = this._capabilityFromOllamaModel(model);
      if (!cap) continue;
      try {
        const res = await fetch(`${this.host}/api/show`, {
          method: "POST",
          headers: this._headers(),
          body: JSON.stringify({ model: cap.name }),
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          const show = await res.json();
          this._applyCapabilityMetadata(cap, show.capabilities);
          if (show.details) {
            cap.parameter_count = show.details.parameter_size || cap.parameter_count;
            cap.quantization = show.details.quantization_level || cap.quantization;
          }
          this._applyContext(cap, this._contextFromObject(show.model_info));
          const loadedContext = String(show.parameters || "")
            .match(/(?:num_ctx|n_ctx|ctx_size)\s+(\d+)/)?.[1];
          if (loadedContext) this._applyContext(cap, loadedContext, { loaded: true });
        }
      } catch {
        // Keep tags metadata if show is unavailable.
      }
      models.push(cap.name);
      modelCapabilities[cap.name] = cap;
    }
    try {
      const res = await fetch(`${this.host}/api/ps`, {
        headers: this._headers(),
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        const ps = await res.json();
        for (const model of ps.models || []) {
          const name = model?.name || model?.model;
          if (name && modelCapabilities[name]) {
            modelCapabilities[name].is_loaded = true;
            this._applyContext(
              modelCapabilities[name],
              this._contextFromObject(model),
              { loaded: true },
            );
          }
        }
      }
    } catch {
      // /api/ps is optional for older Ollama builds.
    }
    return { models, modelCapabilities };
  }

  _anthropicContent(content) {
    if (typeof content === "string") return content;
    if (!Array.isArray(content)) return String(content || "");
    const blocks = [];
    for (const item of content) {
      if (!item || typeof item !== "object") {
        blocks.push({ type: "text", text: String(item) });
        continue;
      }
      if (item.type === "text" || item.type === "input_text") {
        if (item.text || item.content) {
          blocks.push({ type: "text", text: String(item.text || item.content) });
        }
        continue;
      }
      const image = item.image_url || item.input_image || item.image;
      const url = typeof image === "string" ? image : image?.url || image?.data || "";
      if (!url) continue;
      if (url.startsWith("data:") && url.includes(";base64,")) {
        const [header, encoded] = url.split(";base64,");
        blocks.push({
          type: "image",
          source: {
            type: "base64",
            media_type: header.replace(/^data:/, "") || "image/png",
            data: encoded,
          },
        });
      } else {
        blocks.push({ type: "image", source: { type: "url", url } });
      }
    }
    return blocks.length ? blocks : "";
  }

  _anthropicPayload({ messages, model, temperature, max_tokens, tools }) {
    const system = [];
    const converted = [];
    for (const msg of messages || []) {
      if (msg.role === "system") {
        if (msg.content) system.push(String(msg.content));
      } else if (msg.role === "tool") {
        converted.push({ role: "user", content: `Tool result: ${msg.content || ""}` });
      } else if (msg.role === "user" || msg.role === "assistant") {
        converted.push({ role: msg.role, content: this._anthropicContent(msg.content) });
      }
    }
    const payload = {
      model: model || "default",
      messages: converted,
      temperature: temperature || 0.7,
      max_tokens: max_tokens || 1024,
    };
    if (system.length) payload.system = system.join("\n\n");
    const convertedTools = (tools || [])
      .map((tool) => tool?.function)
      .filter((fn) => fn?.name)
      .map((fn) => ({
        name: fn.name,
        description: fn.description || "",
        input_schema: fn.parameters || { type: "object", properties: {} },
      }));
    if (convertedTools.length) payload.tools = convertedTools;
    return payload;
  }

  _normalizeAnthropicResponse(data) {
    const text = [];
    const toolCalls = [];
    for (const block of data?.content || []) {
      if (block?.type === "text") text.push(block.text || "");
      if (block?.type === "tool_use") {
        toolCalls.push({
          id: block.id || "",
          type: "function",
          function: {
            name: block.name || "",
            arguments: JSON.stringify(block.input || {}),
          },
        });
      }
    }
    const result = { message: { role: "assistant", content: stripThinkingBlocks(text.join("")).trim() } };
    if (toolCalls.length) {
      result.message.tool_calls = toolCalls;
      result.finish_reason = "tool_calls";
    }
    return result;
  }

  async probeModels() {
    try {
      let url = this.providerType === "ollama"
        ? `${this.host}/api/tags`
        : this._openAIUrl("models");
      if (this.providerType === "lmstudio") {
        url = this._nativeLMStudioUrl("models");
      }

      const res = await fetch(url, {
        headers: this._headers(),
        signal: AbortSignal.timeout(5000),
      });
      if (!res.ok) {
        if (this.providerType === "lmstudio") {
          throw new Error(`LM Studio native models endpoint returned ${res.status}`);
        }
        return { ok: false, status: res.status, models: [], modelCapabilities: {} };
      }

      const data = await res.json();
      if (this.providerType === "ollama") {
        const parsed = await this._parseOllamaModels(data);
        return {
          ok: true,
          status: res.status,
          ...parsed,
        };
      }
      if (this.providerType === "lmstudio") {
        const parsed = this._parseLMStudioModels(data);
        return { ok: true, status: res.status, ...parsed };
      }
      const parsed = this._parseOpenAIModels(data);
      return {
        ok: true,
        status: res.status,
        ...parsed,
      };
    } catch (err) {
      if (this.providerType === "lmstudio") {
        try {
          const res = await fetch(this._openAIUrl("models"), {
            headers: this._headers(),
            signal: AbortSignal.timeout(5000),
          });
          if (res.ok) {
            const parsed = this._parseOpenAIModels(await res.json());
            return { ok: true, status: res.status, ...parsed };
          }
        } catch {
          // Keep the original error below.
        }
      }
      return {
        ok: false,
        status: 0,
        models: [],
        modelCapabilities: {},
        error: err?.message || String(err),
      };
    }
  }

  async listModels() {
    const probe = await this.probeModels();
    return probe.models;
  }

  async handleRequest(msg) {
    const { model, temperature, max_tokens, tools, response_format } = msg;
    const messages = applyThinkingControl(msg.messages || [], msg.thinking_mode);

    if (this.providerType === "ollama") {
      const payload = {
        model: model || "default",
        messages,
        stream: false,
        options: { temperature: temperature || 0.7 },
      };
      if (max_tokens) payload.options.num_predict = max_tokens;
      if (tools) payload.tools = tools;
      if (response_format) payload.format = response_format.json_schema || response_format;

      const res = await fetch(`${this.host}/api/chat`, {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data?.message) {
        data.message = visibleMessageFromMessage(data.message);
      }
      return data;
    } else {
      // OpenAI-compatible (LM Studio, Gemini, and compatible local servers)
      if (ANTHROPIC_PROVIDERS.has(this.providerType)) {
        const res = await fetch(this._openAIUrl("messages"), {
          method: "POST",
          headers: this._headers(),
          body: JSON.stringify(this._anthropicPayload({
            messages,
            model,
            temperature,
            max_tokens,
            tools,
          })),
        });
        if (!res.ok) throw new Error(await res.text());
        return this._normalizeAnthropicResponse(await res.json());
      }
      const payload = {
        model: model || "default",
        messages,
        temperature: temperature || 0.7,
        stream: false,
      };
      if (max_tokens) payload.max_tokens = max_tokens;
      if (tools) payload.tools = tools;
      if (response_format) payload.response_format = response_format;

      const res = await fetch(this._openAIUrl("chat/completions"), {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      // Normalize to Ollama format
      const message = data.choices?.[0]?.message || {};
      const result = {
        message: {
          role: "assistant",
          content: visibleContentFromMessage(message),
        },
      };
      if (message.tool_calls?.length) {
        result.message.tool_calls = message.tool_calls;
        result.finish_reason = data.choices?.[0]?.finish_reason || "tool_calls";
      }
      return result;
    }
  }

  async handleEmbedding(msg) {
    const input = msg.input;
    const model = msg.model || "default";
    if (ANTHROPIC_PROVIDERS.has(this.providerType)) {
      throw new Error("Anthropic-compatible servers do not expose Istara embeddings");
    }

    if (this.providerType === "ollama") {
      const res = await fetch(`${this.host}/api/embed`, {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify({ model, input }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (Array.isArray(input)) return data.embeddings || [];
      return data.embeddings?.[0] || [];
    }

    const res = await fetch(this._openAIUrl("embeddings"), {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify({ model, input }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const embeddings = (data.data || []).map((item) => item.embedding || []);
    return Array.isArray(input) ? embeddings : embeddings[0] || [];
  }

  async loadModel(model, { contextLength, allowUnload = false } = {}) {
    if (!model) throw new Error("No model provided to load");
    if (this.providerType === "lmstudio") {
      const payload = { model, echo_load_config: true };
      if (contextLength) {
        if (allowUnload) await this.unloadLoadedLMStudioInstances();
        payload.context_length = contextLength;
      }
      const res = await fetch(this._nativeLMStudioUrl("models/load"), {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      await res.json();
      const probe = await this.probeModels();
      return { models: probe.models, model_capabilities: probe.modelCapabilities };
    }
    const probe = await this.probeModels();
    if (!probe.models.includes(model)) {
      throw new Error(`Model ${model} is not available on this ${this.providerType} server`);
    }
    return { models: probe.models, model_capabilities: probe.modelCapabilities };
  }

  async unloadLoadedLMStudioInstances() {
    let data;
    try {
      const res = await fetch(this._nativeLMStudioUrl("models"), {
        method: "GET",
        headers: this._headers(),
      });
      if (!res.ok) return;
      data = await res.json();
    } catch {
      return;
    }

    const models = data?.models || data?.data || [];
    const unloaded = new Set();
    for (const model of models) {
      for (const instance of model?.loaded_instances || []) {
        const instanceId = instance?.id || instance?.instance_id;
        if (!instanceId || unloaded.has(instanceId)) continue;
        const res = await fetch(this._nativeLMStudioUrl("models/unload"), {
          method: "POST",
          headers: this._headers(),
          body: JSON.stringify({ instance_id: instanceId }),
        });
        if (res.ok) unloaded.add(instanceId);
      }
    }
  }
}

export async function detectLocalLLM({
  providerType = "",
  host = "",
  apiKey = "",
  candidates,
} = {}) {
  const probeCandidates = [];
  if (host) {
    probeCandidates.push({ providerType, host });
  }
  probeCandidates.push(...(candidates || DEFAULT_LOCAL_LLM_CANDIDATES));

  const seen = new Set();
  for (const candidate of probeCandidates) {
    const proxy = new LLMProxy(candidate.providerType || providerType, candidate.host, apiKey);
    const key = `${proxy.providerType}|${proxy.host}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const probe = await proxy.probeModels();
    if (probe.ok) {
      return {
        providerType: proxy.providerType,
        host: proxy.host,
        models: probe.models,
        modelCapabilities: probe.modelCapabilities || {},
        status: probe.status,
      };
    }
  }
  return null;
}
