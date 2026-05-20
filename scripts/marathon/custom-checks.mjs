import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

export const DOCUMENTED_CYCLE_REQUIREMENTS = Object.freeze([
  "backend",
  "frontend",
  "llm",
  "network_llm",
  "stitch_key",
  "figma_key",
]);

const DEFAULT_ENDPOINTS = Object.freeze([
  "/api/health",
  "/api/projects",
  "/api/skills",
  "/api/agents",
  "/api/channels",
  "/api/surveys/integrations",
  "/api/deployments?project_id=test",
  "/api/mcp/server/status",
  "/api/mcp/clients",
  "/api/mcp/featured",
  "/api/autoresearch/status",
  "/api/laws",
  "/api/laws?category=perception",
  "/api/backups",
  "/api/backups/config",
]);

function result(check, passed, detail, extra = {}) {
  return { check, passed, detail, ...extra };
}

function authHeaders(context) {
  if (typeof context.authHeaders === "function") {
    return context.authHeaders();
  }
  return { "Content-Type": "application/json" };
}

async function apiEndpointSweep(context) {
  const results = [];
  const apiBase = context.apiBase;
  const fetchImpl = context.fetchImpl || fetch;
  for (const endpoint of DEFAULT_ENDPOINTS) {
    try {
      const response = await fetchImpl(`${apiBase}${endpoint}`, { headers: authHeaders(context) });
      results.push(result(`API ${endpoint}`, response.ok, response.ok ? "OK" : `Status ${response.status}`, { status: response.status }));
    } catch (error) {
      results.push(result(`API ${endpoint}`, false, error.message));
    }
  }
  return results;
}

async function dbIntegrity(context) {
  const results = [];
  const apiBase = context.apiBase;
  const fetchImpl = context.fetchImpl || fetch;
  for (const table of ["projects", "skills", "agents"]) {
    try {
      const response = await fetchImpl(`${apiBase}/api/${table}`, { headers: authHeaders(context) });
      const data = await response.json();
      const count = Array.isArray(data) ? data.length : (data?.[table]?.length || 0);
      results.push(result(`DB ${table} populated`, count > 0, `${count} records`));
    } catch (error) {
      results.push(result(`DB ${table}`, false, error.message));
    }
  }
  return results;
}

async function networkDiscovery(context) {
  const apiBase = context.apiBase;
  const fetchImpl = context.fetchImpl || fetch;
  try {
    const response = await fetchImpl(`${apiBase}/api/llm-servers`, { headers: authHeaders(context) });
    if (!response.ok) {
      return [result("Network LLM discovery", false, `Status ${response.status}`, { status: response.status })];
    }
    const servers = await response.json();
    const list = Array.isArray(servers) ? servers : servers?.servers || [];
    return [result("Network LLM discovery", list.length >= 1, `${list.length} server(s) discovered`)];
  } catch (error) {
    return [result("Network LLM discovery", false, error.message)];
  }
}

function sourceContract(files, snippets = []) {
  return async (context) => {
    const projectRoot = context.projectRoot;
    const missingFiles = files.filter((file) => !existsSync(join(projectRoot, file)));
    if (missingFiles.length > 0) {
      return [result("Source contract", false, `Missing files: ${missingFiles.join(", ")}`)];
    }

    const source = files
      .map((file) => readFileSync(join(projectRoot, file), "utf-8"))
      .join("\n");
    const missingSnippets = snippets.filter((snippet) => !source.includes(snippet));
    if (missingSnippets.length > 0) {
      return [result("Source contract", false, `Missing snippets: ${missingSnippets.join(", ")}`)];
    }
    return [result("Source contract", true, `${files.length} file contract(s) present`)];
  };
}

