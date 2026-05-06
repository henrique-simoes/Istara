"use client";

export interface ModelProviderOption {
  value: string;
  label: string;
  description: string;
  defaultHost?: string;
}

export interface LocalModelCapability {
  name: string;
  parameter_count: string | null;
  context_length: number | null;
  supports_tools: boolean;
  supports_vision: boolean;
  supports_audio: boolean;
  supports_json: boolean;
  quantization?: string | null;
  source?: string | null;
  is_loaded?: boolean | null;
  trained_context_length?: number | null;
  loaded_context_length?: number | null;
  endpoint_family?: string | null;
  modalities?: {
    text: boolean;
    vision: boolean;
    audio: boolean;
  };
}

export interface LocalLLMDetection {
  provider: string;
  providerType: string;
  host: string;
  models: string[];
  modelCount: number;
  modelCapabilities: Record<string, LocalModelCapability>;
}

export const MODEL_PROVIDER_OPTIONS: ModelProviderOption[] = [
  {
    value: "openai_compat",
    label: "OpenAI Compatible",
    description: "Any server exposing /v1/models and /v1/chat/completions.",
  },
  {
    value: "lmstudio",
    label: "LM Studio",
    description: "Native LM Studio metadata plus OpenAI-compatible inference.",
    defaultHost: "http://localhost:1234",
  },
  {
    value: "ollama",
    label: "Ollama",
    description: "Ollama native tags/show/chat/embed endpoints.",
    defaultHost: "http://localhost:11434",
  },
  {
    value: "llamacpp",
    label: "llama.cpp",
    description: "llama-server OpenAI-compatible endpoint.",
    defaultHost: "http://localhost:8080",
  },
  {
    value: "vllm",
    label: "vLLM",
    description: "vLLM OpenAI-compatible API server.",
    defaultHost: "http://localhost:8000",
  },
  {
    value: "sglang",
    label: "SGLang",
    description: "SGLang OpenAI-compatible API server.",
    defaultHost: "http://localhost:30000",
  },
  {
    value: "mlx",
    label: "MLX",
    description: "MLX/MLX-LM OpenAI-compatible local server.",
  },
  {
    value: "gemini_openai",
    label: "Gemini OpenAI",
    description: "Google Gemini's OpenAI-compatible endpoint.",
    defaultHost: "https://generativelanguage.googleapis.com/v1beta/openai",
  },
  {
    value: "anthropic",
    label: "Anthropic",
    description: "Claude Messages API with Anthropic model discovery.",
    defaultHost: "https://api.anthropic.com",
  },
];

const PROVIDER_LABELS = Object.fromEntries(
  MODEL_PROVIDER_OPTIONS.map((option) => [option.value, option.label])
);

export const LOCAL_LLM_CANDIDATES: Array<{ providerType: string; host: string }> = [
  { providerType: "lmstudio", host: "http://localhost:1234" },
  { providerType: "lmstudio", host: "http://127.0.0.1:1234" },
  { providerType: "ollama", host: "http://localhost:11434" },
  { providerType: "ollama", host: "http://127.0.0.1:11434" },
  { providerType: "llamacpp", host: "http://localhost:8080" },
  { providerType: "llamacpp", host: "http://127.0.0.1:8080" },
  { providerType: "vllm", host: "http://localhost:8000" },
  { providerType: "sglang", host: "http://localhost:30000" },
];

export function providerLabel(providerType?: string | null): string {
  if (!providerType) return "Unknown";
  return PROVIDER_LABELS[providerType] || providerType;
}

export function defaultHostForProvider(providerType: string): string {
  return MODEL_PROVIDER_OPTIONS.find((option) => option.value === providerType)?.defaultHost || "";
}

