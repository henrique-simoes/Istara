#!/usr/bin/env node
/**
 * Istara Test Marathon — Single Cycle Runner
 *
 * Runs one test cycle (A-L) from the marathon configuration.
 * Called by the scheduled task every 30 minutes.
 *
 * Usage:
 *   node scripts/marathon/run-cycle.mjs              # Auto-picks next cycle
 *   node scripts/marathon/run-cycle.mjs --cycle A    # Run specific cycle
 *   node scripts/marathon/run-cycle.mjs --all        # Run all cycles sequentially
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync, spawnSync } from "child_process";
import { runCustomChecks } from "./custom-checks.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, "..", "..");
const CONFIG_FILE = join(__dirname, "config.json");
const LOG_DIR = join(PROJECT_ROOT, "data", "test-marathon");
const CYCLES_DIR = join(LOG_DIR, "cycles");
const ISSUES_DIR = join(LOG_DIR, "issues");
const STATE_FILE = join(LOG_DIR, ".marathon-state.json");
const MARATHON_LOG = join(LOG_DIR, "MARATHON_LOG.md");

const API_BASE = process.env.ISTARA_API_URL || "http://localhost:8000";
const FRONTEND_BASE = process.env.ISTARA_FRONTEND_URL || "http://localhost:3000";

// JWT auth token (populated by authenticate())
let AUTH_TOKEN = null;

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (AUTH_TOKEN) h["Authorization"] = `Bearer ${AUTH_TOKEN}`;
  return h;
}

function stripEnvValue(value) {
  return String(value || "").trim().replace(/^['"]|['"]$/g, "");
}

function envValue(key) {
  const envFiles = [
    join(PROJECT_ROOT, "backend", ".env.local"),
    join(PROJECT_ROOT, "backend", ".env"),
    join(PROJECT_ROOT, ".env.local"),
    join(PROJECT_ROOT, ".env"),
  ];
  for (const envFile of envFiles) {
    try {
      const envContent = readFileSync(envFile, "utf-8");
      const match = envContent.match(new RegExp(`^(?:export\\s+)?${key}=(.+)$`, "m"));
      if (match) return stripEnvValue(match[1]);
    } catch {}
  }
  return "";
}

function localTokenAllowed() {
  return ["1", "true", "yes"].includes(String(process.env.ISTARA_E2E_ALLOW_LOCAL_TOKEN || "").toLowerCase());
}

function useLocalSignedToken(username) {
  if (!localTokenAllowed()) return false;

  const backendPath = join(PROJECT_ROOT, "backend");
  const script = [
    "import sys",
    `sys.path.insert(0, ${JSON.stringify(backendPath)})`,
    "from app.core.auth import create_token",
    `print(create_token("marathon-admin", ${JSON.stringify(username)}, "admin", mfa_verified=True))`,
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
    const token = stripEnvValue(result.stdout);
    if (!token) {
      lastError = `${pythonBin} returned an empty token`;
      continue;
    }
    AUTH_TOKEN = token;
    console.log("  ✅ Marathon authenticated with local signed token");
    return true;
  }

  console.log(`  ⚠ Local signed token fallback failed: ${lastError.substring(0, 160)}`);
  return false;
}

async function authenticate() {
  const providedToken = stripEnvValue(process.env.ISTARA_TEST_AUTH_TOKEN || "");
  if (providedToken) {
    AUTH_TOKEN = providedToken;
    console.log("  ✅ Marathon using provided test auth token");
    return;
  }
  const username = process.env.ADMIN_USERNAME || envValue("ADMIN_USERNAME") || "admin";
  let password = process.env.ADMIN_PASSWORD || envValue("ADMIN_PASSWORD");
  if (!password) {
    if (useLocalSignedToken(username)) return;
    console.log("  ⚠ No ADMIN_PASSWORD found — marathon may fail auth");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password: stripEnvValue(password) }),
    });
    if (res.ok) {
      const data = await res.json();
      AUTH_TOKEN = data.token || data.access_token;
      console.log("  ✅ Marathon authenticated");
    } else {
      console.log(`  ⚠ Auth failed: ${res.status}`);
      useLocalSignedToken(username);
    }
  } catch (e) {
    console.log(`  ⚠ Auth error: ${e.message}`);
    useLocalSignedToken(username);
  }
}

// Ensure directories
mkdirSync(CYCLES_DIR, { recursive: true });
mkdirSync(ISSUES_DIR, { recursive: true });

// Parse args
const args = process.argv.slice(2);
const specificCycle = args.includes("--cycle") ? args[args.indexOf("--cycle") + 1] : null;
const runAll = args.includes("--all");

// Load config
const config = JSON.parse(readFileSync(CONFIG_FILE, "utf-8"));

// Load/init state
function loadState() {
  if (existsSync(STATE_FILE)) {
    return JSON.parse(readFileSync(STATE_FILE, "utf-8"));
  }
  return {
    started_at: new Date().toISOString(),
    current_cycle_index: 0,
    total_cycles_completed: 0,
    total_checks_run: 0,
    total_passed: 0,
    total_failed: 0,
    issues: [],
    cycle_history: [],
  };
}

function saveState(state) {
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

// Environment checks
async function checkEnvironment() {
  const env = {
    backend: false,
    frontend: false,
    llm: false,
    network_llm: false,
    stitch_key: false,
    figma_key: false,
  };

  // Backend
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    env.backend = res.ok;
  } catch { /* not running */ }

  // Frontend
  try {
    const res = await fetch(FRONTEND_BASE);
    env.frontend = res.ok;
  } catch { /* not running */ }

  // LLM (requires auth)
  try {
    const res = await fetch(`${API_BASE}/api/llm-servers`, { headers: authHeaders() });
    if (res.ok) {
      const data = await res.json();
      const servers = data?.servers || (Array.isArray(data) ? data : []);
      const healthy = servers.filter((s) => s.is_healthy);
      env.llm = healthy.length > 0;
      env.network_llm = healthy.length > 1;
    }
  } catch { /* */ }

  // Stitch/Figma keys (requires auth)
  try {
    const res = await fetch(`${API_BASE}/api/settings/hardware`, { headers: authHeaders() });
    if (res.ok) {
      env.stitch_key = true; // If we can reach settings, keys are configured in .env
      env.figma_key = true;
    }
  } catch { /* */ }

  return env;
}