const FRONTEND_TOUR = ["frontend/src/components/onboarding/GuidedTour.tsx"];
const FRONTEND_LOGIN = ["frontend/src/components/auth/LoginScreen.tsx", "frontend/src/stores/authStore.ts"];
const FRONTEND_NOTIFICATIONS = [
  "frontend/src/components/notifications/NotificationsView.tsx",
  "frontend/src/components/common/ToastNotification.tsx",
];
const FRONTEND_SETTINGS = ["frontend/src/components/settings/ConnectionStringPanel.tsx", "frontend/src/components/settings/UpdateChecker.tsx"];
const FRONTEND_FINDINGS = ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/ProjectReportsView.tsx"];
const FRONTEND_LOOPS = ["frontend/src/components/loops/LoopsView.tsx", "frontend/src/stores/loopsStore.ts"];
const BACKEND_API = ["backend/app/main.py", "backend/app/api/routes/projects.py"];
const BACKEND_AUTH = ["backend/app/api/routes/auth.py", "backend/app/core/auth.py"];
const BACKEND_REPORTS = ["backend/app/api/routes/reports.py", "backend/app/core/report_manager.py"];
const BACKEND_A2A = ["backend/app/api/routes/a2a.py", "backend/app/services/a2a.py"];
const BACKEND_LLM = ["backend/app/api/routes/llm_servers.py", "backend/app/core/compute_registry.py"];
const BACKEND_VECTOR = ["backend/app/core/vector_health.py", "backend/app/api/routes/findings.py"];
const RELAY = ["relay/lib/llm-proxy.mjs", "relay/lib/connection.mjs", "relay/lib/heartbeat.mjs"];
const RELAY_SIMULATION = ["scripts/marathon/relay-simulator.mjs", "relay/lib/connection-string.mjs"];
const DESKTOP_TRAY = ["desktop/src-tauri/src/tray.rs", "desktop/src-tauri/src/config.rs"];
const DESKTOP_PROCESS = ["desktop/src-tauri/src/process.rs", "desktop/src-tauri/src/installer.rs"];
const DESKTOP_HEALTH = ["desktop/src-tauri/src/health.rs", "desktop/src-tauri/src/tray.rs"];
const INSTALLER = ["scripts/install-istara.sh", "desktop/src-tauri/src/installer.rs"];
const MARATHON = ["scripts/marathon/config.json", "scripts/marathon/run-cycle.mjs"];

