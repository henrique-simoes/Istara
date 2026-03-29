#!/usr/bin/env node
/**
 * ReClaw Simulation Agent — automated QA, UX evaluation, and regression testing.
 *
 * Usage:
 *   node run.mjs                    # Full run (headless)
 *   node run.mjs --headless=false   # Watch in browser
 *   node run.mjs --scenario 01     # Single scenario
 *   node run.mjs --skip-eval        # Skip accessibility/heuristic evaluators
 */

import { chromium } from "playwright";
import { mkdirSync, writeFileSync, readFileSync, existsSync, symlinkSync, unlinkSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { spawn } from "child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = join(__dirname, ".results");
const RUNS_DIR = join(RESULTS_DIR, "runs");

// Parse CLI args
const args = process.argv.slice(2);
const headless = !args.includes("--headless=false");
const singleScenario = args.includes("--scenario") ? args[args.indexOf("--scenario") + 1] : null;
const skipEval = args.includes("--skip-eval");
const skipSkills = args.includes("--skip-skills");

const API_BASE = "http://localhost:8000";
const FRONTEND = "http://localhost:3000";

// ── Timeout Configuration ──────────────────────────────────
// Generous timeouts to ensure the runner NEVER gets killed by timeouts.
// Per-scenario: 30 minutes. Total run: no global limit (scenarios run sequentially).
const SCENARIO_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes per scenario
const PLAYWRIGHT_NAV_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes for page navigations
const PLAYWRIGHT_ACTION_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes for actions/selectors

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

// ── API Client ──────────────────────────────────────────────

const apiClient = {
  _token: null,

  async authenticate() {
    // Try to login with admin credentials from env or .env file
    const username = process.env.ADMIN_USERNAME || "admin";
    let password = process.env.ADMIN_PASSWORD || "";

    // Read password from .env file if not set in environment
    if (!password) {
      try {
        const envContent = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../backend/.env"), "utf-8");
        const match = envContent.match(/ADMIN_PASSWORD=(.+)/);
        if (match) password = match[1].trim();
      } catch {}
    }

    if (!password) {
      console.warn("  \u26A0 No ADMIN_PASSWORD found \u2014 tests may fail auth");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (res.ok) {
        const data = await res.json();
        this._token = data.token || data.access_token;
        console.log("  \u2705 Authenticated as admin");
      } else {
        console.warn(`  \u26A0 Auth failed: ${res.status}`);
      }
    } catch (e) {
      console.warn(`  \u26A0 Auth error: ${e.message}`);
    }
  },

  _headers() {
    const h = { "Content-Type": "application/json" };
    if (this._token) h["Authorization"] = `Bearer ${this._token}`;
    return h;
  },

  async get(path) {
    const res = await fetch(`${API_BASE}${path}`, { headers: this._headers() });
    if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
    return res.json();
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
  const scenarioFiles = [
    "01-health-check",
    "02-onboarding",
    "03-project-setup",
    "04-file-upload",
    "05-chat-interaction",
    "06-skill-execution",
    "07-findings-chain",
    "08-kanban-workflow",
    "09-navigation-search",
    "10-agent-architecture",
    "10-settings-models",
    "11-agents-system",
    "12-chat-sessions",
    "13-task-agent-assignment",
    "14-agent-communication",
    "15-vector-db",
    "16-findings-population",
    "17-full-pipeline",
    "18-task-verification",
    "19-file-preview",
    "20-all-skills-comprehensive",
    "21-agent-work-simulation",
    "22-architecture-evaluation",
    "23-memory-view",
    "24-context-dag",
    "25-systemic-robustness",
    "26-model-session-persistence",
    "27-agent-identity-system",
    "28-self-evolution-prompt-compression",
    "29-documents-system",
    "30-event-wiring-audit",
    "31-task-documents-tools",
    "32-auth-flow",
    "33-task-locking",
    "34-compute-pool",
    "35-ensemble-validation",
    "36-llm-servers",
    "37-ensemble-health-view",
    "38-task-routing",
    "39-data-migration",
    "40-agent-identity-editing",
    "41-skill-creation",
    "42-content-guard",
    "43-process-hardening",
    "44-agent-factory",
    "45-interfaces-menu",
    "46-stitch-figma-integration",
    "47-atomic-research-design",
    "48-real-user-simulation",
    "49-loops-schedule",
    "50-notifications",
    "51-backup-system",
    "52-meta-hyperagent",
    "53-channel-lifecycle",
    "55-survey-integration",
    "56-mcp-server-security",
    "57-mcp-client-registry",
    "58-research-deployment",
    "59-agent-integration-knowledge",
    "61-autoresearch-isolation",
    "64-docker-security",
    "65-laws-of-ux",
    "66-featured-mcp-servers",
    "67-auth-enforcement",
    "68-data-security",
    "69-user-management-ui",
  ];

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

// ── Report Generation ───────────────────────────────────────

function generateReport(runDir, scenarioResults, evalResults, duration) {
  const timestamp = new Date().toISOString();
  const totalChecks = scenarioResults.reduce((sum, r) => sum + (r.result?.checks?.length || 0), 0);
  const totalPassed = scenarioResults.reduce((sum, r) => sum + (r.result?.passed || 0), 0);
  const totalFailed = scenarioResults.reduce((sum, r) => sum + (r.result?.failed || 0), 0);

  let md = `# ReClaw Simulation Report\n\n`;
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

  md += `---\nGenerated by ReClaw Simulation Agent\n`;

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
  console.log("\n🐾 ReClaw Simulation Agent\n");

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

  // Keep the computer awake for the entire test run
  startCaffeinate();

  // Launch browser with generous timeouts so nothing times out prematurely
  const browser = await chromium.launch({
    headless,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: "dark",
  });
  context.setDefaultTimeout(PLAYWRIGHT_ACTION_TIMEOUT_MS);
  context.setDefaultNavigationTimeout(PLAYWRIGHT_NAV_TIMEOUT_MS);
  const page = await context.newPage();
  page.setDefaultTimeout(PLAYWRIGHT_ACTION_TIMEOUT_MS);
  page.setDefaultNavigationTimeout(PLAYWRIGHT_NAV_TIMEOUT_MS);

  const screenshotFn = async (name) => {
    try {
      await page.screenshot({ path: join(screenshotDir, `${name}.png`) });
    } catch {}
  };

  // Load components
  const generators = await loadGenerators();
  const scenarios = await loadScenarios();
  const evaluators = skipEval ? [] : await loadEvaluators();

  // Pause all ReClaw agent/LLM operations so the model is free for testing.
  // Tests use the user's currently configured model — no model switching needed.
  // This prevents LM Studio from loading two models on limited RAM.
  let maintenancePaused = false;
  try {
    const pauseRes = await fetch(`${API_BASE}/api/settings/maintenance/pause?reason=simulation-tests`, {
      method: "POST",
      headers: apiClient._headers(),
    });
    if (pauseRes.ok) {
      const pauseData = await pauseRes.json();
      maintenancePaused = true;
      console.log(`  ReClaw operations paused for testing (${pauseData.paused_agents?.length || 0} agents halted)`);
    } else {
      console.log(`  Maintenance pause failed (${pauseRes.status}), tests may compete with agents for model`);
    }
    // Log which model tests will use
    const modelsRes = await fetch(`${API_BASE}/api/settings/models`, { headers: apiClient._headers() });
    if (modelsRes.ok) {
      const modelsData = await modelsRes.json();
      console.log(`  Using model: ${modelsData.active_model || "unknown"} (user-configured)`);
    }
  } catch (e) {
    console.log(`  Maintenance pause skipped: ${e.message}`);
  }

  // ── Persistent Simulation Project ─────────────────────────
  // All scenarios share ONE project. This prevents dozens of orphan projects
  // from accumulating on every test run.
  const SIM_PROJECT_NAME = "[SIM] ReClaw Simulation Project";
  let simProjectId = null;

  console.log("\nSetting up persistent simulation project...");
  try {
    // Clean up old SIM projects (any with [SIM] or [SIM- prefix)
    const allProjects = await apiClient.get("/api/projects");
    const simProjects = allProjects.filter(
      (p) => p.name?.startsWith("[SIM]") || p.name?.startsWith("[SIM-")
    );

    if (simProjects.length > 1) {
      // Multiple SIM projects exist — keep only the canonical one, delete rest
      const canonical = simProjects.find((p) => p.name === SIM_PROJECT_NAME);
      for (const p of simProjects) {
        if (canonical && p.id === canonical.id) continue;
        try { await apiClient.delete(`/api/projects/${p.id}`); } catch {}
      }
      if (canonical) {
        simProjectId = canonical.id;
        console.log(`  Reusing existing project: ${simProjectId}`);
      }
    } else if (simProjects.length === 1) {
      if (simProjects[0].name === SIM_PROJECT_NAME) {
        simProjectId = simProjects[0].id;
        console.log(`  Reusing existing project: ${simProjectId}`);
      } else {
        // Wrong name — delete and recreate
        try { await apiClient.delete(`/api/projects/${simProjects[0].id}`); } catch {}
      }
    }

    // Create the canonical project if it doesn't exist
    if (!simProjectId) {
      const created = await apiClient.post("/api/projects", {
        name: SIM_PROJECT_NAME,
        description: "Persistent simulation project — all automated tests run against this single project.",
        company_context: "TechStart Inc — B2B SaaS project management platform. Target: mid-market teams (50-500 employees). Culture: data-driven, move fast, user-centric.",
      });
      simProjectId = created.id;
      console.log(`  Created new project: ${simProjectId}`);
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
    llmConnected: false,
  };

  // ── Run ALL scenarios — never skip, never bail early ──────
  // Each scenario gets a generous timeout. If it exceeds the timeout, it is
  // marked as TIMEOUT (a failure) and the runner moves on to the next scenario.
  console.log(`\nRunning ${singleScenario ? "scenario " + singleScenario : `${scenarios.length} scenarios`}...`);
  console.log(`  Per-scenario timeout: ${SCENARIO_TIMEOUT_MS / 60000} minutes\n`);

  const scenarioResults = [];
  for (const scenario of scenarios) {
    if (singleScenario && !scenario.id.includes(singleScenario)) continue;

    process.stdout.write(`  ${scenario.id}: ${scenario.name}... `);
    const scenarioStart = Date.now();
    try {
      // Wrap scenario.run in a timeout — never let a single scenario hang the runner
      const result = await Promise.race([
        scenario.run(ctx),
        new Promise((_, reject) =>
          setTimeout(
            () => reject(new Error(`TIMEOUT after ${SCENARIO_TIMEOUT_MS / 60000} minutes`)),
            SCENARIO_TIMEOUT_MS
          )
        ),
      ]);
      const elapsed = ((Date.now() - scenarioStart) / 1000).toFixed(1);
      scenarioResults.push({ id: scenario.id, name: scenario.name, result, elapsed });
      const status = result.failed > 0 ? "FAIL" : result.skipped ? "SKIP" : "PASS";
      console.log(`${status} (${result.passed}/${result.passed + result.failed}) [${elapsed}s]`);
    } catch (e) {
      const elapsed = ((Date.now() - scenarioStart) / 1000).toFixed(1);
      const isTimeout = e.message.startsWith("TIMEOUT");
      scenarioResults.push({
        id: scenario.id,
        name: scenario.name,
        result: { checks: [], passed: 0, failed: 1 },
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
  console.log(`  RECLAW SIMULATION RESULTS`);
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

  // Resume ReClaw operations after simulation tests complete
  if (maintenancePaused) {
    try {
      const resumeRes = await fetch(`${API_BASE}/api/settings/maintenance/resume`, {
        method: "POST",
        headers: apiClient._headers(),
      });
      if (resumeRes.ok) {
        const resumeData = await resumeRes.json();
        console.log(`  ReClaw operations resumed (${resumeData.resumed_agents?.length || 0} agents reactivated)`);
      }
    } catch {
      console.log(`  Could not resume ReClaw operations — restart the server if agents remain paused`);
    }
  }

  stopCaffeinate();
  process.exit(totalFailed > 0 ? 1 : 0);
}

// Safety: resume ReClaw operations and stop caffeinate on crash or interrupt
async function emergencyCleanup() {
  stopCaffeinate();
  try {
    await fetch(`${API_BASE}/api/settings/maintenance/resume`, {
      method: "POST",
      headers: apiClient._headers(),
    });
    console.log("  ReClaw operations resumed (emergency cleanup)");
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
