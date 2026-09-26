/**
 * Registry integrity: every id must be unique — a duplicated id would let one
 * scenario file satisfy two registry entries and break the selection bijection.
 */
export function findDuplicateScenarioIds(source = scenarioFiles) {
  const seen = new Set();
  const duplicates = new Set();
  for (const id of source) {
    if (seen.has(id)) duplicates.add(id);
    seen.add(id);
  }
  return [...duplicates];
}

/**
 * Credential-free release obligations (remediation plan B1/B4/B5,
 * testing-to-main-remediation-20260909): these scenarios must reach a dated
 * container-lane execution before any release claim; until then the ui-journeys
 * ledger must name them explicitly as pending release obligations, never as a
 * generic "not yet proven" crowd.
 */
export const releaseObligationIds = Object.freeze([
  "82-quality-dashboard",
  "83-chat-model-controls",
  "84-token-session-lifecycle",
]);

/**
 * Scenario ids for the container-first ui-journeys lane (Phase 2+). The list is
 * the registry of record consumed by the runner, the CI selection resolver, and
 * the not_runnable boundary ledger (D.8).
 */
export const scenarioFiles = Object.freeze([
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
  "70-mid-execution-steering",
  "70-research-integrity",
  "71-plan-and-execute",
  "72-circuit-breaker-health",
  "73-a2a-debate-and-reports",
  "76-long-horizon-trajectory",
  "77-voice-transcription",
  "78-real-time-voice",
  "79-engine-selector",
  "75-participant-simulation",
  "74-2fa-login-flow",
  "80-channels-and-surveys-live-integration",
  "81-project-settings",
  "82-quality-dashboard",
  "83-chat-model-controls",
  "84-token-session-lifecycle",
  "85-retrieval-correctness",
]);
