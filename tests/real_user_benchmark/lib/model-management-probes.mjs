/**
 * Pi Model Management + Petals bridge probes for the real-user benchmark.
 *
 * Covers what the donor-sandbox layer cannot: the server-side pipelines that
 * make a donated model usable — model catalog, endpoint resolution inputs,
 * model warnings, strict-routing state, and the Petals bridge
 * (consent/status/node-scoped completions live behind admin auth).
 *
 * Live calls are isolated in `exerciseModelManagement`; everything else is
 * pure and unit-tested. Plan-only mode never calls this module's runner.
 */

export function catalogEntryForEndpoint(catalog, endpointId) {
  const id = String(endpointId || "").trim();
  if (!id || !Array.isArray(catalog)) return null;
  return catalog.find((entry) => String(entry?.endpoint_id || entry?.id || "") === id) || null;
}

export function donorEndpointIdsInCatalog(catalog, endpointIds = []) {
  const ids = [...new Set(endpointIds.map((id) => String(id || "").trim()).filter(Boolean))];
  const covered = [];
  const missing = [];
  for (const id of ids) {
    if (catalogEntryForEndpoint(catalog, id)) covered.push(id);
    else missing.push(id);
  }
  return { requested: ids, covered, missing, ok: missing.length === 0 };
}

export function summarizeModelWarnings(warnings) {
  const list = Array.isArray(warnings) ? warnings : Array.isArray(warnings?.warnings) ? warnings.warnings : [];
  const bySeverity = {};
  for (const warning of list) {
    const severity = String(warning?.severity || "info").toLowerCase();
    bySeverity[severity] = (bySeverity[severity] || 0) + 1;
  }
  return { count: list.length, by_severity: bySeverity };
}

export async function exerciseModelManagement({
  api,
  projectId,
  logger,
  featureResults,
  donorEndpointIds = [],
  timeoutMs = 15000,
}) {
  const evidence = {
    project_id: projectId || "",
    catalog_loaded: false,
    catalog_size: 0,
    donor_endpoint_coverage: null,
    warnings: null,
    petals_status: null,
    errors: [],
  };
  const record = (step, ok, extra = {}) => {
    logger.action("model_management.probe", { step, ok, ...extra });
    if (!ok && extra.error) evidence.errors.push({ step, error: extra.error });
  };

  let catalog = [];
  try {
    const response = await api.get("/api/chat/model-catalog", { timeoutMs });
    catalog = Array.isArray(response) ? response : Array.isArray(response?.endpoints) ? response.endpoints : [];
    evidence.catalog_loaded = true;
    evidence.catalog_size = catalog.length;
    record("catalog", true, { size: catalog.length });
  } catch (error) {
    record("catalog", false, { error: error.message });
  }

  if (donorEndpointIds.length > 0) {
    evidence.donor_endpoint_coverage = donorEndpointIdsInCatalog(catalog, donorEndpointIds);
    record("donor_coverage", evidence.donor_endpoint_coverage.ok, {
      covered: evidence.donor_endpoint_coverage.covered,
      missing: evidence.donor_endpoint_coverage.missing,
    });
    if (featureResults && evidence.catalog_loaded) {
      featureResults.piManagedEndpointCatalogued = evidence.donor_endpoint_coverage.ok;
    }
  }

  try {
    const response = await api.get("/api/compute/model-warnings", { timeoutMs });
    evidence.warnings = summarizeModelWarnings(response?.warnings || response);
    record("warnings", true, evidence.warnings);
  } catch (error) {
    record("warnings", false, { error: error.message });
  }

  try {
    const response = await api.get("/api/petals/v1/status", { timeoutMs });
    evidence.petals_status = {
      reachable: true,
      node_count: Array.isArray(response?.nodes) ? response.nodes.length : 0,
    };
    record("petals_status", true, evidence.petals_status);
    if (featureResults) featureResults.petalsBridgeStatus = true;
  } catch (error) {
    // Bridge disabled or admin-only: recorded, not fatal. Fail-closed paths
    // (503 petals_unavailable) are themselves valid evidence when present.
    evidence.petals_status = { reachable: false, reason: error.message };
    record("petals_status", false, { error: error.message });
  }

  logger.writeJson("model-management-probes.json", evidence);
  return evidence;
}
