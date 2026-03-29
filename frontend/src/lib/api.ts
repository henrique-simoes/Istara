/** API client for ReClaw backend. */

import type { ChatSession, ChatMessage, InferencePresetConfig, DAGNode, DAGHealth, DAGExpandResult, DAGGrepResult, ReclawDocument, DocumentContent, DocumentTag, DocumentStats, InterfacesStatus, BackupRecord, BackupConfig, MetaProposal, MetaVariant, MetaHyperagentStatus, ChannelInstance, ChannelMessage, ChannelConversation, ResearchDeployment, DeploymentAnalytics, SurveyIntegration, SurveyLink, MCPServerConfig, MCPAccessPolicy, MCPAuditEntry, AutoresearchStatus, AutoresearchExperiment, AutoresearchConfig, ModelSkillLeaderboard, UXLaw, LawMatch, ComplianceProfile, RadarChartData, FeaturedMCPServer, ReclawUser, ProjectReport, CodebookVersionType, CodeApplicationType } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function _getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("reclaw_token");
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ..._getAuthHeaders(), ...options?.headers },
    ...options,
  });
  if (res.status === 401) {
    // Only clear token and signal re-auth — do NOT reload (causes infinite loop)
    const hadToken = !!localStorage.getItem("reclaw_token");
    localStorage.removeItem("reclaw_token");
    if (hadToken && typeof window !== "undefined") {
      // Token was present but expired/invalid — dispatch event for auth gate
      window.dispatchEvent(new Event("reclaw:auth-expired"));
    }
    throw new Error("Authentication required");
  }
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
  return fetch(`${API_BASE}${path}`, { method: "DELETE", headers: { ..._getAuthHeaders() } });
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
    fetch(`${API_BASE}/api/projects/${id}`, { method: "DELETE", headers: { ..._getAuthHeaders() } }),
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
    fetch(`${API_BASE}/api/tasks/${id}`, { method: "DELETE", headers: { ..._getAuthHeaders() } }),
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
      headers: { "Content-Type": "application/json", ..._getAuthHeaders() },
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
    return fetch(`${API_BASE}/api/findings/${plural[type]}/${id}`, { method: "DELETE", headers: { ..._getAuthHeaders() } });
  },
};

// --- Files ---

