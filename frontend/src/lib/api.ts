/** API client for ReClaw backend. */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// --- Projects ---

export const projects = {
  list: () => request<any[]>("/api/projects"),
  get: (id: string) => request<any>(`/api/projects/${id}`),
  create: (data: { name: string; description?: string }) =>
    request<any>("/api/projects", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetch(`${API_BASE}/api/projects/${id}`, { method: "DELETE" }),
  versions: (id: string) => request<any[]>(`/api/projects/${id}/versions`),
};

// --- Tasks ---

export const tasks = {
  list: (projectId?: string, status?: string) => {
    const params = new URLSearchParams();
    if (projectId) params.set("project_id", projectId);
    if (status) params.set("status", status);
    return request<any[]>(`/api/tasks?${params}`);
  },
  create: (data: { project_id: string; title: string; description?: string }) =>
    request<any>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  move: (id: string, status: string) =>
    request<any>(`/api/tasks/${id}/move?status=${status}`, { method: "POST" }),
  delete: (id: string) =>
    fetch(`${API_BASE}/api/tasks/${id}`, { method: "DELETE" }),
};

// --- Chat ---

export const chat = {
  send: async function* (projectId: string, message: string) {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, project_id: projectId }),
    });

    if (!res.ok) throw new Error(`Chat error: ${res.status}`);
    if (!res.body) throw new Error("No response body");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6));
          } catch {
            // Skip malformed SSE lines
          }
        }
      }
    }
  },
  history: (projectId: string, limit = 50) =>
    request<any[]>(`/api/chat/history/${projectId}?limit=${limit}`),
};

// --- Findings ---

export const findings = {
  nuggets: (projectId?: string) => {
    const params = projectId ? `?project_id=${projectId}` : "";
    return request<any[]>(`/api/findings/nuggets${params}`);
  },
  facts: (projectId?: string) => {
    const params = projectId ? `?project_id=${projectId}` : "";
    return request<any[]>(`/api/findings/facts${params}`);
  },
  insights: (projectId?: string) => {
    const params = projectId ? `?project_id=${projectId}` : "";
    return request<any[]>(`/api/findings/insights${params}`);
  },
  recommendations: (projectId?: string) => {
    const params = projectId ? `?project_id=${projectId}` : "";
    return request<any[]>(`/api/findings/recommendations${params}`);
  },
  summary: (projectId: string) =>
    request<any>(`/api/findings/summary/${projectId}`),
};

// --- Files ---

export const files = {
  upload: async (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/files/upload/${projectId}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload error: ${res.status}`);
    return res.json();
  },
  list: (projectId: string) => request<any>(`/api/files/${projectId}`),
  stats: (projectId: string) => request<any>(`/api/files/${projectId}/stats`),
};

// --- Skills ---

export const skills = {
  list: (phase?: string) => {
    const params = phase ? `?phase=${phase}` : "";
    return request<any>(`/api/skills${params}`);
  },
  get: (name: string) => request<any>(`/api/skills/${name}`),
  create: (data: {
    name: string;
    display_name: string;
    description: string;
    phase: string;
    skill_type: string;
    plan_prompt?: string;
    execute_prompt?: string;
    output_schema?: string;
  }) => request<any>("/api/skills", { method: "POST", body: JSON.stringify(data) }),
  update: (name: string, data: Record<string, unknown>) =>
    request<any>(`/api/skills/${name}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (name: string) =>
    fetch(`${API_BASE}/api/skills/${name}`, { method: "DELETE" }),
  toggle: (name: string, enabled: boolean) =>
    request<any>(`/api/skills/${name}/toggle?enabled=${enabled}`, { method: "POST" }),
  execute: (name: string, data: { project_id: string; user_context?: string }) =>
    request<any>(`/api/skills/${name}/execute`, { method: "POST", body: JSON.stringify(data) }),
  health: () => request<any>("/api/skills/health/all"),
  skillHealth: (name: string) => request<any>(`/api/skills/${name}/health`),
  proposals: {
    pending: () => request<any>("/api/skills/proposals/pending"),
    all: (limit = 50) => request<any>(`/api/skills/proposals/all?limit=${limit}`),
    approve: (id: string) =>
      request<any>(`/api/skills/proposals/${id}/approve`, { method: "POST" }),
    reject: (id: string, reason = "") =>
      request<any>(`/api/skills/proposals/${id}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" }),
  },
};

// --- Settings ---

export const settings = {
  hardware: () => request<any>("/api/settings/hardware"),
  models: () => request<any>("/api/settings/models"),
  status: () => request<any>("/api/settings/status"),
  switchModel: (model: string) =>
    request<any>(`/api/settings/model?model_name=${model}`, { method: "POST" }),
};
