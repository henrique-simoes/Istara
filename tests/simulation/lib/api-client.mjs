/**
 * Direct REST client for the Istara backend API.
 *
 * Mirrors the endpoint structure from `frontend/src/lib/api.ts` but uses
 * plain `fetch()` so it can run from Node without a browser.  All methods
 * return parsed JSON (or throw on non-2xx responses).
 *
 * For chat, the streaming endpoint is consumed fully and returned as a
 * collected array — streaming is irrelevant for test assertions.
 */

const API_BASE = process.env.ISTARA_API_URL || "http://localhost:8000";
let authToken = process.env.ISTARA_TEST_AUTH_TOKEN || "";

export function setAuthToken(token) {
  authToken = token || "";
}

export function getApiBase() {
  return API_BASE;
}

export function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  return headers;
}

function requireProjectId(projectId, surface) {
  const value = typeof projectId === "string" ? projectId.trim() : "";
  if (!value) throw new Error(`project_id is required for ${surface}`);
  return value;
}

function projectScopedQuery(projectId, surface, extra = {}) {
  const params = new URLSearchParams();
  params.set("project_id", requireProjectId(projectId, surface));
  for (const [key, value] of Object.entries(extra)) {
    if (value !== undefined && value !== null) params.set(key, String(value));
  }
  return params.toString();
}

// ---------------------------------------------------------------------------
// Internal request helper
// ---------------------------------------------------------------------------

/**
 * @param {string}      path
 * @param {RequestInit}  [options]
 * @returns {Promise<any>}
 */
async function request(path, options) {
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    headers: authHeaders({ "Content-Type": "application/json", ...options?.headers }),
    ...options,
  });

  if (!res.ok) {
    let detail;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = res.statusText;
    }
    const err = new Error(`API ${res.status}: ${detail} [${options?.method || "GET"} ${path}]`);
    err.status = res.status;
    throw err;
  }

  // DELETE endpoints may return 204 No Content
  if (res.status === 204) return null;

  return res.json();
}

/**
 * Fire-and-forget request that only checks for a successful status code.
 * Used for DELETE endpoints that return no body.
 */
