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

const queryString = (params?: Record<string, string | number | boolean>) =>
  params ? `?${new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)])).toString()}` : "";

export const notificationsApi = {
  list: (params?: Record<string, string | number | boolean>) => json<any>(`/api/notifications${queryString(params)}`),
  unreadCount: (projectId: string) => json<{ count: number }>(`/api/notifications/unread-count?${new URLSearchParams({ project_id: projectId }).toString()}`),
  markRead: (id: string, projectId: string) => json<any>(`/api/notifications/${id}/read${queryString({ project_id: projectId })}`, { method: "POST", body: "{}" }),
  markAllRead: (projectId: string) => json<any>("/api/notifications/read-all", { method: "POST", body: JSON.stringify({ project_id: projectId }) }),
  delete: (id: string, projectId: string) => json<void>(`/api/notifications/${id}${queryString({ project_id: projectId })}`, { method: "DELETE" }),
  preferences: () => json<any>("/api/notifications/preferences"),
  updatePreferences: (prefs: any[]) => json<any>("/api/notifications/preferences", { method: "PUT", body: JSON.stringify({ preferences: prefs }) }),
};