// Check if cycle requirements are met
function canRunCycle(cycle, env) {
  for (const req of cycle.requires || []) {
    if (!env[req]) return { can: false, missing: req };
  }
  return { can: true };
}

// Run simulation scenarios via the existing test runner
function parseScenarioOutput(output) {
  const scenarioSummary = output.match(/(?:PASS|FAIL)\s+\((\d+)\/(\d+)\)/);
  if (scenarioSummary) {
    const passed = Number.parseInt(scenarioSummary[1], 10);
    const total = Number.parseInt(scenarioSummary[2], 10);
    return { passed, failed: Math.max(0, total - passed) };
  }
  const passMatch = output.match(/(\d+)\s*passed/i);
  const failMatch = output.match(/(\d+)\s*failed/i);
  return {
    passed: passMatch ? Number.parseInt(passMatch[1], 10) : 0,
    failed: failMatch ? Number.parseInt(failMatch[1], 10) : 0,
  };
}

async function runScenarios(scenarioIds) {
  const results = [];
  const scenarioEnv = { ...process.env };
  if (AUTH_TOKEN && !scenarioEnv.ISTARA_TEST_AUTH_TOKEN) {
    scenarioEnv.ISTARA_TEST_AUTH_TOKEN = AUTH_TOKEN;
  }
  for (const id of scenarioIds) {
    try {
      const output = execSync(
        `cd "${PROJECT_ROOT}" && node tests/simulation/run.mjs --scenario ${id} --skip-eval 2>&1`,
        { timeout: 300000, encoding: "utf-8", maxBuffer: 10 * 1024 * 1024, env: scenarioEnv }
      );
      // Parse results from output
      const parsed = parseScenarioOutput(output);
      results.push({
        scenario: id,
        passed: parsed.passed,
        failed: parsed.failed,
        output: output.slice(-1200),
        success: parsed.failed === 0,
      });
    } catch (e) {
      const output = String(e.stdout || e.stderr || e.message || "Execution error");
      const parsed = parseScenarioOutput(output);
      results.push({
        scenario: id,
        passed: parsed.passed,
        failed: parsed.failed || 1,
        output: output.slice(-1200),
        success: false,
        error: true,
      });
    }
  }
  return results;
}

