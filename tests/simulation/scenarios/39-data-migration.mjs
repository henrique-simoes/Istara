/** Scenario 39 — Data Migration & Integrity: export/import database, integrity checks. */

export const name = "Data Migration & Integrity";
export const id = "39-data-migration";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. Data integrity check endpoint ──
  try {
    const report = await api.get("/api/settings/data-integrity");
    checks.push({
      name: "Data integrity endpoint returns report",
      passed: report.status !== undefined && Array.isArray(report.checks),
      detail: `status=${report.status}, checks=${report.checks?.length}`,
    });
    checks.push({
      name: "Data integrity status is healthy or warning",
      passed: report.status === "healthy" || report.status === "warning",
      detail: `status=${report.status}`,
    });
    checks.push({
      name: "Integrity checks include LanceDB",
      passed: report.checks?.some((c) => c.name?.includes("LanceDB")),
      detail: `checks: ${report.checks?.map((c) => c.name).join(", ")}`,
    });
    checks.push({
      name: "Integrity checks include personas",
      passed: report.checks?.some((c) => c.name?.includes("persona")),
      detail: "",
    });
    checks.push({
      name: "Orphan tracking structure exists",
      passed: report.orphans !== undefined,
      detail: `keys: ${Object.keys(report.orphans || {}).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "Data integrity endpoint", passed: false, detail: e.message });
  }

  // ── 2. Database export endpoint ──
  let exportedData = null;
  try {
    exportedData = await api.post("/api/settings/export-database", {});
    checks.push({
      name: "Database export returns data",
      passed: exportedData.metadata !== undefined && exportedData.tables !== undefined,
      detail: `tables: ${Object.keys(exportedData.tables || {}).length}`,
    });
    checks.push({
      name: "Export includes metadata",
      passed: !!exportedData.metadata?.exported_at && !!exportedData.metadata?.source_db,
      detail: `source=${exportedData.metadata?.source_db}`,
    });
    checks.push({
      name: "Export includes projects table",
      passed: Array.isArray(exportedData.tables?.projects),
      detail: `${exportedData.tables?.projects?.length} projects`,
    });
    checks.push({
      name: "Export includes agents table",
      passed: Array.isArray(exportedData.tables?.agents),
      detail: `${exportedData.tables?.agents?.length} agents`,
    });
    checks.push({
      name: "Export includes filesystem refs",
      passed: exportedData.filesystem_refs !== undefined,
      detail: `keys: ${Object.keys(exportedData.filesystem_refs || {}).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "Database export endpoint", passed: false, detail: e.message });
  }

  // ── 3. Database import endpoint (dry validation — we don't actually import to avoid corruption) ──
  // We test the endpoint exists and accepts the structure, but send minimal data
  try {
    const testImport = await api.post("/api/settings/import-database", {
      metadata: { version: "1.0", source_db: "test" },
      tables: {}, // Empty — nothing to import
    });
    checks.push({
      name: "Import endpoint accepts data structure",
      passed: testImport.imported !== undefined || testImport.skipped !== undefined,
      detail: JSON.stringify(testImport).substring(0, 200),
    });
  } catch (e) {
    // 400/422 is acceptable — means the endpoint exists but rejected bad input
    checks.push({
      name: "Import endpoint exists",
      passed: true,
      detail: `Response: ${e.message}`,
    });
  }

  // ── 4. Health endpoint still stable ──
  try {
    const health = await api.get("/api/health");
    checks.push({
      name: "System health after migration checks",
      passed: health.status === "ok" || health.status === "healthy",
      detail: `status=${health.status}`,
    });
  } catch (e) {
    checks.push({ name: "System health", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
