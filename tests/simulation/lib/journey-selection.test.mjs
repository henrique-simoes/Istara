import assert from "node:assert/strict";
import test from "node:test";

import { releaseObligationIds, scenarioFiles } from "./scenario-registry.mjs";
import { explainSelection, resolveJourneySelection } from "./journey-selection.mjs";

const REGISTERED = [...scenarioFiles];
const SMOKE = ["01-health-check", "02-onboarding", "03-project-setup", "09-navigation-search", "32-auth-flow", "67-auth-enforcement", "81-project-settings"];

test("selection is a bijection: every registered scenario is selected once or in the not_runnable ledger", () => {
  const selection = resolveJourneySelection({ registered: REGISTERED, smoke: SMOKE, extra: [], scope: "full" });

  assert.deepEqual(selection.errors, []);
  const accounted = [...selection.selected, ...selection.notRunnable.map((entry) => entry.scenario)].sort();
  assert.deepEqual(accounted, [...REGISTERED].sort());
  assert.equal(new Set(accounted).size, accounted.length, "no scenario may be accounted twice");
  assert.equal(selection.registeredCount, REGISTERED.length);
  assert.equal(selection.provenCount, SMOKE.length);
});

test("smoke scope selects exactly the smoke list; full scope selects smoke plus proven-extra", () => {
  const extra = ["82-quality-dashboard"];
  const smokeRun = resolveJourneySelection({ registered: REGISTERED, smoke: SMOKE, extra: [], scope: "smoke" });
  assert.deepEqual(smokeRun.selected, SMOKE);

  const fullRun = resolveJourneySelection({ registered: REGISTERED, smoke: SMOKE, extra, scope: "full" });
  assert.deepEqual(fullRun.selected, [...SMOKE, ...extra]);
});

test("unknown scenario ids fail closed before execution", () => {
  const selection = resolveJourneySelection({
    registered: REGISTERED,
    smoke: [...SMOKE, "999-does-not-exist"],
    extra: [],
    scope: "full",
  });
  assert.ok(selection.errors.some((e) => e.includes("unknown scenario id \"999-does-not-exist\"")));
});

test("duplicate ids inside a list or across lists fail closed (no silent de-duplication)", () => {
  const within = resolveJourneySelection({
    registered: REGISTERED,
    smoke: [...SMOKE, "01-health-check"],
    extra: [],
    scope: "full",
  });
  assert.ok(within.errors.some((e) => e.includes("duplicate scenario id \"01-health-check\" in smoke")));

  const across = resolveJourneySelection({
    registered: REGISTERED,
    smoke: SMOKE,
    extra: ["01-health-check"],
    scope: "full",
  });
  assert.ok(across.errors.some((e) => e.includes('duplicate scenario id "01-health-check" across smoke and proven-extra')));
});

test("release obligations 82/83/84 are named individually, never by the generic reason", () => {
  const selection = resolveJourneySelection({ registered: REGISTERED, smoke: SMOKE, extra: [], scope: "full" });

  assert.equal(selection.releaseObligationsPending, releaseObligationIds.length);
  for (const id of releaseObligationIds) {
    const entry = selection.notRunnable.find((e) => e.scenario === id);
    assert.ok(entry, `${id} must appear in the not_runnable ledger while unproven`);
    assert.equal(entry.release_obligation, true);
    assert.ok(entry.reason.includes("credential-free release obligation"));
    assert.ok(!entry.reason.includes(GENERIC_REASON_PLACEHOLDER), "reason must not be the generic crowd string");
  }
  // All other unproven scenarios keep the honest documented generic reason.
  const others = selection.notRunnable.filter((e) => !e.release_obligation);
  assert.ok(others.length > 0);
  for (const entry of others) assert.ok(entry.reason.includes("dated run evidence"));
});

const GENERIC_REASON_PLACEHOLDER = "__never_matches__";

test("an empty selected scope fails closed in both scopes", () => {
  const full = resolveJourneySelection({ registered: REGISTERED, smoke: [], extra: [], scope: "full" });
  assert.ok(full.errors.some((e) => e.includes("no-journeys-selected — the full proven scope is empty")));

  const smoke = resolveJourneySelection({ registered: REGISTERED, smoke: [], extra: [], scope: "smoke" });
  assert.ok(smoke.errors.some((e) => e.includes("no-journeys-selected — the smoke scope is empty")));
});

test("an invalid scope name is an error, not a fallback", () => {
  const selection = resolveJourneySelection({ registered: REGISTERED, smoke: SMOKE, extra: [], scope: "everything" });
  assert.ok(selection.errors.some((e) => e.includes("unknown journey scope")));
});

test("malformed journey lists are errors, not silent selections", () => {
  const selection = resolveJourneySelection({ registered: REGISTERED, smoke: "01-health-check", extra: null, scope: "full" });
  assert.ok(selection.errors.some((e) => e.includes("must be string arrays")));
});

test("every declared release obligation is a registered scenario", () => {
  const registered = new Set(REGISTERED);
  for (const id of releaseObligationIds) {
    assert.ok(registered.has(id), `${id} must exist in scenarioFiles`);
  }
});

test("explainSelection reports the full accounting on one line", () => {
  const selection = resolveJourneySelection({ registered: REGISTERED, smoke: SMOKE, extra: [], scope: "full" });
  const line = explainSelection(selection);
  assert.match(line, /registered=\d+ proven=7 selected=7 not_runnable=\d+ release_obligations_pending=3/);
});
