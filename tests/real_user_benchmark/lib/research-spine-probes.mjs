function preview(value) {
  return JSON.parse(JSON.stringify(value, (_key, val) => {
    if (typeof val === "string" && val.length > 400) return `${val.slice(0, 400)}...`;
    return val;
  }));
}

function validateCodingRun({
  codingRun,
  requiredCoders,
  requiredDonorRoutes,
  featureResults,
  blockers,
  logger,
}) {
  const distinctModelCount = Number(codingRun?.distinct_model_count || 0);
  const raterCount = Number(codingRun?.rater_count || 0);
  const reliabilityMethod = String(codingRun?.reliability_method || "");
  const fallbackReason = String(codingRun?.fallback_reason || "");
  const lowerAssurance = /single_coder|lower_assurance/i.test(`${reliabilityMethod} ${fallbackReason}`);
  const routeEvidence = Array.isArray(codingRun?.route_evidence)
    ? codingRun.route_evidence
    : [];
  const servedDonorRouteCount = new Set(routeEvidence
    .filter((route) => String(route?.outcome || "").toLowerCase() === "served" || route?.served_request_count > 0)
    .map((route) => String(route?.node_id || "").trim())
    .filter(Boolean)).size;
  const fullMultiModelOk = requiredCoders >= 3
    ? distinctModelCount >= 3 && raterCount >= 3 && !lowerAssurance
    : requiredCoders >= 2
      ? distinctModelCount >= 2 && raterCount >= 2 && !lowerAssurance
      : distinctModelCount >= 1 && raterCount >= 1;
  const donorRouteOk = requiredDonorRoutes >= 2
    ? servedDonorRouteCount >= requiredDonorRoutes
    : true;
  featureResults.multiModelResearchSpineValidation = fullMultiModelOk && donorRouteOk;
  if ((!fullMultiModelOk || !donorRouteOk) && requiredCoders >= 2) {
    const detail = !fullMultiModelOk
      ? `Research Spine coding fell back to ${reliabilityMethod || "unknown"} with ${distinctModelCount}/${requiredCoders} distinct model coders.`
      : `Research Spine coding used ${servedDonorRouteCount}/${requiredDonorRoutes} required distinct served donor routes.`;
    blockers.push(detail);
    logger.issue({
      area: "research-spine",
      severity: "high",
      title: "Multi-model Research Spine validation was not proven",
      detail,
      evidence: {
        expected_distinct_coders: requiredCoders,
        distinct_model_count: distinctModelCount,
        rater_count: raterCount,
        reliability_method: reliabilityMethod,
        fallback_reason: fallbackReason,
        expected_distinct_donor_routes: requiredDonorRoutes,
        served_donor_route_count: servedDonorRouteCount,
      },
    });
  }
}

async function recoverLatestCodingRun({ api, projectId, logger, timeoutMs = 180000 }) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const runs = await api.get(`/api/research-validity/${projectId}/coding-runs?limit=5`, { timeoutMs: 60000 });
      const rows = Array.isArray(runs) ? runs : [];
      const completed = rows.find((run) => String(run?.status || "").toLowerCase() === "completed");
      const candidate = completed || rows[0] || null;
      logger.action("research_spine.coding_run_recovery.poll", {
        ok: Boolean(candidate),
        status: candidate?.status || "",
        run_id: candidate?.id || "",
      });
      if (completed) return completed;
    } catch (error) {
      logger.action("research_spine.coding_run_recovery.poll_error", { error: error.message });
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 5000));
  }
  return null;
}

