#!/usr/bin/env node
/**
 * Istara Simulation Agent — automated QA, UX evaluation, and regression testing.
 *
 * Usage:
 *   node run.mjs                    # Full run (headless)
 *   node run.mjs --headless=false   # Watch in browser
 *   node run.mjs --scenario 01     # Single scenario
 *   node run.mjs --skip-eval        # Skip accessibility/heuristic evaluators
 *   node run.mjs --scenario-timeout-ms 7200000 # Override per-scenario timeout
 */

// playwright is imported lazily inside main() so that `--dry-run` engine-plan
// resolution (benchmark task B0-2) works in environments without the browser
// dependency installed. A live run imports it on demand right before launch.
import { mkdirSync, writeFileSync, readFileSync, existsSync, symlinkSync, unlinkSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { spawn, spawnSync } from "child_process";
import http from "http";
import https from "https";
import {
  SIMULATION_PROJECT_NAME,
  selectCanonicalSimulationProject,
} from "./lib/project-selection.mjs";
import { scenarioFiles } from "./lib/scenario-registry.mjs";
import {
  setAuthToken as setClientAuthToken,
  setDefaultEngine as setClientDefaultEngine,
} from "./lib/api-client.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(__dirname, ".results");
const RUNS_DIR = join(RESULTS_DIR, "runs");

// Parse CLI args
const args = process.argv.slice(2);
const headless = !args.includes("--headless=false");
const singleScenario = args.includes("--scenario") ? args[args.indexOf("--scenario") + 1] : null;
const skipEval = args.includes("--skip-eval");
const skipSkills = args.includes("--skip-skills");
const scenarioTimeoutArgIndex = args.indexOf("--scenario-timeout-ms");

// ── Benchmark engine plumbing (benchmark task B0-2) ────────────────────────
// `--engine pi|legacy|both` selects the AgenticDispatcher engine per request via
// the `x-istara-agent-engine` header (honored by the dispatcher; see
// backend/app/core/agentic/dispatcher.py). `--dry-run` resolves and prints the
// engine plan and exits WITHOUT launching a browser or any services, so the
// plumbing is verifiable in CI/T0 (plan acceptance A2).
const AGENT_ENGINE_HEADER = "x-istara-agent-engine";
const rawEngine = args.includes("--engine") ? args[args.indexOf("--engine") + 1] : null;
const dryRun = args.includes("--dry-run");

function resolveEngines(raw) {
  const value = String(raw || "").trim().toLowerCase();
  if (value === "both") return ["legacy", "pi"];
  if (value === "pi" || value === "legacy") return [value];
  console.error(`Invalid --engine=${raw}; expected one of pi|legacy|both.`);
  process.exit(2);
}
const selectedEngines = rawEngine !== null ? resolveEngines(rawEngine) : [];
// A single browser context carries one engine; `both` is a planning-only concept
// here (the paired Python runner drives real pairing). Live runs use the first
// concrete engine when exactly one is selected.
const liveEngineHeader = selectedEngines.length === 1 ? selectedEngines[0] : null;
if (liveEngineHeader) {
  // Consume the computed plan (B0-2 completion): every request the shared
  // client makes — including chat-producing paths — now carries the header,
  // and the [SIM] project fixture is pinned to the same persisted choice.
  setClientDefaultEngine(liveEngineHeader);
}

if (dryRun) {
  const plan = selectedEngines.length ? selectedEngines : ["(default)"];
  console.log("[dry-run] Istara simulation harness — no browser or services launched.");
  console.log(`[dry-run] scenario: ${singleScenario || "all"}`);
  for (const engine of plan) {
    const header =
      engine === "(default)"
        ? "(engine header unset — dispatcher default)"
        : `${AGENT_ENGINE_HEADER}: ${engine}`;
    console.log(`[dry-run] engine=${engine} -> ${header}`);
  }
  process.exit(0);
}

function parsePositiveInteger(value, fallback, label) {
  if (value === undefined || value === null || value === "") return fallback;
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    console.warn(`Invalid ${label}=${value}; using ${fallback}.`);
    return fallback;
  }
  return parsed;
}

const API_BASE = process.env.ISTARA_API_URL || "http://localhost:8000";
const FRONTEND = process.env.ISTARA_FRONTEND_URL || "http://localhost:3000";
const FIXED_TEST_MODEL = (process.env.ISTARA_FIXED_LLM_TEST_MODEL || "google/gemma-4-e4b").trim();

// Intercept Node-level fetch requests directed at loopback backend so scenarios
// with hardcoded localhost:8000 / 127.0.0.1:8000 resolve to API_BASE in Docker.
if (API_BASE !== "http://localhost:8000" && API_BASE !== "http://127.0.0.1:8000") {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = function (resource, options) {
    if (typeof resource === "string") {
      resource = resource.replace(/^http:\/\/(?:localhost|127\.0\.0\.1):8000/, API_BASE);
    } else if (resource instanceof URL) {
      if (
        (resource.hostname === "localhost" || resource.hostname === "127.0.0.1") &&
        resource.port === "8000"
      ) {
        const target = new URL(API_BASE);
        resource.protocol = target.protocol;
        resource.host = target.host;
        resource.port = target.port;
      }
    } else if (resource && typeof resource.url === "string") {
      const newUrl = resource.url.replace(/^http:\/\/(?:localhost|127\.0\.0\.1):8000/, API_BASE);
      if (newUrl !== resource.url) {
        resource = new Request(newUrl, resource);
      }
    }
    return originalFetch.call(this, resource, options);
  };
}


