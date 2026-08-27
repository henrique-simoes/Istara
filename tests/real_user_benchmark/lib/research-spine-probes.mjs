function preview(value) {
  return JSON.parse(JSON.stringify(value, (_key, val) => {
    if (typeof val === "string" && val.length > 400) return `${val.slice(0, 400)}...`;
    return val;
  }));
}

function assessTraceabilityCodingRunBinding(traceability, codingRun) {
  const runId = String(codingRun?.id || "").trim();
  const codingRuns = Array.isArray(traceability?.coding_runs) ? traceability.coding_runs : [];
  const applications = Array.isArray(traceability?.code_applications)
    ? traceability.code_applications
    : [];
  const decisions = Array.isArray(traceability?.reconciliation_decisions)
    ? traceability.reconciliation_decisions
    : [];
  const edges = Array.isArray(traceability?.evidence_graph_edges)
    ? traceability.evidence_graph_edges
    : [];
  const runApplications = applications.filter((row) => String(row?.coding_run_id || "").trim() === runId);
  const runDecisions = decisions.filter((row) => String(row?.coding_run_id || "").trim() === runId);
  const runEdges = edges.filter((edge) => String(edge?.coding_run_id || "").trim() === runId);
  const expectedApplicationCount = Number(codingRun?.code_application_count ?? 0);
  const runListed = Boolean(runId) && codingRuns.some(
    (run) => String(run?.id || "").trim() === runId,
  );
  const applicationEvidenceOk = expectedApplicationCount > 0
    ? runApplications.length >= expectedApplicationCount
    : runApplications.length > 0;
  const edgeEvidenceOk = runEdges.some((edge) => (
    String(edge?.source_type || "").trim() === "evidence_unit"
      && String(edge?.relation || "").trim() === "coded_as"
      && String(edge?.target_type || "").trim() === "code_application"
  ));
  return {
    ok: runListed && applicationEvidenceOk && edgeEvidenceOk,
    run_id: runId,
    run_listed: runListed,
    expected_application_count: expectedApplicationCount,
    application_count: runApplications.length,
    decision_count: runDecisions.length,
    edge_count: runEdges.length,
    application_evidence_ok: applicationEvidenceOk,
    edge_evidence_ok: edgeEvidenceOk,
  };
}

const NON_SUBSTANTIVE_SOURCE_PATTERN = /(?:canonical corpus|source-specific protocol|moderator probes|project guardrails|research spine|do not infer|treat every participant story|distinguish raw source evidence|recommendations must cite)/i;

function sourceKey(unit) {
  const sourceId = String(unit?.source_id || "").trim();
  if (sourceId) return sourceId;
  const location = String(unit?.source_location || "").trim();
  // A unit id is not source diversity. When older rows lack source_id, use the
  // document-level part of source_location and keep an unknown location grouped
  // as unknown rather than manufacturing one source per evidence unit.
  return location ? location.split("#", 1)[0].trim() : "";
}

