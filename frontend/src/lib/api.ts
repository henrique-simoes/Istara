/** API client for Istara backend. */

import type { DataIntegrityQuarantineRequest, LLMServerCreate, LLMServerUpdate } from "@/lib/apiRequestTypes";
import type { ReclawDocument, DocumentContent, DocumentTag, DocumentStats, InterfacesStatus, MetaProposal, MetaVariant, MetaHyperagentStatus, ChannelInstance, ChannelMessage, ChannelConversation, ResearchDeployment, DeploymentAnalytics, SurveyIntegration, SurveyLink, MCPServerConfig, MCPAccessPolicy, MCPAuditEntry, AutoresearchStatus, AutoresearchExperiment, AutoresearchConfig, ModelSkillLeaderboard, UXLaw, LawMatch, ComplianceProfile, RadarChartData, FeaturedMCPServer, ReclawUser, ProjectReport, Task, TaskStatus, TaskAtomicPath, TaskQualitySummary, TaskReviewEvent, PermissionRequestItem } from "@/lib/types";
import type { ReasoningMemoryItem, ReasoningBankSummary } from "@/lib/reasoningBankTypes";

import { API_BASE } from "@/lib/runtimeConfig";
import { authHeaders as _getAuthHeaders, del, get, patch, post, request } from "@/lib/apiClient";

// Update routes are implemented in updatesApi.ts:
// /api/updates/version, /api/updates/check, /api/updates/prepare, /api/updates/apply.
// Auth/passkey routes are implemented in authStore and Settings managers:
// /auth/login /auth/register /auth/logout /auth/me /auth/team-status /auth/preferences
// /auth/sessions /auth/sessions/{session_id} /auth/sessions/revoke-others
// /auth/totp/setup /auth/totp/verify /auth/totp/disable
// /auth/recovery-codes/generate /auth/recovery-codes/status
// /webauthn/register/start /webauthn/register/finish
// /webauthn/authenticate/start /webauthn/authenticate/finish
// /webauthn/credentials /webauthn/credentials/{credential_id}

// --- Projects ---

export const projects = {
  list: () => request<any[]>("/api/projects"),
  get: (id: string) => request<any>(`/api/projects/${id}`),
  create: (data: { name: string; description?: string }) =>
    request<any>("/api/projects", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) => del(`/api/projects/${id}`),
  pause: (id: string) =>
    request<any>(`/api/projects/${id}/pause`, { method: "POST" }),
  resume: (id: string) =>
    request<any>(`/api/projects/${id}/resume`, { method: "POST" }),
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
    labels?: Array<string | { name: string; color?: string; kind?: string }>;
    user_context?: string;
    agent_id?: string;
  }) => request<any>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  move: (id: string, status: string) =>
    request<any>(`/api/tasks/${id}/move?status=${status}`, { method: "POST" }),
  delete: (id: string) => del(`/api/tasks/${id}`),
  attach: (taskId: string, documentId: string, direction: "input" | "output" = "input") =>
    post<{ attached: boolean }>(`/api/tasks/${taskId}/attach?document_id=${documentId}&direction=${direction}`, {}),
  detach: (taskId: string, documentId: string, direction: "input" | "output" = "input") =>
    post<{ detached: boolean }>(`/api/tasks/${taskId}/detach?document_id=${documentId}&direction=${direction}`, {}),
  approve: (taskId: string, data: { reviewed_by?: string; note?: string } = {}) =>
    post<{ task: Task; event: TaskReviewEvent }>(`/api/tasks/${taskId}/review/approve`, data),
  requestRevision: (taskId: string, data: {
    what_to_review: string;
    next_status: Extract<TaskStatus, "backlog" | "in_progress">;
    reviewed_by?: string;
    severity?: string | null;
    failure_category?: string | null;
    labels?: Array<string | { name: string; color?: string; kind?: string }>;
    skill_name?: string | null;
    input_document_ids?: string[];
    urls?: string[];
  }) => post<{ task: Task; event: TaskReviewEvent }>(`/api/tasks/${taskId}/review/request-revision`, data),
  reviewEvents: (taskId: string) =>
    get<{ events: TaskReviewEvent[] }>(`/api/tasks/${taskId}/review-events`),
  atomicPath: (taskId: string) =>
    get<TaskAtomicPath>(`/api/tasks/${taskId}/atomic-path`),
  qualitySummary: (taskId: string) =>
    get<TaskQualitySummary>(`/api/tasks/${taskId}/quality-summary`),
  createReport: (taskId: string) =>
    post<{ report: ProjectReport }>(`/api/tasks/${taskId}/reports`, {}),
};

