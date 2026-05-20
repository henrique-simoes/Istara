import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { IstaraApiClient } from "./api-client.mjs";

test("auth fallback does not report local env password mismatch as a product issue", async () => {
  const repoRoot = mkdtempSync(join(tmpdir(), "istara-rub-auth-"));
  const fakePython = join(repoRoot, "fake-python");
  const originalFetch = globalThis.fetch;
  const originalEnv = {
    PYTHON: process.env.PYTHON,
    ISTARA_E2E_ALLOW_LOCAL_TOKEN: process.env.ISTARA_E2E_ALLOW_LOCAL_TOKEN,
    ISTARA_BENCHMARK_ADMIN_PASSWORD: process.env.ISTARA_BENCHMARK_ADMIN_PASSWORD,
    ISTARA_ADMIN_PASSWORD: process.env.ISTARA_ADMIN_PASSWORD,
    ADMIN_PASSWORD: process.env.ADMIN_PASSWORD,
  };
  const actions = [];
  const issues = [];

  try {
    mkdirSync(join(repoRoot, "backend"), { recursive: true });
    writeFileSync(join(repoRoot, "backend", ".env"), "ADMIN_PASSWORD=stale-local-password\n");
    writeFileSync(fakePython, "#!/bin/sh\nprintf 'fake.local.token\\n'\n");
    chmodSync(fakePython, 0o755);

    process.env.PYTHON = fakePython;
    process.env.ISTARA_E2E_ALLOW_LOCAL_TOKEN = "1";
    delete process.env.ISTARA_BENCHMARK_ADMIN_PASSWORD;
    delete process.env.ISTARA_ADMIN_PASSWORD;
    delete process.env.ADMIN_PASSWORD;

    globalThis.fetch = async () => new Response(
      JSON.stringify({ detail: "Invalid username or password." }),
      { status: 401, headers: { "content-type": "application/json" } },
    );

    const client = new IstaraApiClient({
      apiBase: "http://localhost:8000",
      repoRoot,
      logger: {
        action: (step, payload) => actions.push({ step, payload }),
        issue: (issue) => issues.push(issue),
      },
    });

    const result = await client.authenticate();

    assert.equal(result.ok, true);
    assert.equal(result.method, "local-signed-token");
    assert.equal(issues.length, 0);
    assert.equal(actions.some((entry) => entry.step === "auth.password_failed_using_local_token_fallback"), true);
  } finally {
    globalThis.fetch = originalFetch;
    for (const [key, value] of Object.entries(originalEnv)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    rmSync(repoRoot, { recursive: true, force: true });
  }
});
