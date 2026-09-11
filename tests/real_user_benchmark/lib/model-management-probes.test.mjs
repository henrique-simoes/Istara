import { test } from "node:test";
import assert from "node:assert/strict";

import {
  catalogEntryForEndpoint,
  donorEndpointIdsInCatalog,
  summarizeModelWarnings,
} from "./model-management-probes.mjs";

test("catalogEntryForEndpoint matches endpoint_id or id", () => {
  const catalog = [{ endpoint_id: "pi-deepseek-default" }, { id: "legacy-x" }];
  assert.equal(catalogEntryForEndpoint(catalog, "pi-deepseek-default")?.endpoint_id, "pi-deepseek-default");
  assert.equal(catalogEntryForEndpoint(catalog, "legacy-x")?.id, "legacy-x");
  assert.equal(catalogEntryForEndpoint(catalog, "missing"), null);
  assert.equal(catalogEntryForEndpoint(null, "x"), null);
});

test("donorEndpointIdsInCatalog reports covered vs missing", () => {
  const catalog = [{ endpoint_id: "a" }];
  const result = donorEndpointIdsInCatalog(catalog, ["a", "b", "a"]);
  assert.deepEqual(result.covered, ["a"]);
  assert.deepEqual(result.missing, ["b"]);
  assert.equal(result.ok, false);
  assert.equal(donorEndpointIdsInCatalog(catalog, ["a"]).ok, true);
});

test("summarizeModelWarnings counts by severity", () => {
  const summary = summarizeModelWarnings([{ severity: "high" }, { severity: "HIGH" }, {}]);
  assert.equal(summary.count, 3);
  assert.deepEqual(summary.by_severity, { high: 2, info: 1 });
});
