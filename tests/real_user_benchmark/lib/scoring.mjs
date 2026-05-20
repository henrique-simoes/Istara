const RUBRIC = [
  ["install", 10],
  ["onboarding", 8],
  ["corpus", 10],
  ["chat", 10],
  ["grounding", 10],
  ["tasks", 12],
  ["reports_findings", 10],
  ["integrations", 10],
  ["loops_autoresearch", 6],
  ["url_fetching", 4],
  ["interfaces", 4],
  ["stability_performance", 4],
  ["researcher_usefulness", 2],
];

export function scoreRun({ mode, metrics, integrationMatrix = [], blockers = [], completedTasks = 0, chatTurns = 0, uploadedDocuments = 0, sandbox = {}, featureResults = {} }) {
  const integrationScores = integrationMatrix.map((item) => {
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
    corpus: uploadedDocuments >= 20 ? 1 : uploadedDocuments > 0 ? 0.6 : metrics?.corpusDocuments >= 20 ? 0.4 : 0.2,
    chat: chatTurns >= 100 ? 1 : chatTurns >= 8 ? 0.45 : chatTurns > 0 ? 0.25 : 0.1,
    grounding: featureResults.citedSources ? 1 : featureResults.uploadedAndQueried ? 0.55 : 0.25,
    tasks: completedTasks >= 50 ? 1 : completedTasks >= 8 ? 0.45 : completedTasks > 0 ? 0.25 : 0.1,
    reports_findings: featureResults.findingsCreated || featureResults.reportGenerated ? 0.75 : 0.25,
    integrations: avgIntegration,
    loops_autoresearch: featureResults.loops ? 0.65 : 0.2,
    url_fetching: featureResults.urlFetch ? 0.7 : 0.2,
    interfaces: featureResults.interfaces ? 0.85 : 0.2,
    stability_performance: blockers.length === 0 ? 0.85 : blockers.length < 4 ? 0.55 : 0.25,
    researcher_usefulness: completedTasks >= 50 && chatTurns >= 100 ? 0.9 : 0.35,
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
    distinct_donor_endpoints_verified: Boolean(featureResults.distinctDonorEndpoints),
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