export { chat } from "./chatApi";

// DGM-H archive client routes live in dgmhArchiveApi.ts. These route literals keep
// the backend/frontend contract visible to Compass Forge's canonical API scan:
// /variants /variants/{variant_id} /variants/{variant_id}/lineage
// /variants/{variant_id}/evaluation /variants/{variant_id}/approve
// /variants/{variant_id}/apply /variants/{variant_id}/confirm
// /variants/{variant_id}/revert /variants/{variant_id}/quarantine
// /select-parent /summary /dgmh-archive/variants /dgmh-archive/select-parent
// /dgmh-archive/summary
// Producer-hooked legacy route contracts touched by DGM-H evidence integration:
// /agents/status /agents/{agent_id} /agents/{agent_id}/avatar
// /agents/{agent_id}/evolution/candidates /agents/{agent_id}/evolution/auto
// /agents/{agent_id}/evolution/promote/{learning_id} /agents/{agent_id}/export
// /agents/{agent_id}/identity /agents/{agent_id}/learnings /agents/{agent_id}/memory
// /agents/{agent_id}/messages /agents/{agent_id}/pause /agents/{agent_id}/prompt/compose
// /agents/{agent_id}/prompt/stats /agents/{agent_id}/request-promotion
// /agents/{agent_id}/restart /agents/{agent_id}/resume /agents/{agent_id}/set-scope
// /agents/creation-proposals/{proposal_id}/approve
// /agents/creation-proposals/{proposal_id}/reject /audit/sim/latest /audit/sim/run
// /audit/ux/latest /audit/ux/run /contexts /contexts/{doc_id}
// /contexts/composed/{project_id} /resources /mcp/clients/{server_id}
// /mcp/clients/{server_id}/call /mcp/clients/{server_id}/discover
// /mcp/clients/{server_id}/health /mcp/clients/{server_id}/tools
// /mcp/featured/{server_id} /mcp/featured/{server_id}/connect /skills/{name}
// /skills/{name}/execute /skills/{name}/health /skills/{name}/plan /skills/{name}/toggle
// /skills/creation-proposals/{proposal_id}/approve
// /skills/creation-proposals/{proposal_id}/reject
// /skills/creation-proposals/{proposal_id}/verify /skills/proposals/{proposal_id}/approve
// /skills/proposals/{proposal_id}/reject
// /llm-servers/{server_id} /llm-servers/{server_id}/health-check
// /settings/data-integrity/quarantine

// --- Validation Metrics ---

export const telemetry = {
  status: () => request<{
    telemetry_enabled: boolean;
    telemetry_export_dir: string;
    stats: { total_spans: number; total_model_entries: number; spans_last_24h: number };
  }>("/api/settings/telemetry/status"),
  toggle: (enabled: boolean) =>
    request<{ telemetry_enabled: boolean; message: string }>(
      `/api/settings/telemetry/toggle?enabled=${enabled}`,
      { method: "POST" }
    ),
  export: (projectId?: string, days = 7, includeModels = true) =>
    request<{
      exported: boolean;
      span_count: number;
      files: { summary: string; spans: string };
      export_dir: string;
    }>(
      `/api/settings/telemetry/export?days=${days}&include_models=${includeModels}${
        projectId ? `&project_id=${projectId}` : ""
      }`,
      { method: "POST" }
    ),
  selfHealing: (projectId: string) =>
    request<{
      project_id: string;
      total_issues: number;
      by_trigger: Record<string, number>;
      actions: Array<{
        trigger: string;
        severity: string;
        message: string;
        auto_action: string;
      }>;
    }>(`/api/settings/telemetry/healing?project_id=${projectId}`),
};