async function requestVoid(path, options) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: authHeaders({ "Content-Type": "application/json", ...options?.headers }),
    ...options,
  });
  if (!res.ok) {
    let detail;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = res.statusText;
    }
    const err = new Error(`API ${res.status}: ${detail} [${options?.method || "GET"} ${path}]`);
    err.status = res.status;
    throw err;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export const projects = {
  /** @returns {Promise<any[]>} */
  list: () => request("/api/projects"),

  /** @param {string} id */
  get: (id) => request(`/api/projects/${id}`),

  /**
   * @param {{ name: string, description?: string }} data
   * @returns {Promise<any>}
   */
  create: (data) =>
    request("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * @param {string} id
   * @param {Record<string,unknown>} data
   */
  update: (id, data) =>
    request(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** @param {string} id */
  delete: (id) =>
    requestVoid(`/api/projects/${id}`, { method: "DELETE" }),

  /** @param {string} id */
  versions: (id) => request(`/api/projects/${id}/versions`),
};

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export const tasks = {
  /**
   * @param {string} projectId
   * @param {string} [status]
   */
  list: (projectId, status) => {
    const qs = projectScopedQuery(projectId, "tasks.list", { status });
    return request(`/api/tasks?${qs}`);
  },

  /**
   * @param {{ project_id: string, title: string, description?: string }} data
   */
  create: (data) =>
    request("/api/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * @param {string} id
   * @param {string} projectId
   * @param {Record<string,unknown>} data
   */
  update: (id, projectId, data) =>
    request(`/api/tasks/${id}?${projectScopedQuery(projectId, "tasks.update")}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /**
   * Move a task to a new status column.
   * @param {string} id
   * @param {string} projectId
   * @param {string} status  e.g. "backlog", "in_progress", "in_review", "done"
   */
  move: (id, projectId, status) =>
    request(`/api/tasks/${id}/move?${projectScopedQuery(projectId, "tasks.move", { status })}`, {
      method: "POST",
    }),

  /**
   * @param {string} id
   * @param {string} projectId
   */
  delete: (id, projectId) =>
    requestVoid(`/api/tasks/${id}?${projectScopedQuery(projectId, "tasks.delete")}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Chat  (non-streaming for tests)
// ---------------------------------------------------------------------------

export const chat = {
  /**
   * Send a chat message and collect the full streamed response.
   *
   * The backend returns SSE (`data: {...}\n`).  We consume everything and
   * return an array of parsed SSE events so tests can assert on the final
   * assistant reply without dealing with streaming.
   *
   * @param {string} projectId
   * @param {string} message
   * @returns {Promise<any[]>}  Array of SSE event payloads
   */
  send: async (projectId, message) => {
    const url = `${API_BASE}/api/chat`;
    const res = await fetch(url, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ message, project_id: projectId }),
    });

    if (!res.ok) {
      throw new Error(`Chat error ${res.status}: ${res.statusText}`);
    }

    // Collect SSE events
    const events = [];
    const text = await res.text();
    for (const line of text.split("\n")) {
      if (line.startsWith("data: ")) {
        try {
          events.push(JSON.parse(line.slice(6)));
        } catch {
          // Skip malformed SSE lines
        }
      }
    }

    return events;
  },

  /**
   * Get chat history for a project.
   * @param {string} projectId
   * @param {number} [limit=50]
   */
  history: (projectId, limit = 50) =>
    request(`/api/chat/history/${projectId}?limit=${limit}`),
};

// ---------------------------------------------------------------------------
// Findings
// ---------------------------------------------------------------------------

export const findings = {
  /** @param {string} projectId */
  nuggets: (projectId) =>
    request(`/api/findings/nuggets?${projectScopedQuery(projectId, "findings.nuggets")}`),

  /** @param {string} projectId */
  facts: (projectId) =>
    request(`/api/findings/facts?${projectScopedQuery(projectId, "findings.facts")}`),

  /** @param {string} projectId */
  insights: (projectId) =>
    request(`/api/findings/insights?${projectScopedQuery(projectId, "findings.insights")}`),

  /** @param {string} projectId */
  recommendations: (projectId) =>
    request(`/api/findings/recommendations?${projectScopedQuery(projectId, "findings.recommendations")}`),

  /** @param {string} projectId */
  summary: (projectId) =>
    request(`/api/findings/summary/${projectId}`),
};

// ---------------------------------------------------------------------------
// Files
// ---------------------------------------------------------------------------

export const files = {
  /**
   * Upload a file to a project.
   *
   * Unlike the frontend `File` API, here we accept a Node `Buffer` or
   * `ReadableStream` with a filename.
   *
   * @param {string} projectId
   * @param {Buffer|Blob} fileContent
   * @param {string} filename
   * @returns {Promise<any>}
   */
  upload: async (projectId, fileContent, filename) => {
    const formData = new FormData();

    // In Node 18+ the global FormData + Blob API is available
    const blob =
      fileContent instanceof Blob
        ? fileContent
        : new Blob([fileContent], { type: "application/octet-stream" });

    formData.append("file", blob, filename);

    const res = await fetch(`${API_BASE}/api/files/upload/${projectId}`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
      // Let fetch set the multipart Content-Type with boundary
    });

    if (!res.ok) {
      throw new Error(`Upload error ${res.status}: ${res.statusText}`);
    }

    return res.json();
  },

  /** @param {string} projectId */
  list: (projectId) => request(`/api/files/${projectId}`),

  /** @param {string} projectId */
  stats: (projectId) => request(`/api/files/${projectId}/stats`),
};

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------

export const skills = {
  /** @param {string} [phase] */
  list: (phase) => {
    const qs = phase ? `?phase=${encodeURIComponent(phase)}` : "";
    return request(`/api/skills${qs}`);
  },

  /** @param {string} name */
  get: (name) => request(`/api/skills/${encodeURIComponent(name)}`),

  /**
   * @param {{ name: string, display_name: string, description: string, phase: string, skill_type: string, plan_prompt?: string, execute_prompt?: string, output_schema?: string }} data
   */
  create: (data) =>
    request("/api/skills", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * @param {string} name
   * @param {Record<string,unknown>} data
   */
  update: (name, data) =>
    request(`/api/skills/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** @param {string} name */
  delete: (name) =>
    requestVoid(`/api/skills/${encodeURIComponent(name)}`, { method: "DELETE" }),

  /**
   * @param {string} name
   * @param {{ project_id: string, user_context?: string }} data
   */
  execute: (name, data) =>
    request(`/api/skills/${encodeURIComponent(name)}/execute`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Get project-scoped health for all skills */
  health: (projectId) =>
    request(`/api/skills/health/all?${projectScopedQuery(projectId, "skills.health")}`),

  /**
   * @param {string} name
   * @param {string} projectId
   */
  skillHealth: (name, projectId) =>
    request(
      `/api/skills/${encodeURIComponent(name)}/health?${projectScopedQuery(projectId, "skills.skillHealth")}`,
    ),

  /**
   * @param {string} name
   * @param {boolean} enabled
   */
  toggle: (name, enabled) =>
    request(
      `/api/skills/${encodeURIComponent(name)}/toggle?enabled=${enabled}`,
      { method: "POST" },
    ),

  proposals: {
    /** @param {string} projectId */
    pending: (projectId) =>
      request(
        `/api/skills/proposals/pending?${projectScopedQuery(projectId, "skills.proposals.pending")}`,
      ),

    /**
     * @param {string} projectId
     * @param {number} [limit=50]
     */
    all: (projectId, limit = 50) =>
      request(
        `/api/skills/proposals/all?${projectScopedQuery(projectId, "skills.proposals.all", { limit })}`,
      ),

    /**
     * @param {string} id
     * @param {string} projectId
     */
    approve: (id, projectId) =>
      request(
        `/api/skills/proposals/${id}/approve?${projectScopedQuery(projectId, "skills.proposals.approve")}`,
        { method: "POST" },
      ),

    /**
     * @param {string} id
     * @param {string} projectId
     * @param {string} [reason=""]
     */
    reject: (id, projectId, reason = "") =>
      request(
        `/api/skills/proposals/${id}/reject?${projectScopedQuery(projectId, "skills.proposals.reject", { reason })}`,
        { method: "POST" },
      ),
  },

  creationProposals: {
    /** @param {string} projectId */
    pending: (projectId) =>
      request(
        `/api/skills/creation-proposals/pending?${projectScopedQuery(projectId, "skills.creationProposals.pending")}`,
      ),

    /**
     * @param {string} projectId
     * @param {number} [limit=20]
     */
    all: (projectId, limit = 20) =>
      request(
        `/api/skills/creation-proposals/all?${projectScopedQuery(projectId, "skills.creationProposals.all", { limit })}`,
      ),

    /**
     * @param {string} id
     * @param {string} projectId
     */
    approve: (id, projectId) =>
      request(
        `/api/skills/creation-proposals/${id}/approve?${projectScopedQuery(projectId, "skills.creationProposals.approve")}`,
        { method: "POST" },
      ),

    /**
     * @param {string} id
     * @param {string} projectId
     * @param {string} [reason=""]
     */
    reject: (id, projectId, reason = "") =>
      request(
        `/api/skills/creation-proposals/${id}/reject?${projectScopedQuery(projectId, "skills.creationProposals.reject", { reason })}`,
        { method: "POST" },
      ),
  },
};

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export const settings = {
  hardware: () => request("/api/settings/hardware"),
  models: () => request("/api/settings/models"),
  status: () => request("/api/settings/status"),

  /** @param {string} model */
  switchModel: (model) =>
    request(`/api/settings/model?model_name=${encodeURIComponent(model)}`, {
      method: "POST",
    }),
};

// ---------------------------------------------------------------------------
// Contexts (context hierarchy documents)
// ---------------------------------------------------------------------------

export const contexts = {
  /**
   * @param {string} projectId
   * @param {number} [level]
   */
  list: (projectId, level) => {
    const qs = projectScopedQuery(projectId, "contexts.list", { level });
    return request(`/api/contexts?${qs}`);
  },

  /** @param {string} docId */
  get: (docId) => request(`/api/contexts/${docId}`),

  /**
   * @param {{ name: string, level: number, level_type: string, content: string, project_id?: string, parent_id?: string, priority?: number }} data
   */
  create: (data) =>
    request("/api/contexts", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * @param {string} docId
   * @param {Record<string,unknown>} data
   */
  update: (docId, data) =>
    request(`/api/contexts/${docId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** @param {string} docId */
  delete: (docId) =>
    requestVoid(`/api/contexts/${docId}`, { method: "DELETE" }),

  /**
   * Get the fully-composed context for a project (all layers merged).
   * @param {string} projectId
   */
  composed: (projectId) => request(`/api/contexts/composed/${projectId}`),
};

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

/**
 * Quick connectivity check — hits GET /api/health.
 * @returns {Promise<any>}
 */
export async function healthCheck() {
  return request("/api/health");
}
