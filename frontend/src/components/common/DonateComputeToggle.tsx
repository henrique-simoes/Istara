"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Cpu, Wifi, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";

import { WS_BASE } from "@/lib/runtimeConfig";
import {
  detectLocalLLM,
  openAIUrl,
  providerLabel,
  type LocalLLMDetection,
} from "@/lib/modelProviders";

/**
 * Browser-based compute donation toggle.
 *
 * When enabled, opens a WebSocket to /ws/relay and registers as a
 * browser compute node. Proxies LLM requests from the server to a
 * local model-server instance.
 *
 * Limitation: browser tabs are throttled when backgrounded, so this
 * is a convenience feature. For reliable donation, use the desktop app.
 */
export default function DonateComputeToggle() {
  const [enabled, setEnabled] = useState(false);
  const [connected, setConnected] = useState(false);
  const [localLLM, setLocalLLM] = useState<LocalLLMDetection | null>(null);
  const [donationError, setDonationError] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);

  // Detect local LLM on mount
  useEffect(() => {
    async function detectLLM() {
      setLocalLLM(await detectLocalLLM());
    }
    detectLLM();
  }, []);

  const fetchModelProbe = useCallback(async (): Promise<Pick<LocalLLMDetection, "models" | "modelCapabilities">> => {
    try {
      if (localLLM?.providerType === "ollama") {
        const res = await fetch(`${localLLM.host}/api/tags`);
        const data = await res.json();
        const models = (data.models || []).map((m: any) => m.name).filter(Boolean);
        return {
          models,
          modelCapabilities: Object.fromEntries(
            models.map((model: string) => [
              model,
              localLLM.modelCapabilities[model] || {
                name: model,
                source: "ollama",
                supports_tools: false,
                supports_vision: false,
                supports_audio: false,
                supports_json: false,
                context_length: 4096,
                parameter_count: "unknown",
                is_loaded: null,
              },
            ])
          ),
        };
      }
      const endpoint =
        localLLM?.providerType === "lmstudio"
          ? `${localLLM.host}/api/v1/models`
          : openAIUrl(localLLM?.host || "", localLLM?.providerType || "openai_compat", "models");
      const res = await fetch(endpoint);
      const data = await res.json();
      const rawModels = localLLM?.providerType === "lmstudio" ? data.models || [] : data.data || [];
      const models = rawModels.map((m: any) => m.key || m.id || m.name).filter(Boolean);
      return {
        models,
        modelCapabilities: Object.fromEntries(
          models.map((model: string) => [
            model,
            localLLM?.modelCapabilities[model] || {
              name: model,
              source: localLLM?.providerType || "openai_compat",
              supports_tools: false,
              supports_vision: false,
              supports_audio: false,
              supports_json: false,
              context_length: 4096,
              parameter_count: "unknown",
              is_loaded: null,
            },
          ])
        ),
      };
    } catch { return { models: [], modelCapabilities: {} }; }
  }, [localLLM]);

  // Manage WebSocket connection
  useEffect(() => {
    if (!enabled || !localLLM) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
      return;
    }

    const token = localStorage.getItem("istara_token");
    const url = `${WS_BASE}/ws/relay${token ? `?token=${token}` : ""}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = async () => {
      setConnected(true);
      setDonationError("");
      // Register as browser node
      const modelProbe = await fetchModelProbe();
      ws.send(JSON.stringify({
        type: "register",
        hostname: `Browser (${navigator.userAgent.split(" ").pop()})`,
        user_id: "browser",
        provider_type: localLLM.providerType,
        provider_host: localLLM.host,
        loaded_models: modelProbe.models,
        model_capabilities: modelProbe.modelCapabilities,
        ram_total_gb: (navigator as any).deviceMemory || 0,
        cpu_cores: navigator.hardwareConcurrency || 0,
      }));
    };

    ws.onmessage = async (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "llm_request") {
          // Proxy the LLM request to local server
          const result = await proxyRequest(msg, localLLM);
          if (result?.error) setDonationError(String(result.error));
          else setDonationError("");
          ws.send(JSON.stringify({
            type: "llm_response",
            request_id: msg.request_id,
            ...(result?.error ? { error: result.error } : { result }),
          }));
        } else if (msg.type === "embed_request") {
          const result = await proxyEmbedding(msg, localLLM);
          if (result?.error) setDonationError(String(result.error));
          else setDonationError("");
          ws.send(JSON.stringify({
            type: "embed_response",
            request_id: msg.request_id,
            ...(result?.error ? { error: result.error } : { result }),
          }));
        }
      } catch (e) {
        console.error("Donate compute error:", e);
      }
    };

    ws.onclose = () => setConnected(false);
    ws.onerror = () => {
      setDonationError("Relay connection failed");
      setConnected(false);
    };

    // Heartbeat
    const heartbeat = setInterval(async () => {
      if (ws.readyState === WebSocket.OPEN) {
        const modelProbe = await fetchModelProbe();
        ws.send(JSON.stringify({
          type: "heartbeat",
          stats: {
            ram_available_gb: 0,
            cpu_load_pct: 0,
            loaded_models: modelProbe.models,
            model_capabilities: modelProbe.modelCapabilities,
            state: "idle",
          },
        }));
      }
    }, 30000);

    return () => {
      clearInterval(heartbeat);
      ws.close();
      wsRef.current = null;
      setConnected(false);
    };
  }, [enabled, fetchModelProbe, localLLM]);

  async function proxyRequest(msg: any, provider: LocalLLMDetection) {
    try {
      const host = provider.host;
      const endpoint =
        provider.providerType === "ollama"
          ? `${host}/api/chat`
          : openAIUrl(host, provider.providerType, "chat/completions");

      const body = provider.providerType === "ollama"
        ? { model: msg.model, messages: msg.messages, stream: false }
        : {
            model: msg.model,
            messages: msg.messages,
            stream: false,
            temperature: msg.temperature,
            max_tokens: msg.max_tokens,
            tools: msg.tools,
            response_format: msg.response_format,
          };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        return { error: data?.error?.message || data?.error || `HTTP ${res.status}` };
      }
      if (provider.providerType === "ollama") {
        return data;
      }
      const choice = data?.choices?.[0] || {};
      const message = choice.message || {};
      const result: any = {
        message: {
          role: "assistant",
          content: message.content || "",
        },
      };
      if (message.tool_calls) {
        result.message.tool_calls = message.tool_calls;
        result.finish_reason = choice.finish_reason || "tool_calls";
      }
      return result;
    } catch (e: any) {
      return { error: e.message };
    }
  }

  async function proxyEmbedding(msg: any, provider: LocalLLMDetection) {
    try {
      const host = provider.host;
      const endpoint =
        provider.providerType === "ollama"
          ? `${host}/api/embed`
          : openAIUrl(host, provider.providerType, "embeddings");
      const body = provider.providerType === "ollama"
        ? { model: msg.model, input: msg.input }
        : { model: msg.model, input: msg.input };
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        return { error: data?.error?.message || data?.error || `HTTP ${res.status}` };
      }
      if (provider.providerType === "ollama") {
        if (Array.isArray(msg.input)) return data.embeddings || [];
        return data.embeddings?.[0] || [];
      }
      const embeddings = (data.data || []).map((item: any) => item.embedding || []);
      return Array.isArray(msg.input) ? embeddings : embeddings[0] || [];
    } catch (e: any) {
      return { error: e.message };
    }
  }

  if (!localLLM) return null; // No local LLM detected — don't show toggle

  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
      <Cpu size={16} className="text-slate-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Donate Compute
        </p>
        <p className="text-xs text-slate-400">
          {donationError
            ? donationError
            : connected
            ? "Sharing your local LLM with the server"
            : `${providerLabel(localLLM.providerType)} detected`
          }
        </p>
      </div>
      <div className="flex items-center gap-2">
        {enabled && (
          connected
            ? <Wifi size={14} className="text-green-500" />
            : <WifiOff size={14} className="text-red-400" />
        )}
        <button
          onClick={() => setEnabled(!enabled)}
          className={cn(
            "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
            enabled ? "bg-istara-600" : "bg-slate-300 dark:bg-slate-600"
          )}
          role="switch"
          aria-checked={enabled}
          aria-label="Toggle compute donation"
        >
          <span
            className={cn(
              "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
              enabled ? "translate-x-6" : "translate-x-1"
            )}
          />
        </button>
      </div>
    </div>
  );
}