// Generate cycle report
function generateCycleReport(cycle, env, scenarioResults, customResults, startTime) {
  const endTime = new Date();
  const duration = Math.round((endTime - startTime) / 1000);

  const allChecks = [
    ...scenarioResults.map((r) => ({ name: `Scenario ${r.scenario}`, passed: r.success, detail: `${r.passed}P/${r.failed}F` })),
    ...customResults.map((r) => ({ name: r.check, passed: r.passed, detail: r.detail })),
  ];

  const totalPassed = allChecks.filter((c) => c.passed).length;
  const totalFailed = allChecks.filter((c) => !c.passed).length;
  const failures = allChecks.filter((c) => !c.passed);

  return {
    cycle_id: `${cycle.id}-${endTime.toISOString().replace(/[:.]/g, "-")}`,
    cycle_type: cycle.id,
    cycle_name: cycle.name,
    started_at: startTime.toISOString(),
    completed_at: endTime.toISOString(),
    duration_seconds: duration,
    environment: env,
    results: {
      total_checks: allChecks.length,
      passed: totalPassed,
      failed: totalFailed,
      pass_rate: allChecks.length ? Math.round((totalPassed / allChecks.length) * 1000) / 10 : 100,
    },
    checks: allChecks,
    failures,
    scenario_details: scenarioResults,
  };
}

// Update MARATHON_LOG.md
function updateMarathonLog(state, latestReport) {
  const issueCount = state.issues.length;
  const resolvedCount = state.issues.filter((i) => i.status === "FIXED").length;
  const passRate = state.total_checks_run > 0
    ? Math.round((state.total_passed / state.total_checks_run) * 1000) / 10
    : 0;

  let log = `# Istara Test Marathon — Pre-Release Validation

Started: ${state.started_at}
Last updated: ${new Date().toISOString()}

## Dashboard
- Total cycles completed: ${state.total_cycles_completed}
- Total checks run: ${state.total_checks_run}
- Overall pass rate: ${passRate}%
- Issues found: ${issueCount}
- Issues resolved: ${resolvedCount}
- Current/last cycle: ${latestReport.cycle_name} (${latestReport.cycle_type})

## Latest Cycle: ${latestReport.cycle_name}
- **Time**: ${latestReport.started_at} (${latestReport.duration_seconds}s)
- **Passed**: ${latestReport.results.passed}/${latestReport.results.total_checks} (${latestReport.results.pass_rate}%)
- **Failed**: ${latestReport.results.failed}
${latestReport.failures.length > 0 ? "\n### Failures\n" + latestReport.failures.map((f) => `- ❌ ${f.name}: ${f.detail}`).join("\n") : "\n✅ All checks passed!"}

## Issue Tracker
| # | Severity | Domain | Description | Found | Status |
|---|----------|--------|-------------|-------|--------|
${state.issues.map((issue, i) => `| ${i + 1} | ${issue.severity} | ${issue.domain} | ${issue.description} | ${issue.found_in} | ${issue.status} |`).join("\n") || "| - | - | - | No issues found yet | - | - |"}

## Cycle History (last 20)
${state.cycle_history.slice(-20).reverse().map((c) => `- **${c.cycle_name}** (${c.cycle_type}) — ${c.results.pass_rate}% (${c.results.passed}/${c.results.total_checks}) — ${c.duration_seconds}s — ${c.completed_at}`).join("\n")}
`;

  writeFileSync(MARATHON_LOG, log);
}

