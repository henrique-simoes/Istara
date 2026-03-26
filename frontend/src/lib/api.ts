/** API client for ReClaw backend. */

import type { ChatSession, ChatMessage, InferencePresetConfig, DAGNode, DAGHealth, DAGExpandResult, DAGGrepResult, ReclawDocument, DocumentContent, DocumentTag, DocumentStats, InterfacesStatus } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function _getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("reclaw_token");
  if (token && token !== "local-mode") {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ..._getAuthHeaders(), ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

function post<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(data) });
}

function patch<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(data) });
}

function del(path: string): Promise<Response> {
  return fetch(`${API_BASE}${path}`, { method: "DELETE" });
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
  create: (data: {
    project_id: string;
    title: string;
    description?: string;
    skill_name?: string;
    instructions?: string;
    priority?: string;
    input_document_ids?: string[];
    output_document_ids?: string[];
    urls?: string[];
    user_context?: string;
    agent_id?: string;
  }) => request<any>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  move: (id: string, status: string) =>
    request<any>(`/api/tasks/${id}/move?status=${status}`, { method: "POST" }),
  delete: (id: string) =>
    fetch(`${API_BASE}/api/tasks/${id}`, { method: "DELETE" }),
  attach: (taskId: string, documentId: string, direction: "input" | "output" = "input") =>
    post<{ attached: boolean }>(`/api/tasks/${taskId}/attach?document_id=${documentId}&direction=${direction}`, {}),
  detach: (taskId: string, documentId: string, direction: "input" | "output" = "input") =>
    post<{ detached: boolean }>(`/api/tasks/${taskId}/detach?document_id=${documentId}&direction=${direction}`, {}),
};

// --- Chat ---