export function openAIUrl(host: string, providerType: string, suffix: string): string {
  const cleanHost = host.replace(/\/+$/, "");
  const cleanSuffix = suffix.replace(/^\/+/, "");
  try {
    const parsed = new URL(cleanHost.includes("://") ? cleanHost : `http://${cleanHost}`);
    const path = parsed.pathname.replace(/\/+$/, "");
    const hasOpenAIBase =
      providerType === "gemini_openai"
      || parsed.hostname.includes("generativelanguage.googleapis.com")
      || path.endsWith("/openai")
      || path.endsWith("/v1");
    return hasOpenAIBase
      ? `${cleanHost}/${cleanSuffix}`
      : `${cleanHost}/v1/${cleanSuffix}`;
  } catch {
    return `${cleanHost}/v1/${cleanSuffix}`;
  }
}

function capabilityFromName(name: string, providerType: string): LocalModelCapability {
  const lower = name.toLowerCase();
  const match = name.match(/(\d+\.?\d*)\s*b/i);
  const params = match ? `${match[1]}B` : "unknown";
  const paramNum = match ? Number.parseFloat(match[1]) : 0;
  const context = lower.includes("claude")
    ? 200000
    : paramNum > 12
      ? 32768
      : paramNum > 4
        ? 8192
        : 4096;
  const supportsTools =
    paramNum >= 7
    || ["qwen", "llama-3", "llama-4", "mistral", "gemma", "gpt", "claude"].some((family) =>
      lower.includes(family)
    );
  const supportsVision = [
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
  ].some((token) => lower.includes(token));
  const supportsAudio = ["audio", "omni", "whisper", "ultravox"].some((token) =>
    lower.includes(token)
  );
  return {
    name,
    parameter_count: params,
    context_length: context,
    trained_context_length: context,
    loaded_context_length: null,
    supports_tools: supportsTools,
    supports_vision: supportsVision,
    supports_audio: supportsAudio,
    supports_json: supportsTools || ["json", "instruct", "gpt", "claude"].some((token) =>
      lower.includes(token)
    ),
    quantization: null,
    source: providerType,
    is_loaded: null,
    endpoint_family: providerType === "ollama" ? "ollama" : "openai",
    modalities: { text: true, vision: supportsVision, audio: supportsAudio },
  };
}

function applyCapabilityMetadata(cap: LocalModelCapability, metadata: unknown) {
  if (!metadata) return;
  if (Array.isArray(metadata)) {
    const normalized = metadata.map((item) => String(item).toLowerCase());
    cap.supports_tools ||= normalized.some((item) =>
      ["tool", "tools", "tool_use", "function_calling"].includes(item)
    );
    cap.supports_vision ||= normalized.some((item) =>
      ["vision", "image", "images", "multimodal"].includes(item)
    );
    cap.supports_audio ||= normalized.some((item) =>
      ["audio", "input_audio", "audio_input"].includes(item)
    );
    cap.supports_json ||= normalized.some((item) =>
      ["json", "json_mode", "structured_outputs"].includes(item)
    );
  } else if (typeof metadata === "object") {
    const record = metadata as Record<string, unknown>;
    cap.supports_vision ||= Boolean(record.vision || record.image || record.images || record.multimodal);
    cap.supports_audio ||= Boolean(record.audio || record.input_audio || record.audio_input);
    cap.supports_tools ||= Boolean(record.trained_for_tool_use || record.tool_use || record.tools || record.function_calling);
    cap.supports_json ||= Boolean(record.json || record.json_mode || record.structured_outputs || record.response_format);
  }
  if (cap.modalities) {
    cap.modalities.vision = cap.supports_vision;
    cap.modalities.audio = cap.supports_audio;
  }
}

function contextFromObject(value: unknown): number | null {
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
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    const parsed = Number.parseInt(String(raw), 10);
    const normalized = key.toLowerCase();
    if ((exact.has(normalized) || normalized.endsWith(".context_length")) && parsed > 0) {
      return parsed;
    }
  }
  return null;
}