// Main execution
async function main() {
  const state = loadState();

  // Authenticate before anything else
  await authenticate();

  const env = await checkEnvironment();

  console.log("\n🏃 Istara Test Marathon — Cycle Runner");
  console.log("=====================================");
  console.log(`Backend: ${env.backend ? "✅" : "❌"}  Frontend: ${env.frontend ? "✅" : "❌"}  LLM: ${env.llm ? "✅" : "❌"}  Network LLM: ${env.network_llm ? "✅" : "❌"}`);
  console.log(`Stitch: ${env.stitch_key ? "✅" : "❌"}  Figma: ${env.figma_key ? "✅" : "❌"}`);

  if (!env.backend) {
    console.log("\n❌ Backend not running. Skipping cycle.");
    process.exit(0);
  }

  // Determine which cycle to run
  let cyclesToRun = [];
  if (specificCycle) {
    const cycle = config.cycles.find((c) => c.id === specificCycle.toUpperCase());
    if (!cycle) { console.error(`Unknown cycle: ${specificCycle}`); process.exit(1); }
    cyclesToRun = [cycle];
  } else if (runAll) {
    cyclesToRun = config.cycles;
  } else {
    // Auto-rotate through cycles
    const idx = state.current_cycle_index % config.cycles.length;
    cyclesToRun = [config.cycles[idx]];
    state.current_cycle_index = idx + 1;
  }

  for (const cycle of cyclesToRun) {
    const canRun = canRunCycle(cycle, env);
    if (!canRun.can) {
      console.log(`\n⏭️  Skipping cycle ${cycle.id} (${cycle.name}) — missing: ${canRun.missing}`);
      if (!runAll && !specificCycle) {
        // Auto-advance to next cycle if this one can't run
        state.current_cycle_index = (state.current_cycle_index) % config.cycles.length;
      }
      continue;
    }

    console.log(`\n🔄 Running cycle ${cycle.id}: ${cycle.name}`);
    console.log(`   ${cycle.description}`);
    const startTime = new Date();

    // Run scenarios
    console.log(`   Scenarios: ${(cycle.scenarios || []).join(", ")}`);
    const scenarioResults = await runScenarios(cycle.scenarios || []);

    // Run custom checks
    const customResults = await runCustomChecks(cycle.custom_checks, {
      apiBase: API_BASE,
      projectRoot: PROJECT_ROOT,
      authHeaders,
      fetchImpl: fetch,
    });

    // Generate report
    const report = generateCycleReport(cycle, env, scenarioResults, customResults, startTime);
    console.log(`   ✅ ${report.results.passed} passed  ❌ ${report.results.failed} failed  (${report.results.pass_rate}%) — ${report.duration_seconds}s`);

    // Save cycle report
    const cycleFile = join(CYCLES_DIR, `${report.cycle_id}.json`);
    writeFileSync(cycleFile, JSON.stringify(report, null, 2));

    // Track new failures as issues
    for (const failure of report.failures) {
      const existing = state.issues.find((i) => i.description === failure.name && i.status !== "FIXED");
      if (!existing) {
        state.issues.push({
          severity: "Medium",
          domain: cycle.name,
          description: failure.name,
          detail: failure.detail,
          found_in: report.cycle_id,
          status: "OPEN",
          found_at: new Date().toISOString(),
        });
      }
    }

    // Update state
    state.total_cycles_completed++;
    state.total_checks_run += report.results.total_checks;
    state.total_passed += report.results.passed;
    state.total_failed += report.results.failed;
    state.cycle_history.push({
      cycle_type: cycle.id,
      cycle_name: cycle.name,
      results: report.results,
      duration_seconds: report.duration_seconds,
      completed_at: report.completed_at,
    });

    saveState(state);
    updateMarathonLog(state, report);

    // Save issues
    writeFileSync(join(ISSUES_DIR, "all-issues.json"), JSON.stringify(state.issues, null, 2));
  }

  console.log("\n✅ Marathon cycle complete. Log: data/test-marathon/MARATHON_LOG.md\n");
}

main().catch((e) => {
  console.error("Marathon error:", e);
  process.exit(1);
});
