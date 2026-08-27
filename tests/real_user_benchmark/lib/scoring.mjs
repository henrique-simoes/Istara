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
const ACCEPTANCE_PROFILES = new Set(["provider", "petals", "combined"]);

// Acceptance profiles are executable workload contracts, not scorecard labels.
// Keep the matrix in this small, dependency-free module so both the runner and
// deterministic contract tests use exactly the same scope declaration.
const ACCEPTANCE_WORKLOADS = Object.freeze({
  provider: Object.freeze({
    provider: true,
    petals: false,
    corpus: true,
    coding: true,
    commonWorkflow: false,
    chat: false,
    tasks: false,
    ui: false,
    selfImprovement: false,
    integrations: false,
    findings: false,
    marathon: false,
    longHorizon: false,
  }),
  petals: Object.freeze({
    provider: false,
    petals: true,
    corpus: false,
    coding: false,
    commonWorkflow: false,
    chat: false,
    tasks: false,
    ui: false,
    selfImprovement: false,
    integrations: false,
    findings: false,
    marathon: false,
    longHorizon: false,
  }),
  combined: Object.freeze({
    provider: true,
    petals: true,
    corpus: true,
    coding: true,
    commonWorkflow: true,
    chat: true,
    tasks: true,
    ui: true,
    selfImprovement: true,
    integrations: true,
    findings: true,
    marathon: true,
    longHorizon: true,
  }),
});

export function normalizeAcceptanceProfile(value = "combined") {
  const normalized = String(value || "combined").trim().toLowerCase();
  return ACCEPTANCE_PROFILES.has(normalized) ? normalized : "combined";
}

export function benchmarkWorkloadForProfile(profile = "combined") {
  const normalizedProfile = normalizeAcceptanceProfile(profile);
  return { ...ACCEPTANCE_WORKLOADS[normalizedProfile] };
}

export function profileRunsSurface(profile, surface) {
  return Boolean(benchmarkWorkloadForProfile(profile)[surface]);
}

/**
 * Report which validity gates were selected and what evidence they reached.
 *
 * Provider validity is the Research Spine path (independent model coding,
 * reliability, reconciliation, and promotion). Petals validity is the
 * donated-compute/relay interoperability path. They are deliberately
 * reported separately so a passing donation relay cannot masquerade as
 * Research Spine evidence, or vice versa.
 */
export function acceptanceGateStatus({
  profile = "combined",
  codingValidationEnabled = false,
  requireComputeDonation = false,
  requireLongHorizon = false,
  longHorizonVerified = false,
  featureResults = {},
} = {}) {
  const normalizedProfile = normalizeAcceptanceProfile(profile);
  const providerSelected = normalizedProfile !== "petals";
  const petalsSelected = normalizedProfile !== "provider";
  const providerEnabled = providerSelected && Boolean(codingValidationEnabled);
  const petalsEnabled = petalsSelected && Boolean(requireComputeDonation);
  // Coding is only accepted as a provider gate when the independent
  // multi-model run and source-grounded Research Spine traceability are also
  // present.  Keeping this invariant in the scorecard prevents callers with
  // an inconsistent feature payload from receiving a false "verified" result.
  const providerVerified = providerEnabled
    && Boolean(featureResults.codingValidation)
    && Boolean(featureResults.multiModelResearchSpineValidation)
    && Boolean(featureResults.researchSpineTraceability);
  const petalsVerified = petalsEnabled && Boolean(featureResults.computeDonation);
  const gate = (selected, enabled, verified) => ({
    selected,
    status: !selected ? "not_selected" : !enabled ? "not_run" : verified ? "verified" : "blocked",
    verified: Boolean(verified),
  });
  const combinedSelected = normalizedProfile === "combined";
  const combinedVerified = combinedSelected
    && providerVerified
    && petalsVerified
    && (!requireLongHorizon || Boolean(longHorizonVerified));
  const combinedStatus = !combinedSelected
    ? "not_selected"
    : combinedVerified
      ? "verified"
      : !providerEnabled && !petalsEnabled
        ? "not_run"
        : "blocked";

  return {
    profile: normalizedProfile,
    provider: gate(providerSelected, providerEnabled, providerVerified),
    petals: gate(petalsSelected, petalsEnabled, petalsVerified),
    combined: {
      selected: combinedSelected,
      status: combinedStatus,
      verified: combinedVerified,
    },
  };
}