export const chat = {
  send: async function* (projectId: string, message: string, sessionId?: string) {
    const payload: Record<string, unknown> = { message, project_id: projectId };
    if (sessionId) payload.session_id = sessionId;
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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
  evidenceChain: (findingType: string, findingId: string) =>
    request<any>(`/api/findings/${findingType}/${findingId}/evidence-chain`),
  createNugget: (projectId: string, data: { text: string; source: string; source_location?: string; tags?: string[] }) =>
    post<any>("/api/findings/nuggets", { project_id: projectId, ...data }),
  linkEvidence: (findingType: string, findingId: string, linkId: string, linkType: string) =>
    patch<any>(`/api/findings/${findingType}/${findingId}/link`, { link_id: linkId, link_type: linkType }),
  delete: (type: "nugget" | "fact" | "insight" | "recommendation", id: string) => {
    const plural: Record<string, string> = {
      nugget: "nuggets",
      fact: "facts",
      insight: "insights",
      recommendation: "recommendations",
    };
    return fetch(`${API_BASE}/api/findings/${plural[type]}/${id}`, { method: "DELETE" });
  },
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
  content: (projectId: string, filename: string) =>
    request<{ filename: string; type: string; content: string | null; media_url?: string; pages?: number; size: number }>(
      `/api/files/${projectId}/content/${encodeURIComponent(filename)}`
    ),
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
  creationProposals: {
    pending: () => request<any>("/api/skills/creation-proposals/pending"),
    all: (limit = 20) => request<any>(`/api/skills/creation-proposals/all?limit=${limit}`),
    approve: (id: string) =>
      request<any>(`/api/skills/creation-proposals/${id}/approve`, { method: "POST" }),
    reject: (id: string, reason = "") =>
      request<any>(`/api/skills/creation-proposals/${id}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" }),
  },
};

// --- Agents ---

export const agents = {
  list: (includeSystem = true) =>
    request<any>(`/api/agents?include_system=${includeSystem}`),
  get: (id: string) => request<any>(`/api/agents/${id}`),
  create: (data: {
    name: string;
    role?: string;
    system_prompt?: string;
    capabilities?: string[];
    heartbeat_interval?: number;
  }) => request<any>("/api/agents", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/agents/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetch(`${API_BASE}/api/agents/${id}`, { method: "DELETE" }),
  pause: (id: string) =>
    request<any>(`/api/agents/${id}/pause`, { method: "POST" }),
  resume: (id: string) =>
    request<any>(`/api/agents/${id}/resume`, { method: "POST" }),
  uploadAvatar: async (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/agents/${id}/avatar`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload error: ${res.status}`);
    return res.json();
  },
  avatarUrl: (id: string) => `${API_BASE}/api/agents/${id}/avatar`,
  memory: (id: string) => request<any>(`/api/agents/${id}/memory`),
  updateMemory: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/agents/${id}/memory`, { method: "PATCH", body: JSON.stringify(data) }),
  messages: (id: string, limit = 50) =>
    request<any>(`/api/agents/${id}/messages?limit=${limit}`),
  sendMessage: (
    id: string,
    data: { to_agent_id?: string; content: string; message_type?: string }
  ) =>
    request<any>(`/api/agents/${id}/messages`, { method: "POST", body: JSON.stringify(data) }),
  a2aLog: (limit = 100) => request<any>(`/api/agents/a2a/log?limit=${limit}`),
  heartbeat: () => request<any>("/api/agents/heartbeat/status"),
  capacity: () => request<any>("/api/agents/capacity"),
  getIdentity: (id: string) =>
    request<{
      agent_id: string;
      display_name: string;
      has_persona: boolean;
      identity_length: number;
      files: Record<string, string>;
    }>(`/api/agents/${id}/identity`),
  updateIdentity: (id: string, files: Record<string, string>) =>
    request<any>(`/api/agents/${id}/identity`, {
      method: "PUT",
      body: JSON.stringify({ files }),
    }),
  listPersonas: () =>
    request<{ personas: { agent_id: string; display_name: string }[] }>(
      "/api/agents/personas/list"
    ),
  creationProposals: {
    pending: () => request<any>("/api/agents/creation-proposals/pending"),
    all: (limit = 20) => request<any>(`/api/agents/creation-proposals/all?limit=${limit}`),
    approve: (id: string) =>
      request<any>(`/api/agents/creation-proposals/${id}/approve`, { method: "POST" }),
    reject: (id: string, reason = "") =>
      request<any>(`/api/agents/creation-proposals/${id}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" }),
  },
};

// --- Sessions ---

export const sessions = {
  list: (projectId: string) => get<{ sessions: ChatSession[] }>(`/api/sessions/${projectId}`).then(r => r.sessions),
  create: (data: { project_id: string; title?: string; agent_id?: string; inference_preset?: string }) =>
    post<ChatSession>("/api/sessions", data),
  get: (sessionId: string) => get<ChatSession & { messages: ChatMessage[] }>(`/api/sessions/detail/${sessionId}`),
  update: (sessionId: string, data: Record<string, unknown>) =>
    patch<ChatSession>(`/api/sessions/${sessionId}`, data),
  delete: (sessionId: string) => del(`/api/sessions/${sessionId}`),
  star: (sessionId: string) => post<{ starred: boolean }>(`/api/sessions/${sessionId}/star`, {}),
  ensureDefault: (projectId: string) => get<ChatSession>(`/api/sessions/${projectId}/ensure-default`),
  presets: () => get<{ presets: Record<string, InferencePresetConfig> }>("/api/inference-presets").then(r => r.presets),
};

// --- Project Export ---

export const projectExport = {
  export: (projectId: string) => post<{ exported: boolean; path: string; files_count: number }>(`/api/projects/${projectId}/export`, {}),
};

// --- Memory ---

export const memory = {
  list: (projectId: string, page = 1, pageSize = 50) =>
    get<{
      chunks: Array<{
        text: string;
        source: string;
        page: number;
        agent_id: string;
        chunk_type: string;
        created_at: number;
        confidence: number;
      }>;
      total: number;
      page: number;
      page_size: number;
      sources?: Array<{ name: string; count: number }>;
      error?: string;
    }>(`/api/memory/${projectId}?page=${page}&page_size=${pageSize}`),
  search: (projectId: string, query: string, topK = 20) =>
    get<{
      results: Array<{
        text: string;
        source: string;
        score: number;
        page: number | null;
      }>;
      query: string;
      total: number;
    }>(`/api/memory/${projectId}/search?query=${encodeURIComponent(query)}&top_k=${topK}`),
  stats: (projectId: string) =>
    get<{
      vector_chunks: number;
      keyword_chunks: number;
      sources: Array<{ name: string; chunk_count: number }>;
      embedding_model: string;
      vector_dimensions: number;
      chunk_size: number;
      chunk_overlap: number;
      hybrid_weights: { vector: number; keyword: number };
    }>(`/api/memory/${projectId}/stats`),
  agentNotes: (projectId: string, agentId: string) =>
    get<{
      agent_id: string;
      project_id: string;
      notes: Array<{ text: string; source: string }>;
    }>(`/api/memory/${projectId}/agent/${agentId}/notes`),
  deleteSource: (projectId: string, sourceName: string) =>
    request<{ deleted: boolean; source: string }>(
      `/api/memory/${projectId}/source/${encodeURIComponent(sourceName)}`,
      { method: "DELETE" }
    ),
};

// --- Settings ---

export const settings = {
  hardware: () => request<any>("/api/settings/hardware"),
  models: () => request<any>("/api/settings/models"),
  status: () => request<any>("/api/settings/status"),
  switchModel: (model: string) =>
    request<any>(`/api/settings/model?model_name=${model}`, { method: "POST" }),
  switchProvider: (provider: "ollama" | "lmstudio") =>
    request<any>(`/api/settings/provider?provider=${provider}`, { method: "POST" }),
  maintenance: () => request<any>("/api/settings/maintenance"),
};

// --- Data Management ---

export const dataManagement = {
  checkIntegrity: () => request<any>("/api/settings/data-integrity"),
  exportDatabase: () => request<any>("/api/settings/export-database", { method: "POST" }),
  importDatabase: (data: any) =>
    request<any>("/api/settings/import-database", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// --- Task Locking ---

export const taskLocking = {
  lock: (taskId: string, userId: string = "local") =>
    post<any>(`/api/tasks/${taskId}/lock?user_id=${userId}`, {}),
  unlock: (taskId: string, userId: string = "local", force: boolean = false) =>
    post<any>(`/api/tasks/${taskId}/unlock?user_id=${userId}&force=${force}`, {}),
};

// --- LLM Servers ---

export const llmServers = {
  list: () => request<any>("/api/llm-servers"),
  add: (data: { name: string; provider_type: string; host: string; api_key?: string; priority?: number }) =>
    post<any>("/api/llm-servers", data),
  healthCheck: (serverId: string) =>
    post<any>(`/api/llm-servers/${serverId}/health-check`, {}),
  update: (serverId: string, data: Record<string, unknown>) =>
    patch<any>(`/api/llm-servers/${serverId}`, data),
  delete: (serverId: string) => del(`/api/llm-servers/${serverId}`),
  discover: () => post<any>("/api/llm-servers/discover", {}),
};

// --- Compute Pool ---

export const compute = {
  nodes: () => request<any>("/api/compute/nodes"),
  stats: () => request<any>("/api/compute/stats"),
};

// --- Documents ---

export const documents = {
  list: (params: {
    project_id?: string;
    phase?: string;
    tag?: string;
    source?: string;
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") query.set(k, String(v));
    });
    return get<{
      documents: ReclawDocument[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>(`/api/documents?${query}`);
  },
  get: (id: string) => get<ReclawDocument & { content_text: string }>(`/api/documents/${id}`),
  create: (data: {
    project_id: string;
    title: string;
    description?: string;
    file_path?: string;
    file_name?: string;
    file_type?: string;
    source?: string;
    task_id?: string;
    agent_ids?: string[];
    skill_names?: string[];
    tags?: string[];
    phase?: string;
    atomic_path?: Record<string, unknown>;
    content_preview?: string;
    content_text?: string;
  }) => post<ReclawDocument>("/api/documents", data),
  update: (id: string, data: Record<string, unknown>) =>
    patch<ReclawDocument>(`/api/documents/${id}`, data),
  delete: (id: string) => del(`/api/documents/${id}`),
  content: (id: string) => get<DocumentContent>(`/api/documents/${id}/content`),
  search: (projectId: string, q: string, phase?: string, tag?: string, limit = 20) => {
    const params = new URLSearchParams({ project_id: projectId, q, limit: String(limit) });
    if (phase) params.set("phase", phase);
    if (tag) params.set("tag", tag);
    return get<{ query: string; results: ReclawDocument[]; total: number }>(
      `/api/documents/search/full?${params}`
    );
  },
  tags: (projectId: string) =>
    get<{ tags: DocumentTag[] }>(`/api/documents/tags/${projectId}`),
  sync: (projectId: string) =>
    post<{ synced: number; total: number }>(`/api/documents/sync/${projectId}`, {}),
  stats: (projectId: string) =>
    get<DocumentStats>(`/api/documents/stats/${projectId}`),
};

// --- Interfaces ---

export const interfaces = {
  status: () => get<InterfacesStatus>("/api/interfaces/status"),

  screens: {
    list: (projectId: string) => get<any[]>(`/api/interfaces/screens?project_id=${projectId}`),
    get: (screenId: string) => get<any>(`/api/interfaces/screens/${screenId}`),
    delete: (screenId: string) => del(`/api/interfaces/screens/${screenId}`),
  },

  generate: (data: { project_id: string; prompt: string; device_type?: string; model?: string; seed_finding_ids?: string[] }) =>
    post<any>("/api/interfaces/screens/generate", data),
  generateVariants: (data: { screen_id: string; variant_type: string; count?: number }) =>
    post<any>("/api/interfaces/screens/variant", data),
  editScreen: (data: { screen_id: string; instructions: string }) =>
    post<any>("/api/interfaces/screens/edit", data),

  figma: {
    import: (data: { project_id: string; figma_url: string }) =>
      post<any>("/api/interfaces/figma/import", data),
    export: (data: { screen_id: string; figma_file_key: string }) =>
      post<any>("/api/interfaces/figma/export", data),
    designSystem: (fileKey: string) => get<any>(`/api/interfaces/figma/design-system/${fileKey}`),
    components: (fileKey: string) => get<any>(`/api/interfaces/figma/components/${fileKey}`),
  },

  handoff: {
    generateBrief: (data: { project_id: string }) =>
      post<any>("/api/interfaces/handoff/brief", data),
    generateDevSpec: (data: { screen_id: string }) =>
      post<any>("/api/interfaces/handoff/dev-spec", data),
    listBriefs: (projectId: string) => get<{ briefs: any[] }>(`/api/interfaces/handoff/briefs?project_id=${projectId}`),
  },

  configure: {
    stitch: (data: { api_key: string }) => post<any>("/api/interfaces/configure/stitch", data),
    figma: (data: { api_token: string }) => post<any>("/api/interfaces/configure/figma", data),
  },

  designChat: {
    send: async function* (projectId: string, message: string, sessionId?: string) {
      const payload: Record<string, unknown> = { message, project_id: projectId };
      if (sessionId) payload.session_id = sessionId;
      const res = await fetch(`${API_BASE}/api/interfaces/design-chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ..._getAuthHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Design chat error: ${res.status}`);
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
            try { yield JSON.parse(line.slice(6)); } catch { /* skip */ }
          }
        }
      }
    },
  },
};

// --- Context DAG ---

export const contextDag = {
  getStructure: (sessionId: string) =>
    get<{
      session_id: string;
      nodes: DAGNode[];
      stats: DAGHealth;
    }>(`/api/context-dag/${sessionId}`),
  health: (sessionId: string) =>
    get<DAGHealth>(`/api/context-dag/${sessionId}/health`),
  expand: (sessionId: string, nodeId: string) =>
    post<DAGExpandResult>(`/api/context-dag/${sessionId}/expand`, { node_id: nodeId }),
  grep: (sessionId: string, query: string) =>
    post<DAGGrepResult>(`/api/context-dag/${sessionId}/grep`, { query }),
  node: (sessionId: string, nodeId: string) =>
    get<DAGNode>(`/api/context-dag/${sessionId}/node/${nodeId}`),
  compact: (sessionId: string) =>
    post<{ compacted: boolean }>(`/api/context-dag/${sessionId}/compact`, {}),
};