function assessApplicationCoverage(
  rows,
  expectedUnits,
  requiredCoders,
  expectedCodingRunId,
  expectedServedModelIdentities,
) {
  const expectedUnitIds = new Set((Array.isArray(expectedUnits) ? expectedUnits : [])
    .map((unit) => String(unit?.id || "").trim())
    .filter(Boolean));
  const expectedUnitsById = new Map((Array.isArray(expectedUnits) ? expectedUnits : [])
    .map((unit) => [String(unit?.id || "").trim(), unit])
    .filter(([unitId]) => Boolean(unitId)));
  const normalizedExpectedRunId = String(expectedCodingRunId || "").trim();
  const expectedModels = new Set(
    (expectedServedModelIdentities instanceof Set
      ? [...expectedServedModelIdentities]
      : Array.isArray(expectedServedModelIdentities) ? expectedServedModelIdentities : [])
      .map((model) => String(model || "").trim().toLocaleLowerCase())
      .filter(Boolean),
  );
  const byCoder = new Map();
  const coderModels = new Map();
  const observedModels = new Set();
  const invalidRows = [];
  const sourceSpanMismatches = [];
  const sourceLocationMismatches = [];
  const sourceOffsetMismatches = [];
  const missingCodePayloads = [];
  const invalidConfidenceRows = [];
  const applicationIdCounts = new Map();
  for (const row of Array.isArray(rows) ? rows : []) {
    const applicationId = String(row?.id || "").trim();
    const codingRunId = String(row?.coding_run_id || "").trim();
    const coderId = String(row?.coder_id || "").trim();
    const unitId = String(row?.evidence_unit_id || "").trim();
    const codeId = String(row?.code_id || "").trim();
    const sourceText = String(row?.source_text || "").trim();
    const sourceLocation = String(row?.source_location || "").trim();
    const reasoning = String(row?.reasoning || "").trim();
    const confidence = row?.confidence;
    const route = row?.route_evidence && typeof row.route_evidence === "object"
      ? row.route_evidence
      : null;
    const servedModel = String(route?.model || route?.served_model || "").trim();
    const rowModel = String(row?.model_name || "").trim();
    const normalizedRowModel = rowModel.toLocaleLowerCase();
    const expectedUnit = expectedUnitsById.get(unitId);
    const expectedSourceText = String(expectedUnit?.source_text || "").trim();
    const expectedSourceLocation = String(expectedUnit?.source_location || "").trim();
    const expectedStartOffset = expectedUnit?.start_offset;
    const expectedEndOffset = expectedUnit?.end_offset;
    const startOffsetRequired = expectedStartOffset !== null
      && expectedStartOffset !== undefined
      && expectedStartOffset !== "";
    const endOffsetRequired = expectedEndOffset !== null
      && expectedEndOffset !== undefined
      && expectedEndOffset !== "";
    const observedStartOffset = row?.start_offset;
    const observedEndOffset = row?.end_offset;
    const startOffsetMatches = !startOffsetRequired
      || (Number.isInteger(Number(observedStartOffset))
        && Number(observedStartOffset) === Number(expectedStartOffset));
    const endOffsetMatches = !endOffsetRequired
      || (Number.isInteger(Number(observedEndOffset))
        && Number(observedEndOffset) === Number(expectedEndOffset));
    const sourceOffsetsMatch = startOffsetMatches && endOffsetMatches;
    const confidenceValid = confidence !== null
      && confidence !== undefined
      && confidence !== ""
      && Number.isFinite(Number(confidence))
      && Number(confidence) >= 0
      && Number(confidence) <= 1;
    // The API persists the coder's quote, not a synthetic summary. Require
    // that quote to be a contiguous substring of the exact selected raw unit
    // and that the persisted location remains bound to that unit. Non-empty
    // fields alone would let fabricated/paraphrased evidence pass the oracle.
    const sourceSpanGrounded = Boolean(
      expectedSourceText && sourceText && expectedSourceText.includes(sourceText),
    );
    const sourceLocationMatches = Boolean(
      expectedSourceLocation && sourceLocation && sourceLocation === expectedSourceLocation,
    );
    const routeServed = String(route?.outcome || "").toLowerCase() === "served";
    if (!codeId || !reasoning) {
      missingCodePayloads.push({
        id: applicationId,
        evidence_unit_id: unitId,
        has_code_id: Boolean(codeId),
        has_reasoning: Boolean(reasoning),
      });
    }
    if (!confidenceValid) {
      invalidConfidenceRows.push({
        id: applicationId,
        evidence_unit_id: unitId,
        confidence,
      });
    }
    if (!sourceOffsetsMatch) {
      sourceOffsetMismatches.push({
        id: applicationId,
        evidence_unit_id: unitId,
        expected_start_offset: expectedStartOffset ?? null,
        observed_start_offset: observedStartOffset ?? null,
        expected_end_offset: expectedEndOffset ?? null,
        observed_end_offset: observedEndOffset ?? null,
      });
    }
    if (applicationId) {
      applicationIdCounts.set(applicationId, (applicationIdCounts.get(applicationId) || 0) + 1);
    }
    if (!applicationId || !normalizedExpectedRunId || codingRunId !== normalizedExpectedRunId
      || !coderId || !expectedUnitIds.has(unitId) || !codeId || !sourceText || !sourceLocation
      || !reasoning || !confidenceValid
      || !sourceSpanGrounded || !sourceLocationMatches
      || !sourceOffsetsMatch
      || !routeServed || !servedModel || !rowModel || rowModel !== servedModel
      || (expectedModels.size > 0 && !expectedModels.has(normalizedRowModel))) {
      invalidRows.push({
        id: String(row?.id || "").trim(),
        coding_run_id: codingRunId,
        expected_coding_run_id: normalizedExpectedRunId,
        coder_id: coderId,
        evidence_unit_id: unitId,
        code_id: codeId,
        has_code_id: Boolean(codeId),
        has_reasoning: Boolean(reasoning),
        confidence,
        confidence_valid: confidenceValid,
        has_source_text: Boolean(sourceText),
        has_source_location: Boolean(sourceLocation),
        expected_source_location: expectedSourceLocation,
        source_span_grounded: sourceSpanGrounded,
        source_location_matches: sourceLocationMatches,
        source_offsets_match: sourceOffsetsMatch,
        route_served: routeServed,
        served_model: servedModel,
        row_model: rowModel,
      });
    }
    if (!sourceSpanGrounded) {
      sourceSpanMismatches.push({
        id: applicationId,
        evidence_unit_id: unitId,
        expected_source_text_chars: expectedSourceText.length,
        observed_source_text_chars: sourceText.length,
      });
    }
    if (!sourceLocationMatches) {
      sourceLocationMismatches.push({
        id: applicationId,
        evidence_unit_id: unitId,
        expected_source_location: expectedSourceLocation,
        observed_source_location: sourceLocation,
      });
    }
    if (normalizedRowModel) {
      observedModels.add(normalizedRowModel);
      if (coderId) {
        const modelsForCoder = coderModels.get(coderId) || new Set();
        modelsForCoder.add(normalizedRowModel);
        coderModels.set(coderId, modelsForCoder);
      }
    }
    if (coderId && expectedUnitIds.has(unitId)) {
      if (!byCoder.has(coderId)) byCoder.set(coderId, new Set());
      byCoder.get(coderId).add(unitId);
    }
  }
  const duplicateApplicationIds = [...applicationIdCounts.entries()]
    .filter(([_id, count]) => count > 1)
    .map(([id]) => id)
    .sort();
  for (const id of duplicateApplicationIds) {
    invalidRows.push({
      id,
      duplicate_application_id: true,
      duplicate_count: applicationIdCounts.get(id),
    });
  }
  const coderModelConflicts = [...coderModels.entries()]
    .filter(([_coderId, models]) => models.size > 1)
    .map(([coderId, models]) => ({ coder_id: coderId, model_identities: [...models].sort() }))
    .sort((left, right) => left.coder_id.localeCompare(right.coder_id));
  for (const conflict of coderModelConflicts) {
    invalidRows.push({
      coder_id: conflict.coder_id,
      coder_model_conflict: true,
      model_identities: conflict.model_identities,
    });
  }
  const missingServedModelIdentities = [...expectedModels]
    .filter((model) => !observedModels.has(model))
    .sort();
  const unexpectedServedModelIdentities = [...observedModels]
    .filter((model) => expectedModels.size > 0 && !expectedModels.has(model))
    .sort();
  if (missingServedModelIdentities.length > 0 || unexpectedServedModelIdentities.length > 0) {
    invalidRows.push({
      model_coverage_gap: true,
      missing_served_model_identities: missingServedModelIdentities,
      unexpected_served_model_identities: unexpectedServedModelIdentities,
    });
  }
  const coderIds = [...byCoder.keys()].sort();
  const missingPairs = [];
  for (const coderId of coderIds) {
    for (const unitId of expectedUnitIds) {
      if (!byCoder.get(coderId).has(unitId)) missingPairs.push({ coder_id: coderId, evidence_unit_id: unitId });
    }
  }
  return {
    ok: expectedUnitIds.size > 0
      && coderIds.length >= requiredCoders
      && missingPairs.length === 0
      && invalidRows.length === 0,
    expected_unit_count: expectedUnitIds.size,
    observed_coder_count: coderIds.length,
    coder_ids: coderIds,
    missing_pairs: missingPairs,
    duplicate_application_ids: duplicateApplicationIds,
    coder_model_conflicts: coderModelConflicts,
    observed_model_identities: [...observedModels].sort(),
    expected_served_model_identities: [...expectedModels].sort(),
    missing_served_model_identities: missingServedModelIdentities,
    unexpected_served_model_identities: unexpectedServedModelIdentities,
    source_span_mismatches: sourceSpanMismatches,
    source_location_mismatches: sourceLocationMismatches,
    source_offset_mismatches: sourceOffsetMismatches,
    missing_code_payloads: missingCodePayloads,
    invalid_confidence_rows: invalidConfidenceRows,
    invalid_rows: invalidRows,
  };
}