export function benchmarkExitCode({ mode, blockers = [] }) {
  if (mode === "plan-only") return 0;
  return blockers.length > 0 ? 1 : 0;
}

export function liveAcceptanceBlockers({
  maxChatTurns = 0,
  chatTurnCount = 0,
  maxTasks = 0,
  completedTasks = 0,
  codingValidationEnabled = false,
  acceptanceProfile = null,
  requireComputeDonation = false,
  requireLongHorizon = false,
  longHorizonVerified = false,
  featureResults = {},
}) {
  const blockers = [];
  if (maxChatTurns > 0 && chatTurnCount < maxChatTurns) {
    blockers.push(`Live run completed only ${chatTurnCount}/${maxChatTurns} requested chat turns.`);
  }
  if (maxTasks > 0 && completedTasks < 1) {
    blockers.push(`Live run completed no human-reviewed task approvals from ${maxTasks} requested tasks.`);
  }
  if (maxTasks > 0 && !featureResults.taskReviewLoop) {
    blockers.push("Requested task review/revision workflow did not complete.");
  }
  if (maxTasks > 0 && !featureResults.approvedTaskFindings) {
    blockers.push("Requested task-backed Findings/report path did not complete.");
  }
  // A selected acceptance profile is an executable contract, not merely a
  // scorecard label.  If a caller explicitly disables the selected gate, fail
  // closed before scorecard output can be mistaken for a passing retake.  Keep
  // the legacy behavior when no profile is supplied so older harness-only
  // callers retain their narrower workflow assertions.
  if (acceptanceProfile) {
    const normalizedProfile = normalizeAcceptanceProfile(acceptanceProfile);
    const providerSelected = normalizedProfile !== "petals";
    const petalsSelected = normalizedProfile !== "provider";
    if (providerSelected && !codingValidationEnabled) {
      blockers.push("Selected provider Research Spine gate was disabled; acceptance cannot pass.");
    } else if (providerSelected && !featureResults.codingValidation) {
      blockers.push("Requested three-model Research Spine coding validation did not complete.");
    } else if (providerSelected && !featureResults.multiModelResearchSpineValidation) {
      blockers.push("Requested independent multi-model Research Spine validation did not complete.");
    }
    if (providerSelected && codingValidationEnabled && !featureResults.researchSpineTraceability) {
      blockers.push("Requested Research Spine traceability validation did not complete.");
    }
    if (petalsSelected && !requireComputeDonation) {
      blockers.push("Selected Petals donation interoperability gate was disabled; acceptance cannot pass.");
    } else if (petalsSelected && !featureResults.computeDonation) {
      blockers.push("Requested Petals donation interoperability did not complete.");
    }
  } else {
    if (codingValidationEnabled && !featureResults.codingValidation) {
      blockers.push("Requested three-model Research Spine coding validation did not complete.");
    }
    if (codingValidationEnabled && featureResults.codingValidation && !featureResults.multiModelResearchSpineValidation) {
      blockers.push("Requested independent multi-model Research Spine validation did not complete.");
    }
    if (codingValidationEnabled && !featureResults.researchSpineTraceability) {
      blockers.push("Requested Research Spine traceability validation did not complete.");
    }
  }
  if (requireLongHorizon && !longHorizonVerified) {
    blockers.push("Requested two-call long-horizon workload did not complete in the Docker runner.");
  }
  return blockers;
}

