import test from "node:test";
import assert from "node:assert/strict";

import { buildRegistrationPayload } from "./heartbeat.mjs";

test("relay registration includes available RAM from the first payload", () => {
  const payload = buildRegistrationPayload({
    stats: {
      hostname: "donor-workstation",
      ram_total_gb: 64,
      ram_available_gb: 41.5,
      cpu_cores: 16,
      gpu_name: "RTX",
      gpu_vram_mb: 24576,
    },
    modelProbe: {
      ok: true,
      models: ["google/gemma-4-e4b"],
      modelCapabilities: {
        "google/gemma-4-e4b": { supports_tools: true },
      },
    },
    providerType: "lmstudio",
    providerHost: "http://localhost:1234",
    userId: "authenticated",
    connectionString: "rcl_signed_compute_donation",
  });

  assert.equal(payload.type, "register");
  assert.equal(payload.ram_total_gb, 64);
  assert.equal(payload.ram_available_gb, 41.5);
  assert.equal(payload.cpu_cores, 16);
  assert.deepEqual(payload.loaded_models, ["google/gemma-4-e4b"]);
  assert.equal(payload.health_error, "");
  assert.equal(payload.connection_string, "rcl_signed_compute_donation");
});
