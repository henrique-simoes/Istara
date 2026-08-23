import { API_BASE } from "@/lib/runtimeConfig";
import type { ChatUsage, PiCatalogProvider, PiEndpointInfo, ThinkingMode } from "@/lib/types";

function authHeaders(): Record<string, string> {
  const token = typeof window === "undefined" ? "" : localStorage.getItem("istara_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function json<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(((await res.json().catch(() => ({}))) as any).detail || `API error: ${res.status}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const chat = {
  send: async function* (
    projectId: string,
    message: string,
    sessionId?: string,
    signal?: AbortSignal,
    thinkingMode?: ThinkingMode,
    engine?: "pi" | "legacy"
  ) {
    const payload: Record<string, unknown> = { message, project_id: projectId };
    if (sessionId) payload.session_id = sessionId;
    if (thinkingMode) payload.thinking_mode = thinkingMode;
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        // Per-request Agentic Core override so the backend routes this turn
        // through the exact core shown in the UI (CF-SPEC-1 ITEM-001).
        ...(engine ? { "x-istara-agent-engine": engine } : {}),
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!res.ok) throw new Error(`Chat error: ${res.status}`);
    if (!res.body) throw new Error("No response body");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    const timeoutMs = 60_000;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const resetTimeout = () => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => reader.cancel("SSE read timeout"), timeoutMs);
    };
    resetTimeout();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        resetTimeout();

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              yield JSON.parse(line.slice(6));
            } catch {
              // Skip malformed SSE lines.
            }
          }
        }
      }
    } finally {
      clearTimeout(timeout);
    }
  },
  history: (projectId: string, limit = 50) =>
    json<any[]>(`/api/chat/history/${projectId}?limit=${limit}`),
  modelCatalog: (projectId: string) =>
    json<{ providers: PiCatalogProvider[]; total_models: number; configured: PiEndpointInfo[]; legacy_models: string[]; engine: string }>(
      `/api/chat/model-catalog?project_id=${encodeURIComponent(projectId)}`
    ),
  usage: (projectId: string, sessionId?: string) =>
    json<ChatUsage>(
      `/api/chat/usage/${encodeURIComponent(projectId)}${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`
    ),
  transcribeVoice: async (audioFile: File, projectId: string, language?: string): Promise<{
    text: string;
    language: string;
    confidence: number;
    icr_kappa: number;
    icr_confidence: string;
    needs_review: boolean;
    tags: string[];
  }> => {
    const formData = new FormData();
    formData.append("audio", audioFile);
    formData.append("project_id", projectId);
    if (language) formData.append("language", language);

    const res = await fetch(`${API_BASE}/api/chat/voice`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });

    if (!res.ok) throw new Error(`Voice transcription error: ${res.status}`);
    return res.json();
  },
};
