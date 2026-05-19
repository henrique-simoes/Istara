import type { ChatMessage, ChatSession, InferencePresetConfig, ThinkingMode } from "@/lib/types";
import { API_BASE } from "@/lib/runtimeConfig";

function authHeaders(): Record<string, string> {
  const token = typeof window === "undefined" ? "" : localStorage.getItem("istara_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function projectQuery(projectId: string): string {
  return `project_id=${encodeURIComponent(projectId)}`;
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
    thinking_mode?: ThinkingMode;
  }) => json<ChatSession>("/api/sessions", { method: "POST", body: JSON.stringify(data) }),
  get: (sessionId: string, projectId: string) =>
    json<ChatSession & { messages: ChatMessage[] }>(
      `/api/sessions/detail/${sessionId}?${projectQuery(projectId)}`
    ),
  update: (sessionId: string, projectId: string, data: Record<string, unknown>) =>
    json<ChatSession>(`/api/sessions/${sessionId}?${projectQuery(projectId)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (sessionId: string, projectId: string) =>
    json<void>(`/api/sessions/${sessionId}?${projectQuery(projectId)}`, { method: "DELETE" }),
  star: (sessionId: string, projectId: string) =>
    json<{ starred: boolean }>(`/api/sessions/${sessionId}/star?${projectQuery(projectId)}`, {
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