function requestJson(method, url, { headers = {}, body = null, timeoutMs = 0, label = "" } = {}) {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const transport = target.protocol === "https:" ? https : http;
    const payload = body === null || body === undefined ? null : JSON.stringify(body);
    const requestHeaders = { ...headers };
    if (payload !== null && !("Content-Length" in requestHeaders)) {
      requestHeaders["Content-Length"] = Buffer.byteLength(payload);
    }

    const req = transport.request(
      target,
      {
        method,
        headers: requestHeaders,
      },
      (res) => {
        const chunks = [];
        res.setEncoding("utf8");
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const text = chunks.join("");
          if (res.statusCode < 200 || res.statusCode >= 300) {
            reject(new Error(`${method} ${target.pathname}${target.search}: ${res.statusCode}`));
            return;
          }
          if (!text) {
            resolve({});
            return;
          }
          try {
            resolve(JSON.parse(text));
          } catch (e) {
            reject(new Error(`${method} ${target.pathname}${target.search}: invalid JSON (${e.message})`));
          }
        });
      }
    );

    req.on("error", reject);
    if (timeoutMs > 0) {
      req.setTimeout(timeoutMs, () => {
        req.destroy(
          new Error(`TIMEOUT: ${label || `${method} ${target.pathname}`} exceeded ${timeoutMs}ms`)
        );
      });
    }
    if (payload !== null) {
      req.write(payload);
    }
    req.end();
  });
}

// ── Timeout Configuration ──────────────────────────────────
// Per-scenario defaults stay bounded for regular CI, but long live-LLM rehearsals
// can opt into larger budgets without changing test code.
const DEFAULT_SCENARIO_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes per scenario
const SCENARIO_TIMEOUT_MS = parsePositiveInteger(
  process.env.ISTARA_SCENARIO_TIMEOUT_MS ||
    (scenarioTimeoutArgIndex >= 0 ? args[scenarioTimeoutArgIndex + 1] : undefined),
  DEFAULT_SCENARIO_TIMEOUT_MS,
  "scenario timeout"
);
const AUTH_MAX_ATTEMPTS = parsePositiveInteger(
  process.env.ISTARA_AUTH_MAX_ATTEMPTS,
  10,
  "auth max attempts"
);
const PLAYWRIGHT_NAV_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes for page navigations
const PLAYWRIGHT_ACTION_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes for actions/selectors
const DESKTOP_VIEWPORT = { width: 1280, height: 800 };

// ── Keep Computer Awake (macOS caffeinate) ─────────────────
let caffeinateProcess = null;

function startCaffeinate() {
  if (process.platform !== "darwin") return; // macOS only
  try {
    // -d: prevent display sleep, -i: prevent idle sleep,
    // -m: prevent disk sleep, -s: prevent system sleep (AC power)
    caffeinateProcess = spawn("caffeinate", ["-dims"], {
      stdio: "ignore",
      detached: false,
    });
    caffeinateProcess.on("error", () => {
      // caffeinate not available — not fatal
      caffeinateProcess = null;
    });
    caffeinateProcess.on("exit", () => {
      caffeinateProcess = null;
    });
    console.log("  caffeinate: keeping system awake during tests (PID " + caffeinateProcess.pid + ")");
  } catch {
    // Non-fatal — tests still run, machine might sleep
    console.warn("  caffeinate: could not start (non-fatal)");
  }
}

function stopCaffeinate() {
  if (caffeinateProcess) {
    try {
      caffeinateProcess.kill("SIGTERM");
    } catch {}
    caffeinateProcess = null;
  }
}

async function ensureBrowserScenarioState(page, { projectId = null, activeView = "chat" } = {}) {
  if (!apiClient._token) return false;

  const frontendOrigin = new URL(FRONTEND).origin;
  if (!page.url().startsWith(frontendOrigin)) {
    await page.goto(FRONTEND, { waitUntil: "domcontentloaded" });
  }

  await page.setViewportSize(DESKTOP_VIEWPORT).catch(() => {});
  await page.evaluate(
    ({ token, userId, projectId: selectedProjectId, activeView: selectedView }) => {
      localStorage.setItem("istara_token", token);
      localStorage.removeItem("istara_tour_state");
      if (userId) {
        localStorage.setItem("istara_auth_user_id", userId);
        localStorage.setItem(`istara_tour_completed_${userId}`, "true");
      } else {
        localStorage.removeItem("istara_auth_user_id");
        localStorage.setItem("istara_tour_completed_anonymous", "true");
      }
      if (selectedProjectId) {
        localStorage.setItem("istara-active-project", selectedProjectId);
      }
      if (selectedView) {
        localStorage.setItem("istara_active_view", selectedView);
      }
      window.dispatchEvent(new Event("istara:auth-changed"));
    },
    {
      token: apiClient._token,
      userId: apiClient._userId,
      projectId,
      activeView,
    }
  );
  await page.reload({ waitUntil: "domcontentloaded" });
  return true;
}

// ── API Client ──────────────────────────────────────────────

