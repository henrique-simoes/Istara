import type { ChatMessage, ChatSession, InferencePresetConfig } from "@/lib/types";
import { API_BASE } from "@/lib/runtimeConfig";

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

export const sessions = {
  list: (projectId: string) =>
    json<{ sessions: ChatSession[] }>(`/api/sessions/${projectId}`).then((r) => r.sessions),
  create: (data: {
    project_id: string;
    title?: string;
    agent_id?: string;
    inference_preset?: string;
  }) => json<ChatSession>("/api/sessions", { method: "POST", body: JSON.stringify(data) }),
  get: (sessionId: string) =>
    json<ChatSession & { messages: ChatMessage[] }>(`/api/sessions/detail/${sessionId}`),
  update: (sessionId: string, data: Record<string, unknown>) =>
    json<ChatSession>(`/api/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (sessionId: string) =>
    json<void>(`/api/sessions/${sessionId}`, { method: "DELETE" }),
  star: (sessionId: string) =>
    json<{ starred: boolean }>(`/api/sessions/${sessionId}/star`, {
      method: "POST",
      body: "{}",
    }),
  ensureDefault: (projectId: string) =>
    json<ChatSession>(`/api/sessions/${projectId}/ensure-default`),
  presets: () =>
    json<{ presets: Record<string, InferencePresetConfig> }>("/api/inference-presets").then(
      (r) => r.presets
    ),
};
