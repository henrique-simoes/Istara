import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dirname, "..", "..", "..");

test("StatusBar exposes a persistent accessible system connection status", () => {
  const source = readFileSync(join(root, "frontend/src/components/layout/StatusBar.tsx"), "utf8");
  assert.match(source, /role="status"/);
  assert.match(source, /aria-live="polite"/);
    assert.match(source, /System status:/);
    assert.match(source, /Connected · Live updates/);
    assert.match(source, /<span>\{connectionState\}<\/span>/);
  });