const apiClient = {
  _token: null,
  _userId: null,

  _setToken(token) {
    this._token = token || null;
    // Keep the module-level REST/chat client in lockstep with the harness
    // authentication state. Without this, API methods use the token while
    // imported chat/authHeaders helpers silently remain anonymous.
    setClientAuthToken(this._token || "");
  },

  _useLocalSignedToken(username) {
    if (!["1", "true", "yes"].includes(String(process.env.ISTARA_E2E_ALLOW_LOCAL_TOKEN || "").toLowerCase())) {
      return false;
    }
    const backendPath = join(__dirname, "../../backend");
    const script = [
      "import sys",
      `sys.path.insert(0, ${JSON.stringify(backendPath)})`,
      "from app.core.auth import create_token",
      `print(create_token("simulation-admin", ${JSON.stringify(username)}, "admin", mfa_verified=True))`,
    ].join("\n");

    const candidates = [
      process.env.PYTHON,
      process.env.PYTHON_EXECUTABLE,
      "python",
      "python3",
    ].filter(Boolean);

    let lastError = "";
    for (const pythonBin of candidates) {
      const result = spawnSync(pythonBin, ["-c", script], {
        encoding: "utf-8",
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"],
      });
      if (result.status !== 0) {
        lastError = (result.stderr || result.error?.message || "").trim();
        continue;
      }
      const token = (result.stdout || "").trim();
      if (!token) {
        lastError = `${pythonBin} returned an empty token`;
        continue;
      }
      this._setToken(token);
      this._userId = "simulation-admin";
      console.log("  ✅ Authenticated with local signed simulation token");
      return true;
    }

    console.warn(`  ⚠ Local signed token fallback failed: ${lastError.substring(0, 160)}`);
    return false;
  },

  async authenticate() {
    const providedToken = String(process.env.ISTARA_TEST_AUTH_TOKEN || "").trim();
    if (providedToken) {
      this._setToken(providedToken);
      try {
        const meRes = await fetch(`${API_BASE}/api/auth/me`, {
          headers: this._headers(),
        });
        if (meRes.ok) {
          const me = await meRes.json();
          this._userId = me.id || null;
        }
      } catch {}
      console.log("  ✅ Authenticated with provided simulation test token");
      return;
    }

    // Try to login with admin credentials from env or the backend env files.
    // Match app precedence: local overrides are tried before shared defaults.
    const envFiles = [
      "../../backend/.env.local",
      "../../backend/.env",
      "../../.env.local",
      "../../.env",
    ];
    const envValue = (key) => {
      for (const relPath of envFiles) {
        try {
          const envContent = readFileSync(
            join(dirname(fileURLToPath(import.meta.url)), relPath),
            "utf-8"
          );
          const match = envContent.match(new RegExp(`^${key}=(.+)$`, "m"));
          if (match) return match[1].trim();
        } catch {}
      }
      return "";
    };
    const username = process.env.ADMIN_USERNAME || envValue("ADMIN_USERNAME") || "admin";
    let password = process.env.ADMIN_PASSWORD || "";

    // Read password from env files if not set in environment
    if (!password) {
      password = envValue("ADMIN_PASSWORD");
    }

    if (!password) {
      if (this._useLocalSignedToken(username)) return;
      console.warn("  \u26A0 No ADMIN_PASSWORD found \u2014 tests may fail auth");
      return;
    }

    try {
      let res = null;
      for (let attempt = 0; attempt < AUTH_MAX_ATTEMPTS; attempt++) {
        res = await fetch(`${API_BASE}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        if (![429, 500, 502, 503, 504].includes(res.status)) break;
        if (attempt + 1 >= AUTH_MAX_ATTEMPTS) break;
        const retryAfter = Number(res.headers.get("retry-after") || "0");
        const transientWaitMs = Math.min(30_000, 1_000 * 2 ** attempt);
        const waitMs = res.status === 429
          ? Math.max(retryAfter * 1000, 65_000)
          : transientWaitMs;
        console.warn(
          `  ⚠ Auth transient status ${res.status}; retrying in ${Math.round(waitMs / 1000)}s`
        );
        await new Promise((resolve) => setTimeout(resolve, waitMs));
      }
      if (res.ok) {
        const data = await res.json();
        this._setToken(data.token || data.access_token);
        this._userId = data.user?.id || null;
        if (!this._userId && this._token) {
          try {
            const meRes = await fetch(`${API_BASE}/api/auth/me`, {
              headers: this._headers(),
            });
            if (meRes.ok) {
              const me = await meRes.json();
              this._userId = me.id || null;
            }
          } catch {}
        }
        console.log("  \u2705 Authenticated as admin");
      } else {
        console.warn(`  \u26A0 Auth failed: ${res.status}`);
        this._useLocalSignedToken(username);
      }
    } catch (e) {
      console.warn(`  \u26A0 Auth error: ${e.message}`);
      this._useLocalSignedToken(username);
    }
  },

  _headers() {
    const h = { "Content-Type": "application/json" };
    if (this._token) h["Authorization"] = `Bearer ${this._token}`;
    if (liveEngineHeader) h[AGENT_ENGINE_HEADER] = liveEngineHeader;
    return h;
  },

  async get(path) {
    const res = await fetch(`${API_BASE}${path}`, { headers: this._headers() });
    if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
    return res.json();
  },
  async post(path, body, options = {}) {
    try {
      return await requestJson("POST", `${API_BASE}${path}`, {
        headers: this._headers(),
        body,
        timeoutMs: options.timeoutMs,
        label: options.label || `POST ${path}`,
      });
    } catch (e) {
      throw e;
    }
  },
  async patch(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "PATCH",
      headers: this._headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`PATCH ${path}: ${res.status}`);
    return res.json();
  },
  async put(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "PUT",
      headers: this._headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`PUT ${path}: ${res.status}`);
    return res.json();
  },
  async delete(path) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers: this._headers(),
    });
    return res;
  },
  async uploadFile(projectId, filePath, fileName) {
    const { readFileSync } = await import("fs");
    const fileData = readFileSync(filePath);
    const formData = new FormData();
    formData.append("file", new Blob([fileData]), fileName);
    const headers = {};
    if (this._token) headers["Authorization"] = `Bearer ${this._token}`;
    const res = await fetch(`${API_BASE}/api/files/upload/${projectId}`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload ${fileName}: ${res.status}`);
    return res.json();
  },
  async uploadContent(projectId, content, fileName) {
    const formData = new FormData();
    formData.append("file", new Blob([content], { type: "text/plain" }), fileName);
    const headers = {};
    if (this._token) headers["Authorization"] = `Bearer ${this._token}`;
    const res = await fetch(`${API_BASE}/api/files/upload/${projectId}`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload ${fileName}: ${res.status}`);
    return res.json();
  },
};

// ── Data Generators ─────────────────────────────────────────

async function loadGenerators() {
  try {
    const interviews = await import("./data/generators/interviews.mjs");
    const surveys = await import("./data/generators/surveys.mjs");
    const usabilityTests = await import("./data/generators/usability-tests.mjs");
    const researchNotes = await import("./data/generators/research-notes.mjs");
    return { interviews, surveys, usabilityTests, researchNotes };
  } catch (e) {
    console.warn("⚠ Data generators not fully available:", e.message);
    // Provide fallback generators
    const fallback = {
      generateTranscript: () => ({
        filename: "interview-sim.txt",
        content: "[00:00] Interviewer: Tell me about your experience.\n[00:30] Sarah: It was mostly positive but the onboarding was confusing.\n[01:15] Interviewer: What specifically was confusing?\n[01:45] Sarah: I couldn't find where to set up my team workspace.\n",
      }),
      generateSurveyCSV: () => ({
        filename: "survey-sim.csv",
        content: "respondent_id,age,role,company_size,signup_ease,onboarding_satisfaction,feature_usefulness,time_to_first_task_min,would_recommend,open_feedback\nR001,28,Designer,50-200,4,3,4,5,8,The interface is clean but I got lost in the settings\nR002,35,PM,200-500,3,2,4,12,6,Onboarding took too long\nR003,42,Engineer,50-200,5,4,5,3,9,Love the keyboard shortcuts\n",
      }),
      generateUsabilityReport: () => ({
        filename: "usability-sim.md",
        content: "# Usability Test Report\n## Task 1: Create a project\n- Completion: 80%\n- Avg time: 45s\n- Errors: 1\n## SUS Score: 72\n",
      }),
      generateFieldNotes: () => ({
        filename: "field-notes-sim.md",
        content: "# Field Notes\n## Session 1\n**Participant:** Sarah Chen\n### Observations\n- Hesitated at the onboarding step 2\n- Asked 'what does context mean here?'\n### Notable Quotes\n> 'I wish the help text was more specific' — Sarah\n",
      }),
    };
    return {
      interviews: fallback,
      surveys: fallback,
      usabilityTests: fallback,
      researchNotes: fallback,
    };
  }
}

// ── Scenarios ───────────────────────────────────────────────

async function loadScenarios() {
  const scenarios = [];
  for (const file of scenarioFiles) {
    // --skip-skills omits the long-running all-skills comprehensive test
    if (skipSkills && file === "20-all-skills-comprehensive") continue;
    try {
      const mod = await import(`./scenarios/${file}.mjs`);
      scenarios.push({ id: mod.id || file, name: mod.name || file, run: mod.run });
    } catch (e) {
      console.warn(`⚠ Could not load scenario ${file}: ${e.message}`);
    }
  }
  return scenarios;
}

// ── Evaluators ──────────────────────────────────────────────

async function loadEvaluators() {
  const evalFiles = ["accessibility", "heuristics", "performance"];
  const evaluators = [];
  for (const file of evalFiles) {
    try {
      const mod = await import(`./evaluators/${file}.mjs`);
      evaluators.push({ name: mod.name || file, evaluate: mod.evaluate });
    } catch (e) {
      console.warn(`⚠ Could not load evaluator ${file}: ${e.message}`);
    }
  }
  return evaluators;
}

async function applyFixedTestModel() {
  // Model selection is governed by Pi Model Management. The harness validates
  // its requested identity but never mutates or restores classical global state.
  if (/^(1|true|yes)$/i.test(String(process.env.ISTARA_FIXED_LLM_SKIP || ""))) {
    console.log(`  Fixed test model pinning skipped (ISTARA_FIXED_LLM_SKIP); turns resolve via the unified provider plane.`);
    return null;
  }
  if (!FIXED_TEST_MODEL) return null;

  const statusRes = await fetch(`${API_BASE}/api/settings/models`, {
    headers: apiClient._headers(),
  });
  if (!statusRes.ok) {
    throw new Error(`Could not inspect active model before fixed-model test run (${statusRes.status})`);
  }

  const inventory = await statusRes.json();
  const known = Array.isArray(inventory.pi_catalog)
    && inventory.pi_catalog.some((entry) => entry?.model === FIXED_TEST_MODEL);
  if (!known) {
    throw new Error(
      `Fixed test model ${FIXED_TEST_MODEL} is not admitted by Pi Model Management; configure an endpoint before the run`,
    );
  }

  console.log(`  Fixed test model admitted by Pi Model Management: ${FIXED_TEST_MODEL}`);
  return FIXED_TEST_MODEL;
}

// ── Report Generation ───────────────────────────────────────

function generateReport(runDir, scenarioResults, evalResults, duration) {
  const timestamp = new Date().toISOString();
  const totalChecks = scenarioResults.reduce((sum, r) => sum + (r.result?.checks?.length || 0), 0);
  const totalPassed = scenarioResults.reduce((sum, r) => sum + (r.result?.passed || 0), 0);
  const totalFailed = scenarioResults.reduce((sum, r) => sum + (r.result?.failed || 0), 0);

  let md = `# Istara Simulation Report\n\n`;
  md += `**Run:** ${timestamp}\n`;
  md += `**Duration:** ${Math.round(duration / 1000)}s\n`;
  md += `**Overall:** ${totalPassed}/${totalChecks} checks passed (${totalChecks ? Math.round((totalPassed / totalChecks) * 100) : 0}%)\n\n`;

  // Scenario results
  md += `## Scenario Results\n\n`;
  md += `| # | Scenario | Passed | Failed | Status |\n`;
  md += `|---|----------|--------|--------|--------|\n`;
  for (const s of scenarioResults) {
    const status = s.result?.failed > 0 ? "FAIL" : s.result?.skipped ? "SKIP" : "PASS";
    md += `| ${s.id} | ${s.name} | ${s.result?.passed || 0} | ${s.result?.failed || 0} | ${status} |\n`;
  }

  // Detailed scenario output
  md += `\n## Detailed Results\n\n`;
  for (const s of scenarioResults) {
    md += `### ${s.name}\n`;
    if (s.result?.checks) {
      for (const c of s.result.checks) {
        md += `- ${c.passed ? "PASS" : "FAIL"} ${c.name}${c.detail ? `: ${c.detail}` : ""}\n`;
      }
    }
    if (s.error) md += `- ERROR: ${s.error}\n`;
    md += `\n`;
  }

  // Evaluator results
  if (evalResults.length > 0) {
    md += `## Evaluations\n\n`;
    for (const e of evalResults) {
      md += `### ${e.name}\n`;
      md += `${e.result?.summary || "No summary"}\n\n`;

      if (e.result?.scores) {
        md += `| Heuristic | Score | Observations |\n|-----------|-------|-------------|\n`;
        for (const s of e.result.scores) {
          md += `| ${s.id}: ${s.name} | ${s.score}/5 | ${s.observations[0] || ""} |\n`;
        }
        md += `\n`;
      }

      if (e.result?.violations?.length > 0) {
        md += `**Violations (${e.result.violations.length}):**\n`;
        for (const v of e.result.violations.slice(0, 20)) {
          md += `- [${v.impact}] ${v.view}: ${v.help} (${v.id})\n`;
        }
        md += `\n`;
      }

      if (e.result?.metrics) {
        md += `| Metric | Value | Threshold |\n|--------|-------|----------|\n`;
        for (const m of e.result.metrics) {
          md += `| ${m.name} | ${m.value}${m.unit} | ${m.threshold}${m.unit} |\n`;
        }
        md += `\n`;
      }
    }
  }

  // Issues for developers
  const issues = [];
  for (const s of scenarioResults) {
    if (s.result?.checks) {
      for (const c of s.result.checks) {
        if (!c.passed) {
          issues.push({
            source: s.name,
            title: c.name,
            detail: c.detail || "",
            severity: "medium",
            category: "functional",
          });
        }
      }
    }
  }
  for (const e of evalResults) {
    if (e.result?.violations) {
      for (const v of e.result.violations) {
        issues.push({
          source: `${e.name} — ${v.view}`,
          title: v.help || v.description,
          detail: v.helpUrl || "",
          severity: v.impact === "critical" ? "critical" : v.impact === "serious" ? "high" : "medium",
          category: "accessibility",
        });
      }
    }
    if (e.result?.scores) {
      for (const s of e.result.scores) {
        if (s.score < 3 && s.suggestions.length > 0) {
          issues.push({
            source: e.name,
            title: `${s.id}: ${s.name} — score ${s.score}/5`,
            detail: s.suggestions.join("; "),
            severity: "medium",
            category: "usability",
          });
        }
      }
    }
  }

  if (issues.length > 0) {
    md += `## Issues for Developers (${issues.length})\n\n`;
    const grouped = { critical: [], high: [], medium: [] };
    for (const i of issues) grouped[i.severity]?.push(i) || (grouped.medium.push(i));
    for (const [sev, items] of Object.entries(grouped)) {
      if (items.length === 0) continue;
      md += `### ${sev.toUpperCase()} (${items.length})\n`;
      for (const i of items) {
        md += `- **${i.title}** (${i.category}) — ${i.source}${i.detail ? `\n  ${i.detail}` : ""}\n`;
      }
      md += `\n`;
    }
  }

  md += `---\nGenerated by Istara Simulation Agent\n`;

  // Save
  writeFileSync(join(runDir, "report.md"), md);
  writeFileSync(
    join(runDir, "report.json"),
    JSON.stringify({ timestamp, duration, scenarioResults: scenarioResults.map((s) => ({ ...s, result: s.result })), evalResults: evalResults.map((e) => ({ name: e.name, result: e.result })), issues }, null, 2)
  );
  writeFileSync(join(runDir, "issues.json"), JSON.stringify(issues, null, 2));

  // Update history
  const historyPath = join(RESULTS_DIR, "history.json");
  const history = existsSync(historyPath) ? JSON.parse(readFileSync(historyPath, "utf-8")) : [];
  history.push({
    timestamp,
    duration,
    totalChecks,
    passed: totalPassed,
    failed: totalFailed,
    issueCount: issues.length,
    dir: runDir,
  });
  writeFileSync(historyPath, JSON.stringify(history, null, 2));

  // Update latest symlink
  const latestLink = join(RESULTS_DIR, "latest");
  try { unlinkSync(latestLink); } catch {}
  try { symlinkSync(runDir, latestLink); } catch {}

  return { md, issues };
}

// ── Main ────────────────────────────────────────────────────

async function main() {
  console.log("\n🐾 Istara Simulation Agent\n");

  const startTime = Date.now();
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const runDir = join(RUNS_DIR, timestamp);
  const screenshotDir = join(runDir, "screenshots");
  mkdirSync(screenshotDir, { recursive: true });

  // Check prerequisites
  console.log("Checking prerequisites...");
  try {
    await fetch(`${API_BASE}/api/health`);
    console.log("  Backend: OK");
  } catch {
    console.error("  Backend not reachable at", API_BASE);
    console.error("  Start the backend first: python -m uvicorn app.main:app --port 8000 --app-dir backend");
    process.exit(1);
  }

  try {
    await fetch(FRONTEND);
    console.log("  Frontend: OK");
  } catch {
    console.error("  Frontend not reachable at", FRONTEND);
    console.error("  Start the frontend first: cd frontend && npm run dev");
    process.exit(1);
  }

  // Authenticate the API client — all endpoints now require JWT
  await apiClient.authenticate();

  let settingsStatus = null;
  try {
    settingsStatus = await apiClient.get("/api/settings/status");
    console.log(`  LLM: ${settingsStatus?.services?.llm || "unknown"}`);
    console.log(`  LLM chat-ready: ${settingsStatus?.llm_readiness?.chat_ready === true}`);
  } catch (e) {
    console.log(`  LLM status unavailable: ${e.message}`);
  }

  // Keep the computer awake for the entire test run
  startCaffeinate();

  // Launch browser with generous timeouts so nothing times out prematurely
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({
    headless,
    args: [
      "--no-sandbox",
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
      "--mute-audio",
    ],
  });
  const context = await browser.newContext({
    viewport: DESKTOP_VIEWPORT,
    colorScheme: "dark",
    // Thread the selected benchmark engine onto every frontend-originated API
    // request (benchmark task B0-2); unset means the dispatcher default engine.
    ...(liveEngineHeader
      ? { extraHTTPHeaders: { [AGENT_ENGINE_HEADER]: liveEngineHeader } }
      : {}),
  });
  if (liveEngineHeader) {
    console.log(`Simulation engine: ${AGENT_ENGINE_HEADER}=${liveEngineHeader}`);
  }
  await context.grantPermissions(["microphone"], { origin: new URL(FRONTEND).origin }).catch(() => {});
  context.setDefaultTimeout(PLAYWRIGHT_ACTION_TIMEOUT_MS);
  context.setDefaultNavigationTimeout(PLAYWRIGHT_NAV_TIMEOUT_MS);

  // Route client-side API requests to API_BASE so browser code reaching for loopback
  // (127.0.0.1:8000 / localhost:8000) or /api/ endpoints resolves to the configured
  // backend server across Docker networks with origin aligned to CORS config.
  try {
    const apiTarget = new URL(API_BASE);
    await context.route(/.*(?::8000)?\/api\/.*/, async (route) => {
      const req = route.request();
      const targetUrl = new URL(req.url());
      targetUrl.protocol = apiTarget.protocol;
      targetUrl.host = apiTarget.host;
      targetUrl.port = apiTarget.port;

      const headers = { ...req.headers() };
      headers.origin = "http://localhost:3000";

      try {
        const response = await route.fetch({
          url: targetUrl.toString(),
          headers,
        });
        const responseHeaders = response.headers();
        responseHeaders["access-control-allow-origin"] = req.headers().origin || "*";
        responseHeaders["access-control-allow-credentials"] = "true";
        await route.fulfill({
          response,
          headers: responseHeaders,
        });
      } catch {
        await route.continue().catch(() => {});
      }
    });
  } catch (e) {
    console.warn(`  ⚠ Route proxy setup warning: ${e.message}`);
  }

  // Inject token and bypass onboarding across all future page navigations
  if (apiClient._token) {
    await context.addInitScript(
      ({ token, userId }) => {
        try {
          localStorage.setItem("istara_token", token);
          localStorage.removeItem("istara_tour_state");
          if (userId) {
            localStorage.setItem("istara_auth_user_id", userId);
            localStorage.setItem(`istara_tour_completed_${userId}`, "true");
          } else {
            localStorage.setItem("istara_tour_completed_anonymous", "true");
          }
        } catch {}
      },
      { token: apiClient._token, userId: apiClient._userId }
    );
  }

  const page = await context.newPage();
  page.setDefaultTimeout(PLAYWRIGHT_ACTION_TIMEOUT_MS);
  page.setDefaultNavigationTimeout(PLAYWRIGHT_NAV_TIMEOUT_MS);

  // Inject JWT token into browser localStorage so the frontend authenticates
  if (apiClient._token) {
    await page.goto(FRONTEND, { waitUntil: "domcontentloaded" });
    await page.evaluate(({ token, userId }) => {
      localStorage.setItem("istara_token", token);
      localStorage.removeItem("istara_tour_state");
      if (userId) {
        localStorage.setItem("istara_auth_user_id", userId);
        localStorage.setItem(`istara_tour_completed_${userId}`, "true");
      } else {
        localStorage.setItem("istara_tour_completed_anonymous", "true");
      }
    }, { token: apiClient._token, userId: apiClient._userId });
    await page.reload({ waitUntil: "domcontentloaded" });
    console.log("  ✅ JWT token injected into browser");
  }

  const screenshotFn = async (name) => {
    try {
      await page.screenshot({ path: join(screenshotDir, `${name}.png`) });
    } catch {}
  };

  // Load components
  const generators = await loadGenerators();
  const scenarios = await loadScenarios();
  const evaluators = skipEval ? [] : await loadEvaluators();

  // Pause all Istara agent/LLM operations so live test calls have exclusive
  // access to the configured test profile and local providers do not compete.
  let maintenancePaused = false;
  try {
    const pauseRes = await fetch(`${API_BASE}/api/settings/maintenance/pause?reason=simulation-tests`, {
      method: "POST",
      headers: apiClient._headers(),
    });
    if (pauseRes.ok) {
      const pauseData = await pauseRes.json();
      maintenancePaused = true;
      console.log(`  Istara operations paused for testing (${pauseData.paused_agents?.length || 0} agents halted)`);
    } else {
      console.log(`  Maintenance pause failed (${pauseRes.status}), tests may compete with agents for model`);
    }
  } catch (e) {
    console.log(`  Maintenance pause skipped: ${e.message}`);
  }

  try {
    await applyFixedTestModel();
  } catch (e) {
    throw new Error(`Fixed test model setup failed: ${e.message}`);
  }

  // ── Persistent Simulation Project ─────────────────────────
  // All scenarios share ONE project. This prevents dozens of orphan projects
  // from accumulating on every test run.
  const SIM_PROJECT_NAME = SIMULATION_PROJECT_NAME;
  let simProjectId = null;

  console.log("\nSetting up persistent simulation project...");
  try {
    // Clean up old SIM projects (any with [SIM] or [SIM- prefix)
    const allProjects = await apiClient.get("/api/projects");
    const { canonical, staleProjects } = selectCanonicalSimulationProject(allProjects, SIM_PROJECT_NAME);

    for (const project of staleProjects) {
      try { await apiClient.delete(`/api/projects/${project.id}`); } catch {}
    }

    if (canonical) {
      simProjectId = canonical.id;
      console.log(`  Reusing existing project: ${simProjectId}`);
      if (liveEngineHeader) {
        // Keep the persisted project choice in lockstep with the selected
        // engine so header-level and project-level routing agree (CF-SPEC-1).
        try {
          await apiClient.patch(`/api/projects/${simProjectId}`, { agentic_engine: liveEngineHeader });
          console.log(`  Project agentic_engine pinned: ${liveEngineHeader}`);
        } catch (e) {
          console.log(`  Could not pin project agentic_engine (${e.message}) — relying on header`);
        }
      }
    }

    // Create the canonical project if it doesn't exist
    if (!simProjectId) {
      const created = await apiClient.post("/api/projects", {
        name: SIM_PROJECT_NAME,
        description: "Persistent simulation project — all automated tests run against this single project.",
        company_context: "TechStart Inc — B2B SaaS project management platform. Target: mid-market teams (50-500 employees). Culture: data-driven, move fast, user-centric.",
        ...(liveEngineHeader ? { agentic_engine: liveEngineHeader } : {}),
      });
      simProjectId = created.id;
      console.log(`  Created new project: ${simProjectId}${liveEngineHeader ? ` (agentic_engine=${liveEngineHeader})` : ""}`);
    }

    if (simProjectId) {
      await context.addInitScript(
        ({ projectId }) => {
          try {
            if (projectId) localStorage.setItem("istara-active-project", projectId);
          } catch {}
        },
        { projectId: simProjectId }
      );
      await ensureBrowserScenarioState(page, { projectId: simProjectId, activeView: "chat" });
    }
  } catch (e) {
    console.log(`  Project setup failed: ${e.message} — scenarios will create as needed`);
  }

  // Context shared across scenarios
  const ctx = {
    api: apiClient,
    page,
    screenshot: screenshotFn,
    generators,
    projectId: simProjectId,
    maintenancePaused,
    frontendUrl: FRONTEND,
    token: apiClient._token,
    llmConnected: settingsStatus?.services?.llm === "connected",
    llmReadiness: settingsStatus?.llm_readiness || null,
    runDir,
    fixedTestModel: FIXED_TEST_MODEL,
  };

  // ── Run ALL scenarios — never skip, never bail early ──────
  // Each scenario gets a generous timeout. If it exceeds the timeout, it is
  // marked as TIMEOUT (a failure) and the runner moves on to the next scenario.
  console.log(`\nRunning ${singleScenario ? "scenario " + singleScenario : `${scenarios.length} scenarios`}...`);
  console.log(`  Per-scenario timeout: ${SCENARIO_TIMEOUT_MS / 60000} minutes\n`);

  const scenarioResults = [];
  const scenarioProgress = new Map();

  function recordScenarioProgress(scenarioId, partial = {}) {
    const snapshot = {
      id: scenarioId,
      updatedAt: new Date().toISOString(),
      ...partial,
    };
    scenarioProgress.set(scenarioId, snapshot);
    try {
      writeFileSync(
        join(runDir, `scenario-${scenarioId}-progress.json`),
        JSON.stringify(snapshot, null, 2)
      );
    } catch {}
  }

  for (const scenario of scenarios) {
    if (singleScenario && !scenario.id.includes(singleScenario)) continue;

    process.stdout.write(`  ${scenario.id}: ${scenario.name}... `);
    const scenarioStart = Date.now();
    const scenarioCtx = {
      ...ctx,
      scenarioId: scenario.id,
      reportProgress: (partial) => recordScenarioProgress(scenario.id, partial),
    };
    try {
      await ensureBrowserScenarioState(page, { projectId: simProjectId, activeView: "chat" });
      // Wrap scenario.run in a timeout — never let a single scenario hang the runner
      const result = await Promise.race([
        scenario.run(scenarioCtx),
        new Promise((_, reject) =>
          setTimeout(
            () => reject(new Error(`TIMEOUT after ${SCENARIO_TIMEOUT_MS / 60000} minutes`)),
            SCENARIO_TIMEOUT_MS
          )
        ),
      ]);
      const normalizedResult = Array.isArray(result)
        ? {
            checks: result,
            passed: result.filter((check) => check?.passed).length,
            failed: result.filter((check) => !check?.passed).length,
            summary: result.map((check) => `${check?.passed ? "PASS" : "FAIL"} ${check?.name || "Unnamed check"}`).join("\n"),
          }
        : result;
      const elapsed = ((Date.now() - scenarioStart) / 1000).toFixed(1);
      scenarioResults.push({ id: scenario.id, name: scenario.name, result: normalizedResult, elapsed });
      const status = normalizedResult.failed > 0 ? "FAIL" : normalizedResult.skipped ? "SKIP" : "PASS";
      console.log(`${status} (${normalizedResult.passed}/${normalizedResult.passed + normalizedResult.failed}) [${elapsed}s]`);
    } catch (e) {
      const elapsed = ((Date.now() - scenarioStart) / 1000).toFixed(1);
      const isTimeout = e.message.startsWith("TIMEOUT");
      const progress = scenarioProgress.get(scenario.id) || {};
      const partialChecks = Array.isArray(progress.checks) ? progress.checks : [];
      const checks = [
        ...partialChecks,
        {
          name: isTimeout ? "Scenario timed out" : "Scenario error",
          passed: false,
          detail: e.message,
        },
      ];
      scenarioResults.push({
        id: scenario.id,
        name: scenario.name,
        result: {
          checks,
          passed: checks.filter((check) => check?.passed).length,
          failed: checks.filter((check) => !check?.passed).length,
          partial: partialChecks.length > 0,
          summary: progress.summary || "",
        },
        error: e.message,
        elapsed,
        timedOut: isTimeout,
      });
      console.log(`${isTimeout ? "TIMEOUT" : "ERROR"}: ${e.message} [${elapsed}s]`);
    }
  }

  // Run evaluators
  const evalResults = [];
  if (!skipEval) {
    console.log(`\nRunning ${evaluators.length} evaluators...\n`);
    for (const evaluator of evaluators) {
      process.stdout.write(`  ${evaluator.name}... `);
      try {
        const result = await evaluator.evaluate(ctx);
        evalResults.push({ name: evaluator.name, result });
        console.log(result.summary || (result.passed ? "PASS" : "FAIL"));
      } catch (e) {
        evalResults.push({ name: evaluator.name, result: { passed: false, summary: e.message } });
        console.log(`ERROR: ${e.message}`);
      }
    }
  }

  // Clean up temporary projects created by cascade deletion tests
  try {
    const remaining = await apiClient.get("/api/projects");
    for (const p of remaining) {
      if (p.name?.startsWith("[SIM-TEMP]")) {
        try { await apiClient.delete(`/api/projects/${p.id}`); } catch {}
      }
    }
  } catch {}

  // Generate report
  const duration = Date.now() - startTime;
  const { md, issues } = generateReport(runDir, scenarioResults, evalResults, duration);

  await browser.close();

  // ── Comprehensive Summary — everything needing attention ───
  const totalPassed = scenarioResults.reduce((sum, r) => sum + (r.result?.passed || 0), 0);
  const totalFailed = scenarioResults.reduce((sum, r) => sum + (r.result?.failed || 0), 0);
  const totalChecks = totalPassed + totalFailed;

  const failedScenarios = scenarioResults.filter((s) => s.result?.failed > 0 || s.error);
  const timedOutScenarios = scenarioResults.filter((s) => s.timedOut);
  const errorScenarios = scenarioResults.filter((s) => s.error && !s.timedOut);
  const checkFailScenarios = scenarioResults.filter((s) => s.result?.failed > 0 && !s.error);

  console.log(`\n${"=".repeat(70)}`);
  console.log(`  ISTARA SIMULATION RESULTS`);
  console.log(`${"=".repeat(70)}`);
  console.log(`  Scenarios run : ${scenarioResults.length}`);
  console.log(`  Checks passed : ${totalPassed}/${totalChecks} (${totalChecks ? Math.round((totalPassed / totalChecks) * 100) : 0}%)`);
  console.log(`  Failures      : ${failedScenarios.length} scenario(s)`);
  console.log(`  Issues found  : ${issues.length}`);
  console.log(`  Duration      : ${Math.round(duration / 1000)}s`);
  console.log(`  Report        : ${join(runDir, "report.md")}`);
  console.log(`${"=".repeat(70)}`);

  // ── Detailed failure breakdown ───────────────────────────
  if (failedScenarios.length > 0) {
    console.log(`\n  ITEMS NEEDING ATTENTION (${failedScenarios.length})`);
    console.log(`  ${"-".repeat(66)}`);

    if (timedOutScenarios.length > 0) {
      console.log(`\n  TIMED OUT (${timedOutScenarios.length}):`);
      for (const s of timedOutScenarios) {
        console.log(`    - [${s.id}] ${s.name} (ran for ${s.elapsed}s)`);
      }
    }

    if (errorScenarios.length > 0) {
      console.log(`\n  ERRORS (${errorScenarios.length}):`);
      for (const s of errorScenarios) {
        console.log(`    - [${s.id}] ${s.name}: ${s.error}`);
      }
    }

    if (checkFailScenarios.length > 0) {
      console.log(`\n  FAILED CHECKS (${checkFailScenarios.length} scenario(s)):`);
      for (const s of checkFailScenarios) {
        const failedChecks = (s.result?.checks || []).filter((c) => !c.passed);
        console.log(`    - [${s.id}] ${s.name} (${s.result.failed} failed):`);
        for (const c of failedChecks) {
          console.log(`        * ${c.name}${c.detail ? ": " + c.detail : ""}`);
        }
      }
    }
  }

  // Print critical issues from evaluators too
  const critical = issues.filter((i) => i.severity === "critical");
  const high = issues.filter((i) => i.severity === "high");
  if (critical.length > 0 || high.length > 0) {
    console.log(`\n  CRITICAL/HIGH SEVERITY ISSUES (${critical.length + high.length}):`);
    for (const i of critical) {
      console.log(`    [CRITICAL] ${i.title} (${i.source})${i.detail ? " — " + i.detail : ""}`);
    }
    for (const i of high) {
      console.log(`    [HIGH] ${i.title} (${i.source})${i.detail ? " — " + i.detail : ""}`);
    }
  }

  if (failedScenarios.length === 0 && issues.length === 0) {
    console.log(`\n  ALL CLEAR — every scenario passed with no issues.`);
  }

  console.log();

  // Resume Istara operations after simulation tests complete
  if (maintenancePaused) {
    try {
      const resumeRes = await fetch(`${API_BASE}/api/settings/maintenance/resume`, {
        method: "POST",
        headers: apiClient._headers(),
      });
      if (resumeRes.ok) {
        const resumeData = await resumeRes.json();
        console.log(`  Istara operations resumed (${resumeData.resumed_agents?.length || 0} agents reactivated)`);
      }
    } catch {
      console.log(`  Could not resume Istara operations — restart the server if agents remain paused`);
    }
  }

  stopCaffeinate();
  process.exit(totalFailed > 0 ? 1 : 0);
}

// Safety: resume Istara operations and stop caffeinate on crash or interrupt
async function emergencyCleanup() {
  stopCaffeinate();
  try {
    await fetch(`${API_BASE}/api/settings/maintenance/resume`, {
      method: "POST",
      headers: apiClient._headers(),
    });
    console.log("  Istara operations resumed (emergency cleanup)");
  } catch { /* server may be down */ }
}

process.on("SIGINT", async () => {
  console.log("\n  Interrupted — cleaning up...");
  await emergencyCleanup();
  process.exit(130);
});

process.on("SIGTERM", async () => {
  await emergencyCleanup();
  process.exit(143);
});

main().catch(async (e) => {
  console.error("Fatal error:", e);
  await emergencyCleanup();
  process.exit(1);
});