function parseOpenAIModels(data: any, providerType: string) {
  const rawModels = Array.isArray(data) ? data : data?.data || [];
  const models: string[] = [];
  const modelCapabilities: Record<string, LocalModelCapability> = {};
  for (const model of rawModels) {
    const id = model?.id || model?.name || "";
    if (!id) continue;
    const cap = capabilityFromName(id, providerType);
    const context =
      model?.max_model_len
      || model?.max_context_length
      || model?.max_tokens
      || model?.context_length
      || model?.context_window
      || model?.n_ctx
      || contextFromObject(model?.metadata);
    if (context) {
      cap.context_length = Number(context);
      cap.trained_context_length = Number(context);
    }
    applyCapabilityMetadata(cap, model?.capabilities);
    applyCapabilityMetadata(cap, model?.metadata?.capabilities);
    if (model?.type === "vlm") cap.supports_vision = true;
    if (model?.type === "audio") cap.supports_audio = true;
    if (model?.loaded != null) cap.is_loaded = Boolean(model.loaded);
    models.push(id);
    modelCapabilities[id] = cap;
  }
  return { models, modelCapabilities };
}

function parseLMStudioModels(data: any) {
  const models: string[] = [];
  const modelCapabilities: Record<string, LocalModelCapability> = {};
  for (const model of data?.models || []) {
    const id = model?.key || model?.id || model?.name || "";
    if (!id) continue;
    const cap = capabilityFromName(id, "lmstudio");
    const trainedContext = model?.max_context_length || model?.context_length;
    if (trainedContext) {
      cap.context_length = Number(trainedContext);
      cap.trained_context_length = Number(trainedContext);
    }
    if (Array.isArray(model?.loaded_instances)) {
      cap.is_loaded = model.loaded_instances.length > 0;
      const loadedContext = model.loaded_instances
        .map((instance: any) => instance?.config?.context_length)
        .find((value: unknown) => Number.isFinite(value));
      if (loadedContext) {
        cap.context_length = Number(loadedContext);
        cap.loaded_context_length = Number(loadedContext);
      }
    }
    if (model?.type === "vlm") cap.supports_vision = true;
    if (model?.type === "audio") cap.supports_audio = true;
    applyCapabilityMetadata(cap, model?.capabilities);
    if (typeof model?.quantization === "string") cap.quantization = model.quantization;
    if (model?.quantization?.name) cap.quantization = model.quantization.name;
    models.push(id);
    modelCapabilities[id] = cap;
  }
  return { models, modelCapabilities };
}

function parseOllamaModels(data: any) {
  const models: string[] = [];
  const modelCapabilities: Record<string, LocalModelCapability> = {};
  for (const model of data?.models || []) {
    const id = model?.name || model?.model || "";
    if (!id) continue;
    const cap = capabilityFromName(id, "ollama");
    cap.endpoint_family = "ollama";
    cap.is_loaded = false;
    if (model?.details?.parameter_size) cap.parameter_count = model.details.parameter_size;
    if (model?.details?.quantization_level) cap.quantization = model.details.quantization_level;
    models.push(id);
    modelCapabilities[id] = cap;
  }
  return { models, modelCapabilities };
}

export async function detectLocalLLM(): Promise<LocalLLMDetection | null> {
  for (const candidate of LOCAL_LLM_CANDIDATES) {
    try {
      const url =
        candidate.providerType === "ollama"
          ? `${candidate.host}/api/tags`
          : candidate.providerType === "lmstudio"
            ? `${candidate.host}/api/v1/models`
            : openAIUrl(candidate.host, candidate.providerType, "models");
      const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (!res.ok) continue;
      const data = await res.json();
      const parsed =
        candidate.providerType === "ollama"
          ? parseOllamaModels(data)
          : candidate.providerType === "lmstudio"
            ? parseLMStudioModels(data)
            : parseOpenAIModels(data, candidate.providerType);
      return {
        provider: candidate.providerType,
        providerType: candidate.providerType,
        host: candidate.host,
        models: parsed.models,
        modelCount: parsed.models.length,
        modelCapabilities: parsed.modelCapabilities,
      };
    } catch {
      // Try the next known local provider.
    }
  }
  return null;
}