export async function exerciseResearchSpineValidation({
  api,
  projectId,
  taskWorkflow = null,
  logger,
  featureResults,
  blockers = [],
  codingValidationEnabled,
  codingValidationLimit,
  expectedDistinctCoders = 0,
  expectedDistinctDonorRoutes = 0,
}) {
  const requiredCoders = Number(expectedDistinctCoders || 0);
  const requiredDonorRoutes = Number(expectedDistinctDonorRoutes || 0);
  const codingTimeoutMs = Math.max(240000, Number(codingValidationLimit || 0) * 120000);
  const evidence = {
    project_id: projectId,
    coding_validation_enabled: codingValidationEnabled,
    coding_validation_limit: codingValidationLimit,
    approved_task_id: taskWorkflow?.approvedTasks?.[0]?.id || "",
    contract_loaded: false,
    coding_run: null,
    summary: null,
    evidence_units: null,
    coding_runs: null,
    traceability: null,
    telemetry_audit: null,
    errors: [],
  };

  try {
    const contract = await api.get("/api/research-validity/contract", { timeoutMs: 15000 });
    evidence.contract_loaded = Boolean(contract?.contract && contract?.qualitative_coding_protocol);
    logger.action("research_spine.contract", { ok: evidence.contract_loaded });
  } catch (error) {
    evidence.errors.push({ step: "contract", error: error.message });
    logger.action("research_spine.contract", { ok: false, error: error.message });
  }

  if (codingValidationEnabled && codingValidationLimit > 0) {
    const approvedTask = taskWorkflow?.approvedTasks?.[0] || null;
    try {
      evidence.coding_run = await api.post(`/api/research-validity/${projectId}/coding-runs`, {
        // The proof pass must code raw source evidence units. Approved tasks are
        // recorded as review context, but uploaded source evidence is normally
        // project/document-scoped, not duplicated onto every task.
        task_id: null,
        limit: codingValidationLimit,
        max_coders: 3,
        threshold: 0.6,
      }, { timeoutMs: codingTimeoutMs });
      logger.action("research_spine.coding_run", {
        ok: true,
        approved_task_id: approvedTask?.id || "",
        coded_scope: "project_source_evidence_units",
        result: preview(evidence.coding_run),
      });
      validateCodingRun({
        codingRun: evidence.coding_run,
        requiredCoders,
        requiredDonorRoutes,
        featureResults,
        blockers,
        logger,
      });
    } catch (error) {
      evidence.errors.push({ step: "coding_run", error: error.message });
      const canRecoverLongRequest = /fetch failed|headers? timeout|terminated/i.test(error.message);
      const recoveredRun = canRecoverLongRequest
        ? await recoverLatestCodingRun({ api, projectId, logger })
        : null;
      if (recoveredRun) {
        evidence.coding_run = recoveredRun;
        logger.action("research_spine.coding_run_recovered", {
          ok: true,
          error: error.message,
          result: preview(recoveredRun),
        });
        validateCodingRun({
          codingRun: evidence.coding_run,
          requiredCoders,
          requiredDonorRoutes,
          featureResults,
          blockers,
          logger,
        });
      } else {
        if (requiredCoders >= 2) {
          blockers.push(`Research Spine coding validation did not complete: ${error.message}`);
        }
        logger.issue({
          area: "research-spine",
          severity: "medium",
          title: "Research Spine coding validation did not complete",
          detail: error.message,
        });
      }
    }
  }

  for (const [key, path] of [
    ["summary", `/api/research-validity/${projectId}/summary`],
    ["evidence_units", `/api/research-validity/${projectId}/evidence-units?limit=25`],
    ["coding_runs", `/api/research-validity/${projectId}/coding-runs?limit=25`],
    ["traceability", `/api/research-validity/${projectId}/traceability?limit=75`],
    ["telemetry_audit", `/api/research-validity/${projectId}/telemetry-audit?limit=500`],
  ]) {
    try {
      evidence[key] = await api.get(path, { timeoutMs: 60000 });
      logger.action("research_spine.evidence", { key, ok: true, result: preview(evidence[key]) });
    } catch (error) {
      evidence.errors.push({ step: key, error: error.message });
      logger.action("research_spine.evidence", { key, ok: false, error: error.message });
    }
  }

  const evidenceUnitCount = Array.isArray(evidence.evidence_units)
    ? evidence.evidence_units.length
    : Number(evidence.summary?.evidence_unit_count || 0);
  const codingRunCount = Array.isArray(evidence.coding_runs)
    ? evidence.coding_runs.length
    : Number(evidence.summary?.coding_run_count || 0);
  featureResults.codingValidation = Boolean(evidence.coding_run || codingRunCount > 0)
    && (expectedDistinctCoders < 2 || featureResults.multiModelResearchSpineValidation);
  featureResults.researchSpineTraceability = Boolean(evidence.summary || evidence.traceability);
  featureResults.ragTraceabilityEvidence = Boolean(evidence.traceability);
  featureResults.telemetryEvidence = Boolean(evidence.telemetry_audit || evidence.summary);
  logger.writeJson("research-spine-evidence.json", {
    ...evidence,
    evidence_unit_count_observed: evidenceUnitCount,
    coding_run_count_observed: codingRunCount,
  });
  return evidence;
}