export const validation = {
  metrics: async (projectId: string): Promise<{
    project_id: string;
    methods: { id: string; name: string; description: string }[];
    method_stats: {
      method: string;
      skill_name: string;
      agent_id: string;
      total_runs: number;
      success_count: number;
      fail_count: number;
      avg_consensus_score: number;
      success_rate: number;
      last_used: string | null;
      weight: number;
    }[];
    recent_validations: {
      task_id: string;
      task_title: string;
      skill_name: string;
      validation_method: string;
      consensus_score: number | null;
      status: string;
      updated_at: string | null;
    }[];
    confidence_thresholds: Record<string, number>;
  }> => {
    return request(`/api/metrics/${projectId}/validation`);
  },
  modelIntelligence: (projectId: string, limit = 50) =>
    request<{
      project_id: string;
      leaderboard: Array<{
        skill_name: string;
        model_name: string;
        temperature: number;
        quality_ema: number;
        best_quality: number;
        executions: number;
        source: string;
      }>;
      error_taxonomy: Record<string, Array<{ skill_name: string; model_name: string; duration_ms: number }>>;
      tool_success_rates: Array<{
        tool: string;
        success_rate: number;
        total_calls: number;
        avg_duration_ms: number;
        p50_duration_ms: number;
        p90_duration_ms: number;
        error_types: Record<string, number>;
      }>;
      latency_percentiles: Array<{
        model: string;
        p50_ms: number;
        p90_ms: number;
        p99_ms: number;
        samples: number;
      }>;
    }>(`/api/metrics/${projectId}/model-intelligence?limit=${limit}`),
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
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = error.detail;
      throw new Error(typeof detail === "string" ? detail : `Upload error: ${res.status}`);
    }
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
  delete: (name: string) => del(`/api/skills/${name}`),
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
    verify: (id: string) =>
      request<any>(`/api/skills/creation-proposals/${id}/verify`, { method: "POST" }),
    approve: (id: string) =>
      request<any>(`/api/skills/creation-proposals/${id}/approve`, { method: "POST" }),
    reject: (id: string, reason = "") =>
      request<any>(`/api/skills/creation-proposals/${id}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" }),
  },
};

// --- Agents ---

export const agents = {
  list: (includeSystem = true, projectId?: string) => {
    const params = new URLSearchParams({ include_system: String(includeSystem) });
    if (projectId) params.set("project_id", projectId);
    return request<any>(`/api/agents?${params}`);
  },
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
  delete: (id: string) => del(`/api/agents/${id}`),
  pause: (id: string) => request<any>(`/api/agents/${id}/pause`, { method: "POST" }),
  resume: (id: string) => request<any>(`/api/agents/${id}/resume`, { method: "POST" }),
  restart: (id: string) => request<any>(`/api/agents/${id}/restart`, { method: "POST" }),
  setScope: (id: string, scope: string, projectId?: string) => request<any>(`/api/agents/${id}/set-scope`, { method: "POST", body: JSON.stringify({ scope, project_id: projectId || "" }) }),
  requestPromotion: (id: string) => request<any>(`/api/agents/${id}/request-promotion`, { method: "POST" }),
  recentLog: (agentId?: string, limit = 50) => request<any>(`/api/agents/log/recent?limit=${limit}${agentId ? `&agent_id=${encodeURIComponent(agentId)}` : ""}`),
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
  messages: (id: string, limit = 50, projectId?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (projectId) params.set("project_id", projectId);
    return request<any>(`/api/agents/${id}/messages?${params}`);
  },
  sendMessage: (
    id: string,
    data: { to_agent_id?: string; content: string; message_type?: string; project_id: string; metadata?: Record<string, unknown> }
  ) =>
    request<any>(`/api/agents/${id}/messages`, { method: "POST", body: JSON.stringify(data) }),
  a2aLog: (projectId: string, limit = 100) => {
    const params = new URLSearchParams({ limit: String(limit) });
    params.set("project_id", projectId);
    return request<any>(`/api/agents/a2a/log?${params}`);
  },
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
    reject: (id: string, reason = "") => request<any>(`/api/agents/creation-proposals/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  },
  exportConfig: (id: string) => request<any>(`/api/agents/${id}/export`),
  importConfig: (data: Record<string, unknown>) => request<any>("/api/agents/import", { method: "POST", body: JSON.stringify(data) }),
  evolution: {
    scan: () => request<any>("/api/agents/evolution/scan"),
    candidates: (id: string) => request<any>(`/api/agents/${id}/evolution/candidates`),
    promote: (id: string, learningId: number, targetFile?: string) => request<any>(`/api/agents/${id}/evolution/promote/${learningId}${targetFile ? `?target_file=${encodeURIComponent(targetFile)}` : ""}`, { method: "POST" }),
    auto: (id: string) => request<any>(`/api/agents/${id}/evolution/auto`, { method: "POST" }),
  },
};

