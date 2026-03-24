/**
 * LLM Proxy — forwards LLM requests to local Ollama or LM Studio.
 */

export class LLMProxy {
  constructor(providerType, host) {
    this.providerType = providerType; // ollama | lmstudio
    this.host = host.replace(/\/$/, "");
  }

  async listModels() {
    try {
      const url = this.providerType === "ollama"
        ? `${this.host}/api/tags`
        : `${this.host}/v1/models`;

      const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return await res.json();
    } else {
      // OpenAI-compatible (LM Studio)
      const payload = {
        model: model || "default",
        messages,
        temperature: temperature || 0.7,
        stream: false,
      };
      if (max_tokens) payload.max_tokens = max_tokens;

      const res = await fetch(`${this.host}/v1/chat/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      // Normalize to Ollama format
      const content = data.choices?.[0]?.message?.content || "";
      return { message: { role: "assistant", content } };
    }
  }
}