export function selectSubstantiveEvidenceUnits(units, limit) {
  const requested = Math.max(0, Number(limit || 0));
  if (requested === 0) return [];
  const candidates = (Array.isArray(units) ? units : []).filter((unit) => {
    const text = String(unit?.source_text || "").trim();
    return Boolean(unit?.id)
      && text.length >= 120
      && !/^#{1,6}\s/.test(text)
      && !NON_SUBSTANTIVE_SOURCE_PATTERN.test(text);
  });
  if (candidates.length <= requested) return candidates;

  const bySource = new Map();
  for (const candidate of candidates) {
    const key = sourceKey(candidate);
    if (!bySource.has(key)) bySource.set(key, []);
    bySource.get(key).push(candidate);
  }
  if (bySource.size >= requested) {
    // Prefer independent source coverage over multiple convenient spans from
    // the first document. Pick a stable central span from each selected source.
    const groups = [...bySource.values()];
    return Array.from({ length: requested }, (_unused, index) => {
      const groupIndex = Math.floor(((index + 0.5) * groups.length) / requested);
      const group = groups[Math.min(groupIndex, groups.length - 1)];
      return group[Math.floor((group.length - 1) / 2)];
    });
  }

  // Stable quantiles cover the available source window without random seeds or
  // adjacent first-page/header bias. The selected IDs are persisted below so a
  // result can prove exactly which raw spans all three coders received.
  return Array.from({ length: requested }, (_unused, index) => {
    const candidateIndex = Math.floor(((index + 0.5) * candidates.length) / requested);
    return candidates[Math.min(candidateIndex, candidates.length - 1)];
  });
}