export const files = {
  upload: async (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/files/upload/${projectId}`, {
      method: "POST",
      headers: { ..._getAuthHeaders() },
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
    fetch(`${API_BASE}/api/skills/${name}`, { method: "DELETE", headers: { ..._getAuthHeaders() } }),
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
    fetch(`${API_BASE}/api/agents/${id}`, { method: "DELETE", headers: { ..._getAuthHeaders() } }),
  pause: (id: string) =>
    request<any>(`/api/agents/${id}/pause`, { method: "POST" }),
  resume: (id: string) =>
    request<any>(`/api/agents/${id}/resume`, { method: "POST" }),
  uploadAvatar: async (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/agents/${id}/avatar`, {
      method: "POST",
      headers: { ..._getAuthHeaders() },
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

// --- Loops & Schedule ---
export const loops = {
  overview: () => get<any>("/api/loops/overview"),
  agents: () => get<any>("/api/loops/agents"),
  agentConfig: (agentId: string) => get<any>(`/api/loops/agents/${agentId}/config`),
  updateAgentConfig: (agentId: string, data: Record<string, unknown>) =>
    patch<any>(`/api/loops/agents/${agentId}/config`, data),
  pauseAgent: (agentId: string) => post<any>(`/api/loops/agents/${agentId}/pause`, {}),
  resumeAgent: (agentId: string) => post<any>(`/api/loops/agents/${agentId}/resume`, {}),
  executions: (params?: Record<string, string | number>) => {
    const query = params ? "?" + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString() : "";
    return get<any>(`/api/loops/executions${query}`);
  },
  executionStats: (sourceId?: string) => get<any>(`/api/loops/executions/stats${sourceId ? `?source_id=${sourceId}` : ""}`),
  health: () => get<any>("/api/loops/health"),
  createCustom: (data: { name: string; skill_name: string; project_id: string; cron_expression?: string; interval_seconds?: number; description?: string }) =>
    post<any>("/api/loops/custom", data),
};

// --- Notifications ---
export const notificationsApi = {
  list: (params?: Record<string, string | number | boolean>) => {
    const query = params ? "?" + new URLSearchParams(Object.entries(params).filter(([,v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)])).toString() : "";
    return get<any>(`/api/notifications${query}`);
  },
  unreadCount: () => get<{ count: number }>("/api/notifications/unread-count"),
  markRead: (id: string) => post<any>(`/api/notifications/${id}/read`, {}),
  markAllRead: (projectId?: string) => post<any>("/api/notifications/read-all", projectId ? { project_id: projectId } : {}),
  delete: (id: string) => del(`/api/notifications/${id}`),
  preferences: () => get<any>("/api/notifications/preferences"),
  updatePreferences: (prefs: any[]) => request<any>("/api/notifications/preferences", { method: "PUT", body: JSON.stringify(prefs) }),
};

// --- Backups ---

export const backups = {
  list: () => request<BackupRecord[]>("/api/backups"),
  create: (type: "full" | "incremental" = "full") =>
    request<BackupRecord>("/api/backups/create", { method: "POST", body: JSON.stringify({ backup_type: type }) }),
  restore: (id: string) =>
    request<any>(`/api/backups/${id}/restore`, { method: "POST" }),
  verify: (id: string) =>
    request<any>(`/api/backups/${id}/verify`, { method: "POST" }),
  remove: (id: string) =>
    fetch(`${API_BASE}/api/backups/${id}`, { method: "DELETE", headers: { ..._getAuthHeaders() } }),
  config: () => request<BackupConfig>("/api/backups/config"),
  updateConfig: (data: Partial<BackupConfig>) =>
    request<any>("/api/backups/config", { method: "POST", body: JSON.stringify(data) }),
  estimate: () => request<any>("/api/backups/estimate"),
};

// --- Meta-Hyperagent ---

export const metaHyperagent = {
  status: () => request<MetaHyperagentStatus>("/api/meta-hyperagent/status"),
  proposals: () => request<MetaProposal[]>("/api/meta-hyperagent/proposals"),
  approveProposal: (id: string) =>
    request<any>(`/api/meta-hyperagent/proposals/${id}/approve`, { method: "POST" }),
  rejectProposal: (id: string) =>
    request<any>(`/api/meta-hyperagent/proposals/${id}/reject`, { method: "POST" }),
  variants: () => request<MetaVariant[]>("/api/meta-hyperagent/variants"),
  revertVariant: (id: string) =>
    request<any>(`/api/meta-hyperagent/variants/${id}/revert`, { method: "POST" }),
  confirmVariant: (id: string) =>
    request<any>(`/api/meta-hyperagent/variants/${id}/confirm`, { method: "POST" }),
  observations: () => request<any>("/api/meta-hyperagent/observations"),
  toggle: (enabled: boolean) =>
    request<any>("/api/meta-hyperagent/toggle", { method: "POST", body: JSON.stringify({ enabled }) }),
};

// --- Channels ---

export const channels = {
  list: (platform?: string) => {
    const params = platform ? `?platform=${platform}` : "";
    return get<ChannelInstance[]>(`/api/channels${params}`);
  },
  get: (id: string) => get<ChannelInstance>(`/api/channels/${id}`),
  create: (data: { platform: string; name: string; config: Record<string, any>; project_id?: string }) =>
    post<ChannelInstance>("/api/channels", data),
  update: (id: string, data: Record<string, any>) => patch<ChannelInstance>(`/api/channels/${id}`, data),
  delete: (id: string) => del(`/api/channels/${id}`),
  start: (id: string) => post<any>(`/api/channels/${id}/start`, {}),
  stop: (id: string) => post<any>(`/api/channels/${id}/stop`, {}),
  health: (id: string) => get<any>(`/api/channels/${id}/health`),
  messages: (id: string, limit = 50, offset = 0) =>
    get<ChannelMessage[]>(`/api/channels/${id}/messages?limit=${limit}&offset=${offset}`),
  conversations: (id: string) => get<ChannelConversation[]>(`/api/channels/${id}/conversations`),
  send: (id: string, data: { channel_id: string; text: string; metadata?: any }) =>
    post<any>(`/api/channels/${id}/send`, data),
};

// --- Deployments ---

export const deployments = {
  list: (projectId?: string) => {
    const params = projectId ? `?project_id=${projectId}` : "";
    return get<ResearchDeployment[]>(`/api/deployments${params}`);
  },
  get: (id: string) => get<ResearchDeployment>(`/api/deployments/${id}`),
  create: (data: any) => post<ResearchDeployment>("/api/deployments", data),
  activate: (id: string) => post<any>(`/api/deployments/${id}/activate`, {}),
  pause: (id: string) => post<any>(`/api/deployments/${id}/pause`, {}),
  complete: (id: string) => post<any>(`/api/deployments/${id}/complete`, {}),
  analytics: (id: string) => get<DeploymentAnalytics>(`/api/deployments/${id}/analytics`),
  overview: (projectId: string) => get<any>(`/api/deployments/overview?project_id=${projectId}`),
  conversations: (id: string) => get<ChannelConversation[]>(`/api/deployments/${id}/conversations`),
  transcript: (deploymentId: string, conversationId: string) =>
    get<any>(`/api/deployments/${deploymentId}/conversations/${conversationId}/transcript`),
};

// --- Surveys ---

export const surveys = {
  integrations: {
    list: () => get<SurveyIntegration[]>("/api/surveys/integrations"),
    create: (data: { platform: string; name: string; config: Record<string, any> }) =>
      post<SurveyIntegration>("/api/surveys/integrations", data),
    delete: (id: string) => del(`/api/surveys/integrations/${id}`),
    surveys: (id: string) => get<any[]>(`/api/surveys/integrations/${id}/surveys`),
    createSurvey: (id: string, data: any) => post<any>(`/api/surveys/integrations/${id}/create`, data),
  },
  links: {
    list: (projectId?: string) => get<SurveyLink[]>(`/api/surveys/links${projectId ? `?project_id=${projectId}` : ""}`),
    create: (data: any) => post<SurveyLink>("/api/surveys/links", data),
    sync: (id: string) => post<any>(`/api/surveys/links/${id}/sync`, {}),
    responses: (id: string) => get<any[]>(`/api/surveys/links/${id}/responses`),
  },
};

// --- MCP ---

export const mcp = {
  server: {
    status: () => get<any>("/api/mcp/server/status"),
    toggle: (enabled: boolean) => post<any>("/api/mcp/server/toggle", { enabled }),
    policy: () => get<MCPAccessPolicy>("/api/mcp/server/policy"),
    updatePolicy: (data: Record<string, any>) => patch<MCPAccessPolicy>("/api/mcp/server/policy", data),
    audit: (limit = 50, offset = 0) => get<MCPAuditEntry[]>(`/api/mcp/server/audit?limit=${limit}&offset=${offset}`),
    exposure: () => get<any>("/api/mcp/server/exposure"),
  },
  clients: {
    list: async (): Promise<MCPServerConfig[]> => {
      const res = await get<any>("/api/mcp/clients");
      return Array.isArray(res) ? res : (res?.servers ?? []);
    },
    create: (data: { name: string; url: string; transport?: string; headers?: any }) =>
      post<MCPServerConfig>("/api/mcp/clients", data),
    delete: (id: string) => del(`/api/mcp/clients/${id}`),
    discover: (id: string) => post<any>(`/api/mcp/clients/${id}/discover`, {}),
    tools: (id: string) => get<any[]>(`/api/mcp/clients/${id}/tools`),
    call: (id: string, toolName: string, args: any) =>
      post<any>(`/api/mcp/clients/${id}/call`, { tool_name: toolName, arguments: args }),
    health: (id: string) => get<any>(`/api/mcp/clients/${id}/health`),
    allTools: async (): Promise<any[]> => {
      const res = await get<any>("/api/mcp/clients/tools");
      return Array.isArray(res) ? res : (res?.tools ?? []);
    },
  },
  featured: {
    list: () => get<FeaturedMCPServer[]>("/api/mcp/featured"),
    get: (id: string) => get<FeaturedMCPServer>(`/api/mcp/featured/${id}`),
    connect: (id: string, envVars?: Record<string, string>) =>
      post<any>(`/api/mcp/featured/${id}/connect`, { env_vars: envVars || {} }),
  },
};

// --- Autoresearch ---

export const autoresearch = {
  status: () => get<AutoresearchStatus>("/api/autoresearch/status"),
  experiments: (params?: { loop_type?: string; kept?: boolean; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (params?.loop_type) p.set("loop_type", params.loop_type);
    if (params?.kept !== undefined) p.set("kept", String(params.kept));
    if (params?.limit) p.set("limit", String(params.limit));
    if (params?.offset) p.set("offset", String(params.offset));
    return get<AutoresearchExperiment[]>(`/api/autoresearch/experiments?${p}`);
  },
  experiment: (id: string) => get<AutoresearchExperiment>(`/api/autoresearch/experiments/${id}`),
  start: (data: { loop_type: string; target: string; max_iterations?: number; project_id?: string }) =>
    post<any>("/api/autoresearch/start", data),
  stop: () => post<any>("/api/autoresearch/stop", {}),
  config: () => get<AutoresearchConfig>("/api/autoresearch/config"),
  updateConfig: (data: Record<string, any>) => patch<AutoresearchConfig>("/api/autoresearch/config", data),
  leaderboard: () => get<ModelSkillLeaderboard[]>("/api/autoresearch/leaderboard"),
  toggle: (enabled: boolean) => post<any>("/api/autoresearch/toggle", { enabled }),
};

// --- Laws of UX ---

export const laws = {
  list: (category?: string) => {
    const params = category ? `?category=${category}` : "";
    return get<UXLaw[]>(`/api/laws${params}`);
  },
  get: (lawId: string) => get<UXLaw>(`/api/laws/${lawId}`),
  byHeuristic: (heuristicId: string) => get<UXLaw[]>(`/api/laws/by-heuristic/${heuristicId}`),
  match: (query: string, topK?: number) =>
    get<LawMatch[]>(`/api/laws/match?query=${encodeURIComponent(query)}&top_k=${topK || 5}`),
  compliance: (projectId: string) => get<ComplianceProfile>(`/api/laws/compliance/${projectId}`),
  radar: (projectId: string) => get<RadarChartData>(`/api/laws/compliance/${projectId}/radar`),
};

// --- Users ---

export const users = {
  list: () => get<ReclawUser[]>("/api/auth/users"),
  create: (data: { username: string; email: string; password: string; display_name?: string }) =>
    post<ReclawUser>("/api/auth/users", data),
  delete: (id: string) => del(`/api/auth/users/${id}`),
  changeRole: (id: string, role: string) =>
    patch<ReclawUser>(`/api/auth/users/${id}/role`, { role }),
};

// --- Research Integrity ---

export const reports = {
  list: (projectId: string) => get<ProjectReport[]>(`/api/reports/${projectId}`),
};

export const codebookVersions = {
  list: (projectId: string) => get<CodebookVersionType[]>(`/api/codebook-versions/${projectId}`),
  latest: (projectId: string) => get<CodebookVersionType>(`/api/codebook-versions/${projectId}/latest`),
  create: (data: {
    project_id: string;
    version: string;
    codes: unknown[];
    change_log: string;
    methodology?: string;
  }) => post<CodebookVersionType>("/api/codebook-versions", data),
};

export const codeApplications = {
  list: (projectId: string, status?: string) =>
    get<CodeApplicationType[]>(`/api/code-applications/${projectId}${status ? `?status=${status}` : ""}`),
  pending: (projectId: string) =>
    get<CodeApplicationType[]>(`/api/code-applications/${projectId}/pending`),
  review: (applicationId: string, reviewStatus: string, reviewedBy?: string) =>
    patch<CodeApplicationType>(`/api/code-applications/${applicationId}/review`, {
      review_status: reviewStatus,
      reviewed_by: reviewedBy || "user",
    }),
  bulkApprove: (projectId: string, minConfidence?: number) =>
    post<{ approved_count: number }>(`/api/code-applications/${projectId}/bulk-approve?min_confidence=${minConfidence || 0.9}`, {}),
};
