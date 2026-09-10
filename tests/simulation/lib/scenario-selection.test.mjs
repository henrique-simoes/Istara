import assert from "node:assert/strict";
import test from "node:test";

import {
  findDuplicateScenarioIds,
  scenarioFiles,
} from "./scenario-registry.mjs";
import { resolveJourneySelection } from "./journey-selection.mjs";
import {
  assertNoDuplicateScenarioIds,
  assertRequestedScenariosMatch,
} from "./scenario-selection.mjs";

const SCENARIOS = [
  { id: "01-health-check", name: "health", run: async () => ({}) },
  { id: "83-chat-model-controls", name: "chat", run: async () => ({}) },
];

test("duplicate detector is wired to the real registry check (N-R1)", () => {
  // The live registry must have zero duplicates — and the guard must be
  // invoked against the real detector, not a reimplementation.
  assertNoDuplicateScenarioIds(scenarioFiles, findDuplicateScenarioIds);
  assert.deepEqual(findDuplicateScenarioIds(scenarioFiles), []);
});

test("registry duplicates fail closed instead of double-running", () => {
  assert.throws(
    () =>
      assertNoDuplicateScenarioIds(
        ["01-health-check", "01-health-check"],
        findDuplicateScenarioIds
      ),
    /Duplicate scenario id\(s\) in the registry: 01-health-check/
  );
});

test("requested ids use substring selection for real ids", () => {
  assertRequestedScenariosMatch(SCENARIOS, { singleScenario: "01" });
  assertRequestedScenariosMatch(SCENARIOS, { multiScenarios: ["01", "83"] });
  assertRequestedScenariosMatch(SCENARIOS, {});
  assertRequestedScenariosMatch(SCENARIOS, {
    singleScenario: null,
    multiScenarios: null,
  });
});

test("a requested id that matches nothing fails closed (no green empty run)", () => {
  assert.throws(
    () => assertRequestedScenariosMatch(SCENARIOS, { singleScenario: "999-nope" }),
    /Requested scenario id\(s\) matched nothing: 999-nope/
  );
  assert.throws(
    () =>
      assertRequestedScenariosMatch(SCENARIOS, {
        multiScenarios: ["01", "999-nope"],
      }),
    /Requested scenario id\(s\) matched nothing: 999-nope/
  );
});

test("duplicates inside the registry fail the CI selection resolve step", () => {
  const selection = resolveJourneySelection({
    registered: ["01-health-check", "01-health-check"],
    smoke: ["01-health-check"],
    extra: [],
    scope: "smoke",
  });
  assert.ok(
    selection.errors.some((e) =>
      e.includes('duplicate scenario id "01-health-check" in the registry')
    )
  );
});