async function validateCodingRun({
  api,
  projectId,
  codingRun,
  requiredCoders,
  requiredDonorRoutes,
  expectedEvidenceUnits,
  featureResults,
  blockers,
  logger,
}) {
  const distinctModelCount = Number(codingRun?.distinct_model_count || 0);
  const raterCount = Number(codingRun?.rater_count || 0);
  const reliabilityMethod = String(codingRun?.reliability_method || "");
  const kappa = codingRun?.kappa;
  const alpha = codingRun?.alpha;
  const threshold = Number(codingRun?.threshold ?? 0.6);
  const hasNumericKappa = kappa !== null && kappa !== "" && Number.isFinite(Number(kappa));
  const hasNumericAlpha = alpha !== null && alpha !== "" && Number.isFinite(Number(alpha));
  // Fleiss/Cohen kappa is an agreement coefficient bounded to [-1, 1].
  // Krippendorff alpha is also bounded above by 1 (negative values are valid
  // disagreement signals and must remain visible to the threshold gate).
  const kappaInRange = hasNumericKappa && Number(kappa) >= -1 && Number(kappa) <= 1;
  const alphaInRange = hasNumericAlpha && Number(alpha) <= 1;
  const reliabilityMetricBoundsOk = kappaInRange && alphaInRange;
  const reliabilityMetricOutOfRange = (hasNumericKappa && !kappaInRange)
    || (hasNumericAlpha && !alphaInRange);
  const kappaMeetsThreshold = Number.isFinite(threshold)
    && kappaInRange
    && Number(kappa) >= threshold;
  const fallbackReason = String(codingRun?.fallback_reason || "");
  const status = String(codingRun?.status || "").toLowerCase();
  const promotionStatus = String(codingRun?.promotion_status || "").toLowerCase();
  const applicationCount = Number(codingRun?.code_application_count ?? -1);
  const acceptedPromotion = ["accepted", "accepted_after_reconciliation"].includes(promotionStatus);
  const currentRunOk = status === "completed"
    && acceptedPromotion
    && applicationCount !== 0;
  const algorithmOk = requiredCoders >= 3
    ? reliabilityMethod === "fleiss_kappa_with_krippendorff_alpha_companion"
      && reliabilityMetricBoundsOk
      && (!acceptedPromotion || kappaMeetsThreshold)
    : requiredCoders >= 2
      ? reliabilityMethod === "cohen_kappa_with_krippendorff_alpha_companion"
        && reliabilityMetricBoundsOk
        && (!acceptedPromotion || kappaMeetsThreshold)
      : true;
  const lowerAssurance = /single_coder|lower_assurance/i.test(`${reliabilityMethod} ${fallbackReason}`);
  const routeEvidence = Array.isArray(codingRun?.route_evidence)
    ? codingRun.route_evidence
    : [];
  const servedDonorRouteCount = new Set(routeEvidence
    .filter((route) => String(route?.outcome || "").toLowerCase() === "served" || route?.served_request_count > 0)
    .map((route) => String(route?.node_id || "").trim())
    .filter(Boolean)).size;
  // The backend's distinct_model_count is derived from persisted coding rows,
  // but the acceptance probe must independently cross-check the route receipt.
  // A count alone could be fabricated by a malformed adapter response; the
  // served route evidence must itself contain the required distinct identities.
  const servedModelIdentities = new Set(routeEvidence
    .filter((route) => String(route?.outcome || "").toLowerCase() === "served" || route?.served_request_count > 0)
    .map((route) => String(route?.model || "").trim().toLocaleLowerCase())
    .filter(Boolean));
  const servedModelCount = servedModelIdentities.size;
  const modelReliabilityOk = requiredCoders >= 3
    ? distinctModelCount >= 3
      && servedModelCount >= requiredCoders
      && servedModelCount === distinctModelCount
      && raterCount >= 3
      && !lowerAssurance
    : requiredCoders >= 2
      ? distinctModelCount >= 2
        && servedModelCount >= requiredCoders
        && servedModelCount === distinctModelCount
        && raterCount >= 2
        && !lowerAssurance
      : distinctModelCount >= 1 && servedModelCount >= 1 && raterCount >= 1;
  const fullMultiModelOk = currentRunOk && modelReliabilityOk && algorithmOk;
  const donorRouteOk = requiredDonorRoutes >= 2
    ? servedDonorRouteCount >= requiredDonorRoutes
    : true;
  let coverageOk = true;
  let coverageEvidence = null;
  let applicationEvidenceAvailable = false;
  let reconciliationOk = true;
  let reconciliationEvidence = null;
  if (fullMultiModelOk && donorRouteOk) {
    try {
      const runId = String(codingRun?.id || "").trim();
      const [applications, decisions] = await Promise.all([
        api.get(`/api/code-applications/${projectId}?coding_run_id=${encodeURIComponent(runId)}`, { timeoutMs: 60000 }),
        api.get(`/api/research-validity/${projectId}/reconciliation-decisions?coding_run_id=${encodeURIComponent(runId)}&limit=500`, { timeoutMs: 60000 }),
      ]);
      const rows = Array.isArray(applications) ? applications : [];
      const decisionRows = Array.isArray(decisions) ? decisions : [];
      applicationEvidenceAvailable = true;
      const expectedCount = Math.max(0, applicationCount);
      coverageEvidence = assessApplicationCoverage(
        rows,
        expectedEvidenceUnits,
        requiredCoders,
        runId,
        servedModelIdentities,
      );
      coverageOk = coverageEvidence.ok;
      if (!coverageOk) {
        reconciliationOk = false;
      }
      const acceptedRows = rows.filter((row) =>
        ["accepted", "accepted_after_reconciliation"].includes(String(row?.promotion_status || "").toLowerCase())
        && ["accepted", "reconciled"].includes(String(row?.reconciliation_status || "").toLowerCase())
        && String(row?.review_status || "").toLowerCase() === "approved");
      const invalidDecisionRows = decisionRows.filter((decision) =>
        !runId || String(decision?.coding_run_id || "").trim() !== runId);
      const decisionIds = new Set(decisionRows
        .filter((decision) => !invalidDecisionRows.includes(decision)
          && ["accepted", "revised"].includes(String(decision?.decision_type || "").toLowerCase()))
        .map((decision) => String(decision?.code_application_id || "").trim())
        .filter(Boolean));
      const allApplicationsHaveDecisions = rows.every((row) => decisionIds.has(String(row?.id || "").trim()));
      reconciliationOk = coverageOk
        && expectedCount > 0
        && rows.length === expectedCount
        && acceptedRows.length === expectedCount
        && invalidDecisionRows.length === 0
        && allApplicationsHaveDecisions;
      reconciliationEvidence = {
        expected_application_count: expectedCount,
        observed_application_count: rows.length,
        reconciled_application_count: acceptedRows.length,
        accepted_decision_count: decisionIds.size,
        invalid_decision_count: invalidDecisionRows.length,
        all_applications_have_decisions: allApplicationsHaveDecisions,
      };
      if (coverageEvidence) {
        reconciliationEvidence.application_coverage = coverageEvidence;
      }
      if (coverageOk && !reconciliationOk) {
        const detail = invalidDecisionRows.length > 0
          ? `Research Spine reliability passed, but ${invalidDecisionRows.length}/${decisionRows.length} reconciliation decisions belong to another coding run.`
          : `Research Spine reliability passed, but ${acceptedRows.length}/${expectedCount} code applications have accepted reconciliation decisions (${decisionIds.size} linked decisions for ${rows.length} applications).`;
        blockers.push(detail);
        logger.issue({
          area: "research-spine",
          severity: "high",
          title: "Research Spine reconciliation was not proven",
          detail,
          evidence: reconciliationEvidence,
        });
      }
    } catch (error) {
      reconciliationOk = false;
      reconciliationEvidence = { error: error.message };
      const detail = `Research Spine reconciliation proof failed closed: ${error.message}`;
      blockers.push(detail);
      logger.issue({
        area: "research-spine",
        severity: "high",
        title: "Research Spine reconciliation was not proven",
        detail,
        evidence: reconciliationEvidence,
      });
    }
  }
  // Keep the diagnostic signal separate from accepted Research Spine validity.
  // It answers whether the three independent coders, exact reliability method,
  // source-grounded application coverage, and served donor routes were proven;
  // reconciliation remains a distinct human-governed gate below.
  const ensembleCodingOk = fullMultiModelOk
    && donorRouteOk
    && coverageOk
    && applicationEvidenceAvailable;
  featureResults.ensembleCodingValidation = ensembleCodingOk;
  codingRun.ensemble_coding_evidence = {
    verified: ensembleCodingOk,
    pre_reconciliation: true,
    accepted_reportable: false,
    full_multi_model_evidence: fullMultiModelOk,
    donor_route_evidence: donorRouteOk,
    application_coverage_evidence: coverageOk && applicationEvidenceAvailable,
    reconciliation_verified: reconciliationOk,
  };
  logger.action("research_spine.ensemble_coding", {
    ok: ensembleCodingOk,
    pre_reconciliation: true,
    accepted_reportable: false,
    full_multi_model_evidence: fullMultiModelOk,
    donor_route_evidence: donorRouteOk,
    application_coverage_evidence: coverageOk && applicationEvidenceAvailable,
    reconciliation_verified: reconciliationOk,
  });
  featureResults.multiModelResearchSpineValidation = fullMultiModelOk
    && donorRouteOk
    && coverageOk
    && reconciliationOk;
  if (reconciliationEvidence) codingRun.reconciliation_evidence = reconciliationEvidence;
  if (coverageEvidence) codingRun.application_coverage = coverageEvidence;
  if (!fullMultiModelOk || !donorRouteOk || !coverageOk) {
    const detail = !currentRunOk
      ? status === "blocked" || promotionStatus === "blocked"
        ? `Research Spine validation observed a blocked current coding run (${status || "unknown"}/${promotionStatus || "unknown"}, ${applicationCount < 0 ? "unknown" : applicationCount} code applications).`
        : `Research Spine coding completed as ${promotionStatus || "unknown"}, not accepted; human reconciliation and accepted code applications remain required (${status || "unknown"}, ${applicationCount < 0 ? "unknown" : applicationCount} code applications).`
      : !modelReliabilityOk
        ? `Research Spine coding proved ${distinctModelCount}/${requiredCoders} backend-reported model coders but only ${servedModelCount}/${requiredCoders} distinct served model identities in route evidence.`
      : !algorithmOk
        ? reliabilityMetricOutOfRange
          ? `Research Spine validation rejected out-of-range reliability metrics (kappa=${kappa ?? "missing"} must be within [-1, 1]; alpha=${alpha ?? "missing"} must be <= 1).`
          : `Research Spine validation did not prove the required reliability algorithm with numeric Fleiss kappa and Krippendorff alpha (observed ${reliabilityMethod || "unknown"}, kappa=${kappa ?? "missing"}, alpha=${alpha ?? "missing"}).`
      : !coverageOk
          ? `Research Spine code applications did not prove complete coder-by-evidence-unit coverage, substantive open-code payload, and source/served-model provenance (${coverageEvidence?.observed_coder_count || 0} coders, ${coverageEvidence?.missing_pairs?.length || 0} missing pairs, ${coverageEvidence?.invalid_rows?.length || 0} invalid rows).`
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
        served_model_count: servedModelCount,
        served_model_identities: [...servedModelIdentities].sort(),
        rater_count: raterCount,
        reliability_method: reliabilityMethod,
        kappa,
        alpha,
        threshold,
        kappa_in_range: kappaInRange,
        alpha_in_range: alphaInRange,
        reliability_metric_bounds_ok: reliabilityMetricBoundsOk,
        reliability_metric_out_of_range: reliabilityMetricOutOfRange,
        kappa_meets_threshold: kappaMeetsThreshold,
        fallback_reason: fallbackReason,
        expected_distinct_donor_routes: requiredDonorRoutes,
        served_donor_route_count: servedDonorRouteCount,
        application_coverage: coverageEvidence,
      },
    });
  }
}