export function scoreRun({ mode, metrics, integrationMatrix = [], blockers = [], completedTasks = 0, chatTurns = 0, uploadedDocuments = 0, sandbox = {}, featureResults = {}, acceptanceProfile = "combined", codingValidationEnabled = false, requireComputeDonation = false, requireLongHorizon = false, longHorizonVerified = false, workloadScope = null, unrelatedWorkflowFailures = [], connectionRevocation = null }) {
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
    loops_autoresearch: featureResults.selfImprovementGovernance
      && featureResults.telemetryEvidence
      && featureResults.autoresearchEvidence
      ? 1
      : featureResults.selfImprovementGovernance
        || featureResults.reasoningBankEvidence
        || featureResults.metaHyperagentEvidence
        || featureResults.loops
          ? 0.65
          : 0.2,
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
  // Keep the legacy traceability field as a structural-presence alias, but expose
  // accepted validation separately so a populated graph cannot be mistaken for
  // three-model coding, reliability, reconciliation, and promotion evidence.
  const researchSpineStructurePresent = Boolean(featureResults.researchSpineTraceability);
  const researchSpineValidationVerified = Boolean(
    featureResults.codingValidation
      && featureResults.multiModelResearchSpineValidation
      && featureResults.researchSpineTraceability,
  );
  const researchSpineDonorRoutesVerified = Boolean(featureResults.multiModelResearchSpineValidation);
  const acceptanceGates = acceptanceGateStatus({
    profile: acceptanceProfile,
    codingValidationEnabled,
    requireComputeDonation,
    requireLongHorizon,
    longHorizonVerified,
    featureResults,
  });
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
    coding_validation_verified: Boolean(featureResults.codingValidation),
    ensemble_coding_verified: Boolean(featureResults.ensembleCodingValidation),
    synthetic_reconciliation_verified: Boolean(featureResults.syntheticReconciliationValidation),
    donor_endpoint_contract_verified: Boolean(featureResults.distinctDonorEndpoints),
    research_spine_structure_present: researchSpineStructurePresent,
    research_spine_validation_verified: researchSpineValidationVerified,
    research_spine_donor_routes_verified: researchSpineDonorRoutesVerified,
    research_spine_traceability_verified: researchSpineStructurePresent,
    acceptance_profile: acceptanceGates.profile,
    workload_scope: workloadScope || benchmarkWorkloadForProfile(acceptanceGates.profile),
    long_horizon_required: Boolean(requireLongHorizon),
    long_horizon_verified: Boolean(longHorizonVerified),
    unrelated_workflow_failures: [...unrelatedWorkflowFailures],
    connection_revocation: connectionRevocation,
    acceptance_gates: acceptanceGates,
    telemetry_evidence_verified: Boolean(featureResults.telemetryEvidence),
    reasoning_bank_evidence_verified: Boolean(featureResults.reasoningBankEvidence),
    memento_skill_evidence_verified: Boolean(featureResults.mementoSkillEvidence),
    meta_hyperagent_evidence_verified: Boolean(featureResults.metaHyperagentEvidence),
    self_improvement_governance_verified: Boolean(featureResults.selfImprovementGovernance),
    autoresearch_evidence_verified: Boolean(featureResults.autoresearchEvidence),
    rag_traceability_evidence_verified: Boolean(featureResults.ragTraceabilityEvidence),
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
    `Acceptance profile: ${scorecard.acceptance_profile}`,
    "",
    `Workload scope: ${Object.entries(scorecard.workload_scope || {}).filter(([, selected]) => selected === true).map(([key]) => key).join(", ") || "none"}`,
    "",
    `Long-horizon two-call workload: ${scorecard.long_horizon_verified ? "verified" : scorecard.long_horizon_required ? "blocked" : "not selected"}`,
    "",
    `Research Spine ensemble coding evidence (pre-reconciliation): ${scorecard.ensemble_coding_verified ? "verified" : "not verified"} (diagnostic only; not reportable until governed reconciliation and Done-task gates pass)`,
    `Synthetic reconciliation diagnostic (opt-in, non-reportable): ${scorecard.synthetic_reconciliation_verified ? "verified" : "not requested or not verified"}`,
    "",
    "| Acceptance gate | Selected | Status | Verified |",
    "| --- | ---: | --- | ---: |",
    `| provider Research Spine | ${scorecard.acceptance_gates.provider.selected ? "yes" : "no"} | ${scorecard.acceptance_gates.provider.status} | ${scorecard.acceptance_gates.provider.verified ? "yes" : "no"} |`,
    `| Petals donation interoperability | ${scorecard.acceptance_gates.petals.selected ? "yes" : "no"} | ${scorecard.acceptance_gates.petals.status} | ${scorecard.acceptance_gates.petals.verified ? "yes" : "no"} |`,
    `| combined | ${scorecard.acceptance_gates.combined.selected ? "yes" : "no"} | ${scorecard.acceptance_gates.combined.status} | ${scorecard.acceptance_gates.combined.verified ? "yes" : "no"} |`,
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
  if (scorecard.unrelated_workflow_failures?.length) {
    lines.push("", "## Unrelated Workflow Failures", "");
    for (const failure of scorecard.unrelated_workflow_failures) {
      lines.push(`- ${failure}`);
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
