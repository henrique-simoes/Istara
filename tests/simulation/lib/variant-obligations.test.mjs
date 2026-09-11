import assert from "node:assert/strict";
import test from "node:test";

import { VARIANT_RESULTS, createVariantLedger } from "./variant-obligations.mjs";

const CELLS = [
  { variantId: "role=admin", expectation: "admin drives the journey" },
  { variantId: "role=researcher", expectation: "researcher reads the view" },
  { variantId: "role=viewer", expectation: "viewer reads the view" },
  { variantId: "role=stranger", expectation: "stranger is held at login" },
];

test("every declared cell emits a machine-checkable row with a stable variant id", () => {
  const ledger = createVariantLedger("82-quality-dashboard", CELLS);
  ledger.record({ variantId: "role=admin", result: "pass", detail: "sections rendered" });
  ledger.record({ variantId: "role=researcher", result: "pass", detail: "ok" });
  ledger.record({ variantId: "role=viewer", result: "pass", detail: "ok" });
  ledger.record({ variantId: "role=stranger", result: "pass", detail: "login screen" });

  const rows = ledger.finalize();
  for (const cell of CELLS) {
    const row = rows.find((r) => r.name.includes(`variant ${cell.variantId}`));
    assert.ok(row, `missing row for ${cell.variantId}`);
    assert.ok(row.name.includes(cell.expectation), "row must carry the expectation");
    assert.ok(row.detail.includes("result=pass"));
  }
  const enforcement = rows[rows.length - 1];
  assert.equal(enforcement.name, "[82-quality-dashboard] obligation ledger complete (4 required cells)");
  assert.equal(enforcement.passed, true);
});

test("a missing required cell fails the aggregate (B5: cells cannot hide behind scenario status)", () => {
  const ledger = createVariantLedger("83-chat-model-controls", CELLS);
  ledger.record({ variantId: "role=admin", result: "pass", detail: "ok" });
  // researcher / viewer / stranger never recorded.

  const rows = ledger.finalize();
  assert.equal(rows[rows.length - 1].passed, false);
  assert.ok(rows[rows.length - 1].detail.includes("missing=3"));
  for (const id of ["role=researcher", "role=viewer", "role=stranger"]) {
    const row = rows.find((r) => r.name.includes(`variant ${id}`));
    assert.equal(row.passed, false);
    assert.ok(row.detail.includes("result=missing"));
  }
});

test("a failed cell fails the aggregate", () => {
  const ledger = createVariantLedger("84-token-session-lifecycle", CELLS);
  for (const cell of CELLS) {
    ledger.record({
      variantId: cell.variantId,
      result: cell.variantId === "role=viewer" ? "fail" : "pass",
      detail: "driven",
    });
  }
  const rows = ledger.finalize();
  assert.equal(rows[rows.length - 1].passed, false);
  const viewerRow = rows.find((r) => r.name.includes("variant role=viewer"));
  assert.equal(viewerRow.passed, false);
  assert.ok(viewerRow.detail.includes("result=fail"));
});

test("a not_runnable cell without a named capability is invalid and fails the aggregate", () => {
  const ledger = createVariantLedger("82-quality-dashboard", CELLS);
  ledger.record({ variantId: "role=admin", result: "pass", detail: "ok" });
  ledger.record({ variantId: "role=researcher", result: "pass", detail: "ok" });
  ledger.record({ variantId: "role=viewer", result: "pass", detail: "ok" });
  ledger.record({ variantId: "role=stranger", result: "not_runnable", detail: "could not run right now" });

  const rows = ledger.finalize();
  assert.equal(rows[rows.length - 1].passed, false);
  const strangerRow = rows.find((r) => r.name.includes("variant role=stranger"));
  assert.equal(strangerRow.passed, false);
  assert.ok(strangerRow.detail.includes("result=not_runnable-invalid"));
  assert.ok(rows[rows.length - 1].detail.includes("no capability named"));
});

test("a credential-free required cell may never be not_runnable, even with a capability named", () => {
  const ledger = createVariantLedger("82-quality-dashboard", CELLS);
  ledger.record({ variantId: "role=admin", result: "pass", detail: "ok" });
  ledger.record({ variantId: "role=researcher", result: "pass", detail: "ok" });
  ledger.record({ variantId: "role=viewer", result: "pass", detail: "ok" });
  ledger.record({
    variantId: "role=stranger",
    result: "not_runnable",
    detail: "capability: live provider lane — no accounts",
  });

  const rows = ledger.finalize();
  assert.equal(rows[rows.length - 1].passed, false);
  const strangerRow = rows.find((r) => r.name.includes("variant role=stranger"));
  assert.ok(strangerRow.detail.includes("credential-free required cell may not be not_runnable"));
});

test("a genuinely live-only cell with a named capability is validly unavailable and does not block the aggregate", () => {
  const ledger = createVariantLedger("84-token-session-lifecycle", [
    ...CELLS,
    { variantId: "live=voice-session", expectation: "voice custody", credentialFree: false },
  ]);
  for (const cell of CELLS) ledger.record({ variantId: cell.variantId, result: "pass", detail: "ok" });
  ledger.record({
    variantId: "live=voice-session",
    result: "not_runnable",
    detail: "capability: live-provider voice session (credential lane); no synthetic substitute",
  });

  const rows = ledger.finalize();
  const enforcement = rows[rows.length - 1];
  assert.equal(enforcement.passed, true);
  assert.ok(enforcement.detail.includes("valid_not_runnable=1"));
  const liveRow = rows.find((r) => r.name.includes("variant live=voice-session"));
  assert.equal(liveRow.passed, true); // obligation accounting is valid…
  assert.ok(liveRow.detail.includes("result=not_runnable")); // …and the detail still records the honest verdict
});

test("undeclared variants, unknown results, and duplicate declarations are construction errors", () => {
  const ledger = createVariantLedger("83-chat-model-controls", CELLS);
  assert.throws(() => ledger.record({ variantId: "role=root", result: "pass" }), /not a declared obligation/);
  assert.throws(
    () => ledger.record({ variantId: "role=admin", result: "skipped", detail: "x" }),
    /result must be one of/,
  );
  assert.throws(
    () => ledger.record({ variantId: "role=admin", result: "not_runnable", detail: "   " }),
    /requires a reason/,
  );
  assert.throws(
    () => createVariantLedger("83-chat-model-controls", [{ variantId: "role=admin", expectation: "a" }, { variantId: "role=admin", expectation: "b" }]),
    /duplicate variantId/,
  );
  assert.throws(() => createVariantLedger("83-chat-model-controls", []), /at least one obligation/);
});

test("artifact references ride the machine-readable detail", () => {
  const ledger = createVariantLedger("84-token-session-lifecycle", CELLS);
  ledger.record({
    variantId: "role=admin",
    result: "pass",
    detail: "custody held",
    artifacts: ["screenshots/84-admin-custody.png", "har/84-admin.har"],
  });
  const rows = ledger.finalize();
  const adminRow = rows.find((r) => r.name.includes("variant role=admin"));
  assert.ok(adminRow.detail.includes("artifacts=screenshots/84-admin-custody.png, har/84-admin.har"));
});

test("result vocabulary is exactly pass|fail|not_runnable", () => {
  assert.deepEqual([...VARIANT_RESULTS], ["pass", "fail", "not_runnable"]);
});