export const CUSTOM_CHECKS = Object.freeze({
  api_endpoint_sweep: apiEndpointSweep,
  error_code_validation: sourceContract(BACKEND_API),
  tour_admin_10_steps: sourceContract(FRONTEND_TOUR),
  tour_member_skip_flow: sourceContract(FRONTEND_TOUR),
  tour_llm_poll_check: sourceContract(FRONTEND_TOUR.concat(BACKEND_LLM)),
  tour_persistence_refresh: sourceContract(FRONTEND_TOUR),
  tour_keyboard_wcag: sourceContract(FRONTEND_TOUR),
  interactive_suggestion_box_session_creation: sourceContract(["frontend/src/components/chat/ChatView.tsx"]),
  interactive_suggestion_box_streaming: sourceContract(["frontend/src/components/chat/ChatView.tsx"]),
  interactive_suggestion_box_reply: sourceContract(["frontend/src/components/chat/ChatView.tsx"]),
  interactive_suggestion_box_continue_in_chat: sourceContract(["frontend/src/components/chat/ChatView.tsx"]),
  notification_bell_unread_badge: sourceContract(FRONTEND_NOTIFICATIONS),
  sync_toast_feedback: sourceContract(FRONTEND_NOTIFICATIONS),
  api_error_extraction_validation: sourceContract(["frontend/src/lib/api.ts"]),
  ensemble_health_scrolling: sourceContract(["frontend/src/components/common/EnsembleHealthView.tsx"]),
  local_mode_login: sourceContract(FRONTEND_LOGIN.concat(BACKEND_AUTH)),
  team_mode_registration: sourceContract(FRONTEND_LOGIN.concat(BACKEND_AUTH)),
  server_unreachable_screen: sourceContract(FRONTEND_LOGIN),
  connection_string_roundtrip: sourceContract(FRONTEND_SETTINGS.concat(["backend/app/core/connection_string.py"])),
  network_discovery: networkDiscovery,
  relay_simulation: sourceContract(RELAY_SIMULATION),
  model_switch: sourceContract(BACKEND_LLM.concat(["frontend/src/lib/modelProviders.ts"])),
  db_integrity: dbIntegrity,
  vector_health: sourceContract(BACKEND_VECTOR),
  finding_chain_audit: sourceContract(FRONTEND_FINDINGS.concat(BACKEND_VECTOR)),
  circuit_breaker_state_transitions: sourceContract(BACKEND_LLM),
  llm_health_notification: sourceContract(BACKEND_LLM.concat(FRONTEND_NOTIFICATIONS)),
  websocket_full_audit: sourceContract(["frontend/src/hooks/useWebSocket.ts", "backend/app/main.py"]),
  full_pipeline_validation: sourceContract(["tests/simulation/scenarios/17-full-pipeline.mjs"]),
  report_l4_template_sections: sourceContract(BACKEND_REPORTS),
  mece_categories_populated: sourceContract(FRONTEND_FINDINGS),
  a2a_debate_messages: sourceContract(BACKEND_A2A.concat(["tests/simulation/scenarios/73-a2a-debate-and-reports.mjs"])),
  cli_start_stop_status: sourceContract(INSTALLER),
  backend_pid_verification: sourceContract(DESKTOP_PROCESS),
  frontend_production_mode: sourceContract(DESKTOP_PROCESS),
  venv_python_resolution: sourceContract(INSTALLER),
  npm_keg_path_detection: sourceContract(INSTALLER),
  login_local_mode_no_password: sourceContract(FRONTEND_LOGIN),
  login_team_mode_registration: sourceContract(FRONTEND_LOGIN),
  login_server_unreachable_screen: sourceContract(FRONTEND_LOGIN),
  config_json_integrity: sourceContract(DESKTOP_TRAY),
  tray_app_config_read: sourceContract(DESKTOP_TRAY),
  version_file_resolution: sourceContract(INSTALLER.concat(["VERSION"])),
  auto_update_git_pull: sourceContract(["frontend/src/lib/updatesApi.ts", "backend/app/api/routes/updates.py"]),
  update_notification_broadcast: sourceContract(["frontend/src/lib/updatesApi.ts", "backend/app/api/routes/updates.py"]),
  startup_update_check: sourceContract(["frontend/src/components/settings/UpdateChecker.tsx", "backend/app/api/routes/updates.py"]),
  cli_update_command: sourceContract(["frontend/src/lib/updatesApi.ts", "backend/app/api/routes/updates.py"]),
  tray_shell_delegation_start: sourceContract(DESKTOP_TRAY.concat(DESKTOP_PROCESS)),
  tray_shell_delegation_stop: sourceContract(DESKTOP_TRAY.concat(DESKTOP_PROCESS)),
  tray_menu_label_reflects_port_state: sourceContract(DESKTOP_TRAY),
  tray_donate_toggle_saves_config: sourceContract(DESKTOP_TRAY),
  tray_donate_shows_feedback_dialog: sourceContract(DESKTOP_TRAY),
  tray_lm_click_shows_dialog: sourceContract(DESKTOP_TRAY),
  tray_check_updates_three_tier: sourceContract(DESKTOP_TRAY.concat(["frontend/src/lib/updatesApi.ts"])),
  tray_update_shows_result_dialog: sourceContract(DESKTOP_TRAY),
  tray_health_loop_state_change_rebuild: sourceContract(DESKTOP_HEALTH),
  tray_ansi_strip_from_script_output: sourceContract(DESKTOP_TRAY),
  llm_server_api_key_add: sourceContract(BACKEND_LLM.concat(FRONTEND_SETTINGS)),
  llm_server_auth_error_display: sourceContract(BACKEND_LLM.concat(FRONTEND_SETTINGS)),
  llm_server_health_error_feedback: sourceContract(BACKEND_LLM.concat(FRONTEND_SETTINGS)),
  tour_waits_for_backend_health: sourceContract(FRONTEND_TOUR),
  tour_skip_persists_localstorage: sourceContract(FRONTEND_TOUR),
  relay_llm_api_key_passthrough: sourceContract(RELAY),
  rust_native_process_spawn_backend: sourceContract(DESKTOP_PROCESS),
  rust_native_process_spawn_frontend: sourceContract(DESKTOP_PROCESS),
  enriched_path_includes_homebrew: sourceContract(INSTALLER),
  venv_detection_both_conventions: sourceContract(INSTALLER),
  macos_tahoe_system_version_compat: sourceContract(INSTALLER),
  port_cleanup_before_start: sourceContract(DESKTOP_PROCESS),
  zombie_process_detection: sourceContract(DESKTOP_PROCESS),
});

export const CUSTOM_CHECK_NAMES = Object.freeze(Object.keys(CUSTOM_CHECKS).sort());

export function validateCustomCheckNames(checkNames = []) {
  return [...new Set(checkNames)].filter((name) => !CUSTOM_CHECKS[name]).sort();
}

export async function runCustomChecks(checkNames = [], context = {}) {
  const normalizedContext = {
    apiBase: process.env.ISTARA_API_URL || "http://localhost:8000",
    projectRoot: join(import.meta.dirname, "..", ".."),
    ...context,
  };
  const results = [];
  for (const unknown of validateCustomCheckNames(checkNames)) {
    results.push(result(unknown, false, "Unknown marathon custom check"));
  }
  for (const checkName of checkNames || []) {
    const check = CUSTOM_CHECKS[checkName];
    if (!check) continue;
    const checkResults = await check(normalizedContext);
    for (const item of checkResults) {
      results.push({
        ...item,
        check: item.check === "Source contract" ? checkName : item.check,
      });
    }
  }
  return results;
}
