import { readFileSync } from "fs";
import { join } from "path";
import { spawnSync } from "child_process";

function parseEnvFileValue(content, key) {
  const line = content.split(/\r?\n/).find((entry) => entry.trim().startsWith(`${key}=`));
  if (!line) return "";
  return line.slice(line.indexOf("=") + 1).trim().replace(/^["']|["']$/g, "");
}

export class IstaraApiClient {
  constructor({
    apiBase,
    repoRoot,
    logger,
    networkAccessToken = "",
    adminUsername = "",
    adminPassword = "",
    chatHeaders = {},
    agentEngine = "",
  }) {
    this.apiBase = apiBase.replace(/\/$/, "");
    this.repoRoot = repoRoot;
    this.logger = logger;
    this.token = "";
    this.userId = "";
    this.networkAccessToken = networkAccessToken;
    this.adminUsername = adminUsername;
    this.adminPassword = adminPassword;
    this.chatHeaders = { ...chatHeaders };
    if (agentEngine) this.chatHeaders["x-istara-agent-engine"] = agentEngine;
  }

  headers(extra = {}) {
    const headers = { "Content-Type": "application/json", ...extra };
    if (this.networkAccessToken) headers["X-Access-Token"] = this.networkAccessToken;
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    return headers;
  }

  async request(method, path, body = undefined, options = {}) {
    const started = Date.now();
    const controller = options.timeoutMs ? new AbortController() : null;
    let timeout = null;
    if (controller) {
      timeout = setTimeout(() => controller.abort(), options.timeoutMs);
    }
    try {
      const response = await fetch(`${this.apiBase}${path}`, {
        method,
        headers: options.headers || this.headers(),
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller?.signal,
      });
      const text = await response.text();
      const contentType = response.headers.get("content-type") || "";
      let data = text;
      if (contentType.includes("application/json") && text) {
        data = JSON.parse(text);
      }
      this.logger?.action("api.request", {
        method,
        path,
        status: response.status,
        ok: response.ok,
        duration_ms: Date.now() - started,
      });
      if (!response.ok) {
        const detail = typeof data === "object" ? JSON.stringify(data).slice(0, 500) : String(data).slice(0, 500);
        throw new Error(`${method} ${path}: ${response.status} ${detail}`);
      }
      return data || {};
    } catch (error) {
      this.logger?.action("api.error", {
        method,
        path,
        duration_ms: Date.now() - started,
        error: error.message,
      });
      throw error;
    } finally {
      if (timeout) clearTimeout(timeout);
    }
  }

  get(path, options) {
    return this.request("GET", path, undefined, options);
  }

  post(path, body, options) {
    return this.request("POST", path, body, options);
  }

  patch(path, body, options) {
    return this.request("PATCH", path, body, options);
  }

  delete(path, options) {
    return this.request("DELETE", path, undefined, options);
  }

  async health() {
    try {
      const response = await fetch(`${this.apiBase}/api/health`);
      return { ok: response.ok, status: response.status, data: response.ok ? await response.json().catch(() => ({})) : {} };
    } catch (error) {
      return { ok: false, status: 0, error: error.message };
    }
  }

  async authenticate() {
    const username = this.adminUsername || process.env.ISTARA_BENCHMARK_ADMIN_USERNAME || process.env.ISTARA_ADMIN_USERNAME || process.env.ADMIN_USERNAME || "admin";
    const envFiles = [
      join(this.repoRoot, "backend", ".env.local"),
      join(this.repoRoot, "backend", ".env"),
      join(this.repoRoot, ".env.local"),
      join(this.repoRoot, ".env"),
    ];
    const localTokenAllowed = ["1", "true", "yes"].includes(String(process.env.ISTARA_E2E_ALLOW_LOCAL_TOKEN || "").toLowerCase());
    const passwordCandidates = [
      [this.adminPassword, "constructor"],
      [process.env.ISTARA_BENCHMARK_ADMIN_PASSWORD, "env:ISTARA_BENCHMARK_ADMIN_PASSWORD"],
      [process.env.ISTARA_ADMIN_PASSWORD, "env:ISTARA_ADMIN_PASSWORD"],
      [process.env.ADMIN_PASSWORD, "env:ADMIN_PASSWORD"],
      [process.env.ISTARA_TEST_ADMIN_PASSWORD || "istara123", "reset-test-default"],
    ];
    let password = "";
    let passwordSource = "";
    for (const [candidate, source] of passwordCandidates) {
      if (candidate) {
        password = String(candidate).trim();
        passwordSource = source;
        break;
      }
    }
    for (const path of envFiles) {
      if (password) break;
      try {
        password = parseEnvFileValue(readFileSync(path, "utf8"), "ADMIN_PASSWORD");
        if (password) passwordSource = `file:${path.replace(`${this.repoRoot}/`, "")}:ADMIN_PASSWORD`;
      } catch {}
    }

    if (password) {
      try {
        const result = await this.post("/api/auth/login", { username, password });
        this.token = result.access_token || result.token || "";
        this.userId = result.user?.id || result.user_id || username;
        if (this.token) return { ok: true, method: "password", user_id: this.userId };
      } catch (error) {
        const explicitBenchmarkCredential = ["constructor", "env:ISTARA_BENCHMARK_ADMIN_PASSWORD"].includes(passwordSource);
        const failure = {
          source: passwordSource || "unknown",
          fallback_allowed: localTokenAllowed,
          detail: error.message,
        };
        if (explicitBenchmarkCredential || !localTokenAllowed) {
          this.logger?.issue({
            area: "auth",
            severity: "low",
            title: "Password auth failed during benchmark setup",
            detail: error.message,
            evidence: {
              credential_source: passwordSource || "unknown",
              fallback_allowed: localTokenAllowed,
            },
          });
        } else {
          this.logger?.action("auth.password_failed_using_local_token_fallback", failure);
        }
      }
    }

    if (!localTokenAllowed) {
      return { ok: false, method: "none", reason: "No credentials and local signed token disabled." };
    }

    const script = [
      "import sys",
      `sys.path.insert(0, ${JSON.stringify(join(this.repoRoot, "backend"))})`,
      "from app.core.auth import create_token",
      `print(create_token("benchmark-admin", ${JSON.stringify(username)}, "admin", mfa_verified=True))`,
    ].join("\n");
    for (const pythonBin of [process.env.PYTHON, process.env.PYTHON_EXECUTABLE, "python3", "python"].filter(Boolean)) {
      const result = spawnSync(pythonBin, ["-c", script], {
        cwd: this.repoRoot,
        encoding: "utf8",
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"],
      });
      if (result.status === 0 && result.stdout.trim()) {
        this.token = result.stdout.trim();
        this.userId = "benchmark-admin";
        return { ok: true, method: "local-signed-token", user_id: this.userId };
      }
    }
    return { ok: false, method: "local-signed-token", reason: "Could not mint local token." };
  }

  async uploadFile(projectId, filePath, fileName) {
    const fileData = readFileSync(filePath);
    const formData = new FormData();
    formData.append("file", new Blob([fileData]), fileName);
    const headers = {};
    if (this.networkAccessToken) headers["X-Access-Token"] = this.networkAccessToken;
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const response = await fetch(`${this.apiBase}/api/files/upload/${projectId}`, {
      method: "POST",
      headers,
      body: formData,
    });
    const text = await response.text();
    let data = text;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {}
    this.logger?.action("api.upload", {
      path: `/api/files/upload/${projectId}`,
      file_name: fileName,
      status: response.status,
      ok: response.ok,
    });
    if (!response.ok) throw new Error(`Upload ${fileName}: ${response.status} ${String(text).slice(0, 300)}`);
    return data;
  }

  async sendChat({
    projectId,
    message,
    sessionId = null,
    maxHistory = 30,
    timeoutMs = 240000,
    headers = {},
    agentEngine = "",
  }) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    const started = Date.now();
    try {
      const response = await fetch(`${this.apiBase}/api/chat`, {
        method: "POST",
        headers: this.headers({
          ...this.chatHeaders,
          ...(agentEngine ? { "x-istara-agent-engine": agentEngine } : {}),
          ...headers,
        }),
        body: JSON.stringify({
          project_id: projectId,
          message,
          session_id: sessionId,
          include_history: true,
          max_history: maxHistory,
        }),
        signal: controller.signal,
      });
      const raw = await response.text();
      if (!response.ok) throw new Error(`POST /api/chat: ${response.status} ${raw.slice(0, 300)}`);
      const parsed = parseSse(raw);
      if (parsed.errors.length) {
        throw new Error(`POST /api/chat SSE error: ${parsed.errors.join(" | ").slice(0, 500)}`);
      }
      return {
        ok: true,
        duration_ms: Date.now() - started,
        raw,
        content: parsed.content,
        events: parsed.events,
        errors: parsed.errors,
        session_id: parsed.session_id || sessionId,
      };
    } finally {
      clearTimeout(timeout);
    }
  }
}

export function parseSse(raw) {
  const events = [];
  const errors = [];
  let content = "";
  let sessionId = "";
  for (const line of raw.split(/\r?\n/)) {
    if (!line.startsWith("data:")) continue;
    const body = line.slice(5).trim();
    if (!body || body === "[DONE]") continue;
    try {
      const event = JSON.parse(body);
      events.push(event);
      if (event.type === "chunk" && event.content) content += event.content;
      if (event.type === "error") errors.push(event.message || JSON.stringify(event));
      if (event.session_id) sessionId = event.session_id;
    } catch {
      content += body;
    }
  }
  return { events, errors, content, session_id: sessionId };
}