export async function exerciseSelfImprovementGovernance({
  api,
  projectId,
  taskWorkflow = null,
  researchSpineEvidence = null,
  logger,
  featureResults,
  runId,
  selfImprovementProbeEnabled,
  startAutoresearchExperiment,
}) {
  if (!selfImprovementProbeEnabled) {
    logger.action("self_improvement.skip", { reason: "ISTARA_BENCHMARK_SELF_IMPROVEMENT_PROBE disabled" });
    return null;
  }

  const evidence = {
    project_id: projectId,
    telemetry: {},
    reasoning_bank: {},
    memento_skills: {},
    governance: {},
    meta_hyperagent: {},
    autoresearch: {},
    errors: [],
  };
  const projectQuery = `project_id=${encodeURIComponent(projectId)}`;
  const probe = async (bucket, label, fn) => {
    try {
      const result = await fn();
      evidence[bucket][label] = { ok: true, result: preview(result) };
      logger.action("self_improvement.probe", { bucket, label, ok: true, result: preview(result) });
      return result;
    } catch (error) {
      evidence[bucket][label] = { ok: false, error: error.message };
      evidence.errors.push({ bucket, label, error: error.message });
      logger.action("self_improvement.probe", { bucket, label, ok: false, error: error.message });
      return null;
    }
  };

  const telemetryStatus = await probe("telemetry", "settings_status", () => api.get("/api/settings/telemetry/status"));
  await probe("telemetry", "healing_rules", () => api.get(`/api/settings/telemetry/healing?${projectQuery}`));

  const skillHealth = await probe("memento_skills", "skill_health_all", () => api.get(`/api/skills/health/all?${projectQuery}`));
  const reasoningSummaryBefore = await probe("reasoning_bank", "summary_before", () => api.get(`/api/reasoning-bank/summary?${projectQuery}`));
  const memory = await probe("reasoning_bank", "record_process_memory", () => api.post("/api/reasoning-bank/memories", {
    project_id: projectId,
    agent_id: "real-user-benchmark",
    source_kind: "benchmark_process",
    source_id: runId,
    outcome: "governed_probe",
    title: "Real-user benchmark Research Spine learning",
    description: "Content-free process lesson from the benchmark; not report evidence.",
    content: "Use accepted evidence, Research Spine traceability, and project-scoped telemetry before strengthening skill/model routing.",
    tags: ["real-user-benchmark", "research-spine", "process-only"],
    domain: "self-improvement-governance",
    evidence_refs: [
      { kind: "project", id: projectId },
      { kind: "research_spine_summary", observed: Boolean(researchSpineEvidence?.summary) },
    ],
    judge_score: 0.75,
    confidence: 0.7,
  }));
  const retrieved = await probe("reasoning_bank", "retrieve_process_memory", () => api.post("/api/reasoning-bank/retrieve", {
    project_id: projectId,
    query: "How should skills learn from Research Spine validation without becoming report evidence?",
    source_kinds: ["benchmark_process", "report_grounding", "coding_run"],
    limit: 5,
  }));
  await probe("reasoning_bank", "summary_after", () => api.get(`/api/reasoning-bank/summary?${projectQuery}`));

  const governanceSummaryBefore = await probe("governance", "summary_before", () => api.get(`/api/improvement-governance/summary?${projectQuery}`));
  await probe("governance", "feature_contract", () => api.get("/api/improvement-governance/feature-contract"));
  const proposal = await probe("governance", "create_proposal", () => api.post("/api/improvement-governance/proposals", {
    source_system: "real_user_benchmark",
    source_id: runId,
    project_id: projectId,
    agent_id: "real-user-benchmark",
    title: "Benchmark proposal: strengthen project-scoped Research Spine learning evidence",
    summary: "Exercise the governed proposal path without approving or applying a live mutation.",
    rationale: "Self-improvement should learn from content-free telemetry, ReasoningBank process memory, skill health, and Research Spine gates without becoming report evidence.",
    affected_surfaces: ["telemetry", "reasoning_bank", "memento_skills", "meta_hyperagent", "autoresearch", "benchmark"],
    risk_level: "medium",
    approval_policy: "human_governed",
    before_state: { scorecard_pending: true, run_id: runId },
    proposed_change: {
      type: "benchmark_evaluation_policy",
      requires_approval_before_apply: true,
      no_report_evidence: true,
    },
    rollback_plan: { type: "proposal_only_no_live_mutation" },
    evidence: [
      { kind: "telemetry_status", ok: Boolean(telemetryStatus) },
      { kind: "reasoning_memory_created", ok: Boolean(memory?.memory?.id) },
      { kind: "research_spine_summary", ok: Boolean(researchSpineEvidence?.summary) },
    ],
    metrics_before: {
      approved_tasks: taskWorkflow?.approvals || 0,
      research_spine_evidence_units: researchSpineEvidence?.summary?.evidence_unit_count || 0,
    },
    metrics_after: {},
    reasoning_memory_ids: memory?.memory?.id ? [memory.memory.id] : [],
    improvement_score: 0.01,
    confidence: 0.65,
  }));
  const proposalId = proposal?.proposal?.id || "";
  if (proposalId) {
    await probe("governance", "sandbox_evaluation", () => api.post(
      `/api/improvement-governance/proposals/${proposalId}/sandbox-evaluation?${projectQuery}`,
      {
        evidence: {
          run_id: runId,
          sandboxed: true,
          no_live_mutation: true,
          checks: ["project_scoped_memory", "research_spine_traceability", "telemetry_status"],
        },
      },
    ));
    await probe("governance", "record_evaluation", () => api.post(
      `/api/improvement-governance/proposals/${proposalId}/evaluation?${projectQuery}`,
      {
        metrics_before: { reasoning_summary_count: reasoningSummaryBefore?.count || 0 },
        metrics_after: { retrieved_memories: retrieved?.memories?.length || 0 },
        passed: true,
        evidence: { approval_required_before_apply: true, report_evidence: false },
      },
    ));
  }
  await probe("governance", "summary_after", () => api.get(`/api/improvement-governance/summary?${projectQuery}`));

  await probe("meta_hyperagent", "status", () => api.get(`/api/meta-hyperagent/status?${projectQuery}`));
  await probe("meta_hyperagent", "proposals", () => api.get(`/api/meta-hyperagent/proposals?${projectQuery}`));
  await probe("meta_hyperagent", "variants", () => api.get(`/api/meta-hyperagent/variants?${projectQuery}`));
  await probe("meta_hyperagent", "observations", () => api.get(`/api/meta-hyperagent/observations?${projectQuery}`));

  await probe("autoresearch", "status", () => api.get(`/api/autoresearch/status?${projectQuery}`));
  await probe("autoresearch", "config", () => api.get("/api/autoresearch/config"));
  await probe("autoresearch", "leaderboard", () => api.get(`/api/autoresearch/leaderboard?${projectQuery}`));
  if (startAutoresearchExperiment) {
    await probe("autoresearch", "start_bounded_experiment", () => api.post("/api/autoresearch/start", {
      project_id: projectId,
      loop_type: "question_bank",
      target: "real-user-benchmark",
      max_iterations: 1,
    }));
  }

  featureResults.telemetryEvidence = featureResults.telemetryEvidence || Boolean(telemetryStatus);
  featureResults.reasoningBankEvidence = Boolean(memory?.memory?.id || retrieved?.memories?.length);
  featureResults.mementoSkillEvidence = Boolean(skillHealth);
  featureResults.selfImprovementGovernance = Boolean(proposalId);
  featureResults.metaHyperagentEvidence = Object.values(evidence.meta_hyperagent).some((item) => item.ok);
  featureResults.autoresearchEvidence = Object.values(evidence.autoresearch).some((item) => item.ok);
  logger.writeJson("self-improvement-evidence.json", {
    ...evidence,
    governance_summary_before: preview(governanceSummaryBefore),
  });
  return evidence;
}
