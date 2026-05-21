const RUBRIC = [
  ["install", 8],
  ["onboarding", 7],
  ["corpus", 8],
  ["chat", 8],
  ["grounding", 9],
  ["tasks", 10],
  ["reports_findings", 9],
  ["integrations", 6],
  ["loops_autoresearch", 5],
  ["url_fetching", 3],
  ["interfaces", 3],
  ["stability_performance", 4],
  ["researcher_usefulness", 3],
  ["multi_user_collaboration", 8],
  ["interviews", 4],
  ["agentic_orchestration", 5],
];

const REPRESENTATIVE_CORPUS_DOCUMENTS = 120;

export function scoreRun({ mode, metrics, integrationMatrix = [], blockers = [], completedTasks = 0, chatTurns = 0, uploadedDocuments = 0, sandbox = {}, featureResults = {} }) {
  const requiredIntegrations = integrationMatrix.filter((item) => item.required_success !== false);
  const integrationScores = requiredIntegrations.map((item) => {
    switch (item.classification) {
      case "live-tested": return 1;
      case "developer-harness-tested": return 0.85;
      case "setup-error-path-tested": return 0.55;
      case "blocked-no-test-harness": return 0.25;
      case "not-implemented": return 0;
      default: return 0.2;
    }
  });
  const avgIntegration = integrationScores.length
    ? integrationScores.reduce((sum, item) => sum + item, 0) / integrationScores.length
    : 0;

  const raw = {
    install: sandbox.serverStarted ? 1 : sandbox.serverAttempted ? 0.45 : mode === "plan-only" ? 0.2 : 0.3,
    onboarding: featureResults.uiOnboarding ? 1 : featureResults.uiVisited ? 0.55 : 0.2,
    corpus: uploadedDocuments >= REPRESENTATIVE_CORPUS_DOCUMENTS
      ? 1
      : uploadedDocuments > 0
        ? 0.6
        : metrics?.corpusDocuments >= REPRESENTATIVE_CORPUS_DOCUMENTS
          ? 0.4
          : 0.2,
    chat: chatTurns >= 100 ? 1 : chatTurns >= 8 ? 0.45 : chatTurns > 0 ? 0.25 : 0.1,
    grounding: featureResults.citedSources ? 1 : featureResults.uploadedAndQueried ? 0.55 : 0.25,
    tasks: featureResults.taskReviewLoop && completedTasks >= 50 ? 1 : featureResults.taskReviewLoop && completedTasks >= 8 ? 0.55 : completedTasks > 0 ? 0.3 : 0.1,
    reports_findings: featureResults.approvedTaskFindings && featureResults.reportGenerated ? 1 : featureResults.findingsCreated || featureResults.reportGenerated ? 0.75 : 0.25,
    integrations: avgIntegration,
    loops_autoresearch: featureResults.loops ? 0.65 : 0.2,
    url_fetching: featureResults.urlFetch ? 0.7 : 0.2,
    interfaces: featureResults.interfaces ? 0.85 : 0.2,
    stability_performance: blockers.length === 0 ? 0.85 : blockers.length < 4 ? 0.55 : 0.25,
    researcher_usefulness: completedTasks >= 50 && chatTurns >= 100 && featureResults.multiUserCollaboration ? 0.95 : completedTasks > 0 && chatTurns > 0 ? 0.45 : 0.25,
    multi_user_collaboration: featureResults.multiUserCollaboration ? 1 : featureResults.researcherUi ? 0.5 : 0.15,
    interviews: featureResults.interviewProcess ? 1 : featureResults.interviewEvidence ? 0.55 : 0.2,
    agentic_orchestration: featureResults.naturalComputeOrchestration
      && featureResults.multiDonorCompute
      && featureResults.taskReviewLoop
      && featureResults.approvedTaskFindings
      ? 1
      : featureResults.naturalComputeOrchestration && featureResults.taskReviewLoop && featureResults.approvedTaskFindings
        ? 0.65
        : featureResults.naturalComputeOrchestration || featureResults.multiDonorCompute
          ? 0.45
          : 0.2,
  };

  const dimensions = RUBRIC.map(([key, weight]) => ({
    key,
    weight,
    score: Math.round(raw[key] * weight * 100) / 100,
    max: weight,
    ratio: raw[key],
  }));
  const total = Math.round(dimensions.reduce((sum, dim) => sum + dim.score, 0) * 10) / 10;
  return {
    total,
    max: 100,
    mode,
    completed_tasks: completedTasks,
    chat_turns: chatTurns,
    uploaded_documents: uploadedDocuments,
    compute_donation_verified: Boolean(featureResults.computeDonation),
    multi_donor_compute_verified: Boolean(featureResults.multiDonorCompute),
    natural_compute_orchestration_verified: Boolean(featureResults.naturalComputeOrchestration),
    distinct_donor_endpoints_verified: Boolean(featureResults.distinctDonorEndpoints),
    multi_user_collaboration_verified: Boolean(featureResults.multiUserCollaboration),
    task_review_loop_verified: Boolean(featureResults.taskReviewLoop),
    approved_task_findings_verified: Boolean(featureResults.approvedTaskFindings),
    interview_process_verified: Boolean(featureResults.interviewProcess),
    compute_donor_count_requested: sandbox.relayExpectedCount || 0,
    compute_donor_count_started: sandbox.relayStartedCount || 0,
    donor_model_server_count_requested: sandbox.modelServerExpectedCount || 0,
    donor_model_server_count_started: sandbox.modelServerStartedCount || 0,
    live_chat_verified: Boolean(featureResults.liveChat),
    dimensions,
    blockers,
    integration_summary: integrationMatrix.map((item) => ({
      integration: item.integration,
      classification: item.classification,
      required_success: item.required_success !== false,
    })),
  };
}

export function writeScorecardMarkdown(scorecard) {
  const lines = [
    "## Scorecard",
    "",
    `Overall score: ${scorecard.total}/100`,
    "",
    "| Dimension | Score | Max |",
    "| --- | ---: | ---: |",
  ];
  for (const dim of scorecard.dimensions) {
    lines.push(`| ${dim.key} | ${dim.score} | ${dim.max} |`);
  }
  if (scorecard.blockers.length) {
    lines.push("", "## Blockers", "");
    for (const blocker of scorecard.blockers) {
      lines.push(`- ${blocker}`);
    }
  }
  if (scorecard.integration_summary.length) {
    lines.push("", "## Integration Classifications", "");
    for (const item of scorecard.integration_summary) {
      lines.push(`- ${item.integration}: ${item.classification}`);
    }
  }
  return `${lines.join("\n")}\n`;
}