const RECOVERY_CLOCK_SKEW_MS = 60_000;

async function recoverLatestCodingRun({
  api,
  projectId,
  logger,
  notBefore = null,
  timeoutMs = 180000,
}) {
  const notBeforeMs = notBefore ? Date.parse(notBefore) : null;
  if (notBefore && !Number.isFinite(notBeforeMs)) {
    logger.action("research_spine.coding_run_recovery.invalid_correlation", {
      ok: false,
      not_before: notBefore,
    });
    return null;
  }
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const runs = await api.get(`/api/research-validity/${projectId}/coding-runs?limit=5`, { timeoutMs: 60000 });
      const rows = Array.isArray(runs) ? runs : [];
      const completed = rows.filter((run) => String(run?.status || "").toLowerCase() === "completed");
      const candidate = completed.find((run) => {
        if (!Number.isFinite(notBeforeMs)) return true;
        const runTimestamp = Date.parse(run?.started_at || run?.created_at || "");
        return Number.isFinite(runTimestamp)
          && runTimestamp >= notBeforeMs - RECOVERY_CLOCK_SKEW_MS;
      }) || null;
      logger.action("research_spine.coding_run_recovery.poll", {
        ok: Boolean(candidate),
        status: candidate?.status || "",
        run_id: candidate?.id || "",
      });
      if (candidate) return candidate;
      if (notBefore && completed.length > 0 && !rows.some((run) => (
        ["draft", "queued", "running", "in_progress", "pending"].includes(
          String(run?.status || "").toLowerCase(),
        )
      ))) {
        logger.action("research_spine.coding_run_recovery.stale", {
          ok: false,
          not_before: notBefore,
          completed_run_ids: completed.map((run) => run?.id || "").filter(Boolean),
        });
        return null;
      }
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
  expectedDistinctCoders = 3,
  expectedDistinctDonorRoutes = 0,
  expectedDistinctSources = 0,
}) {
  const requiredCoders = Number(expectedDistinctCoders || 0);
  const requiredDonorRoutes = Number(expectedDistinctDonorRoutes || 0);
  const requiredSources = Number(expectedDistinctSources || 0);
  const codingTimeoutMs = Math.max(240000, Number(codingValidationLimit || 0) * 120000);
  const evidence = {
    project_id: projectId,
    coding_validation_enabled: codingValidationEnabled,
    coding_validation_limit: codingValidationLimit,
    approved_task_id: taskWorkflow?.approvedTasks?.[0]?.id || "",
    contract_loaded: false,
    coding_selection: null,
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
    evidence.contract_loaded = Boolean(
      contract
      && typeof contract === "object"
      && Object.prototype.hasOwnProperty.call(contract, "contract")
      && Object.prototype.hasOwnProperty.call(contract, "qualitative_coding_protocol"),
    );
    logger.action("research_spine.contract", { ok: evidence.contract_loaded });
  } catch (error) {
    evidence.errors.push({ step: "contract", error: error.message });
    logger.action("research_spine.contract", { ok: false, error: error.message });
  }

  if (codingValidationEnabled && codingValidationLimit > 0) {
    const approvedTask = taskWorkflow?.approvedTasks?.[0] || null;
    const codingRequestStartedAt = new Date().toISOString();
    let selectedEvidenceUnits = [];
    try {
      if (!evidence.contract_loaded) {
        const detail = "Research Spine contract was unavailable; coding validation is unproven.";
        blockers.push(detail);
        logger.issue({
          area: "research-spine",
          severity: "high",
          title: "Research Spine contract was not loaded",
          detail,
        });
        throw new Error("research_validity_contract_unavailable");
      }
      const pageSize = 500;
      const maxPages = 10;
      const availableUnits = [];
      let pagesScanned = 0;
      for (let page = 0; page < maxPages; page += 1) {
        const rows = await api.get(
          `/api/research-validity/${projectId}/evidence-units?limit=${pageSize}&offset=${page * pageSize}`,
          { timeoutMs: 60000 },
        );
        const pageRows = Array.isArray(rows) ? rows : [];
        availableUnits.push(...pageRows);
        pagesScanned += 1;
        const currentSelection = selectSubstantiveEvidenceUnits(
          availableUnits,
          codingValidationLimit,
        );
        const selectedSourceCount = new Set(currentSelection.map(sourceKey).filter(Boolean)).size;
        if (pageRows.length < pageSize
          || selectedSourceCount >= Math.min(codingValidationLimit, 3)) break;
      }
      const selectedUnits = selectSubstantiveEvidenceUnits(
        availableUnits,
        codingValidationLimit,
      );
      selectedEvidenceUnits = selectedUnits;
      const selectedSourceCount = new Set(selectedUnits.map(sourceKey).filter(Boolean)).size;
      evidence.coding_selection = {
        strategy: "deterministic_substantive_source_diverse",
        candidate_window_limit: pageSize * maxPages,
        candidate_window_count: availableUnits.length,
        page_size: pageSize,
        pages_scanned: pagesScanned,
        selected_unit_count: selectedUnits.length,
        selected_source_count: selectedSourceCount,
        selected_units: selectedUnits.map((unit) => ({
          id: unit.id,
          source_id: unit.source_id || "",
          source_location: unit.source_location || "",
          unit_index: unit.unit_index ?? null,
          source_text_chars: String(unit.source_text || "").length,
        })),
      };
      if (selectedUnits.length < codingValidationLimit) {
        throw new Error(
          `Substantive coding selection found ${selectedUnits.length}/${codingValidationLimit} required raw source spans after scanning ${availableUnits.length} evidence units.`,
        );
      }
      if (requiredSources > 0 && selectedSourceCount < requiredSources) {
        const detail = `Research Spine coding selection found ${selectedSourceCount}/${requiredSources} distinct source identities; source diversity is required before three-model validation.`;
        blockers.push(detail);
        logger.issue({
          area: "research-spine",
          severity: "high",
          title: "Research Spine source diversity was not proven",
          detail,
          evidence: {
            expected_distinct_sources: requiredSources,
            selected_source_count: selectedSourceCount,
            selected_units: evidence.coding_selection.selected_units,
          },
        });
      }
      if (requiredSources > 0 && selectedSourceCount < requiredSources) {
        throw new Error("source_diversity_not_proven");
      }
      evidence.coding_run = await api.post(`/api/research-validity/${projectId}/coding-runs`, {
        // The proof pass must code raw source evidence units. Approved tasks are
        // recorded as review context, but uploaded source evidence is normally
        // project/document-scoped, not duplicated onto every task.
        task_id: null,
        evidence_unit_ids: selectedUnits.map((unit) => unit.id),
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
      await validateCodingRun({
        api,
        projectId,
        codingRun: evidence.coding_run,
        requiredCoders,
        requiredDonorRoutes,
        expectedEvidenceUnits: selectedEvidenceUnits,
        featureResults,
        blockers,
        logger,
      });
    } catch (error) {
      evidence.errors.push({ step: "coding_run", error: error.message });
      const canRecoverLongRequest = /fetch failed|headers? timeout|terminated/i.test(error.message);
      const recoveredRun = canRecoverLongRequest
        ? await recoverLatestCodingRun({
          api,
          projectId,
          logger,
          notBefore: codingRequestStartedAt,
        })
        : null;
      if (recoveredRun) {
        evidence.coding_run = recoveredRun;
        logger.action("research_spine.coding_run_recovered", {
          ok: true,
          error: error.message,
          result: preview(recoveredRun),
        });
        await validateCodingRun({
          api,
          projectId,
          codingRun: evidence.coding_run,
          requiredCoders,
          requiredDonorRoutes,
          expectedEvidenceUnits: selectedEvidenceUnits,
          featureResults,
          blockers,
          logger,
        });
      } else {
        if (requiredCoders >= 2
          && !["source_diversity_not_proven", "research_validity_contract_unavailable"].includes(error.message)) {
          blockers.push(`Research Spine coding validation did not complete: ${error.message}`);
        }
        if (![
          "source_diversity_not_proven",
          "research_validity_contract_unavailable",
        ].includes(error.message)) {
          logger.issue({
            area: "research-spine",
            severity: "medium",
            title: "Research Spine coding validation did not complete",
            detail: error.message,
          });
        }
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
  featureResults.multiModelResearchSpineValidation = Boolean(
    evidence.contract_loaded && featureResults.multiModelResearchSpineValidation,
  );
  featureResults.ensembleCodingValidation = Boolean(
    evidence.contract_loaded && evidence.coding_run && featureResults.ensembleCodingValidation,
  );
  featureResults.codingValidation = Boolean(evidence.contract_loaded && evidence.coding_run)
    && featureResults.multiModelResearchSpineValidation;
  const requiresCurrentCodingRunTraceability = Boolean(
    codingValidationEnabled && Number(codingValidationLimit || 0) > 0,
  );
  const traceabilityCodingRun = requiresCurrentCodingRunTraceability
    ? assessTraceabilityCodingRunBinding(evidence.traceability, evidence.coding_run)
    : {
        ok: true,
        run_id: String(evidence.coding_run?.id || "").trim(),
        run_listed: null,
        expected_application_count: Number(evidence.coding_run?.code_application_count ?? 0),
        application_count: null,
        decision_count: null,
        edge_count: null,
        application_evidence_ok: null,
        edge_evidence_ok: null,
      };
  evidence.traceability_coding_run = traceabilityCodingRun;
  featureResults.researchSpineTraceability = Boolean(
    evidence.summary
    && typeof evidence.summary === "object"
    && Object.prototype.hasOwnProperty.call(evidence.summary, "report_gate")
    && Object.prototype.hasOwnProperty.call(evidence.summary, "evidence_unit_count")
    && Object.prototype.hasOwnProperty.call(evidence.summary, "coding_run_count")
    && traceabilityCodingRun.ok,
  );
  featureResults.ragTraceabilityEvidence = Boolean(
    evidence.traceability
    && typeof evidence.traceability === "object"
    && evidence.traceability.contract
    && typeof evidence.traceability.contract === "object"
    && evidence.traceability.contract.graph_role === "synthesis_and_traceability"
    && evidence.traceability.contract.promotion_rule
    && traceabilityCodingRun.ok,
  );
  if (requiresCurrentCodingRunTraceability && !traceabilityCodingRun.ok) {
    logger.issue({
      area: "research-spine",
      severity: "high",
      title: "Research Spine traceability was not bound to the current coding run",
      detail: "Project-level traceability was present, but it did not expose the current coding run with its source-grounded application and evidence-graph records.",
      evidence: traceabilityCodingRun,
    });
  }
  featureResults.telemetryEvidence = Boolean(
    evidence.telemetry_audit
    && typeof evidence.telemetry_audit === "object"
    && evidence.telemetry_audit.status === "ok"
    && evidence.telemetry_audit.content_policy
    && evidence.telemetry_audit.protected_fields,
  );
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
