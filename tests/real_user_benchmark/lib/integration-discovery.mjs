import { existsSync, readFileSync } from "fs";
import { join } from "path";

export const CLASSIFICATIONS = {
  live: "live-tested",
  harness: "developer-harness-tested",
  setup: "setup-error-path-tested",
  blocked: "blocked-no-test-harness",
  missing: "not-implemented",
};

function fileContains(repoRoot, relPath, pattern) {
  const path = join(repoRoot, relPath);
  if (!existsSync(path)) return false;
  return pattern.test(readFileSync(path, "utf8"));
}

export function discoverStaticHarnesses(repoRoot) {
  return {
    stitch: {
      hasMockEndpoints: fileContains(repoRoot, "backend/app/api/routes/interfaces_mock.py", /interfaces\/mock\/generate/),
      hasLiveRoute: fileContains(repoRoot, "backend/app/api/routes/interfaces_screens.py", /interfaces\/screens\/generate/),
    },
    figma: {
      hasMockImport: fileContains(repoRoot, "backend/app/api/routes/interfaces_mock.py", /figma-import/),
      hasLiveRoute: fileContains(repoRoot, "backend/app/api/routes/interfaces_integrations.py", /figma/i),
    },
    surveys: {
      hasDemoBySimPrefix: fileContains(repoRoot, "backend/app/api/routes/surveys.py", /_is_demo_integration/),
      supportsTypeform: fileContains(repoRoot, "backend/app/api/routes/surveys.py", /typeform/),
      supportsSurveyMonkey: fileContains(repoRoot, "backend/app/api/routes/surveys.py", /surveymonkey/),
      supportsGoogleForms: fileContains(repoRoot, "backend/app/api/routes/surveys.py", /google_forms/),
    },
    telegram: {
      hasAdapter: fileContains(repoRoot, "backend/app/channels/telegram.py", /class TelegramAdapter/),
      hasChannelRoutes: fileContains(repoRoot, "backend/app/api/routes/channels.py", /channels\/\{instance_id\}\/start/),
    },
    aura: {
      hasDeployments: fileContains(repoRoot, "backend/app/api/routes/deployments.py", /deployments\/\{deployment_id\}\/respond/),
      hasConversationCreateApi: fileContains(repoRoot, "backend/app/api/routes/deployments.py", /post\(.+conversations/),
    },
    mcp: {
      hasRoutes: fileContains(repoRoot, "backend/app/api/routes/mcp.py", /mcp\/server\/status/),
      hasClientRoutes: fileContains(repoRoot, "backend/app/api/routes/mcp.py", /mcp\/clients/),
    },
  };
}

async function attempt(logger, integration, action, fn) {
  const started = Date.now();
  try {
    const result = await fn();
    logger.integrationAttempt({
      integration,
      action,
      ok: true,
      duration_ms: Date.now() - started,
      result: summarize(result),
    });
    return { ok: true, result };
  } catch (error) {
    logger.integrationAttempt({
      integration,
      action,
      ok: false,
      duration_ms: Date.now() - started,
      error: error.message,
    });
    return { ok: false, error: error.message };
  }
}

function summarize(value) {
  if (value === undefined) return {};
  if (typeof value === "string") return value.slice(0, 500);
  return JSON.parse(JSON.stringify(value, (_key, val) => {
    if (typeof val === "string" && val.length > 300) return `${val.slice(0, 300)}...`;
    return val;
  }));
}

export async function runIntegrationMatrix({ api, projectId, repoRoot, logger }) {
  const staticHarnesses = discoverStaticHarnesses(repoRoot);
  logger.writeJson("integration-static-discovery.json", staticHarnesses);
  const matrix = [];
  const projectScopeQuery = `project_id=${encodeURIComponent(projectId)}`;
  const projectQuerySuffix = `?${projectScopeQuery}`;

  const interfaceStatus = await attempt(logger, "interfaces", "GET /api/interfaces/status", () => api.get("/api/interfaces/status"));

  let stitchClass = staticHarnesses.stitch.hasMockEndpoints ? CLASSIFICATIONS.harness : CLASSIFICATIONS.missing;
  const stitchGenerate = await attempt(logger, "google_stitch", "POST /api/interfaces/mock/generate", () => api.post("/api/interfaces/mock/generate", {
    project_id: projectId,
    prompt: "CareNav readiness timeline with source confidence and caregiver-safe permissions",
    device_type: "DESKTOP",
  }));
  if (!stitchGenerate.ok) stitchClass = staticHarnesses.stitch.hasLiveRoute ? CLASSIFICATIONS.setup : CLASSIFICATIONS.blocked;
  matrix.push({
    integration: "Google Stitch",
    classification: stitchGenerate.ok ? CLASSIFICATIONS.harness : stitchClass,
    evidence: { static: staticHarnesses.stitch, status: interfaceStatus.result, attempt: stitchGenerate },
  });

  let screenId = stitchGenerate.result?.id;
  if (screenId) {
    await attempt(logger, "google_stitch", "POST /api/interfaces/mock/edit", () => api.post("/api/interfaces/mock/edit", {
      screen_id: screenId,
      instructions: "Add a source freshness warning for stale lab tasks.",
    }));
    await attempt(logger, "google_stitch", "POST /api/interfaces/mock/variants", () => api.post("/api/interfaces/mock/variants", {
      screen_id: screenId,
      variant_type: "REFINE",
      count: 2,
    }));
  }

  const figmaImport = await attempt(logger, "figma", "POST /api/interfaces/mock/figma-import", () => api.post("/api/interfaces/mock/figma-import", {
    project_id: projectId,
    figma_url: "https://www.figma.com/file/fake-benchmark/CareNav?node-id=1-2",
  }));
  matrix.push({
    integration: "Figma",
    classification: figmaImport.ok ? CLASSIFICATIONS.harness : (staticHarnesses.figma.hasLiveRoute ? CLASSIFICATIONS.setup : CLASSIFICATIONS.blocked),
    evidence: { static: staticHarnesses.figma, attempt: figmaImport },
  });

  for (const survey of [
    ["Typeform", "typeform", { api_token: "sim-typeform-token" }],
    ["SurveyMonkey", "surveymonkey", { access_token: "sim-surveymonkey-token" }],
    ["Google Forms", "google_forms", { service_account_json: "{}" }],
  ]) {
    const [label, platform, config] = survey;
    const created = await attempt(logger, label, "POST /api/surveys/integrations", () => api.post("/api/surveys/integrations", {
      platform,
      name: `SIM: Real User Benchmark ${label}`,
      config,
      project_id: projectId,
    }));
    let classification = created.ok && staticHarnesses.surveys.hasDemoBySimPrefix ? CLASSIFICATIONS.harness : CLASSIFICATIONS.setup;
    let link = null;
    if (created.ok) {
      link = await attempt(logger, label, "POST /api/surveys/links", () => api.post("/api/surveys/links", {
        integration_id: created.result.id,
        project_id: projectId,
        external_survey_id: `sim-${platform}-caregiver-readiness`,
        external_survey_name: `SIM: ${label} caregiver readiness survey`,
      }));
      if (link.ok) {
        await attempt(logger, label, "POST /api/surveys/links/{id}/sync", () => api.post(`/api/surveys/links/${link.result.id}/sync${projectQuerySuffix}`, {}));
        await attempt(logger, label, "GET /api/surveys/links/{id}/responses", () => api.get(`/api/surveys/links/${link.result.id}/responses${projectQuerySuffix}`));
      }
    } else if (!staticHarnesses.surveys[`supports${label.replace(/\s/g, "")}`]) {
      classification = CLASSIFICATIONS.missing;
    }
    matrix.push({
      integration: label,
      classification,
      evidence: { static: staticHarnesses.surveys, created, link },
    });
  }

  const telegram = await attempt(logger, "telegram", "POST /api/channels", () => api.post("/api/channels", {
    platform: "telegram",
    name: "SIM: Fake Telegram Bot",
    config: { bot_token: "000000:fake-token-for-benchmark" },
    project_id: projectId,
  }));
  let telegramClassification = telegram.ok ? CLASSIFICATIONS.setup : CLASSIFICATIONS.blocked;
  if (telegram.ok) {
    const start = await attempt(logger, "telegram", "POST /api/channels/{id}/start", () => api.post(`/api/channels/${telegram.result.id}/start${projectQuerySuffix}`, {}));
    const health = await attempt(logger, "telegram", "GET /api/channels/{id}/health", () => api.get(`/api/channels/${telegram.result.id}/health${projectQuerySuffix}`));
    telegramClassification = start.ok && start.result?.status === "started" ? CLASSIFICATIONS.live : CLASSIFICATIONS.setup;
    matrix.push({
      integration: "Telegram",
      classification: telegramClassification,
      evidence: { static: staticHarnesses.telegram, created: telegram, start, health },
    });
  } else {
    matrix.push({
      integration: "Telegram",
      classification: telegramClassification,
      evidence: { static: staticHarnesses.telegram, created: telegram },
    });
  }

  const deployment = await attempt(logger, "aura", "POST /api/deployments", () => api.post("/api/deployments", {
    project_id: projectId,
    name: "SIM: AURA Appointment Prep Interview",
    deployment_type: "interview",
    questions: [
      { text: "What made your last appointment prep easier or harder?", type: "open", expected_insight: "prep blockers" },
      { text: "When did reminders feel useful versus annoying?", type: "open", expected_insight: "reminder trust" },
      { text: "What would make caregiver involvement feel safe?", type: "open", expected_insight: "permission clarity" },
    ],
    channel_instance_ids: telegram.ok ? [telegram.result.id] : [],
    config: {
      adaptive: true,
      adaptive_enabled: true,
      max_followups: 2,
      intro_message: "We are testing appointment-prep coordination.",
      thank_you_message: "Thanks for helping improve CareNav.",
    },
    target_responses: 5,
  }));
  let auraClassification = deployment.ok ? CLASSIFICATIONS.setup : CLASSIFICATIONS.blocked;
  if (deployment.ok) {
    const deploymentProjectQuery = projectScopeQuery;
    await attempt(logger, "aura", "POST /api/deployments/{id}/activate", () => api.post(`/api/deployments/${deployment.result.id}/activate?${deploymentProjectQuery}`, {}));
    const response = await attempt(logger, "aura", "POST /api/deployments/{id}/respond without conversation harness", () => api.post(`/api/deployments/${deployment.result.id}/respond?${deploymentProjectQuery}`, {
      conversation_id: "simulated-conversation-without-create-api",
      message_text: "I missed my lab reminder because it came while I was at work.",
    }));
    if (response.ok && response.result?.action === "error") {
      auraClassification = CLASSIFICATIONS.blocked;
      logger.issue({
        area: "Telegram/AURA",
        severity: "high",
        title: "AURA participant response simulation lacks credential-free conversation harness",
        detail: "Deployment response endpoint requires an existing ChannelConversation, but the public routes do not expose a local simulator or conversation creation path.",
        evidence: response.result,
      });
    }
    matrix.push({
      integration: "Telegram AURA research process",
      classification: auraClassification,
      evidence: { static: staticHarnesses.aura, deployment, response },
    });
  }

  const mcpStatus = await attempt(logger, "mcp", "GET /api/mcp/server/status", () => api.get("/api/mcp/server/status"));
  const mcpProjectQuery = `?project_id=${encodeURIComponent(projectId)}`;
  const mcpClients = await attempt(logger, "mcp", "GET /api/mcp/clients", () => api.get(`/api/mcp/clients${mcpProjectQuery}`));
  const mcpClient = await attempt(logger, "mcp", "POST /api/mcp/clients fake HTTP", () => api.post("/api/mcp/clients", {
    name: "SIM: Fake local HTTP MCP server",
    transport: "http",
    url: "http://127.0.0.1:9/mcp",
    headers: { "X-Benchmark": "real-user" },
    project_id: projectId,
  }));
  let mcpClassification = mcpStatus.ok || mcpClients.ok ? CLASSIFICATIONS.setup : CLASSIFICATIONS.blocked;
  if (mcpClient.ok) {
    const discover = await attempt(logger, "mcp", "POST /api/mcp/clients/{id}/discover", () => api.post(`/api/mcp/clients/${mcpClient.result.id}/discover${mcpProjectQuery}`, {}));
    mcpClassification = discover.ok ? CLASSIFICATIONS.harness : CLASSIFICATIONS.setup;
  }
  matrix.push({
    integration: "MCP",
    classification: mcpClassification,
    evidence: { static: staticHarnesses.mcp, status: mcpStatus, clients: mcpClients, fakeClient: mcpClient },
  });

  logger.writeJson("integration-matrix.json", matrix);
  return matrix;
}
