/**
 * Per-variant obligation ledger for auth-adjacent simulation scenarios
 * (remediation plan W1.5-W1.6, blockers B4/B5 — testing-to-main-remediation-20260909).
 *
 * A scenario-level pass/fail boolean hides required cells (e.g. role variants
 * that were silently never driven). This module makes every required cell a
 * machine-checkable row with a stable `variant_id`, an expectation, a result,
 * the reason/capability when the cell could not run, and artifact references.
 *
 * Aggregation contract (B5): a scenario cannot aggregate to pass while a
 * required cell is missing, failed, or invalidly unavailable. `finalize()`
 * therefore emits one row per cell plus a trailing enforcement row, so the
 * runner's `failed > 0 => FAIL` rule enforces the contract without trusting
 * the scenario's own arithmetic.
 *
 * not_runnable validity (plan W1/W5):
 *   - a `not_runnable` cell must name the specific capability that is missing;
 *   - a credential-free required cell may NEVER be `not_runnable` — a named
 *     capability cannot make a credential-free obligation unavailable, so the
 *     cell is recorded as a failure instead;
 *   - a genuinely live-only cell (credentialFree: false) with a named
 *     capability is a valid unavailable cell: it is recorded with
 *     `result=not_runnable` in its machine-readable detail and does not block
 *     the aggregate. The row's `passed` flag means "obligation accounting is
 *     valid", never "the variant ran and passed".
 */

export const VARIANT_RESULTS = Object.freeze(["pass", "fail", "not_runnable"]);

function cellCheckName(scenarioId, variantId, expectation) {
  return `[${scenarioId}] variant ${variantId} — ${expectation}`;
}

export function createVariantLedger(scenarioId, obligations) {
  if (!scenarioId || typeof scenarioId !== "string") {
    throw new Error("createVariantLedger: scenarioId is required");
  }
  if (!Array.isArray(obligations) || obligations.length === 0) {
    throw new Error(`createVariantLedger(${scenarioId}): at least one obligation must be declared`);
  }

  const declared = new Map();
  for (const obligation of obligations) {
    if (!obligation || typeof obligation.variantId !== "string" || !obligation.variantId.trim()) {
      throw new Error(`createVariantLedger(${scenarioId}): every obligation needs a non-empty variantId`);
    }
    if (typeof obligation.expectation !== "string" || !obligation.expectation.trim()) {
      throw new Error(`createVariantLedger(${scenarioId}): obligation ${obligation.variantId} needs an expectation`);
    }
    if (declared.has(obligation.variantId)) {
      throw new Error(`createVariantLedger(${scenarioId}): duplicate variantId ${obligation.variantId}`);
    }
    declared.set(obligation.variantId, {
      variantId: obligation.variantId,
      expectation: obligation.expectation,
      // Default: the cell is a credential-free release obligation. A live-only
      // cell must opt out explicitly AND name its governed live capability.
      credentialFree: obligation.credentialFree !== false,
    });
  }

  const results = new Map();

  function record({ variantId, result, detail = "", artifacts = [] }) {
    if (!declared.has(variantId)) {
      throw new Error(`createVariantLedger(${scenarioId}): ${variantId} is not a declared obligation`);
    }
    if (!VARIANT_RESULTS.includes(result)) {
      throw new Error(
        `createVariantLedger(${scenarioId}): ${variantId} result must be one of ${VARIANT_RESULTS.join("|")}`,
      );
    }
    if (result === "not_runnable" && !(typeof detail === "string" && detail.trim())) {
      throw new Error(
        `createVariantLedger(${scenarioId}): ${variantId} not_runnable requires a reason in detail`,
      );
    }
    results.set(variantId, {
      variantId,
      result,
      detail: typeof detail === "string" ? detail : String(detail),
      artifacts: Array.isArray(artifacts) ? artifacts.map(String) : [],
    });
  }

  function finalize() {
    const rows = [];
    const violations = [];
    let passedCells = 0;
    let validUnavailable = 0;
    let failedCells = 0;

    for (const obligation of declared.values()) {
      const name = cellCheckName(scenarioId, obligation.variantId, obligation.expectation);
      const cell = results.get(obligation.variantId);
      if (!cell) {
        violations.push(`${obligation.variantId}: required cell never exercised`);
        rows.push({
          name,
          passed: false,
          detail: "result=missing — obligation declared but no result was recorded (cannot hide a required cell)",
        });
        continue;
      }
      const artifactSuffix = cell.artifacts.length > 0 ? `; artifacts=${cell.artifacts.join(", ")}` : "";
      if (cell.result === "pass") {
        passedCells += 1;
        rows.push({ name, passed: true, detail: `result=pass; ${cell.detail}${artifactSuffix}` });
        continue;
      }
      if (cell.result === "fail") {
        failedCells += 1;
        rows.push({ name, passed: false, detail: `result=fail; ${cell.detail}${artifactSuffix}` });
        continue;
      }
      // result === "not_runnable"
      const capability = extractCapability(cell.detail);
      if (!capability) {
        failedCells += 1;
        violations.push(`${obligation.variantId}: invalid not_runnable — no capability named`);
        rows.push({
          name,
          passed: false,
          detail: `result=not_runnable-invalid — a cell may only be unavailable when it names the specific missing capability; ${cell.detail}${artifactSuffix}`,
        });
        continue;
      }
      if (obligation.credentialFree) {
        failedCells += 1;
        violations.push(
          `${obligation.variantId}: invalid not_runnable — credential-free required cell (capability ${capability} cannot excuse it)`,
        );
        rows.push({
          name,
          passed: false,
          detail: `result=not_runnable-invalid — a credential-free required cell may not be not_runnable (capability ${capability}); ${cell.detail}${artifactSuffix}`,
        });
        continue;
      }
      // Valid unavailable: live-only cell with its governed capability named.
      validUnavailable += 1;
      rows.push({
        name,
        passed: true,
        detail: `result=not_runnable (capability: ${capability}) — validly unavailable live-only cell, does not block aggregate; ${cell.detail}${artifactSuffix}`,
      });
    }

    const enforcementPassed = violations.length === 0 && failedCells === 0;
    rows.push({
      name: `[${scenarioId}] obligation ledger complete (${declared.size} required cells)`,
      passed: enforcementPassed,
      detail:
        `pass=${passedCells} valid_not_runnable=${validUnavailable} fail=${failedCells} missing=${declared.size - results.size}` +
        (violations.length > 0 ? `; violations: ${violations.join("; ")}` : "; no required cell hidden by the aggregate"),
    });
    return rows;
  }

  return { record, finalize, declaredVariantIds: () => [...declared.keys()] };
}

/** Extract `capability: <name>` from a not_runnable detail string, if present. */
function extractCapability(detail) {
  const match = /capability:\s*([^;]+)/i.exec(detail || "");
  return match ? match[1].trim() : null;
}
