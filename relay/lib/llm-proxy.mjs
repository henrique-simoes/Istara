/**
 * LLM Proxy — forwards LLM requests to local Ollama or LM Studio.
 * Supports optional API key for servers that require authentication.
 */

export function inferProviderType(providerType, host) {
  const requested = (providerType || "").trim().toLowerCase();
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
  if (parsed.port === "1234") return "lmstudio";
  if (path.endsWith("/v1")) return "openai_compat";
  if (parsed.port === "11434") return "ollama";
  return requested || "openai_compat";
}

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
      h["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return h;
  }

  async listModels() {
    try {
      const url = this.providerType === "ollama"
        ? `${this.host}/api/tags`
        : this._openAIUrl("models");

      const res = await fetch(url, {
        headers: this._headers(),
        signal: AbortSignal.timeout(5000),
      });
      if (!res.ok) return [];

      const data = await res.json();
      if (this.providerType === "ollama") {
        return (data.models || []).map((m) => m.name);
      } else {
        return (data.data || []).map((m) => m.id);
      }
    } catch {
      return [];
    }
  }

  async handleRequest(msg) {
    const { messages, model, temperature, max_tokens } = msg;

    if (this.providerType === "ollama") {
      const payload = {
        model: model || "default",
        messages,
        stream: false,
        options: { temperature: temperature || 0.7 },
      };
      if (max_tokens) payload.options.num_predict = max_tokens;

      const res = await fetch(`${this.host}/api/chat`, {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    } else {
      // OpenAI-compatible (LM Studio, Gemini, and compatible local servers)
      const payload = {
        model: model || "default",
        messages,
        temperature: temperature || 0.7,
        stream: false,
      };
      if (max_tokens) payload.max_tokens = max_tokens;

      const res = await fetch(this._openAIUrl("chat/completions"), {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      // Normalize to Ollama format
      const content = data.choices?.[0]?.message?.content || "";
      return { message: { role: "assistant", content } };
    }
  }

  async handleEmbedding(msg) {
    const input = msg.input;
    const model = msg.model || "default";

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
}
