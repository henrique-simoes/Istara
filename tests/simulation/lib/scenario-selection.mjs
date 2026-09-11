/**
 * Fail-closed scenario-selection guards for the simulation runner (W1
 * readiness-core, blockers B1/N-R1).
 *
 * `run.mjs` imports these so the guards stay unit-testable without importing
 * the runner itself (which launches browsers and services on import).
 */

/**
 * Throw when the registry contains a duplicated scenario id. `findDuplicates`
 * is injected (the registry's `findDuplicateScenarioIds`) so the guard is
 * provably wired to the real detector, not a reimplementation.
 */
export function assertNoDuplicateScenarioIds(scenarioFiles, findDuplicates) {
  const duplicates = findDuplicates(scenarioFiles);
  if (duplicates.length > 0) {
    throw new Error(
      `Duplicate scenario id(s) in the registry: ${duplicates.join(", ")} — ` +
        `the selection must be a bijection`
    );
  }
}

/**
 * Throw when a `--scenario` / `--scenarios` request matches no loaded
 * scenario. Substring selection keeps working for real ids; only a request
 * that selects the empty set fails.
 */
export function assertRequestedScenariosMatch(
  scenarios,
  { singleScenario = null, multiScenarios = null } = {}
) {
  const requested = [
    ...(singleScenario ? [singleScenario] : []),
    ...(multiScenarios || []),
  ];
  if (requested.length === 0) return;
  const unmatched = requested.filter(
    (request) => !scenarios.some((scenario) => scenario.id.includes(request))
  );
  if (unmatched.length > 0) {
    throw new Error(
      `Requested scenario id(s) matched nothing: ${unmatched.join(", ")} — ` +
        `available ids: ${scenarios.map((scenario) => scenario.id).join(",")}`
    );
  }
}