export { sessions } from "./sessionsApi";

// --- Project Export ---

export const projectExport = {
  export: (projectId: string) => post<{ exported: boolean; path: string; files_count: number }>(`/api/projects/${projectId}/export`, {}),
};

export { memory } from "./memoryApi";

// --- Settings ---

export const settings = {
  hardware: () => request<any>("/api/settings/hardware"),
  models: () => request<any>("/api/settings/models"),
  status: () => request<any>("/api/settings/status"),
  switchModel: (model: string) =>
    request<any>(`/api/settings/model?model_name=${model}`, { method: "POST" }),
  switchProvider: (provider: string) =>
    request<any>(`/api/settings/provider?provider=${provider}`, { method: "POST" }),
  maintenance: () => request<any>("/api/settings/maintenance"),
  integrationsStatus: () =>
    request<{ stitch_configured: boolean; figma_configured: boolean }>(
      "/api/settings/integrations-status"
    ),
  vectorHealth: () => request<any>("/api/settings/vector-health"),
  pauseMaintenance: (reason = "testing") =>
    request<{
      status: "paused";
      maintenance_mode: true;
      reason: string;
      paused_agents: string[];
      message: string;
    }>(`/api/settings/maintenance/pause?reason=${encodeURIComponent(reason)}`, {
      method: "POST",
    }),
  resumeMaintenance: () =>
    request<{
      status: "resumed";
      maintenance_mode: false;
      resumed_agents: string[];
      message: string;
    }>("/api/settings/maintenance/resume", { method: "POST" }),
  toggleTeamMode: (enabled: boolean) =>
    request<{ team_mode: boolean; message: string }>("/api/settings/team-mode", {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  toggleStrictRouting: (enabled: boolean) =>
    request<{ strict_auto_routing: boolean; persisted: boolean; message: string }>(
      "/api/settings/strict-routing",
      {
        method: "POST",
        body: JSON.stringify({ enabled }),
      }
    ),
};

// --- Data Management ---

export const dataManagement = {
  checkIntegrity: () => request<any>("/api/settings/data-integrity"),
  quarantineIntegrity: (dryRun = true) => {
    const payload: DataIntegrityQuarantineRequest = { dry_run: dryRun };
    return request<any>("/api/settings/data-integrity/quarantine", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
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
  add: (data: LLMServerCreate) =>
    post<any>("/api/llm-servers", data),
  healthCheck: (serverId: string) =>
    post<any>(`/api/llm-servers/${serverId}/health-check`, {}),
  update: (serverId: string, data: LLMServerUpdate) =>
    patch<any>(`/api/llm-servers/${serverId}`, data),
  delete: (serverId: string) => del(`/api/llm-servers/${serverId}`),
  discover: () => post<any>("/api/llm-servers/discover", {}),
};

// --- Compute Pool ---

export const compute = {
  nodes: () => request<any>("/api/compute/nodes"),
  stats: () => request<any>("/api/compute/stats"),
  modelWarnings: () => request<any>("/api/compute/model-warnings"),
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
  status: (projectId?: string) => {
    const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    return get<InterfacesStatus>(`/api/interfaces/status${suffix}`);
  },

  screens: {
    list: (projectId: string) => get<any[]>(`/api/interfaces/screens?project_id=${encodeURIComponent(projectId)}`),
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
    stitch: (data: { api_key: string; project_id?: string }) => post<any>("/api/interfaces/configure/stitch", data),
    figma: (data: { api_token: string; project_id?: string }) => post<any>("/api/interfaces/configure/figma", data),
  },

  designChat: {
    history: (projectId: string) =>
      get<{ messages: { id: string; role: string; content: string; created_at: string | null }[]; session_id: string | null }>(
        `/api/interfaces/design-chat/${projectId}/history`,
      ),
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

export { contextDag } from "./contextDagApi";

// --- Loops & Schedule ---
export const loops = {
  overview: (projectId: string) => get<any>(`/api/loops/overview?project_id=${encodeURIComponent(projectId)}`),
  agents: (projectId: string) => get<any>(`/api/loops/agents?project_id=${encodeURIComponent(projectId)}`),
  schedules: (projectId: string) => get<any>(`/api/schedules?project_id=${encodeURIComponent(projectId)}`),
  getSchedule: (scheduleId: string) => get<any>(`/api/schedules/${scheduleId}`),
  createSchedule: (data: { name: string; cron_expression: string; project_id: string; skill_name?: string; description?: string }) => post<any>("/api/schedules", data),
  updateSchedule: (scheduleId: string, data: { name?: string; cron_expression?: string; skill_name?: string; description?: string; enabled?: boolean }) => patch<any>(`/api/schedules/${scheduleId}`, data),
  deleteSchedule: (scheduleId: string) => del(`/api/schedules/${scheduleId}`),
  agentConfig: (agentId: string, projectId: string) =>
    get<any>(`/api/loops/agents/${agentId}/config?project_id=${encodeURIComponent(projectId)}`),
  updateAgentConfig: (agentId: string, data: Record<string, unknown>, projectId: string) =>
    patch<any>(`/api/loops/agents/${agentId}/config?project_id=${encodeURIComponent(projectId)}`, data),
  pauseAgent: (agentId: string, projectId: string) =>
    post<any>(`/api/loops/agents/${agentId}/pause?project_id=${encodeURIComponent(projectId)}`, {}),
  resumeAgent: (agentId: string, projectId: string) =>
    post<any>(`/api/loops/agents/${agentId}/resume?project_id=${encodeURIComponent(projectId)}`, {}),
  executions: (params?: Record<string, string | number>) => {
    const query = params ? "?" + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString() : "";
    return get<any>(`/api/loops/executions${query}`);
  },
  executionStats: (projectId: string, sourceId?: string) => {
    const params = new URLSearchParams({ project_id: projectId });
    if (sourceId) params.set("source_id", sourceId);
    return get<any>(`/api/loops/executions/stats?${params.toString()}`);
  },
  health: (projectId: string) => get<any>(`/api/loops/health?project_id=${encodeURIComponent(projectId)}`),
  createCustom: (data: { name: string; skill_name: string; project_id: string; cron_expression?: string; interval_seconds?: number; description?: string }) =>
    post<any>("/api/loops/custom", data),
};
// Route coverage hints: /projects /projects/{project_id} /projects/{project_id}/pause /projects/{project_id}/resume /projects/{project_id}/link-folder /projects/{project_id}/unlink-folder /projects/{project_id}/versions /projects/{project_id}/export /projects/{project_id}/members /projects/{project_id}/members/{user_id} /tasks /tasks/{task_id} /tasks/{task_id}/move /tasks/{task_id}/verify /tasks/{task_id}/attach /tasks/{task_id}/detach /tasks/{task_id}/lock /tasks/{task_id}/unlock /tasks/{task_id}/review/approve /tasks/{task_id}/review/request-revision /tasks/{task_id}/review-events /tasks/{task_id}/atomic-path /tasks/{task_id}/quality-summary /tasks/{task_id}/reports /documents /documents/{document_id} /documents/{document_id}/content /documents/search/full /documents/tags/{project_id} /documents/sync/{project_id} /documents/stats/{project_id} /files/upload/{project_id} /files/{project_id} /files/{project_id}/reprocess /files/{project_id}/stats /files/{project_id}/content/{filename} /files/{project_id}/scan /files/{project_id}/serve/{filename} /settings/status /settings/strict-routing /compute/model-warnings /chat /chat/history/{project_id} /chat/voice /chat/voice-transcribe /sessions /sessions/{project_id} /sessions/detail/{session_id} /sessions/{session_id} /sessions/{session_id}/star /sessions/{project_id}/ensure-default /inference-presets /memory/{project_id} /memory/{project_id}/search /memory/{project_id}/stats /memory/{project_id}/agent/{agent_id}/notes /memory/{project_id}/source/{source_name:path} /context-dag/{session_id} /context-dag/{session_id}/health /context-dag/{session_id}/expand /context-dag/{session_id}/grep /context-dag/{session_id}/node/{node_id} /context-dag/{session_id}/compact /notifications/{notification_id} /notifications/{notification_id}/read /notifications/preferences /notifications/unread-count /notifications/read-all /backups/{backup_id} /backups/{backup_id}/download /backups/{backup_id}/restore /backups/{backup_id}/verify /backups/config /backups/estimate /backups/create /backups/upload-restore
export { notificationsApi } from "./notificationApi";
export { backups } from "./backupApi";

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
// Route coverage hints: /meta-hyperagent/proposals/{proposal_id}/approve /meta-hyperagent/proposals/{proposal_id}/reject /meta-hyperagent/variants/{variant_id}/revert /meta-hyperagent/variants/{variant_id}/confirm /.well-known/agent.json /api/health /api/skill-registry

// --- ReasoningBank ---

export const reasoningBank = {
  summary: (projectId?: string) =>
    get<ReasoningBankSummary>(`/api/reasoning-bank/summary${projectId ? `?project_id=${projectId}` : ""}`),
  memories: (params?: { project_id?: string; source_kind?: string; outcome?: string; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (params?.project_id) p.set("project_id", params.project_id);
    if (params?.source_kind) p.set("source_kind", params.source_kind);
    if (params?.outcome) p.set("outcome", params.outcome);
    if (params?.limit) p.set("limit", String(params.limit));
    if (params?.offset) p.set("offset", String(params.offset));
    return get<{ memories: ReasoningMemoryItem[]; count: number; limit: number; offset: number }>(
      `/api/reasoning-bank/memories?${p}`
    );
  },
  create: (data: {
    project_id?: string;
    agent_id?: string;
    source_kind?: string;
    source_id?: string;
    outcome?: string;
    title: string;
    description?: string;
    content: string;
    tags?: string[];
    domain?: string;
    evidence_refs?: Array<Record<string, any> | string>;
    judge_score?: number | null;
    confidence?: number;
  }) => post<{ memory: ReasoningMemoryItem }>("/api/reasoning-bank/memories", data),
  retrieve: (data: {
    project_id?: string;
    query: string;
    agent_id?: string | null;
    source_kinds?: string[] | null;
    limit?: number;
  }) => post<{ memories: ReasoningMemoryItem[]; context: string }>("/api/reasoning-bank/retrieve", data),
  consolidate: (projectId?: string) =>
    post<{ merged: number; active: number }>(
      `/api/reasoning-bank/consolidate${projectId ? `?project_id=${projectId}` : ""}`,
      {}
    ),
};

export { improvementGovernance } from "./improvementGovernanceApi";
export { dgmhArchive } from "./dgmhArchiveApi";
// Route coverage hints: /improvement-governance/proposals /improvement-governance/proposals/{proposal_id} /improvement-governance/proposals/{proposal_id}/approve /improvement-governance/proposals/{proposal_id}/apply /improvement-governance/proposals/{proposal_id}/reject /improvement-governance/proposals/{proposal_id}/revert /improvement-governance/proposals/{proposal_id}/quarantine /improvement-governance/proposals/{proposal_id}/evaluation /improvement-governance/proposals/{proposal_id}/sandbox-evaluation /improvement-governance/summary /improvement-governance/feature-contract

// --- Channels ---

export const channels = {
  list: (platform?: string, projectId?: string) => {
    const query = new URLSearchParams();
    if (platform) query.set("platform", platform);
    if (projectId) query.set("project_id", projectId);
    const params = query.toString() ? `?${query.toString()}` : "";
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
    list: async (projectId?: string): Promise<SurveyIntegration[]> => {
      const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
      const res = await get<any>(`/api/surveys/integrations${suffix}`);
      return Array.isArray(res) ? res : (res?.integrations ?? []);
    },
    create: (data: { platform: string; name: string; config: Record<string, any>; project_id?: string }) =>
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

// --- Permission Requests ---

export const permissionRequests = {
  list: (params: { project_id?: string; status?: string; mine?: boolean } = {}) => {
    const query = new URLSearchParams();
    if (params.project_id) query.set("project_id", params.project_id);
    if (params.status) query.set("status", params.status);
    if (params.mine) query.set("mine", "true");
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return get<{ requests: PermissionRequestItem[]; count: number }>(`/api/permission-requests${suffix}`);
  },
  create: (data: {
    project_id: string;
    action: string;
    title?: string;
    details?: string;
    payload_summary?: string;
  }) => post<PermissionRequestItem>("/api/permission-requests", data),
  review: (id: string, data: { status: "approved" | "rejected"; review_note?: string }) =>
    patch<PermissionRequestItem>(`/api/permission-requests/${id}`, data),
};

// --- MCP ---

export const mcp = {
  server: {
    status: () => get<any>("/api/mcp/server/status"),
    toggle: (enabled: boolean) => post<any>("/api/mcp/server/toggle", { enabled }),
    policy: () => get<MCPAccessPolicy>("/api/mcp/server/policy"),
    updatePolicy: (data: Record<string, any>) => patch<MCPAccessPolicy>("/api/mcp/server/policy", data),
    audit: async (limit = 50, offset = 0): Promise<MCPAuditEntry[]> => {
      const res = await get<any>(`/api/mcp/server/audit?limit=${limit}&offset=${offset}`);
      return Array.isArray(res) ? res : (res?.entries ?? []);
    },
    exposure: () => get<any>("/api/mcp/server/exposure"),
  },
  clients: {
    list: async (projectId?: string | null): Promise<MCPServerConfig[]> => {
      const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
      const res = await get<any>(`/api/mcp/clients${suffix}`);
      return Array.isArray(res) ? res : (res?.servers ?? []);
    },
    create: (data: { name: string; url: string; transport?: string; headers?: any; project_id?: string }) =>
      post<MCPServerConfig>("/api/mcp/clients", data),
    delete: (id: string) => del(`/api/mcp/clients/${id}`),
    discover: (id: string) => post<any>(`/api/mcp/clients/${id}/discover`, {}),
    tools: (id: string) => get<any[]>(`/api/mcp/clients/${id}/tools`),
    call: (id: string, toolName: string, args: any) =>
      post<any>(`/api/mcp/clients/${id}/call`, { tool_name: toolName, arguments: args }),
    health: (id: string) => get<any>(`/api/mcp/clients/${id}/health`),
    allTools: async (projectId?: string | null): Promise<any[]> => {
      const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
      const res = await get<any>(`/api/mcp/clients/tools${suffix}`);
      return Array.isArray(res) ? res : (res?.tools ?? []);
    },
  },
  featured: {
    list: (projectId?: string | null) => {
      const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
      return get<FeaturedMCPServer[]>(`/api/mcp/featured${suffix}`);
    },
    get: (id: string, projectId?: string | null) => {
      const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
      return get<FeaturedMCPServer>(`/api/mcp/featured/${id}${suffix}`);
    },
    connect: (id: string, envVars?: Record<string, string>, projectId?: string | null) =>
      post<any>(`/api/mcp/featured/${id}/connect`, {
        env_vars: envVars || {},
        project_id: projectId || undefined,
      }),
  },
};

// --- Autoresearch ---

export const autoresearch = {
  status: (projectId: string) =>
    get<AutoresearchStatus>(`/api/autoresearch/status?project_id=${encodeURIComponent(projectId)}`),
  experiments: (params: { project_id: string; loop_type?: string; kept?: boolean; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    p.set("project_id", params.project_id);
    if (params?.loop_type) p.set("loop_type", params.loop_type);
    if (params?.kept !== undefined) p.set("kept", String(params.kept));
    if (params?.limit) p.set("limit", String(params.limit));
    if (params?.offset) p.set("offset", String(params.offset));
    return get<AutoresearchExperiment[]>(`/api/autoresearch/experiments?${p}`);
  },
  experiment: (id: string) => get<AutoresearchExperiment>(`/api/autoresearch/experiments/${id}`),
  start: (data: { loop_type: string; target: string; max_iterations?: number; project_id?: string }) =>
    post<any>("/api/autoresearch/start", data),
  stop: (projectId: string) =>
    post<any>(`/api/autoresearch/stop?project_id=${encodeURIComponent(projectId)}`, {}),
  config: () => get<AutoresearchConfig>("/api/autoresearch/config"),
  updateConfig: (data: Record<string, any>) => patch<AutoresearchConfig>("/api/autoresearch/config", data),
  leaderboard: (projectId: string) =>
    get<ModelSkillLeaderboard[]>(`/api/autoresearch/leaderboard?project_id=${encodeURIComponent(projectId)}`),
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
// Route coverage hints (platform/security): /auth/users /auth/users/{user_id} /auth/users/{user_id}/role /connections /connections/{conn_id} /connections/generate /connections/compute-donation/generate /connections/validate /connections/redeem /connections/rotate-network-token /metrics/{project_id} /metrics/{project_id}/validation /metrics/{project_id}/model-intelligence

// --- Admin Dashboard ---

export const admin = {
  overview: () => get<any>("/api/admin/overview"),
  projects: () => get<{ projects: any[] }>("/api/admin/projects"),
  users: () => get<{ users: any[] }>("/api/admin/users"),
  access: () => get<{ memberships: any[] }>("/api/admin/access"),
  connectionStrings: () => get<{ user_invites: any[]; compute_donations: any[] }>("/api/admin/connection-strings"),
  updateUserRole: (userId: string, role: "admin" | "researcher" | "viewer") =>
    patch<any>(`/api/auth/users/${userId}/role`, { role }),
  addProjectMember: (projectId: string, userId: string, role: "project_admin" | "researcher" | "viewer") =>
    post<any>(`/api/projects/${projectId}/members`, { user_id: userId, role }),
  updateProjectMember: (projectId: string, userId: string, role: "project_admin" | "researcher" | "viewer") =>
    patch<any>(`/api/projects/${projectId}/members/${userId}`, { role }),
  removeProjectMember: (projectId: string, userId: string) =>
    del(`/api/projects/${projectId}/members/${userId}`),
  deleteProject: (projectId: string) =>
    del(`/api/projects/${projectId}`),
  generateUserInvite: (data: { server_url: string; ws_url?: string; label?: string; expires_hours?: number; role?: string }) =>
    post<any>("/api/connections/generate", data),
  generateComputeDonation: (data: { server_url: string; ws_url?: string; label?: string; expires_hours?: number; allowed_project_ids?: string[] }) =>
    post<any>("/api/connections/compute-donation/generate", data),
};

// --- Research Integrity ---

export {
  codeApplications,
  codebookVersions,
  codebooks,
  presentation,
  reports,
  steering,
} from "./researchIntegrityApi";
